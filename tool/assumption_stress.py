#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""가정 취약성 표 — 각 코어가 **자기 가정에 스트레스를 걸면** 어떻게 되는가 (40차 신설).

왜 이 표가 필요한가 🔴
  라인업 보정 후 1차 지표에서 상위 5개가 **1.3%p 안**에 들어왔다(대응 SE ±0.6%p).
  그리고 2차(maximin)는 7코어 중 5개가 `value_max` — 우리 z모델의 자기 최적해 — 에
  지배되어 타이브레이커로 쓸 수 없다. **어떤 승률 측정도 상위 5개를 가르지 못한다.**

  그런데 **가정 취약성은 5%p 를 만든다.** 승률로 못 가르는 다섯을 이것이 가른다.

무엇에 스트레스를 거는가
  코어마다 1순위 중 `measured_source.blend_share_2025_26 < 0.50` 인 선수 —
  즉 GP 가 **2025-26 실측이 아니라 옛 시즌 투영**에 기대고 있는 선수다.
    c1 Haliburton 0%   c3 Lillard 0%   c4 Trae 23%
    c5 Haliburton 0% + Sabonis 29% + Zubac 47%      c2·c6·c7 해당 없음

  강도는 **모든 코어에 같게** 건다 — GP × 0.74 (Haliburton 73 → 54 와 같은 비율).

🔴 왜 강도를 통일하는가
  처음 c5 를 판정할 때 **c5 에만 GP 스트레스를 걸고 c4 에는 안 걸었다.** c4 도 Trae 의
  실측 비중이 23%인데 그대로 두고 「c4 가 5.4%p 앞선다」고 썼다. 한쪽에만 스트레스를
  거는 비교는 결론을 만들어낸다 — 평가 세션이 잡았다. 이 스크립트는 그 대칭을 강제한다.

⚠️ 0.74 라는 배율에 통계적 근거는 없다
  Haliburton 의 54 가 표본 밖 외삽이므로 그것에서 딴 배율도 마찬가지다. 이 표는
  **"GP 가 이만큼 틀리면 순위가 뒤집히는가"** 를 묻는 것이지 GP 를 예측하지 않는다.
  절대값이 아니라 **코어 간 상대적 무너짐**을 볼 것.
"""
import json, io, os, sys, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS
import real_opponents as RO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS, FACTOR, THRESH = 20261020, 4000, 0.74, 0.50


def main():
    cj = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    REAL, _ = RO.build()

    def run(us, gp=None):
        old = {}
        for n, g in (gp or {}).items():
            if n in MS.F:
                old[n] = MS.F[n]["GP"]; MS.F[n]["GP"] = g
        MS._URATE.clear()
        wr = [MS.simulate(us, REAL[m], random.Random(SEED), ITERS)["weekly_win_rate"]
              for m in REAL]
        for n, g in old.items():
            MS.F[n]["GP"] = g
        MS._URATE.clear()
        return round(sum(wr) / len(wr), 4)

    out = {"seed": SEED, "iterations": ITERS, "gp_factor": FACTOR,
           "share_threshold": THRESH,
           "what": ("코어의 1순위 중 GP 실측 비중이 임계 미만인 선수 전원의 GP 에 같은 배율을 "
                    "곱하고 실제 12팀 평균 주간 승률을 다시 잰다."),
           "why": ("승률 1차 지표가 상위 5개를 1.3%p 안으로 몰아넣었고 2차는 쓸 수 없다. "
                   "**가정 취약성이 그 다섯을 가르는 유일한 측정**이다."),
           "caveat": ("배율 0.74 에 통계적 근거는 없다(Haliburton 73→54 와 같은 비율). "
                      "GP 를 예측하는 표가 아니라 **얼마나 흔들리는가**를 보는 표다. "
                      "코어 간 상대 비교로만 읽을 것."),
           "rows": []}

    print("  %-4s %7s %7s %8s   %s" % ("코어", "기준", "스트레스", "차이", "흔든 가정"))
    for co in cj["cores"]:
        us = [s["candidates"][0]["name"] for s in co["slots"]]
        shaky = {}
        for s in co["slots"]:
            n = s["candidates"][0]["name"]
            ms = (MS.PL.get(n) or {}).get("measured_source") or {}
            sh = ms.get("blend_share_2025_26")
            if sh is not None and sh < THRESH and n in MS.F:
                shaky[n] = round(MS.F[n]["GP"] * FACTOR, 1)
        base = run(us)
        alt = run(us, shaky) if shaky else base
        row = {"core": co["id"], "base": base, "stressed": alt,
               "delta": round(alt - base, 4),
               "assumptions": [{"player": n, "share": (MS.PL[n]["measured_source"]
                                                       ["blend_share_2025_26"]),
                                "gp": MS.F[n]["GP"], "gp_stressed": g}
                               for n, g in sorted(shaky.items())]}
        out["rows"].append(row)
        print("  %-4s %6.1f%% %6.1f%% %+7.1f%%p   %s" % (
            co["id"], 100 * base, 100 * alt, 100 * row["delta"],
            " · ".join("%s %.0f→%.0f" % (n.split()[-1], MS.F[n]["GP"], g)
                       for n, g in sorted(shaky.items())) or "없음 (전원 실측 기반)"))

    sim = json.load(io.open(f"{BASE}/data/matchup_sim.json", encoding="utf-8"))
    sim["assumption_stress"] = out
    json.dump(sim, io.open(f"{BASE}/data/matchup_sim.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("data/matchup_sim.json 에 assumption_stress 기록")


if __name__ == "__main__":
    main()
