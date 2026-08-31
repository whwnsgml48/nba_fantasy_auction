#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""작년 12팀 라운드로빈 — 「13캣이 빅맨을 유리하게 만들었는가」 측정 (40차 · 측정만).

사용자 가설
  「작년엔 가드 위주 팀도 꽤 있었는데, 캣이 13개로 바뀌면서 빅맨이 확실히 유리해진 것 같다.」

🔴 우리 코어를 기준으로 재지 않는다
  「우리가 가드팀을 잘 이긴다」는 **우리 7코어가 전부 빅 편향**이라 순환이다 —
  상성을 강함으로 오독한다. 대신 **작년 12팀끼리** 붙인다(66쌍).
  작년 사람들끼리의 리그를 13캣으로 다시 돌리는 것이다.

🔴 성향은 판단이 아니라 측정으로 낸다
  빅 편향도  = (OREB + REB + BLK + DD) 의 **캣별 표준화** z 합
  가드 편향도 = (AST + STL + 3PM + A/T) 의 같은 것
  성향 지수  = 빅 − 가드   (양수면 빅 편향)
  ⚠️ `matchup_sim.z()` 를 쓰지 않는다 — **정규화 없이 합산하면 스케일 큰 캣이 지배**한다.
     40차에 그 함정을 세 번 밟았다(1차 탐색 · guard_stack 참고값 · 슈팅 탐색 첫 실행).

⚠️ 한계 (matchup_sim.json.real_opponents.interpretation)
  이건 **작년 낙찰 조합을 올해 스탯으로 평가**한 것이다. 「작년 그 팀이 올해 강한가」가
  아니라 **이 리그의 드래프트 성향 대리 표본**이다. 가격·예산은 작년 것(12팀·로스터10)이다.
"""
import json, io, os, sys, random, itertools, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import real_opponents as RO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS = 20261020, 2000
BIG = ("OREB", "REB", "BLK", "DD")
GRD = ("AST", "STL", "3PM", "A/T")


def main():
    REAL, _ = RO.build()
    teams = sorted(REAL)

    # ── 성향 지수: 캣별 표준화 후 합산 ────────────────────────────────
    raw = {}
    for t in teams:
        cm, _, _, _ = CM.evaluate(list(REAL[t]))
        raw[t] = cm
    stats = {}
    for c in set(BIG) | set(GRD):
        vs = [(raw[t].get(c) or 0) for t in teams]
        stats[c] = (sum(vs) / len(vs), st.pstdev(vs) or 1.0)

    def zsum(t, cats):
        return sum(((raw[t].get(c) or 0) - stats[c][0]) / stats[c][1] for c in cats)

    tend = {t: {"big": zsum(t, BIG), "guard": zsum(t, GRD)} for t in teams}
    for t in teams:
        tend[t]["index"] = tend[t]["big"] - tend[t]["guard"]

    # ── 라운드로빈 66쌍 ───────────────────────────────────────────────
    wins = {t: [] for t in teams}
    for a, b in itertools.combinations(teams, 2):
        MS._URATE.clear()
        r = MS.simulate(list(REAL[a]), REAL[b], random.Random(SEED), ITERS)
        MS._URATE.clear()
        wins[a].append(r["weekly_win_rate"])
        wins[b].append(1.0 - r["weekly_win_rate"])
    rr = {t: sum(v) / len(v) for t, v in wins.items()}

    # ── 캣별 승률(전 상대 평균) ───────────────────────────────────────
    catw = {}
    for t in teams:
        acc = {}
        for o in teams:
            if o == t:
                continue
            MS._URATE.clear()
            r = MS.simulate(list(REAL[t]), REAL[o], random.Random(SEED), ITERS)
            MS._URATE.clear()
            for c, v in r["cat_win_probs"].items():
                acc.setdefault(c, []).append(v)
        catw[t] = {c: sum(v) / len(v) for c, v in acc.items()}

    order = sorted(teams, key=lambda t: -rr[t])
    print("작년 12팀 라운드로빈 (66쌍 · %d시행 · seed %d) — 13캣 기준\n" % (ITERS, SEED))
    print("  %-6s %8s %9s %8s %8s   %s" % ("팀", "승률", "성향지수", "빅z", "가드z", "OREB / DD"))
    for i, t in enumerate(order, 1):
        d = tend[t]
        print("  %-6s %7.1f%% %9.2f %8.2f %8.2f   %5.1f / %5.1f"
              % (t, 100 * rr[t], d["index"], d["big"], d["guard"],
                 100 * catw[t]["OREB"], 100 * catw[t]["DD"]))

    top3 = order[:3]
    bot3 = order[-3:]
    print("\n  상위 3팀 성향지수: %s  (평균 %.2f)"
          % (", ".join("%s %.2f" % (t, tend[t]["index"]) for t in top3),
             sum(tend[t]["index"] for t in top3) / 3))
    print("  하위 3팀 성향지수: %s  (평균 %.2f)"
          % (", ".join("%s %.2f" % (t, tend[t]["index"]) for t in bot3),
             sum(tend[t]["index"] for t in bot3) / 3))

    out = {"seed": SEED, "iterations": ITERS, "pairs": 66,
           "method": ("작년 12팀을 서로 붙인다(66쌍). 우리 코어는 넣지 않는다 — "
                      "우리 7코어가 전부 빅 편향이라 순환이 된다."),
           "tendency_def": ("빅(OREB·REB·BLK·DD) z합 − 가드(AST·STL·3PM·A/T) z합. "
                            "**캣별 표준화 후** 합산 — matchup_sim.z() 는 정규화가 없어 안 쓴다."),
           "teams": {t: {"win_rate": round(rr[t], 4),
                         "tendency_index": round(tend[t]["index"], 2),
                         "big_z": round(tend[t]["big"], 2),
                         "guard_z": round(tend[t]["guard"], 2),
                         "cat_win": {c: round(v, 3) for c, v in catw[t].items()}}
                     for t in teams},
           "rank": order,
           "caveat": ("작년 낙찰 조합을 **올해 스탯**으로 평가한 것이다. "
                      "'작년 그 팀이 올해 강한가'가 아니라 이 리그의 드래프트 성향 대리 표본이다. "
                      "12점이므로 **회귀를 돌리지 않았다** — 표로 나열하고 보이는지만 본다.")}
    json.dump(out, io.open(f"{BASE}/data/round_robin_12.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/round_robin_12.json 기록")


if __name__ == "__main__":
    main()
