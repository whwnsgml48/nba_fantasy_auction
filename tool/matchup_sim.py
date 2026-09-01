#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주간 맞대결 몬테카를로 — 캣별 승률 · 기대 승리 캣 · 주간 승률.

왜 필요한가
  지금까지의 판정은 **팀 한계기여의 부호**였다("기준선보다 크면 이긴다").
  그건 기대값 비교이고 **분산이 없다.** 같은 3% 마진이 캣에 따라 승률 52%~66%다
  (FT% σ 5.2% vs DD σ 47.8%). 마진 개수를 세는 것은 서로 다른 화폐를 세는 것이다.
  이 스크립트는 주 단위로 표본을 뽑아 **승률**을 직접 낸다.

기존 필드는 덮지 않는다
  cores.json에 cat_win_probs · expected_cats_won · weekly_win_rate 만 **추가**한다.
  cat_team_marginals · cat_win_summary는 손대지 않는다 — 다른 층의 지표다.

🔴 **비교 규약 — 저장값에서 빼지 마라. 양쪽을 같은 규약으로 새로 재라** (40차 · 조율 판정)
  `team_week_prepped` 는 선수 리스트를 **순서대로** 돌며 난수를 뽑는다. 그래서 같은
  로스터·같은 시드라도 **이름 순서가 다르면 값이 달라진다.** 실측(c6 · 12000시행):
      원래 87.632 · 정렬 87.692 · 역순 87.677 · 셔플 87.571 → 폭 **0.121%p**
  대응 SE(0.59%p)의 **20%** 다. 시행수·순서·라인업 캐시 상태가 조금만 달라도 이만큼 움직인다.

    ❌  새로 잰 값 − `matchup_sim.json` 저장값        ← 규약이 다른 두 수를 뺀다
    ✅  A 와 B 를 **같은 실행·같은 시드·같은 순서**로 재고 그 차를 본다

  **저장값은 표시용이다.** 문서 여러 곳이 인용하고 있으므로 다시 계산하지 않는다 —
  0.12%p 를 맞추려고 40차치 문서를 다시 쓰면 얻는 것보다 잃는 게 크다.
  `tool/pivot_delta.py` 는 이름 정렬을 강제해 `measure()` 를 **집합의 순수 함수**로 만든다.
  ⚠️ 그리고 9명이 통째로 바뀌는 비교(피벗·코어 교체)에서는 **몬테카를로 잡음이 두 로스터
     사이에 공유되지 않는다** — 대응 SE 는 상대 12팀 표본 변동만 잡는다. 경계 판정은
     **시드를 바꿔** 확인할 것.

────────────────────────────────────────────────────────────────────────
사전 고정 계수 (24차 DD 방식 — 실측에 맞춰 튜닝하지 않는다)

  경기당 계수형 스탯을 과분산 정규로 근사한다: X ~ N(μ, (c·√μ)²), 0에서 절단.
  c = 경기간 SD / √평균. 포아송이면 c=1이고, 농구는 출장시간·매치업 변동으로 그 위에 있다.

    PTS  1.50   25득점 선수의 경기간 SD ≈ 7.5 (24차 DD와 같은 값)
    REB  1.10   10리바운드 → SD ≈ 3.5
    AST  1.05   8어시스트 → SD ≈ 3.0
    OREB 1.05   평균이 1~4라 거의 포아송
    STL  1.00   평균 ~1, 포아송으로 충분
    BLK  1.05   평균 ~1, 약한 과분산
    TOV  1.05   평균 ~2, 약한 과분산
    3PM  1.15   슈팅은 연속성(hot/cold)이 있어 포아송보다 약간 넓다
    FGA/FTA/3PA 1.00  시도량은 역할이 정하므로 성공보다 안정적이다

  비율캣은 **2단 추출**이다: 시도량을 먼저 뽑고, 성공을 이항으로 뽑는다.
  퍼센트 자체에 별도 과분산을 얹지 않는다 — 그러면 이항 분산을 이중 계산한다.
  (검산 앵커가 이 선택을 검증한다: c6 FT% 승률 22~25%.)

  DD는 cat_model.dd_game_prob 을 그대로 쓴다(24차 실측 25명 검증 완료).

  주간 경기수는 선수별로 {3,4}에서 균등 추출한다 — 로스터 9명은 서로 다른 NBA 팀이라
  같은 주에 같은 경기수를 갖지 않는다. 출장은 경기별로 확률 GP/82의 베르누이다.
