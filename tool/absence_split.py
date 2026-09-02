#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6k 후속 (2) — **부스트 때문인가, 원래 좋은 건가** (2026-09-02 · 측정만).

🔴 앞 측정이 아직 두 가지를 섞고 있었다
  `tool/absence_selection.py` 는 **되돌린 GP 로만** 몬테카를로를 돌렸다. 그래서
  「Tyler Herro → c1 BN +4.7%p」가 나왔는데, 그 +4.7 안에 둘이 섞여 있다:

```
(a) 되돌린 GP 가 만든 **가짜 부스트**        ← 우리 삭감이 지운 것
(b) 그 교체가 **원래부터 좋았던 것**          ← 삭감과 무관. 코어 설계 얘기다
```
  13캣 사전선별에서 **되돌림 180개 vs 대조군 157개**였다 — 즉 대부분은 (b)다.
  그런데 몬테카를로를 (a) 쪽에만 돌렸으니 **표가 (a) 를 과대평가한다.**

무엇을 하나 — **같은 조합을 두 번 잰다**
```
wr_boost   그 선수의 GP 를 삭감 전으로 되돌리고 측정
wr_now     **현재 GP 그대로** 측정          ← 이게 빠져 있었다
base       코어 원안

(a) 삭감 효과 = wr_boost − wr_now     ← 「우리 삭감이 이 조합을 얼마나 낮게 보이게 했나」
(b) 원래 가치 = wr_now  − base        ← 「삭감과 무관하게 이 교체가 좋은가」
```

