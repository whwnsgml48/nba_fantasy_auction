#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3-b — c6 의 **물러설 곳 없는 세 칸**에 승격 후보를 찾는다 (2026-09-01 · 측정만).

🔴 교체가 아니라 **승격**이다 (조율 지시)
```
❌ 못 사는 대체후보를 지우고 살 수 있는 놈으로 바꾼다
✅ 살 수 있는 놈을 **앞으로 올리고**, 기존 것은 **뒤로 내린다 — 지우지 않는다**
```
근거가 **작년 표본 하나**라서다. 지우면 올해 시장이 싸게 흘렀을 때 더 좋은 선수가
목록에 없다. 순서만 바꾸면 양쪽 다 남는다.

승격 조건 — 셋을 **다** 본다
  (a) 작년 환산가 ≤ my_max         살 수 있는가
  (b) pos_elig 성립                그 칸에 들어가는가
  (c) 🔴 **주간 승률 델타**         기존 대체 대비 얼마나 손해인가

🔴 **(c) 없이는 승격하지 않는다.** 살 수 있는데 훨씬 약한 놈을 앞에 세우면
   조달 위험을 **승률로 바꿔치기한 것**뿐이다. 델타가 크면 승격하지 말고
   **「대체 없음」으로 남긴다** — 물러설 곳이 없다는 사실이 가짜 대체보다 낫다.

⚠️ 후보를 **한 축으로 거르지 않는다**(docs/11 ⑦). 자격·조달을 통과한 것을
   전부 시뮬레이션에 넣는다 — 점수식으로 미리 자르면 그 점수식이 답을 정한다.

이 스크립트는 **아무것도 쓰지 않는다.** 반영은 조율 승인 사항이다.
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
import matchup_sim as MS      # noqa: E402
import real_opponents as RO   # noqa: E402
import pos_elig as PE         # noqa: E402
import cat_model as CM        # noqa: E402