────────────────────────────────────────────────────────────────────────
"""
import json, io, os, sys, math, random, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import real_opponents as RO   # 38차: 작년 옥션 실측 12팀 = **실제 상대**
import pos_elig as PE         # 40차: 슬롯 자격 단일 소스
import lineup_feasibility as LF

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F  = CM.F
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))

C_OVER = {"PTS":1.50, "REB":1.10, "AST":1.05, "OREB":1.05, "STL":1.00,
          "BLK":1.05, "TOV":1.05, "3PM":1.15}
C_ATT  = 1.00
COUNT  = ["PTS","REB","OREB","AST","STL","BLK","TOV","3PM"]
RATE   = {"3P%":"3PA", "FT%":"FTA", "FG%":"FGA"}
CATS   = COUNT + list(RATE) + ["A/T", "DD"]
LOWER  = {"TOV"}
WIN_LINE = 7            # 13캣 중 7캣이면 주간 승리
# 38차: 균등 {3,4}(평균 3.5)를 **평균 3.299 가중 추첨**으로 교체했다. 확정 일정
# 2026-10-20~2027-04-11 = 24.857주 · 82경기 → 팀당 주간 3.299경기다. 단일 소스는
# cat_model.GAMES_PER_WEEK. ⚠️ 추첨 방식이 바뀌면 난수 소비가 달라져 **같은 시드에서도
# 승률 절대값이 전부 변한다** — 시드 간 비교는 같은 버전끼리만 해야 한다.
GAMES_RANGE = (3, 4)          # 지지집합 (보고용). 평균은 CM.GAMES_PER_WEEK

def _draw(mu, c, rng):
    """과분산 정규 근사, 0 절단."""
    if mu is None or mu <= 0: return 0.0
    return max(0.0, rng.gauss(mu, c * math.sqrt(mu)))

def _binom(n, p, rng):
    """이항 표본. n이 크면 정규 근사로 바꾼다 — 루프가 시뮬 시간을 지배한다.
    n>=12에서 정규 근사 오차는 승률 소수점 아래라 무해하다."""
    if n <= 0: return 0
    if n < 12: return sum(1 for _ in range(n) if rng.random() < p)
    m = n * p
    return min(n, max(0, int(round(rng.gauss(m, math.sqrt(m * (1 - p)))))))

# ── 라인업 사용률 (40차 · 공식 경로로 승격 · 사용자 결정 2026-08-27) ──────────
#
# 왜 가정이 아니라 **누락된 규칙**인가
#   야후는 라인업을 매일 세팅하고 선발 7칸은 포지션이 정해져 있다. 그날 경기가 있어도
#   넣을 칸이 없으면 그 경기는 통째로 버려진다. 이건 모델링 선택이 아니라 **리그 규칙**이고,
#   보정하지 않은 승률은 **불가능한 로스터 운용**을 계산한 값이다.
#
#   실제로 순위가 바뀐다. 자격 반영 전후로 7코어 중 c2 하나만 −2.5%p 움직였다
#   (나머지는 전부 ±0.4%p 안). c2 는 저평가 구간을 쓸어담는 방식이 곧 C 전용을 5명까지
#   쌓는 방식이었고, 보정 없는 시뮬은 그 5명을 매일 다 쓸 수 있다고 계산했다.
#   「전 코어 1위」가 코어의 강점이 아니라 모델의 맹점에서 나온 이득이었다.
#
# 어떻게
#   `avail = GP/82` 에 **사용률**(그 선수의 경기 중 슬롯을 얻는 비율)을 곱한다.
#   두 손실은 성격이 다르고 곱해지는 것이 맞다 — 결장은 경기가 없는 것,
#   사용률은 경기가 있는데 칸이 없는 것이다.
#
# ⚠️ 무작위 상대만 근사한다
#   무작위 상대는 시행마다 로스터가 바뀌어 매번 사용률을 재면 시뮬이 끝나지 않는다.
#   대신 무작위 로스터 표본에서 **자격집합별 평균 사용률**을 미리 구해 쓴다.
#   1차 지표(실제 12팀)와 고정 상대는 전부 로스터별 실측이므로 근사가 섞이지 않는다.
LINEUP_ADJ   = True
LINEUP_WEEKS = 2500          # 사용률 추정용 주 수. 비율 추정이라 승률만큼 정밀할 필요는 없다
_URATE = {}
_RND_RATE = None

def _pdict(n):
    """자격 판정용 최소 dict. 상대 로스터에는 players.json 에 없는 선수가 있다."""
    p = PL.get(n)
    if p: return p
    r = F.get(n) or {}
    return {"name": n, "pos": r.get("pos"), "pos_yahoo": None,
            "measured_source": {"GP": r.get("GP")}}

def usable_rates(names):
    """로스터별 사용률 {이름: 비율}. 같은 로스터는 캐시한다."""
    key = tuple(names)
    if key not in _URATE:
        _URATE[key] = LF.usable_rates([_pdict(n) for n in names if n in F],
                                      weeks=LINEUP_WEEKS)
    return _URATE[key]

def random_rate_table(rows, rng, samples=120):
    """무작위 상대용 — 자격집합별 평균 사용률. 한 번만 만든다."""
    global _RND_RATE
    if _RND_RATE is not None: return _RND_RATE
    acc = {}
    for _ in range(samples):
        sel = random_roster(rows, rng)
        if not sel: continue
        for n, u in LF.usable_rates([_pdict(x) for x in sel if x in F], weeks=300).items():
            acc.setdefault(frozenset(PE.elig(_pdict(n))), []).append(u)
    _RND_RATE = {k: sum(v) / len(v) for k, v in acc.items()}
    return _RND_RATE

def prep(names, rates=None):
    """선수별 정적 값을 미리 뽑아둔다 — 시행마다 dict 조회를 반복하지 않는다.

    `rates` 를 주면 그 표를 쓰고(무작위 상대용 자격집합별 평균), 안 주면 이 로스터로 직접 잰다.
    """
    if LINEUP_ADJ and rates is None:
        rates = usable_rates(names)
    out = []
    for n in names:
        r = F.get(n)
        if not r: continue
        av = (r.get("GP") or 0) / 82.0
        if LINEUP_ADJ and rates:
            av *= (rates.get(n) if n in rates
                   else rates.get(frozenset(PE.elig(_pdict(n))), 1.0))
        out.append((av,
                    [(k, r.get(k)) for k in COUNT],
                    [(k, a, r.get(a), r.get(k)) for k, a in RATE.items()],
                    CM.dd_game_prob(r.get("PTS"), r.get("REB"), r.get("AST"))))
    return out

def team_week_prepped(pre, rng):
    tot = {k: 0.0 for k in COUNT}
    made = {k: 0.0 for k in RATE}
    att  = {k: 0.0 for k in RATE}
    dd = 0
    for avail, cnts, rts, p_dd in pre:
        for _ in range(CM.draw_week_games(rng)):
            if rng.random() > avail: continue
            for k, mu in cnts:
                if mu: tot[k] += max(0.0, rng.gauss(mu, C_OVER[k] * math.sqrt(mu)))
            for k, a, mu_a, p in rts:
                if mu_a is None or p is None or mu_a <= 0: continue
                na = int(round(max(0.0, rng.gauss(mu_a, C_ATT * math.sqrt(mu_a)))))
                if na <= 0: continue
                att[k] += na; made[k] += _binom(na, p, rng)
            if rng.random() < p_dd: dd += 1
    out = dict(tot)
    for k in RATE: out[k] = (made[k] / att[k]) if att[k] else 0.0
    out["A/T"] = (tot["AST"] / tot["TOV"]) if tot["TOV"] else (tot["AST"] or 0.0)
    out["DD"] = float(dd)
    return out

def team_week(names, rng):
    """로스터의 한 주 표본. 반환은 캣별 팀 합계(비율캣은 성공/시도)."""
    tot = {k: 0.0 for k in COUNT}
    made = {k: 0.0 for k in RATE}
    att  = {k: 0.0 for k in RATE}
    dd = 0
    for n in names:
        r = F.get(n)
        if not r: continue
        avail = (r.get("GP") or 0) / 82.0
        g = CM.draw_week_games(rng)
        p_dd = CM.dd_game_prob(r.get("PTS"), r.get("REB"), r.get("AST"))
        for _ in range(g):
            if rng.random() > avail: continue          # 결장
            for k in COUNT:
                tot[k] += _draw(r.get(k), C_OVER[k], rng)
            for k, a in RATE.items():
                mu_a, p = r.get(a), r.get(k)
                if mu_a is None or p is None: continue
                na = int(round(_draw(mu_a, C_ATT, rng)))
                if na <= 0: continue
                att[k]  += na
                made[k] += sum(1 for _ in range(na) if rng.random() < p)
            if rng.random() < p_dd: dd += 1
    out = dict(tot)
    for k in RATE:
        out[k] = (made[k] / att[k]) if att[k] else 0.0
    out["A/T"] = (tot["AST"] / tot["TOV"]) if tot["TOV"] else (tot["AST"] or 0.0)
    out["DD"]  = float(dd)
    return out

# ── 상대 조립 ────────────────────────────────────────────────────────────
# 지명 풀(시장가 상위 126명) 안에서 $200·포지션 합법으로 9명을 뽑는다.
# 비용은 시장 중간값을 쓴다(상대는 시장가에 산다고 가정).
# 포지션 자격은 DB가 G/F/C 수준까지만 담고 있으므로 **완화된 합법성**을 쓴다:
#   C 자격 >= 1 · G 자격 >= 2 · F 자격 >= 2.  (docs/05 한계 항목)
def pool():
    rows = [PL[p["name"]] for p in
            sorted([q for q in PL.values() if q["name"] in F],
                   key=lambda q: -(q["market_low"] + q["market_high"]) / 2)[:CM.POOL_N]]
    return rows

def cost(p): return (p["market_low"] + p["market_high"]) / 2.0
def has(p, ch): return ch in (p.get("pos") or "")

def legal(sel):
    return (sum(1 for p in sel if has(p, "C")) >= 1 and
            sum(1 for p in sel if has(p, "G")) >= 2 and
            sum(1 for p in sel if has(p, "F")) >= 2)

def greedy(rows, score, budget=200.0, n=9):
    """예산 $200을 **쓰는** 조립. 조립 규칙을 코드에 남긴다.

    ⚠️ 30차 1차 구현의 두 결함:
      (1) score/dollar 효율만 보고 9명을 채워서 **예산을 안 썼다** — 가치최대 상대가
          $200 중 $61만 쓰고 끝났다. 실제 상대는 예산을 다 쓴다.
      (2) 조립 실패 시 None을 돌려줬고, simulate()가 None을 "무작위 상대"로 해석해
          **빅스택 열이 평균 상대의 복제본**이 됐다(c1 8.76 vs 8.81). 조용한 대체였다.
          이제 실패는 FAILED 센티넬로 구분하고 그 열은 계산하지 않는다.

    규칙:
      1) score/cost 내림차순으로 9명을 채운다(예산 초과분 건너뜀).
      2) 포지션 합법이 아니면 점수 최하위를 부족 자격 최고점수로 교체(최대 20회).
      3) **업그레이드**: 남은 예산으로 (선택된 1명 ↔ 미선택 1명) 교환 중
         점수 증가가 가장 큰 것을 반복 적용한다. 합법·예산을 유지하는 교환만.
         더 이상 개선이 없거나 60회면 멈춘다.
    """
    cand = sorted(rows, key=lambda p: -score(p) / max(cost(p), 1.0))
    sel, spent = [], 0.0
    for p in cand:
        if len(sel) >= n: break
        if spent + cost(p) > budget: continue
        sel.append(p); spent += cost(p)
    # ⚠️ 30차 2차 결함: 교체 대상을 점수 최하위로만 골랐더니 **방금 넣은 선수가
    #   다시 빠졌다** — 빅스택은 G 점수가 낮으므로 넣은 G가 곧 최하위가 되어
    #   Josh Hart ↔ Ausar Thompson 이 무한 진동했다(20회 소진 후 실패).
    #   이제 (a) 필요 자격을 **가진** 선수는 빼지 않고, (b) 이미 충족된 최소치를
    #   깨뜨리는 교체도 하지 않는다.
    REQ = (("C", 1), ("G", 2), ("F", 2))
    def counts(lst): return {ch: sum(1 for p in lst if has(p, ch)) for ch, _ in REQ}
    for _ in range(30):
        if legal(sel): break
        cur = counts(sel)
        need = next((ch for ch, k in REQ if cur[ch] < k), None)
        if need is None: break
        order = sorted(range(len(sel)), key=lambda i: score(sel[i]))
        done = False
        for i in order:
            out = sel[i]
            if has(out, need): continue                    # (a) 필요 자격 보유자는 유지
            for p in cand:
                if p in sel or not has(p, need): continue
                if spent - cost(out) + cost(p) > budget: continue
                trial = sel[:i] + [p] + sel[i+1:]
                tc = counts(trial)
                if any(tc[ch] < min(k, cur[ch]) for ch, k in REQ): continue   # (b) 후퇴 금지
                spent += cost(p) - cost(out); sel[i] = p; done = True; break
            if done: break
        if not done: break
    if len(sel) != n or not legal(sel): return FAILED, spent
    # 3) 업그레이드 — 남은 예산을 점수로 바꾼다
    for _ in range(60):
        best = None
        for i, out in enumerate(sel):
            for p in cand:
                if p in sel: continue
                new_spent = spent - cost(out) + cost(p)
                if new_spent > budget: continue
                gain = score(p) - score(out)
                if gain <= 1e-9: continue
                trial = sel[:i] + [p] + sel[i+1:]
                if not legal(trial): continue
                if best is None or gain > best[0]: best = (gain, i, p, new_spent)
        if best is None: break
        _, i, p, new_spent = best
        sel[i] = p; spent = new_spent
    return [p["name"] for p in sel], spent

def z(p, cats):
    """정규화 없이 캣 합 — 조립용 거친 점수. value_reference.z_by_cat 재사용."""
    zb = (p.get("value_reference") or {}).get("z_by_cat") or {}
    return sum(zb.get(c, 0.0) for c in cats)

BIG   = ["REB","OREB","BLK","DD","FG%"]
GUARD = ["AST","STL","3PM","FT%","A/T","3P%"]

# ── 벤치마크 상대 (32차) — 사용자가 지정한 **고정 로스터**. 조립 알고리즘을 태우지 않는다.
# 전원 my_max >= market_high · 포지션 합법(C5 G4 F4) · 시장 상단 전액 $195.
# 검증 완료: 지정가 = DB market_high · 합 $195.
BENCHMARK = ["Karl-Anthony Towns","Derrick White","Desmond Bane","Kon Knueppel",
             "Donovan Clingan","Dyson Daniels","Rudy Gobert","Onyeka Okongwu","Nikola Vučević"]

FAILED = "__failed__"
BASELINE_TEAM = "__baseline__"

def baseline_prep():
    """**기준선 상대** — marginal()이 가정하는 상대를 그대로 팀으로 만든다.

    30차 발견: `cat_baselines`의 기준선은 지명 풀 126명의 **무제약** 평균이고,
    실제 상대는 $200·포지션 제약을 받는다. 둘은 캣별로 -15%~+13% 어긋난다
    (DD -15.3% · PTS -5.9% · AST -6.5% vs BLK +13.2% · OREB +8.0% · STL +6.3%).
    즉 marginal()의 판정 기준은 **어떤 실제 상대도 아니다.**
    사용자 검산 앵커(c6 FT% 22~25%)는 "상대가 기준선에 정확히 앉아 있다"는 가정이므로,
    그 가정을 그대로 구현한 상대를 5번째로 둬서 앵커와 직접 대조할 수 있게 한다.

    구성: baseline_per_game 값을 그대로 갖는 가상 선수 9명, GP는 지명 풀 평균.

    ⚠️ 40차 라인업 보정의 **예외**다. 이 상대는 포지션이 없는 가상 선수라 자격 제약을
    적용할 대상이 없고, 애초에 사용자 검산 앵커(c6 FT% 22~25%)를 재현하기 위한
    대조군이므로 보정을 넣으면 앵커가 움직여 대조 자체가 무의미해진다."""
    Bpg = CM.baselines_per_game()
    gp = statistics.mean([(F[p["name"]].get("GP") or 0) for p in pool() if p["name"] in F])
    avail = gp / 82.0
    cnts = [(k, Bpg[k]) for k in COUNT]
    # 시도량은 풀 평균, 성공률은 기준선 비율
    att_mu = {a: statistics.mean([F[p["name"]][a] for p in pool()
                                  if p["name"] in F and F[p["name"]].get(a) is not None])
              for a in RATE.values()}
    rts = [(k, a, att_mu[a], Bpg[k]) for k, a in RATE.items()]
    p_dd = CM.dd_game_prob(Bpg["PTS"], Bpg["REB"], Bpg["AST"])
    return [(avail, cnts, rts, p_dd)] * 9

def build_opponents(rng):
    rows = pool()
    opp = {}
    # (a) 평균 상대 — 예산·포지션 합법 무작위 9인. 반복 시행마다 다시 뽑는다.
    opp["random"] = None
    v, _ = greedy(rows, lambda p: z(p, CATS))                  # (b) 가치최대
    opp["value_max"] = v
    b, _ = greedy(rows, lambda p: z(p, BIG))                   # (c) 빅스택
    opp["big_stack"] = b
    g, _ = greedy(rows, lambda p: z(p, GUARD))                 # (d) 가드스택
    opp["guard_stack"] = g
    opp["baseline"] = BASELINE_TEAM                            # (e) 기준선 상대 (30차 추가)
    opp["benchmark"] = list(BENCHMARK)                         # (f) 벤치마크 (32차 · 고정)
    return opp

def random_roster(rows, rng, tries=400):
    for _ in range(tries):
        sel = rng.sample(rows, 9)
        if sum(cost(p) for p in sel) <= 200.0 and legal(sel):
            return [p["name"] for p in sel]
    return None

def wins(a, b):
    """캣별 승패. 동점은 무승부로 0.5."""
    out = {}
    for k in CATS:
        x, y = a[k], b[k]
        if x == y: out[k] = 0.5
        elif k in LOWER: out[k] = 1.0 if x < y else 0.0
        else:           out[k] = 1.0 if x > y else 0.0
    return out

BIG5 = ["REB","OREB","BLK","FG%","DD"]   # 32차: 동시 붕괴를 재는 5캣

def simulate(us, opp_names, rng, iters, rows=None):
    """캣별 승률 · 기대 승리캣 · 주간 승률 + **동시 붕괴 지표 3종**.

    ⚠️ 동시 붕괴는 캣별 승률의 **곱으로 계산하지 않는다.** 캣은 서로 상관돼 있다
    (같은 주에 빅맨이 다 죽으면 5캣이 함께 죽는다). 같은 시행 안에서 5캣이
    **동시에** 패한 횟수를 직접 센다."""
    acc = {k: 0.0 for k in CATS}; cats_won = []; weeks = 0
    big5_collapse = 0; blowout = 0
    pu = prep(us)
    po = (baseline_prep() if opp_names == BASELINE_TEAM
          else (prep(opp_names) if opp_names else None))
    for _ in range(iters):
        if po is not None: pt = po
        else:
            them = random_roster(rows, rng)
            if them is None: continue
            pt = prep(them, rates=_RND_RATE)
        w = wins(team_week_prepped(pu, rng), team_week_prepped(pt, rng))
        for k in CATS: acc[k] += w[k]
        s = sum(w.values()); cats_won.append(s)
        weeks += 1 if s >= WIN_LINE else 0
        if all(w[k] == 0.0 for k in BIG5): big5_collapse += 1   # 무승부는 패가 아니다
        if s <= 4: blowout += 1
    n = len(cats_won) or 1
    return {"cat_win_probs": {k: round(acc[k] / n, 4) for k in CATS},
            "expected_cats_won": round(statistics.mean(cats_won), 2) if cats_won else None,
            "weekly_win_rate": round(weeks / n, 4),
            "p_big5_collapse": round(big5_collapse / n, 4),
            "p_cats_won_le4": round(blowout / n, 4),
            "cats_won_sd": round(statistics.pstdev(cats_won), 3) if len(cats_won) > 1 else None,
            "iterations": n}

LABEL = {"random":"무작위","value_max":"가치최대","big_stack":"빅스택",
         "guard_stack":"가드스택","baseline":"기준선","benchmark":"벤치마크"}

if __name__ == "__main__":
    seed  = int(sys.argv[1]) if len(sys.argv) > 1 else 20261020
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    rng = random.Random(seed)
    rows = pool()
    OPP = build_opponents(rng)
    OK = [k for k in OPP if OPP[k] != FAILED]
    print(f"시드 {seed} · 시행 {iters} · 지명 풀 {len(rows)}명")
    if LINEUP_ADJ:
        random_rate_table(rows, random.Random(seed))
        print("라인업 보정 ON — 가용률 = GP/82 × 사용률. 무작위 상대만 자격집합별 평균 근사"
              " (표 %d종) · 그 외는 로스터별 실측 %d주" % (len(_RND_RATE), LINEUP_WEEKS))
    else:
        print("⚠️ 라인업 보정 OFF — 불가능한 로스터 운용을 계산한다")
    print()
    for k in OK:
        v = OPP[k]
        if v is None:              d = "매 시행 무작위 9인 (예산·포지션 합법)"
        elif v == BASELINE_TEAM:   d = "cat_baselines 기준선을 그대로 팀으로 (검산 앵커 대조용)"
        elif k == "benchmark":
            # 벤치마크는 사용자가 **시장 상단 전액**으로 지정한 팀이다.
            # 조립 상대는 예산 제약에 market_mid를 쓰지만(cost()), 여기서는 지정 기준인
            # market_high 합을 표시한다 — 섞으면 $167로 보여 지정과 어긋난다.
            d = "시장상단 합 $%d (중간가 합 $%.0f) · %s" % (
                sum(PL[n]["market_high"] for n in v), sum(cost(PL[n]) for n in v), ", ".join(v))
        else:                      d = "$%.0f · %s" % (sum(cost(PL[n]) for n in v), ", ".join(v))
        print(f"  {LABEL[k]:<6} {d}")
    for k in OPP:
        if OPP[k] == FAILED: print(f"  {LABEL[k]:<6} **조립 실패 — 미계산**")
    print()

    # ── 실제 상대 복원 (38차) ─────────────────────────────────────────
    REAL, RREP = RO.build()
    print("실제 상대(작년 옥션 12팀): 낙찰 %d건 · DB 매칭 %d · BBRef 보충 %d · 미매칭 %d"
          % (RREP["picks_total"], RREP["matched_in_db"], RREP["supplemented"],
             len(RREP["unmatched"])))
    print("  사용 팀 %d/%d · 로스터 앞 %d명"
          % (RREP["teams_used"], RREP["teams_total"], RREP["roster_n"]))
    if RREP["teams_dropped"]:
        print("  버린 팀: " + ", ".join("%s(%d명)" % d for d in RREP["teams_dropped"]))
    print("  ⚠️ 이것은 '작년 그 팀이 올해 강한가'가 아니라 '이 리그 사람들이 짜는 로스터"
          " 유형을 상대로 우리가 이기는가'다.\n")

    res = {}
    for co in CJ["cores"]:
        us = [x["candidates"][0]["name"] for x in co["slots"]]
        res[co["id"]] = {"roster": us}
        for key in OK:
            res[co["id"]][key] = simulate(us, OPP[key], rng, iters, rows)
        # ── 목적함수: 최소 승률(maximin). **값만 산출한다.**
        wr = {k: res[co["id"]][k]["weekly_win_rate"] for k in OK}
        lo = min(wr.values())
        res[co["id"]]["min_win_rate"] = lo
        res[co["id"]]["min_win_rate_vs"] = sorted([k for k in OK if wr[k] == lo])
        res[co["id"]]["tiebreak_p_big5_collapse"] = max(
            res[co["id"]][k]["p_big5_collapse"] for k in OK)
        # ── 1차 지표(38차): 실제 12팀 상대. 조립 상대가 아니라 **이 리그 사람들이
        #    실제로 짠 로스터**다. maximin은 7코어 전부 value_max 하나가 지배하고,
        #    value_max는 우리 z모델의 자기 최적해라 순위가 순환한다.
        rr = {}
        for mgr, names in REAL.items():
            rr[mgr] = simulate(us, names, random.Random(seed), iters, rows)
        wr_r = [v["weekly_win_rate"] for v in rr.values()]
        ec_r = [v["expected_cats_won"] for v in rr.values()]
        res[co["id"]]["real"] = rr
        res[co["id"]]["real_mean_win_rate"] = round(sum(wr_r)/len(wr_r), 4)
        res[co["id"]]["real_min_win_rate"] = round(min(wr_r), 4)
        res[co["id"]]["real_min_win_rate_vs"] = sorted(
            [m for m in rr if rr[m]["weekly_win_rate"] == min(wr_r)])
        res[co["id"]]["real_mean_expected_cats"] = round(sum(ec_r)/len(ec_r), 2)

    # ── 요구 표: 최소 승률 오름차순
    order = sorted(res, key=lambda cid: res[cid]["min_win_rate"])
    print("=== 7코어 × 상대 6종 주간 승률 · 최소 승률 · 동시 붕괴 지표 (최소 승률 오름차순) ===")
    hdr = f"{'코어':<5}" + "".join(f"{LABEL[k]:>9}" for k in OK) + f"{'최소':>8}{'5캣붕괴':>9}{'승리<=4':>9}{'승리캣SD':>9}"
    print(hdr); print("-" * len(hdr))
    for cid in order:
        d = res[cid]
        worst = max(OK, key=lambda k: d[k]["p_big5_collapse"])
        print(f"{cid:<5}" + "".join(f"{d[k]['weekly_win_rate']*100:>8.1f}%" for k in OK)
              + f"{d['min_win_rate']*100:>7.1f}%{d[worst]['p_big5_collapse']*100:>8.1f}%"
              + f"{max(d[k]['p_cats_won_le4'] for k in OK)*100:>8.1f}%"
              + f"{max(d[k]['cats_won_sd'] for k in OK):>9.2f}")
    # ── 1차 지표 표 (38차)
    o2 = sorted(res, key=lambda cid: -res[cid]["real_mean_win_rate"])
    print("\n=== 1차 지표: 실제 12팀 상대 (평균 주간 승률 내림차순) ===")
    h3 = f"{'코어':<5}{'평균':>8}{'최저':>8}{'최저상대':>10}{'기대승리캣':>11}{'(참고)maximin':>14}"
    print(h3); print("-" * len(h3))
    for cid in o2:
        d = res[cid]
        print(f"{cid:<5}{d['real_mean_win_rate']*100:>7.1f}%{d['real_min_win_rate']*100:>7.1f}%"
              f"{','.join(d['real_min_win_rate_vs']):>10}"
              f"{d['real_mean_expected_cats']:>11.2f}{d['min_win_rate']*100:>13.1f}%")
    print("  1차(실제12) 순위: " + " > ".join(o2))
    print("  2차(maximin) 순위: " + " > ".join(sorted(res, key=lambda c: -res[c]["min_win_rate"])))
    print("  ⚠️ 값만 산출한다. 채택은 사람이 한다(32차) — 판단표 변경은 사용자 결정.")

    print("\n※ 5캣붕괴·승리<=4·승리캣SD는 상대 6종 중 **최악값**. 상대별 전체는 data/matchup_sim.json.")
    print("※ 최소 승률 동률 시 우선순위: 5캣 동시 붕괴 P가 낮은 쪽 (tiebreak_p_big5_collapse).")

    # ── 상대별 붕괴 지표 전체
    print("\n=== 상대별 5캣 동시 붕괴 P / P(승리캣<=4) / 승리캣 SD ===")
    h2 = f"{'코어':<5}" + "".join(f"{LABEL[k]:>22}" for k in OK)
    print(h2); print("-" * len(h2))
    for cid in order:
        d = res[cid]
        print(f"{cid:<5}" + "".join(
            f"{d[k]['p_big5_collapse']*100:>7.1f}/{d[k]['p_cats_won_le4']*100:>6.1f}/{d[k]['cats_won_sd']:>6.2f}"
            for k in OK))

    # ── 산출물을 계획 파일에서 분리 (32차)
    # matchup_sim.opponents가 cores.json에 살면 상대 로스터 이름이 core_hits에 잡힌다.
    # core_hits 단일화는 증상만 막았다 — 파일을 분리해 근본을 없앤다.
    out = {"generated_by": "tool/matchup_sim.py", "seed": seed, "iterations": iters,
           "win_line": WIN_LINE, "games_per_week": list(GAMES_RANGE),
           "games_per_week_mean": CM.GAMES_PER_WEEK,
           "games_per_week_p4": CM.WEEK_GAMES_P4,
           "games_per_week_basis": "확정 일정 2026-10-20~2027-04-11 = 174일 = 24.857주 · 82경기 → 3.299 (38차)",
           "overdispersion_c": C_OVER, "attempt_c": C_ATT, "big5": BIG5,
           "opponents": {k: (OPP[k] if OPP[k] not in (None, BASELINE_TEAM, FAILED) else
                             {"random": "매 시행 무작위 9인", BASELINE_TEAM: "cat_baselines 기준선 팀",
                              FAILED: "조립 실패"}.get(OPP[k], "무작위")) for k in OPP},
           "objective": {
               "layer1_primary": "real_mean_win_rate — 실제 12팀 상대 평균 주간 승률 (38차 신설)",
               "layer1_why": ("조립 상대는 우리 모델이 만든 팀이다. 실제 12팀은 이 리그 "
                              "사람들이 실제로 짠 로스터이므로 성향의 대리 표본이 된다."),
               "layer2_robustness": "min_win_rate (maximin — 상대 6종 중 최저 주간 승률)",
               "layer2_why": ("'최적화된 상대에게 얼마나 버티는가'의 상한 테스트로 유효하다. "
                              "다만 **선택 기준이 되면 안 된다** — 아래 진단 참조."),
               "diagnosis_38": [
                   "min_win_rate_vs 가 7코어 전부 value_max 다 — maximin은 단일 상대가 지배한다",
                   "value_max 는 우리 z모델의 자기 최적해이므로 이 순위는 "
                   "'우리 모델에 얼마나 가까운가'에 가깝다",
                   "docs/05 2b-3이 'value_max는 현실적 상대가 아니다'라고 경고했는데, "
                   "그 상대가 목적함수를 단독 지배한다는 사실은 기록돼 있지 않았다"],
               "tiebreak": "min_win_rate 동률이면 p_big5_collapse 낮은 쪽",
               "note": ("값만 산출한다. 이 지표로 코어를 고르지 않는다(32차) — "
                        "38차에 기준점을 교체했지만 **채택은 여전히 사람이 한다.**")},
           "real_opponents": {"source": "data/prior_auction_2025_26/results.json",
                              "built_by": "tool/real_opponents.py",
                              "rosters": REAL, "report": RREP,
                              "interpretation": ("'작년 그 팀이 올해 강한가'가 아니다. "
                                                 "작년 낙찰 조합을 현재 스탯으로 평가한 것이므로 "
                                                 "**이 리그의 드래프트 성향 대리 표본**이다. "
                                                 "가격·예산 제약은 작년 것(12팀·로스터10)이다.")},
           "collapse_note": ("p_big5_collapse는 캣별 승률의 곱이 아니다 — 같은 시행에서 "
                             "REB·OREB·BLK·FG%·DD 5캣이 **동시에** 패한 횟수를 직접 셌다. "
                             "무승부는 패로 세지 않는다."),
           "cores": res}
    json.dump(out, io.open(f"{BASE}/data/matchup_sim.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # cores.json에는 참조만
    for co in CJ["cores"]:
        for k in ("cat_win_probs", "expected_cats_won", "weekly_win_rate"):
            co.pop(k, None)
    CJ.pop("matchup_sim", None)
    CJ["matchup_sim_ref"] = {
        "file": "data/matchup_sim.json", "generated_by": "tool/matchup_sim.py",
        "why_separate": ("32차: 시뮬 산출물이 cores.json에 살면 **상대 로스터 이름**이 "
                         "core_hits에 집계돼 auto basis가 무효화된다(30차 사고 6건). "
                         "core_hits 단일화는 증상만 막았다 — 파일 분리가 근본 제거다."),
        "keys": ["cores[<id>].{cat_win_probs,expected_cats_won,weekly_win_rate,"
                 "p_big5_collapse,p_cats_won_le4,cats_won_sd,min_win_rate}"]}
    json.dump(CJ, io.open(f"{BASE}/data/cores.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/matchup_sim.json 기록 · cores.json에는 matchup_sim_ref 참조만")
