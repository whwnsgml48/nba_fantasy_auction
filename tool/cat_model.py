#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""캣 평가 모델 (21차 정정판) — 단일 소스.

## 왜 정정했나 🔴
16~20차는 **선발 7명만 집계**한다고 가정했습니다. **틀렸습니다.**
야후 판타지는 라인업을 **매일** 세팅하고, NBA 팀들은 서로 다른 날에 경기합니다.
월요일에 선발이던 선수가 화요일엔 벤치이고, 벤치 선수가 그날 선발로 올라갑니다.

  로스터 9명 × 주 3.5경기 = 31.5 선수-경기
  선발 슬롯 7개 × 7일      = 49 슬롯-일   → 용량이 남는다

즉 **9명 전원의 스탯이 집계됩니다.** 같은 날 8명 이상이 겹칠 때만 손실이 생기고,
그건 이 모델에서 미반영(보수적으로 무시)입니다.
`slot`/`BN` 표기는 명목 스케치이고 실제 캣 기여와 무관합니다.

## 출장 경기 수 가중
주간 기여 ∝ 경기당 스탯 × 그 주 출장 경기수. 시즌 가용률 = GP/82.
82경기 선수는 50경기 선수의 1.64배 기여합니다. 결장한 선수의 슬롯-일은 다른 선수가
채우지만 **그 선수의 경기는 이미 계산돼 있으므로 보상되지 않습니다** — 그냥 잃습니다.
따라서 계수형 캣은 `per-game × GP/82`, 비율형 캣은 시도량도 같은 가중을 적용합니다.

