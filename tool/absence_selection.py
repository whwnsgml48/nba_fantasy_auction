#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6k 후속 — **삭감이 「후보에 오르지도 못하게」 했는가** (2026-09-01 · 측정만).

🔴 §6k 가 한쪽만 셌다 (조율 지적)
  GP 삭감은 **두 번** 작동한다:
```
①  my_max 를 낮춘다             → 못 산다              ← §6k 가 센 것 (0건)
②  투영 GP 가 낮아 시뮬 기여가 낮다 → **애초에 코어에 안 뽑힌다**  ← 안 센 것
```
  ②는 **「못 사는 명단」에 안 나타난다** — 후보로 고려된 적이 없으니까.
  26명이 조용히 배제되고 있으면 「결정이 안 바뀐다」는 **결정에 오르지 못한 것을 못 본**
  결과다.

무엇을 하나 — **탐색이 아니라 한 번의 대조**
  ⚠️ 코어 재탐색은 금지다(네 번 닫았다). 이건 경계 검사다:
```
26명 각각 · GP 를 삭감 전(직전 건강 시즌)으로 되돌린 값으로
그가 들어갈 수 있는 슬롯의 **현재 1순위와 승률을 대조**한다
0명이면 ② 까지 닫힌다 · 있으면 그 이름만 올린다
```

🔴 **되돌린 GP 는 가짜다.** `ρ 0.10` 이 모집단 평균이라는 §6k 이유 ②가 여기에도 적용된다.
   그러므로 결과는 **「이 선수는 우리 삭감 때문에 후보에서 빠졌다」**까지이고
   **「그러니 넣어야 한다」가 아니다.** 이 구분을 출력에 박는다.

⚠️ `my_max`·1순위·`data/` 어느 것도 쓰지 않는다. GP 는 메모리에서만 바꾸고 되돌린다.
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

