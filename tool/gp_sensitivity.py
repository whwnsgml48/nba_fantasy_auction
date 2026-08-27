#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""출장 가정 감도 — 가정 하나를 흔들면 코어가 얼마나 내려가는가 (40차 신설).

왜 별도 실행인가
  `matchup_sim.py` 는 데이터에 적힌 GP 로 한 번 돈다. 그런데 몇몇 코어는 **재보지 않은
  GP 가정** 위에 서 있다. Haliburton 이 대표다 — 2025-26 을 통째로 결장했고 혼합 GP 73 은
  전부 2024-25 투영이다.

🔴 54 라는 숫자에 통계적 근거는 없다
  다른 세션이 리그 전체에서 `직전 GP → 다음 GP` 회귀(r≈0.41)로 54.3 을 냈고, 우리 DB
  164명으로 재현하면 r=0.117 · 예측 63.0 이 나온다(표본이 시장 상위 174명이라 범위가
  좁아 상관이 낮게 나오는 것으로, 두 값은 모순이 아니다).
  **그런데 어느 쪽도 Haliburton 에게는 적용되지 않는다** — 그는 2025-26 GP 가 없어
  회귀 표본에 아예 없다. 54 도 63 도 표본 밖 외삽이다.

  우리 DB에서 2025-26 GP ≤ 25 인 9명의 **직전 시즌** GP: 58 · 56 · 31 · 76 · 72 · 70 · 51 · 50 · 54.
  직전이 건강해도 다음 해 결장은 예측되지 않는다 — 어떤 회귀계수보다 이게 강한 증거다.

  → 그래서 **데이터의 GP 는 바꾸지 않는다**(사용자 결정 2026-08-27). 대신 감도를 재서
    화면에 띄운다. 숫자를 고르는 대신 **판단 재료를 준다.**

⚠️ 반드시 `matchup_sim` 본체를 그대로 쓴다
  머리말 경고대로 추첨 방식이 바뀌면 같은 시드에서도 승률 절대값이 전부 변한다.
  애드혹으로 곱해서 재면 본편과 다른 자 위의 숫자가 나온다 — 40차에 고친 바로 그 결함이다.
"""
import json, io, os, sys, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS
import real_opponents as RO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS = 20261020, 4000

# (선수, 대체 GP, 사유) — 재보지 않은 가정 위에 서 있는 1순위
CASES = [("Tyrese Haliburton", 54,
          "아킬레스 복귀 시즌. 혼합 GP 73 은 전부 2024-25 투영이고 2025-26 실측이 0경기다. "
          "54 는 다른 세션의 리그 전체 회귀 예측치로, **근거가 아니라 흔들어 보는 값**이다.")]


def main():
    cj = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    sim = json.load(io.open(f"{BASE}/data/matchup_sim.json", encoding="utf-8"))
    REAL, _ = RO.build()

    def run(us, override=None):
        old = {}
        for n, g in (override or {}).items():
            if n in MS.F:
                old[n] = MS.F[n]["GP"]; MS.F[n]["GP"] = g
        MS._URATE.clear()          # 가용률이 바뀌면 사용률 캐시도 무효다
        wr = [MS.simulate(us, REAL[m], random.Random(SEED), ITERS)["weekly_win_rate"]
              for m in REAL]
        for n, g in old.items():
            MS.F[n]["GP"] = g
        MS._URATE.clear()
        return round(sum(wr) / len(wr), 4), round(min(wr), 4)

    out = {"seed": SEED, "iterations": ITERS,
           "basis": "실제 12팀 상대 평균/최저 주간 승률 · 라인업 보정 적용(matchup_sim 본체)",
           "why_not_change_data": ("데이터의 GP 는 바꾸지 않는다(사용자 결정 2026-08-27). "
                                   "대체 GP 값 자체에 통계적 근거가 없고 — 해당 선수는 "
                                   "직전 GP→다음 GP 회귀의 표본에 들어 있지도 않다 — "
                                   "숫자를 고르는 대신 감도를 화면에 띄운다."),
           "cases": []}
    for who, gp, why in CASES:
        for co in cj["cores"]:
            us = [s["candidates"][0]["name"] for s in co["slots"]]
            if who not in us:
                continue
            base = run(us)
            alt = run(us, {who: gp})
            row = {"core": co["id"], "player": who, "gp_assumed": MS.F[who]["GP"],
                   "gp_alt": gp, "why": why,
                   "mean": base[0], "min": base[1],
                   "alt_mean": alt[0], "alt_min": alt[1],
                   "delta_mean": round(alt[0] - base[0], 4)}
            out["cases"].append(row)
            print("  %-3s %-20s GP %.0f→%d  평균 %.1f%% → %.1f%% (%+.1f%%p) · 최저 %.1f%% → %.1f%%"
                  % (co["id"], who, row["gp_assumed"], gp, 100 * base[0], 100 * alt[0],
                     100 * row["delta_mean"], 100 * base[1], 100 * alt[1]))
    sim["gp_sensitivity"] = out
    json.dump(sim, io.open(f"{BASE}/data/matchup_sim.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("data/matchup_sim.json 에 gp_sensitivity 기록")


if __name__ == "__main__":
    main()