## 기준선
상대도 9명을 지명 풀(시장가 상위 126명)에서 뽑습니다. 따라서 슬롯당 기준선은
**지명 풀 전체 평균**(MPG 필터 없음 — 9칸 전부 집계되므로)에 같은 GP 가중을 적용한 값입니다.
"""
import json, io, os, statistics, math
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# build_measured.py가 이 모듈의 DD 추정 함수를 쓰는데, 그 스크립트가 만드는 파일이
# measured_full.json이다. import 시점에 파일이 없어도 죽지 않아야 순환이 끊긴다
# (DD 수식은 데이터 의존이 없는 순수 함수다).
try:
    F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
except FileNotFoundError:
    F={}
PL={p["name"]:p for p in json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))}
RATE={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
# 24차: DD 편입. 이전에는 evaluate()가 dd_target 플래그만 보고 **측정 없이 +1캣**을
# 줬다 — 코어 7개 중 6개가 그 공짜 캣에 승리선을 의존했다. 이제 DD도 다른 캣과 똑같이
# 경기당 값(더블더블 확률)으로 들어와 marginal()로 판정된다. 아래 dd_game_prob 참조.
COUNT=["PTS","REB","OREB","AST","STL","BLK","TOV","3PM","DD"]
LOWER={"TOV"}
CATS=COUNT+list(RATE)+["A/T"]
POOL_N=126
def avail(r): return (r.get("GP") or 0)/82.0

def baselines_per_game():
    """선수 가중치용 기준선 — 경기당·비가중.
    가중치는 '그 선수가 뛸 때 무엇을 주는가'(실력)를 재는 값이므로 출장률을 섞지 않는다.
    출장 리스크는 GP·gp_qualified·flag가 따로 담당한다."""
    top=sorted([p for p in PL.values() if p["name"] in F],
               key=lambda p:-(p["market_low"]+p["market_high"])/2)[:POOL_N]
    B={}
    for cat in COUNT:
        v=[F[p["name"]][cat] for p in top if F[p["name"]].get(cat) is not None]
        B[cat]=round(statistics.mean(v),4)
    for cat,at in RATE.items():
        v=[F[p["name"]] for p in top if F[p["name"]].get(cat) is not None and F[p["name"]].get(at) is not None]
        B[cat]=round(sum(r[cat]*r[at] for r in v)/sum(r[at] for r in v),5)
    B["A/T"]=round(B["AST"]/B["TOV"],4)
    return B

def player_lift(name, cat, Bpg):
    """선수 한계기여 — 경기당 기준. 가중치 부여·검증에 쓴다."""
    r=F.get(name)
    if not r: return None
    b=Bpg[cat]
    if cat=="A/T": return r.get("at_marginal_lift")
    if cat in RATE:
        v,a=r.get(cat),r.get(RATE[cat])
        return None if (v is None or a is None) else round((v-b)*a*100,2)
    v=r.get(cat)
    if v is None: return None
    return round(b-v,3) if cat in LOWER else round(v-b,3)

def baselines():
    """지명 풀 상위 126명 · GP 가중 · 슬롯당 기대치."""
    top=sorted([p for p in PL.values() if p["name"] in F],
               key=lambda p:-(p["market_low"]+p["market_high"])/2)[:POOL_N]
    B={}
    for cat in COUNT:
        v=[F[p["name"]] for p in top if F[p["name"]].get(cat) is not None and F[p["name"]].get("GP")]
        B[cat]=round(statistics.mean(r[cat]*avail(r) for r in v),4)
    for cat,at in RATE.items():
        v=[F[p["name"]] for p in top if F[p["name"]].get(cat) is not None
           and F[p["name"]].get(at) is not None and F[p["name"]].get("GP")]
        num=sum(r[cat]*r[at]*avail(r) for r in v); den=sum(r[at]*avail(r) for r in v)
        B[cat]=round(num/den,5)
    B["A/T"]=round(B["AST"]/B["TOV"],4)
    return B

def marginal(names, cat, B):
    """팀 한계기여. 양수 = 그 캣을 이긴다. names는 로스터 9명 전원."""
    b=B[cat]
    if cat=="A/T":
        rr=[F[n] for n in names if n in F and F[n].get("AST") is not None
            and F[n].get("TOV") is not None and F[n].get("GP")]
        if not rr: return None
        a=sum(r["AST"]*avail(r) for r in rr); t=sum(r["TOV"]*avail(r) for r in rr)
        return round(a/t-b,3)
    if cat in RATE:
        at=RATE[cat]
        rr=[F[n] for n in names if n in F and F[n].get(cat) is not None
            and F[n].get(at) is not None and F[n].get("GP")]
        if not rr: return None
        num=sum(r[cat]*r[at]*avail(r) for r in rr); den=sum(r[at]*avail(r) for r in rr)
        return round((num/den-b)*den*100,1)
    rr=[F[n] for n in names if n in F and F[n].get(cat) is not None and F[n].get("GP")]
    if not rr: return None
    t=sum(r[cat]*avail(r) for r in rr); base=b*len(rr)
    return round((base-t) if cat in LOWER else (t-base),1)

def evaluate(names, B=None):
    """로스터 9명의 13캣 판정. 승리 캣 수는 **전부 실측/추정 기반**이다.

    ⚠️ 24차 정정: 이전 시그니처는 evaluate(names, B, dd_target=True)였고,
    dd_target이 참이면 **측정 없이 +1캣**을 더했다. DD 실측 소스가 25명뿐이라
    그렇게 뒀던 것인데, 코어 7개 중 6개가 그 공짜 캣으로 승리선(7캣)을 넘고 있었다 —
    가정 하나가 판정 전체를 떠받치는 구조였다. 지금은 DD도 dd_game_prob으로 추정해
    다른 12캣과 똑같이 marginal()로 판정한다."""
    B=B or baselines()
    cm={c:marginal(names,c,B) for c in CATS}
    win=[c for c,v in cm.items() if v is not None and v>0]
    lose=[c for c,v in cm.items() if v is not None and v<=0]
    return cm, len(win), win, lose

def rel_margin(cat, v, B, names=None):
    """상대 마진(%) — 캣 간 비교용. 기준선 대비.

    ⚠️ 29차 정정 — **비율캣 분모가 틀렸다.**
    marginal()의 비율캣 반환값은 v = (rate − b) × 시도량 × 100 이다(볼륨 레버리지).
    이전 구현은 이것을 계수캣과 같은 분모(b×9)로 나눴다:

        (구) v/100/(b*9)*100 = (rate−b)·att/(9b)·100

    여기서 att/9 가 남는다. 팀 시도량은 캣마다 전혀 다르므로 **캣별로 다른 배율**로
    부풀었다 — c6 기준 FG% **10.5배** · FT% 3.3배 · 3P% 2.4배. 계수캣과 같은 자가 아니고,
    비율캣끼리도 같은 자가 아니다. "7캣 전부 N% 이상 마진" 같은 **캣 간 비교가 무의미**했다.

        (신) (rate − b)/b × 100          시도량을 빼고 순수 비율 개선

    비율캣은 시도량 합(den)이 필요하므로 names를 받는다. names 없이 비율캣을 부르면
    계산할 수 없으므로 None을 돌려준다 — 조용히 틀린 값을 내는 것보다 낫다.
    (볼륨 레버리지 자체는 marginal()의 절대값에 그대로 남아 있다. 여기서 빼는 것은
     '캣 간 비교용 무차원 척도'에서다.)"""
    if v is None: return None
    b=B[cat]
    if cat in RATE:
        if not names: return None
        at=RATE[cat]
        rr=[F[n] for n in names if n in F and F[n].get(cat) is not None
            and F[n].get(at) is not None and F[n].get("GP")]
        den=sum(r[at]*avail(r) for r in rr)
        if not den: return None
        num=sum(r[cat]*r[at]*avail(r) for r in rr)
        return (num/den - b)/b*100
    if cat=="A/T":  return v/b*100
    return v/(b*9)*100

# ── DD (더블더블) 추정 ──────────────────────────────────────────────────
# 23차까지 evaluate()는 dd_target이면 **측정 없이 +1캣**을 줬다. 코어 7개 전부가
# 그 공짜 1캣에 승리선(7캣)을 의존하고 있었으므로, 가정 하나가 판정을 떠받치고 있었다.
# BBRef가 DD를 집계하지 않아 실측이 25명(리더보드)뿐이라 그렇게 뒀던 것인데,
# per-game PTS·REB·AST가 있으면 추정은 가능하다.
#
# 모델: 한 경기에서 PTS·REB·AST 중 **2개 이상이 10 이상**일 확률 × 출장경기수.
#   각 스탯을 정규분포 N(μ, σ²)로 근사하고 연속성 보정(10 이상 → 9.5 초과)을 쓴다.
#   σ는 과분산 포아송 형태 σ = c·√μ 로 잡는다. c는 실측 DD를 보지 않고 미리 정한다
#   (검증 집합에 맞춰 c를 튜닝하면 검증이 무의미해진다):
#     PTS c=1.50  — 25득점 선수의 경기간 SD ≈ 7.5
#     REB c=1.10  — 10리바운드 선수의 SD ≈ 3.5
#     AST c=1.05  — 8어시스트 선수의 SD ≈ 3.0
#
# ⚠️ 알려진 편향 두 가지 — 결과를 읽을 때 반드시 같이 본다:
#   (1) **독립 가정**. PTS·REB는 출장시간·사용률이 같이 밀어올리므로 양의 상관이 있다.
#       독립으로 곱하면 P(둘 다 ≥10)이 **과소**추정된다 → 빅맨에서 저추정 경향.
#   (2) **트리플더블 경로 무시 아님**: 2개 이상이므로 TD도 포함된다. 다만 STL·BLK가
#       10을 넘는 경우(사실상 0)는 무시한다.
_DD_C = {"PTS": 1.50, "REB": 1.10, "AST": 1.05}
_DD_THRESHOLD = 10
_DD_CONT = 0.5          # 연속성 보정

def _norm_sf(z):
    """P(Z > z). math.erfc 기반 — 외부 의존 없이."""
    return 0.5*math.erfc(z/math.sqrt(2.0))

def dd_game_prob(pts, reb, ast):
    """한 경기에서 더블더블이 날 확률. 세 스탯의 경기당 평균을 받는다."""
    ps=[]
    for cat, mu in (("PTS",pts),("REB",reb),("AST",ast)):
        mu = mu or 0.0
        if mu <= 0: ps.append(0.0); continue
        sd = _DD_C[cat]*math.sqrt(mu)
        ps.append(_norm_sf(((_DD_THRESHOLD-_DD_CONT)-mu)/sd))
    p1,p2,p3 = ps
    # P(2개 이상) = Σ 쌍곱 − 2·삼중곱
    return p1*p2 + p1*p3 + p2*p3 - 2*p1*p2*p3

def dd_estimate(pts, reb, ast, gp):
    """시즌 DD 추정 = 경기당 확률 × 출장경기수."""
    if not gp: return None
    return dd_game_prob(pts, reb, ast)*gp

def dd_from_row(r):
    """measured_full.json 한 행에서 DD를 추정한다."""
    if not r: return None
    return dd_estimate(r.get("PTS"), r.get("REB"), r.get("AST"), r.get("GP"))
