#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""재설계 후보 탐색 — A(c7 대안) · B(c6·c1 빅스택 열 개선). 기존 코어는 덮지 않는다.

산출: data/rebuild_candidates.json  (기존 c1·c6·c7을 첫 행으로 포함)

혼합 정의 (33차 · 사용자 수치에서 역산)
  13상대 리그(14팀). 좌석 배분을 정수 격자에서 최소오차로 맞췄다:
    보수 = 무작위 4 · 가치최대 2 · 빅스택 4 · 가드스택 3            (오차합 0.08)
    중립 = 무작위 4 · 가치최대 2 · 빅스택 1 · 가드스택 4 · 기준선 2  (오차합 0.03)
  독립 검산 2건 통과: (a) 사용자 "보수 빅스택 4석" 일치
                     (b) "c6 빅스택 38.5→55% 이면 보수 +5.1%p" → 4×16.5/13 = 5.08 일치

취득 원가 (cost) — **시장 중간값**
  33차 1차 시도는 시장 상단으로 잡았다. 그러면 **현 코어가 비교 기준이 되지 못한다**:
  상단 기준 총액이 c1 $218 · c7 $208로 예산 초과이고, my_max < 시장상단인 선수도
  c1 1명(Haliburton) · c7 3명(J.Johnson·Fox·NAW)이다.
  사용자의 미배분 산식($200 − 시장중간합 → c6 $39 · c4 $42)과 같은 기준을 쓴다.
  A의 세계에서는 low_cost_center 6명의 원가를 max(시장중간, overheat_at)으로 올린다.
  ⚠️ 중간값 기준은 "평균적으로 낙찰된다"는 가정이다. 상단 기준(확실히 이긴다)에서는
  현 코어들도 실행 불가이므로 그 세계에서는 비교 자체가 성립하지 않는다.

제약 (기존 코어와 동일 + A 전용)
  9인 · 총액 <= $200 · 총액 >= $180 · my_max >= 취득가
  포지션: C 자격 >= 2 · G >= 2 · F >= 2   (README '공통 필수 요소')
  벤치(최저가 2명) 합 <= $20 · 앵커는 벤치에 두지 않음(최고가 2명은 벤치가 될 수 없음)
"""
import json, io, os, sys, random, itertools, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL, CJ, F = MS.PL, MS.CJ, MS.F
KEYS = ["random", "value_max", "big_stack", "guard_stack", "baseline", "benchmark"]
SEATS = {"보수": {"random":4,"value_max":2,"big_stack":4,"guard_stack":3,"baseline":0,"benchmark":0},
         "중립": {"random":4,"value_max":2,"big_stack":1,"guard_stack":4,"baseline":2,"benchmark":0}}
LCC = {t["player"]: t["overheat_at"] for t in CJ["overheat_thresholds"]
       if t.get("tier") == "low_cost_center"}

def cost(name, overheated=False):
    p = PL[name]
    c = (p["market_low"] + p["market_high"]) / 2.0
    if overheated and name in LCC: c = max(c, LCC[name])
    return c

def feasible(names, overheated=False, grandfather=()):
    """제약 검사. 통과 시 총액, 실패 시 None.

    grandfather: **기존 로스터 멤버**에 한해 `my_max >= 취득가`를 면제한다.
    c1은 Haliburton(my_max $50 < 중간 $60)이 이미 들어 있어 그를 포함한 모든 시행이
    실패한다 — 그래서 단일 슬롯 교체 후보가 **0개**가 나왔다. 기존 코어와 비교하려면
    기존 멤버의 기지(known) 미달은 면제하고 새로 넣는 선수에만 규칙을 적용해야 한다.
    (면제는 표에 명시한다.)"""
    if len(set(names)) != 9: return None
    tot = sum(cost(n, overheated) for n in names)
    if tot > 200 or tot < 180: return None
    for n in names:
        if PL[n]["my_max"] < cost(n, overheated) and n not in grandfather: return None
    has = lambda ch: sum(1 for n in names if ch in (PL[n].get("pos") or ""))
    if has("C") < 2 or has("G") < 2 or has("F") < 2: return None
    pr = sorted(names, key=lambda n: cost(n, overheated))
    if sum(cost(n, overheated) for n in pr[:2]) > 20: return None   # 벤치 <= $20
    top2 = sorted(names, key=lambda n: -cost(n, overheated))[:2]
    if set(top2) & set(pr[:2]): return None                          # 앵커 벤치 금지
    return tot

def evaluate(names, rng, iters, opps, keys=None):
    keys = keys or KEYS
    out = {}
    for k in keys:
        out[k] = MS.simulate(names, opps[k], rng, iters, MS.pool())
    wr = {k: out[k]["weekly_win_rate"] for k in keys}
    row = {"roster": list(names),
           "mid_sum": round(sum((PL[n]["market_low"]+PL[n]["market_high"])/2 for n in names)),
           "high_sum": sum(PL[n]["market_high"] for n in names),
           "win_rate": {k: wr[k] for k in keys},
           "min_win_rate": round(min(wr.values()), 4),
           "min_win_rate_vs": sorted([k for k in keys if wr[k] == min(wr.values())]),
           "p_big5_collapse": {k: out[k]["p_big5_collapse"] for k in keys},
           "p_cats_won_le4": {k: out[k]["p_cats_won_le4"] for k in keys},
           "cats_won_sd": {k: out[k]["cats_won_sd"] for k in keys}}
    if set(keys) == set(KEYS):
        for lab, seat in SEATS.items():
            row.setdefault("mixture", {})[lab] = round(
                sum(wr[k]*seat[k] for k in KEYS)/13, 4)
    return row

def mixmax(row):
    """혼합 열의 최악값 — 붕괴 지표 요약에 쓴다."""
    return {k: max(row[k].values()) for k in ("p_big5_collapse","p_cats_won_le4","cats_won_sd")}
