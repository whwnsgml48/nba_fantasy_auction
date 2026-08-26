#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""my_max(입찰 상한) 산정 모델 — 실측 기반 z-score 가치.

## 왜 필요한가
22차까지 실측·가중치·시장가를 모두 실측 기반으로 정비했지만 **`my_max`는 한 번도
재산정하지 않았습니다.** 드래프트에서 실제로 쓰는 숫자가 `my_max`(입찰 상한)이므로
체인의 마지막 칸이 옛 기준으로 남아 있던 셈입니다.

## 방법
1. 캣별 기여도 = 계수형: `per-game × GP/82` · 비율형: `(rate − 기준선) × 시도량 × GP/82`
   (TOV는 부호 반전 — 적을수록 좋음)
2. 지명 풀(시장가 상위 126명) 안에서 캣별로 표준화(z) → 캣 간 단위를 통일
3. 13캣 z 합계 = 종합 가치. **대체 수준(126위)** 을 0점으로 이동
4. 달러 환산: 총 재량 예산 = $2,800 − 126×$1 = **$2,674** 를 양수 z 비중대로 배분 + $1

## 한계 (반드시 함께 읽을 것)
- **DD 제외**: BBRef가 집계하지 않아 172명 중 25명만 실측. 13캣이 아니라 12캣 기준이다.
  빅맨은 DD가 유리하므로 이 모델은 빅맨을 약간 과소평가한다.
- **동일 가중**: 12캣을 같은 비중으로 본다. 실제로는 코어가 포기하는 캣이 있어
  코어별 가치가 다르다(이 모델은 코어 무관 '일반 가치').
- **출장 투영 아님**: GP는 과거 2시즌 혼합이다. 부상 복귀·역할 변화는 미반영.
- 따라서 이 값은 **참고선**이고, `my_max`를 덮어쓰는 것이 아니라 대조용이다.
"""
import json, io, os, statistics, math
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
PL={p["name"]:p for p in json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))}
CJ=json.load(io.open(f"{BASE}/data/cores.json",encoding="utf-8"))
CB=CJ["opponent_baseline"]["cat_baselines"]
RATE={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
# 24차: DD 편입. 이전엔 실측 소스가 25명뿐이라 제외했고, 그래서 이 모델은
# "DD 미포함 → 빅맨 소폭 과소평가"라는 알려진 편향을 안고 있었다.
# 이제 DD가 경기당 확률로 추정돼 다른 캣과 같은 척도로 들어온다.
COUNT=["PTS","REB","OREB","AST","STL","BLK","TOV","3PM","DD"]
CATS=COUNT+list(RATE)+["A/T"]          # 13캣 전부
LOWER={"TOV"}
BUDGET=2800; DRAFTED=126
def avail(r): return (r.get("GP") or 0)/82.0

def contrib(name, cat):
    r=F.get(name)
    if not r: return None
    if cat=="A/T":
        L=r.get("at_marginal_lift")
        return None if L is None else L*avail(r)
    if cat in RATE:
        v,a=r.get(cat),r.get(RATE[cat])
        if v is None or a is None: return None
        return (v-CB[cat]["baseline_per_game"])*a*avail(r)
    v=r.get(cat)
    if v is None: return None
    x=v*avail(r)
    return -x if cat in LOWER else x

def pool():
    return sorted([p for p in PL.values() if p["name"] in F],
                  key=lambda p:-(p["market_low"]+p["market_high"])/2)[:DRAFTED]

def zscores():
    P=pool()
    stats={}
    for cat in CATS:
        v=[contrib(p["name"],cat) for p in P]
        v=[x for x in v if x is not None]
        m=statistics.mean(v); sd=statistics.pstdev(v) or 1.0
        stats[cat]=(m,sd)
    Z={}
    for name in PL:
        if name not in F: continue
        tot=0.0; per={}
        for cat in CATS:
            x=contrib(name,cat)
            if x is None: continue
            m,sd=stats[cat]
            z=(x-m)/sd; per[cat]=round(z,3); tot+=z
        Z[name]={"z_total":round(tot,3),"z":per}
    return Z, stats

def values():
    Z,_=zscores()
    P=[p["name"] for p in pool()]
    # 대체 수준 = 지명 풀 최하위(126위)의 z 합계
    zs=sorted((Z[n]["z_total"] for n in P if n in Z), reverse=True)
    repl=zs[min(len(zs)-1, DRAFTED-1)]
    disc=BUDGET-DRAFTED*1
    above={n:max(0.0, Z[n]["z_total"]-repl) for n in Z}
    tot=sum(above[n] for n in P if n in above) or 1.0
    out={}
    for n,zz in Z.items():
        val=1+ (above[n]/tot)*disc
        out[n]={"z_total":zz["z_total"],"z_above_replacement":round(above[n],3),
                "value":int(round(val)),"z":zz["z"]}
    return out, repl
