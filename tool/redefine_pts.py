#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PTS 엘리트 기준 재정의 — 한계기여 기반 통일 정의.

문제 (13~16차에 반복 지적):
  · w3(엘리트)가 41명 = DB의 24%. "엘리트"가 아니고, 그 결과 "팀 가중치 합 >= 6" 규칙이
    PTS에서 무의미해져 c1·c4·c5·c6이 "PTS 포기 선언인데 규칙상 확보"로 모순.
  · 더 심각한 것: w2(플러스) 37명 중 29명이 한계기여 **음수**. "플러스"가 실제로는 마이너스.

정의 (docs/07 A/T · 16차 TOV와 동일한 한계기여 틀):
  기준선   = 상대 선발 슬롯당 기대 PTS (지명 풀 126명 중 MPG>=25 평균)
  한계기여 = 선수 PTS − 기준선        양수만 캣에 도움
  w3 엘리트  : 자격 풀 상위 10% 경계값 이상
  w2 플러스  : 자격 풀 상위 25% 경계값 이상
  w1 약플러스: 한계기여 > 0
  미부여     : 한계기여 <= 0  (기준선 이하 — 도움 안 됨)

경계는 **값 임계**로 적용한다(순위가 아니라). 동률 선수가 다른 등급을 받으면
단조성(M1)이 깨지기 때문이다.
"""
import json, io, os, re, statistics
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
pl=json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))
c=json.load(io.open(f"{BASE}/data/cores.json",encoding="utf-8"))
MINGP=40; CAT="PTS"

top=sorted([p for p in pl if p["name"] in F], key=lambda p:-(p["market_low"]+p["market_high"])/2)[:126]
pool=[F[p["name"]][CAT] for p in top
      if (F[p["name"]].get("MPG") or 0)>=25 and F[p["name"]].get(CAT) is not None]
B=round(statistics.mean(pool),2)
q=sorted([F[p["name"]][CAT] for p in pl
          if p["name"] in F and (F[p["name"]].get("GP") or 0)>=MINGP
          and F[p["name"]].get(CAT) is not None], reverse=True)
th3=q[int(len(q)*0.10)]      # 상위 10% 경계값
th2=q[int(len(q)*0.25)]      # 상위 25% 경계값
print(f"기준선 {B} (지명 풀 MPG>=25, {len(pool)}명) · 자격 풀 {len(q)}명")
print(f"임계값: w3 >= {th3} · w2 >= {th2} · w1 > {B} · 미부여 <= {B}")

def grade(v):
    if v>=th3: return 3
    if v>=th2: return 2
    if v>B:    return 1
    return None
added=chg=rm=skip=0
for p in pl:
    r=F.get(p["name"])
    if not r or (r.get("GP") or 0)<MINGP or r.get(CAT) is None:
        if p["cat_weights"].get(CAT) is not None: skip+=1
        continue
    v=r[CAT]; new=grade(v); cur=p["cat_weights"].get(CAT)
    p["pts_context"]={"PTS":v,"baseline":B,"marginal_lift":round(v-B,2),
      "thresholds":{"w3":th3,"w2":th2},"GP":r["GP"],"MPG":r["MPG"]}
    if new is None:
        if cur is not None: p["cat_weights"].pop(CAT); rm+=1
    else:
        if cur is None: added+=1
        elif cur!=new: chg+=1
        p["cat_weights"][CAT]=new
    order=re.findall(r"([A-Z/%0-9]+)\d", p["cats"])
    parts=[f"{c2}{p['cat_weights'][c2]}" for c2 in order if c2 in p["cat_weights"]]
    parts+=[f"{c2}{v2}" for c2,v2 in p["cat_weights"].items() if c2 not in order]
    p["cats"]=" ".join(parts)
json.dump(pl,io.open(f"{BASE}/data/players.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
n=[len([1 for p in pl if p["cat_weights"].get(CAT)==k]) for k in (3,2,1)]
print(f"\n신규 {added} · 변경 {chg} · 제거 {rm} · 자격미달 유지 {skip}")
print(f"결과: PTS 보유 {sum(n)}명 (w3 {n[0]}={n[0]/174*100:.0f}% · w2 {n[1]} · w1 {n[2]})")

# 기준선을 cores.json에 기록
c["opponent_baseline"]["per_slot_PTS"]=B
c["opponent_baseline"]["pts_thresholds"]={"w3":th3,"w2":th2,
  "method":"자격 풀(GP>=40) 상위 10%/25% 경계값 · 한계기여 양수 필수 · 값 임계로 적용"}
json.dump(c,io.open(f"{BASE}/data/cores.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("cores.json.opponent_baseline에 per_slot_PTS · pts_thresholds 기록")