SEED, PRE, FULL = 20261020, 800, 4000
SCALE = 1.11
BUDGET, RESERVE_FLOOR = 200, 4
MISS = 20


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

    # 대상 26명 — §6k 와 같은 기준
    inj = {n for n, p in pl.items() if p.get("injury_exclude")}
    targets = []
    for n, p in pl.items():
        k = norm(n)
        if n in inj or n not in CM.F or k not in g25 or k not in g26:
            continue
        if g25[k] - g26[k] < MISS:
            continue
        cur = CM.F[n].get("GP") or 0
        if g25[k] <= cur:
            continue
        targets.append((n, cur, g25[k]))

    print("삭감이 **후보에 오르지도 못하게** 했는가 — §6k 의 안 센 쪽\n")
    print("  🔴 대상 %d명 (작년 %d경기 이상 결장 + 현재 부상 표기 없음)" % (len(targets), MISS))
    print("  🔴 되돌린 GP 는 **가짜다** — 결과는 「삭감 때문에 빠졌다」까지이고")
    print("     **「그러니 넣어야 한다」가 아니다.**\n")

    def sim(names, iters):
        MS._URATE.clear()
        rs = [MS.simulate(list(names), REAL[m], random.Random(SEED), iters) for m in REAL]
        MS._URATE.clear()
        return sum(r["weekly_win_rate"] for r in rs) / len(rs)

    # 기준선: 각 코어 원안
    bases = {}
    for co in cj["cores"]:
        names = [s["candidates"][0]["name"] for s in co["slots"]]
        prices = [s["candidates"][0]["plan_price"] for s in co["slots"]]
        bases[co["id"]] = (names, prices, sim(names, FULL))
    print("  코어 원안 승률: " + " · ".join("%s %.1f%%" % (k, 100 * v[2])
                                           for k, v in bases.items()) + "\n")

    orig = {n: CM.F[n].get("GP") for n, _, _ in targets}
    combos = []
    try:
        for n, cur, heal in targets:
            CM.F[n]["GP"] = heal                     # 🔴 메모리에서만 되돌린다
            for co in cj["cores"]:
                names, prices, base_wr = bases[co["id"]]
                if n in names:
                    continue
                for i, s in enumerate(co["slots"]):
                    slot = s["slot"]
                    if slot not in ("UTIL", "BN") and slot not in PE.elig(pl[n]):
                        continue
                    trial = list(names)
                    trial[i] = n
                    if len(PE.match([pl[x] for x in trial]) or []) != len(PE.ROSTER_SLOTS):
                        continue
                    tot = sum(prices) - prices[i] + cost(n)
                    if tot > BUDGET - RESERVE_FLOOR:
                        continue
                    # 🔴 미리 자르는 것은 **13캣 전체 평가**이지 한 축이 아니다(docs/11 ⑦).
                    #   그래도 결정적 지표이므로 여기서 이긴 것만 몬테카를로로 다시 잰다.
                    _, w_new, _, _ = CM.evaluate(trial, B)
                    _, w_old, _, _ = CM.evaluate(names, B)
                    if w_new > w_old:
                        combos.append((n, co["id"], slot, names[i], i, trial, tot, base_wr))
            CM.F[n]["GP"] = orig[n]
    finally:
        for n, v in orig.items():
            CM.F[n]["GP"] = v

    # 🔴 대조군 — **GP 를 안 되돌리고** 같은 검사를 돌린다.
    #   위 숫자만 내면 불공정하다: 26명만 부스트를 받고 현직 1순위는 못 받는다.
    #   「부스트한 선수가 현직을 이긴다」는 거의 동어반복이다. **차이**를 봐야 한다.
    ctrl = 0
    for n, cur, heal in targets:
        for co in cj["cores"]:
            names, prices, _ = bases[co["id"]]
            if n in names:
                continue
            for i, s in enumerate(co["slots"]):
                slot = s["slot"]
                if slot not in ("UTIL", "BN") and slot not in PE.elig(pl[n]):
                    continue
                trial = list(names)
                trial[i] = n
                if len(PE.match([pl[x] for x in trial]) or []) != len(PE.ROSTER_SLOTS):
                    continue
                if sum(prices) - prices[i] + cost(n) > BUDGET - RESERVE_FLOOR:
                    continue
                _, w_new, _, _ = CM.evaluate(trial, B)
                _, w_old, _, _ = CM.evaluate(names, B)
                if w_new > w_old:
                    ctrl += 1

    print("  13캣 평가에서 현재 1순위를 넘은 조합")
    print("     삭감 전 GP 로 되돌림 : **%d개**" % len(combos))
    print("     🔴 대조군(안 되돌림)  : **%d개**   ← 이 차이가 **삭감이 만든 배제**다" % ctrl)
    print("     ⚠️ 되돌린 쪽만 부스트를 받는다 — 현직 1순위는 안 받는다.")
    print("        그래서 위 숫자는 **상한**이고, 아래 승률 차도 과대추정이다.")
    if not combos:
        print("\n  🟢 **0개 — ② 까지 닫힌다.**")
        print("     「우리는 깎지만 그것이 아무것도 안 바꾼다」가 참이다.")
        print("     §6k 의 「결정 0건」은 후보에 못 오른 쪽을 못 봐서 나온 값이 아니다.")
        return

    print("\n  🔴 몬테카를로로 다시 잰다 (%d시행 · 승자의 저주)\n" % FULL)
    out = []
    for n, cid, slot, cur1, i, trial, tot, base_wr in combos:
        CM.F[n]["GP"] = dict((a, c) for a, _, c in targets)[n]
        try:
            wr = sim(trial, FULL)
        finally:
            CM.F[n]["GP"] = orig[n]
        out.append((wr - base_wr, wr, n, cid, slot, cur1, tot, base_wr))
    out.sort(reverse=True)
    print("  %-24s %-4s %-5s %-22s %8s %8s %7s"
          % ("삭감 전 GP 로 되돌린 선수", "코어", "슬롯", "밀어내는 1순위", "승률", "원안대비", "총액"))
    win = 0
    for d, wr, n, cid, slot, cur1, tot, base_wr in out:
        mark = " 🔴" if d > 0.0059 else ("" if d > 0 else "  (오차 안/음수)")
        if d > 0.0059:
            win += 1
        print("  %-24s %-4s %-5s %-22s %7.1f%% %+7.1f%%p %6d%s"
              % (n[:24], cid, slot, cur1[:22], 100 * wr, 100 * d, tot, mark))
    print("\n  🔴 **대응 SE 0.59%%p 를 넘긴 조합: %d개**" % win)
    print("\n  ⚠️ 이 표가 말하는 것: **이 선수들은 우리 GP 삭감 때문에 후보에서 빠졌다.**")
    print("     말하지 않는 것: **넣어야 한다.** 되돌린 GP 는 가짜이고, ρ 0.10 은")
    print("     모집단 평균이라 이 개인들이 실제로 건강할지는 이 데이터로 모른다.")
    print("  ⚠️ `my_max` 도 1순위도 안 바꿨다. 목록만 낸다 — 판단은 조율 세션.")


if __name__ == "__main__":
    main()