SEED, PRE, FULL = 20261020, 800, 4000
SCALE = 1.11
BUDGET, RESERVE_FLOOR = 200, 4
TARGET_SLOTS = ["PF", "SF", "BN:Desmond Bane"]   # c6 의 죽은 세 칸


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
    prior = {}
    with io.open(BASE + "/data/prior_auction_2025_26/results.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            prior[norm(r["name_en"])] = int(r["price"])

    def adj(n):
        p = prior.get(norm(n))
        return None if p is None else p * SCALE

    c6 = next(c for c in cj["cores"] if c["id"] == "c6")
    base = [s["candidates"][0]["name"] for s in c6["slots"]]
    plans = [s["candidates"][0]["plan_price"] for s in c6["slots"]]
    REAL, _ = RO.build()

    def sim(names, iters):
        MS._URATE.clear()
        rs = [MS.simulate(list(names), REAL[m], random.Random(SEED), iters) for m in REAL]
        MS._URATE.clear()
        return sum(r["weekly_win_rate"] for r in rs) / len(rs)

    print("P3-b — c6 승격 후보 (측정만 · 아무것도 쓰지 않는다)\n")
    base_wr = sim(base, FULL)
    print("  c6 원안 주간 승률 **%.1f%%** (%d시행) · 계획총액 $%d\n"
          % (100 * base_wr, FULL, sum(plans)))

    pool = [n for n, p in pl.items()
            if not p.get("injury_exclude") and n in CM.F and p.get("value_reference")]

    out = {}
    for tgt in TARGET_SLOTS:
        slot_name = tgt.split(":")[0]
        pin = tgt.split(":")[1] if ":" in tgt else None
        idx = next(i for i, s in enumerate(c6["slots"])
                   if s["slot"] == slot_name and (pin is None or s["candidates"][0]["name"] == pin))
        s = c6["slots"][idx]
        cur1 = s["candidates"][0]["name"]
        alts = [cd["name"] for cd in s["candidates"][1:]]
        room = BUDGET - RESERVE_FLOOR - (sum(plans) - plans[idx])

        print("=" * 74)
        print("  c6 %s  1순위 %s ($%d)  ·  이 칸에 쓸 수 있는 돈 $%d"
              % (slot_name, cur1, plans[idx], room))
        print("  현행 대체: %s" % " · ".join(
            "%s (환산 $%s · 상한 $%d · edge %s)"
            % (a, "%.0f" % adj(a) if adj(a) is not None else "?", pl[a]["my_max"],
               "%+d" % round(pl[a]["my_max"] - adj(a)) if adj(a) is not None else "미판정")
            for a in alts))

        # (a)(b) 통과 후보 — 점수식으로 미리 자르지 않는다
        cands = []
        for n in pool:
            if n in base:
                continue
            if slot_name not in ("UTIL", "BN") and slot_name not in PE.elig(pl[n]):
                continue
            a = adj(n)
            cost = round(a) if a is not None else max(1, pl[n]["my_max"])
            if a is not None and a > pl[n]["my_max"]:
                continue                      # (a) 살 수 없다
            if cost > room:
                continue                      # 예산 밖
            trial = list(base)
            trial[idx] = n
            if len(PE.match([pl[x] for x in trial]) or []) != len(PE.ROSTER_SLOTS):
                continue                      # (b) 아홉 칸이 안 선다
            cands.append((n, cost, a is None))
        print("  (a)조달 + (b)자격 + 예산 통과: **%d명** — 전부 시뮬레이션에 넣는다" % len(cands))
        if not cands:
            print("  🔴 0명 — 이 칸은 정말로 대체가 없다\n")
            out[tgt] = {"cands": 0}
            continue

        pre = []
        for n, cost, unk in cands:
            trial = list(base)
            trial[idx] = n
            pre.append((sim(trial, PRE), n, cost, unk))
        pre.sort(reverse=True)
        top = pre[:6]

        print("  🔴 상위 후보는 %d시행으로 **다시** 잰다 (승자의 저주)" % FULL)
        rows = []
        for _, n, cost, unk in top:
            trial = list(base)
            trial[idx] = n
            wr = sim(trial, FULL)
            rows.append((wr, n, cost, unk))
        # 기존 대체도 같은 잣대로 잰다 — 비교 대상이 있어야 델타가 의미를 갖는다
        alt_rows = []
        for a in alts:
            trial = list(base)
            trial[idx] = a
            alt_rows.append((sim(trial, FULL), a,
                             round(adj(a)) if adj(a) is not None else None))

        print("\n  %-26s %7s %6s %9s" % ("후보", "승률", "지불", "원안 대비"))
        for wr, n, cost, unk in sorted(rows, reverse=True):
            print("    %-24s %6.1f%% %6d %+8.1f%%p%s"
                  % (n[:24], 100 * wr, cost, 100 * (wr - base_wr), "  ⬜작년미지명" if unk else ""))
        print("  ── 현행 대체 (같은 잣대) ──")
        for wr, a, c in sorted(alt_rows, reverse=True):
            print("    %-24s %6.1f%% %6s %+8.1f%%p  🔴 못 산다"
                  % (a[:24], 100 * wr, c if c is not None else "?", 100 * (wr - base_wr)))

        best_new = max(rows)[0]
        best_alt = max(alt_rows)[0]
        print("\n  🔴 **승격 델타 = %+.1f%%p** (살 수 있는 최선 %.1f%% − 못 사는 최선 %.1f%%)"
              % (100 * (best_new - best_alt), 100 * best_new, 100 * best_alt))
        out[tgt] = {"base": round(base_wr, 4), "best_new": round(best_new, 4),
                    "best_alt": round(best_alt, 4),
                    "delta": round(best_new - best_alt, 4),
                    "cands": len(cands),
                    "rows": [{"name": n, "wr": round(w, 4), "cost": c, "unknown_prior": u}
                             for w, n, c, u in sorted(rows, reverse=True)],
                    "current_alts": [{"name": a, "wr": round(w, 4), "prior_adj": c}
                                     for w, a, c in sorted(alt_rows, reverse=True)]}
        print("")

    print("=" * 74)
    print("⚠️ 이 스크립트는 아무것도 쓰지 않았다. 승격 반영은 조율 승인 사항이다.")
    print("⚠️ 델타가 크면 **승격하지 말고 「대체 없음」으로 남긴다** — 물러설 곳이 없다는")
    print("   사실이 가짜 대체보다 낫다. 조달 위험을 승률로 바꿔치기하지 않는다.")
    json.dump({"seed": SEED, "iterations": FULL, "base_wr": round(base_wr, 4), "slots": out},
              io.open(BASE + "/data/c6_promote.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/c6_promote.json 기록 (측정 결과 · cores.json 은 안 건드림)")


if __name__ == "__main__":
    main()
