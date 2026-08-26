#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOV 가중치 체계적 부여.

모델: docs/07의 A/T 한계기여와 같은 구조를 쓴다.
  베이스라인 = 나머지 6명 선발의 TOV 합계 10.0 → 슬롯당 1.67
  한계기여   = 1.67 − 선수 TOV        (양수 = 팀 TOV 총합을 줄임 = 캣에 도움)
  자격 풀 150명(GP>=40)의 중앙값 1.65가 이 베이스라인과 사실상 동일해 근거가 겹친다.

등급 (한계기여 기준):
  w3 엘리트  TOV <= 0.8  (한계기여 >= +0.87)
  w2 플러스  TOV 0.9~1.2 (+0.47 ~ +0.77)
  w1 약플러스 TOV 1.3~1.5 (+0.17 ~ +0.37)
  미부여     TOV >= 1.6  (베이스라인 이상 — 팀 TOV를 줄이지 못함)

주의: TOV는 MPG와 상관 +0.717이다. 저출장 선수가 유리해지는 것은 이 캣의 구조적 성질이고
      (야후 H2H는 선발만 집계 → 실제로 팀 총합을 낮춘다), 전체 가치는 my_max가 담당한다.
      해석을 돕기 위해 tov_context에 MPG와 한계기여를 함께 기록한다.
"""
import json, io, os, re
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
pl=json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))
BASELINE=10.0/6.0          # 1.667 — docs/07 모델과 동일
MINGP=40
def grade(t):
    if t<=0.8: return 3
    if t<=1.2: return 2
    if t<=1.5: return 1
    return None

added=changed=removed=skipped=0
for p in pl:
    r=F.get(p["name"])
    if not r or (r.get("GP") or 0)<MINGP or r.get("TOV") is None:
        # 자격 미달: 기존 가중치를 건드리지 않되 이유를 남긴다
        if p["cat_weights"].get("TOV") is not None:
            p["tov_context"]={"status":"unqualified_kept",
              "reason":"GP<%d 또는 실측 없음 — 기존 가중치 유지(데이터 미검증)"%MINGP,
              "GP":(r or {}).get("GP"),"TOV":(r or {}).get("TOV"),"MPG":(r or {}).get("MPG")}
            skipped+=1
        continue
    t=r["TOV"]; new=grade(t); cur=p["cat_weights"].get("TOV")
    lift=round(BASELINE-t,3)
    p["tov_context"]={"status":"assigned","TOV":t,"MPG":r["MPG"],"GP":r["GP"],
      "baseline_per_slot":round(BASELINE,3),"marginal_lift":lift,
      "note":"양수 한계기여 = 팀 TOV 총합을 줄임. MPG 상관 +0.717이므로 저출장 선수가 유리한 것은 캣의 구조적 성질."}
    if new is None:
        if cur is not None: p["cat_weights"].pop("TOV"); removed+=1
    else:
        if cur is None: added+=1
        elif cur!=new: changed+=1
        p["cat_weights"]["TOV"]=new
    # cats 문자열 재생성
    order=re.findall(r"([A-Z/%0-9]+)\d", p["cats"])
    parts=[f"{c}{p['cat_weights'][c]}" for c in order if c in p["cat_weights"]]
    parts+=[f"{c}{v}" for c,v in p["cat_weights"].items() if c not in order]
    p["cats"]=" ".join(parts)
json.dump(pl,io.open(f"{BASE}/data/players.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
n=[len([1 for p in pl if p["cat_weights"].get("TOV")==k]) for k in (3,2,1)]
print(f"신규 부여 {added} · 등급 변경 {changed} · 제거 {removed} · 자격미달 유지 {skipped}")
print(f"결과: TOV 보유 {sum(n)}명 (w3 {n[0]} · w2 {n[1]} · w1 {n[2]}) — 이전 15명")
print(f"베이스라인 슬롯당 {BASELINE:.3f} TOV (docs/07 모델과 동일)")