🔴 판정 (세 갈래 · 사전 등록 — docs/11 ⑪)
```
(a) 큼 · (b) 작음    → **삭감이 배제를 만들었다.** §6k 의 「0건」이 틀렸다
(a) 작음 · (b) 큼    → 삭감과 무관하다. **코어 설계 얘기이고 그건 네 번 닫혔다**
둘 다 작음            → 아무것도 아니다
```
⚠️ 어느 쪽이든 **반영하지 않는다.** 되돌린 GP 는 가짜다.
"""
import csv
import io
import json
import os
import random
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM        # noqa: E402
import matchup_sim as MS      # noqa: E402
import pos_elig as PE         # noqa: E402
import real_opponents as RO   # noqa: E402

SEED, FULL = 20261020, 4000
SCALE, MISS = 1.11, 20
BUDGET, RESERVE_FLOOR = 200, 4
PAIRED_SE = 0.0059
TOPN = 12


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def gp_of(fn):
    out = {}
    with io.open(BASE + "/data/stats_2025_26/bbref/" + fn, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                g = float(r["GP"])
            except (TypeError, ValueError):
                continue
            k = norm(r["name"])
            if k not in out or g > out[k]:
                out[k] = g
    return out


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
    g25, g26 = gp_of("2024-25_per_game.csv"), gp_of("2025-26_per_game.csv")
    REAL, _ = RO.build()
    B = CM.baselines()

    def cost(n):
        py = pl[n].get("prior_auction_price")
        return round(py * SCALE) if py is not None else max(1, pl[n]["my_max"])

    def sim(names):
        MS._URATE.clear()
        rs = [MS.simulate(list(names), REAL[m], random.Random(SEED), FULL) for m in REAL]
        MS._URATE.clear()
        return sum(r["weekly_win_rate"] for r in rs) / len(rs)

    inj = {n for n, p in pl.items() if p.get("injury_exclude")}
    heal = {}
    for n in pl:
        k = norm(n)
        if n in inj or n not in CM.F or k not in g25 or k not in g26:
            continue
        if g25[k] - g26[k] < MISS:
            continue
        if g25[k] > (CM.F[n].get("GP") or 0):
            heal[n] = g25[k]

    bases = {}
    for co in cj["cores"]:
        names = [s["candidates"][0]["name"] for s in co["slots"]]
        prices = [s["candidates"][0]["plan_price"] for s in co["slots"]]
        bases[co["id"]] = (names, prices, sim(names))

    # 후보 조합 — 되돌린 상태에서 13캣을 넘은 것 (앞 측정과 같은 기준)
    orig = {n: CM.F[n].get("GP") for n in heal}
    combos = []
    try:
        for n, h in heal.items():
            CM.F[n]["GP"] = h
            for co in cj["cores"]:
                names, prices, bw = bases[co["id"]]
                if n in names:
                    continue
                for i, s in enumerate(co["slots"]):
                    if s["slot"] not in ("UTIL", "BN") and s["slot"] not in PE.elig(pl[n]):
                        continue
                    t = list(names)
                    t[i] = n
                    if len(PE.match([pl[x] for x in t]) or []) != len(PE.ROSTER_SLOTS):
                        continue
                    if sum(prices) - prices[i] + cost(n) > BUDGET - RESERVE_FLOOR:
                        continue
                    _, wn, _, _ = CM.evaluate(t, B)
                    _, wo, _, _ = CM.evaluate(names, B)
                    if wn > wo:
                        combos.append((n, co["id"], s["slot"], names[i], t, bw))
            CM.F[n]["GP"] = orig[n]
    finally:
        for n, v in orig.items():
            CM.F[n]["GP"] = v

    print("부스트 때문인가, 원래 좋은 건가 — 같은 조합을 **두 번** 잰다\n")
    print("  🔴 분모: 13캣을 넘은 조합 %d개 중 **상위 %d개**만 몬테카를로로 가른다"
          % (len(combos), TOPN))
    print("     (전수는 %d회 × 12팀 × %d시행이라 안 돌린다 — 상위가 가장 유리한 쪽이므로"
          % (len(combos) * 2, FULL))
    print("      여기서 (a) 가 작으면 아래는 더 작다)\n")

    # 되돌린 상태 승률로 상위 추림
    scored = []
    for n, cid, slot, cur, t, bw in combos:
        CM.F[n]["GP"] = heal[n]
        try:
            wb = sim(t)
        finally:
            CM.F[n]["GP"] = orig[n]
        scored.append((wb - bw, wb, n, cid, slot, cur, t, bw))
    scored.sort(reverse=True)

    print("  %-20s %-4s %-5s %-18s %8s %8s %9s %9s"
          % ("선수", "코어", "슬롯", "밀어내는 1순위", "부스트", "현재GP", "(a)삭감", "(b)원래"))
    na = nb = 0
    rows = []
    for d, wb, n, cid, slot, cur, t, bw in scored[:TOPN]:
        wn = sim(t)                       # 🔴 현재 GP 그대로 — 이게 빠져 있었다
        a, b = wb - wn, wn - bw
        if a > PAIRED_SE:
            na += 1
        if b > PAIRED_SE:
            nb += 1
        rows.append((n, cid, slot, cur, wb, wn, a, b))
        print("  %-20s %-4s %-5s %-18s %7.1f%% %7.1f%% %+8.2f%%p %+8.2f%%p"
              % (n[:20], cid, slot, cur[:18], 100 * wb, 100 * wn, 100 * a, 100 * b))

    print("\n  대응 SE %.2f%%p 를 넘긴 개수:  (a) 삭감 효과 **%d/%d**  ·  (b) 원래 가치 **%d/%d**"
          % (100 * PAIRED_SE, na, TOPN, nb, TOPN))
    ma = sum(r[6] for r in rows) / len(rows)
    mb = sum(r[7] for r in rows) / len(rows)
    print("  평균:  (a) %+.2f%%p  ·  (b) %+.2f%%p" % (100 * ma, 100 * mb))
    print("\n  판정: %s" % (
        "🔴 **삭감이 배제를 만들었다** — §6k 의 「0건」은 이 축을 못 봤다"
        if ma > PAIRED_SE and ma > mb else
        ("🟢 **삭감과 무관하다** — 이득의 대부분이 (b)다. 코어 설계 얘기이고 그건 네 번 닫혔다"
         if mb > ma else "⚪ 둘 다 작다 — 아무것도 아니다")))
    print("\n⚠️ 어느 쪽이든 반영하지 않는다. 되돌린 GP 는 가짜다.")
    json.dump({"seed": SEED, "iterations": FULL, "combos": len(combos), "topn": TOPN,
               "mean_a_cut_effect": round(ma, 5), "mean_b_intrinsic": round(mb, 5),
               "rows": [{"player": r[0], "core": r[1], "slot": r[2], "displaces": r[3],
                         "wr_boost": round(r[4], 4), "wr_now": round(r[5], 4),
                         "a_cut": round(r[6], 5), "b_intrinsic": round(r[7], 5)} for r in rows]},
              io.open(BASE + "/data/absence_split.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
