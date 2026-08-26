#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전 캣에 한계기여 통일 정의 적용 (18차).

17차에서 PTS·TOV에 적용한 정의를 나머지 캣에 확장한다.

  기준선 = 상대 선발 1슬롯의 기대치 — 지명 풀(시장가 상위 126명) 중 MPG>=25
           계수형: 산술평균 · 비율형: 시도량 가중평균
  한계기여 = 계수형  실측 − 기준선      (TOV만 부호 반대)
             비율형  (rate − 기준선) × 시도량 × 100   ← 볼륨 레버리지
  등급    w3 자격 풀(GP>=40) 상위 10% 경계값 이상
          w2 자격 풀 상위 25% 경계값 이상
          w1 한계기여 > 0
          미부여 한계기여 <= 0   (기준선 이하 = 캣에 도움 안 됨)

경계는 값 임계로 적용한다(순위로 자르면 동률이 다른 등급을 받아 단조성 M1이 깨진다).
GP<40 자격 미달자는 기존 가중치를 유지하고 weights_data_verified=false로 남긴다.
"""
import json, io, os, re, statistics
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
pl=json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))
c=json.load(io.open(f"{BASE}/data/cores.json",encoding="utf-8"))
MINGP=40
# 23차: PTS·TOV도 편입. 원래 redefine_pts.py·assign_tov.py가 따로 부여했는데
# 기준선이 갱신될 때 함께 재적합되지 않아 divergence가 남았다(Grant PTS lift -0.018인데 w1).
# 두 스크립트는 정의 문서·context 필드 생성용으로 남기고, **등급 부여는 여기 단일화**한다.
# 24차: DD 편입. DD는 BBRef 미집계라 손으로 36명에게 부여돼 있었고, 기준선이 갱신될 때
# 함께 재적합되지 않았다. 이제 정규근사 추정값(경기당 확률)으로 다른 캣과 같은 규칙을 받는다.
COUNT=["PTS","REB","OREB","AST","STL","BLK","TOV","3PM","DD"]
RATE={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
# 23차: A/T도 여기로 편입했다. 이전엔 apply_full_weights.py가 따로 부여해서
# 기준선이 갱신될 때 함께 재적합되지 않았고, M1(단조성)/M2(비양수 lift)가 깨졌다.
# A/T는 원 비율(A/T)이 아니라 볼륨 인지 필드 at_marginal_lift를 쓴다 —
# 원 비율로 자르면 Luke Kornet(4.75, 저볼륨)이 엘리트로 올라온다(오류 패턴 ③).
ATLIFT="at_marginal_lift"
# ⚠️ 23차: 등급 부여 기준선을 **baseline_per_game(21차 정정 기준)**으로 통일했다.
# 이 스크립트는 원래 자체 'MPG>=25 풀 평균'으로 등급을 매겼는데, 21차에서
# 선수 가중치의 기준선이 '지명 풀 전체·경기당·비가중'으로 바뀌었고(9칸 전부
# 집계되므로 MPG 필터가 근거를 잃었다) validate.py의 M1/M2는 그때부터
# baseline_per_game으로 검사한다. 두 기준이 갈라져 있으면 재실행할 때마다
# 경계선 선수들이 M1/M2 위반으로 튄다 — 실제로 23차에 14건 터졌다.
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as _CM
_B, _BPG = _CM.baselines(), _CM.baselines_per_game()
BASELINE=dict(_BPG)

def lift(name,cat):
    r=F.get(name)
    if not r or (r.get("GP") or 0)<MINGP: return None
    if cat=="A/T":
        return r.get(ATLIFT)
    if cat in RATE:
        v,a=r.get(cat),r.get(RATE[cat])
        return None if (v is None or a is None) else round((v-BASELINE[cat])*a*100,2)
    v=r.get(cat)
    if v is None: return None
    return round(BASELINE[cat]-v,3) if cat=="TOV" else round(v-BASELINE[cat],3)

print(f"{'캣':<6}{'기준선':>10}{'임계 w3':>10}{'임계 w2':>10}   변경 요약")
summary={}
for cat in COUNT+list(RATE)+["A/T"]:
    vals=sorted([x for x in (lift(p["name"],cat) for p in pl) if x is not None], reverse=True)
    th3=vals[int(len(vals)*0.10)]; th2=vals[int(len(vals)*0.25)]
    # 24차 · 퇴화 케이스 처리: 양수 lift가 25% 미만이면 '상위 25%' 경계가 0 이하로 내려간다.
    # 그러면 w2 조건(x>=th2)이 w1 조건(x>0)보다 **느슨해져** w1이 사라진다 —
    # DD가 정확히 그랬다(th2=-0.02 → w1 1명). DD는 소수 빅맨이 독식하는 극단 우편향이다.
    # 이 경우에만 등급 경계를 **양수 모집단 안에서** 다시 자른다. 다른 12캣은 영향 없다.
    pos_only=False
    if th2<=0 or th3<=0:
        pv=[x for x in vals if x>0]
        if len(pv)>=8:
            th3=pv[int(len(pv)*0.10)]; th2=pv[int(len(pv)*0.25)]; pos_only=True
    def grade(x):
        if x>=th3: return 3
        if x>=th2: return 2
        if x>0:    return 1
        return None
    a=ch=rm=sk=0
    for p in pl:
        x=lift(p["name"],cat)
        if x is None:
            if p["cat_weights"].get(cat) is not None: sk+=1
            continue
        cur=p["cat_weights"].get(cat); new=grade(x)
        p.setdefault("cat_lift",{})[cat]=x
        if new is None:
            if cur is not None: p["cat_weights"].pop(cat); rm+=1
        else:
            if cur is None: a+=1
            elif cur!=new: ch+=1
            p["cat_weights"][cat]=new
    n=[len([1 for p in pl if p["cat_weights"].get(cat)==k]) for k in (3,2,1)]
    summary[cat]={"baseline":BASELINE[cat],"th3":th3,"th2":th2,"threshold_pool":("양수 lift 모집단" if pos_only else "자격 풀 전체"),
                  "w3":n[0],"w2":n[1],"w1":n[2],"added":a,"changed":ch,"removed":rm,"kept_unqualified":sk}
    bl=f"{BASELINE[cat]*100:.1f}%" if cat in RATE else f"{BASELINE[cat]:.3f}"
    print(f"{cat:<6}{bl:>10}{th3:>10.2f}{th2:>10.2f}   신규 {a} · 변경 {ch} · 제거 {rm} · 미달유지 {sk}"
          f" → w3 {n[0]}({n[0]/174*100:.0f}%) w2 {n[1]} w1 {n[2]}")
# cats 문자열 재생성
for p in pl:
    order=re.findall(r"([A-Z/%0-9]+)\d", p["cats"])
    parts=[f"{c2}{p['cat_weights'][c2]}" for c2 in order if c2 in p["cat_weights"]]
    parts+=[f"{c2}{v}" for c2,v in p["cat_weights"].items() if c2 not in order]
    p["cats"]=" ".join(parts)
json.dump(pl,io.open(f"{BASE}/data/players.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
# 기준선·임계값을 cores.json에 단일 소스로
# ⚠️ 23차: 여기서 cat_baselines를 **통째로 교체**하던 탓에, 손으로 추가돼 있던
# PTS·TOV 항목과 baseline_per_game 필드가 재실행 때 사라졌다.
# recompute_cores.py는 CATS를 이 dict의 키에서 가져오므로 PTS가 없어져 KeyError로
# 죽고, 팀 한계기여가 stale로 남았다. 이제 **12캣 전체의 단일 작성자**다.
#
# 두 기준선이 목적별로 다르다 — 섞으면 안 된다:
#   baseline          = cat_model.baselines()          GP 가중 · 팀 한계기여 입력
#                       (marginal()이 팀 합을 GP 가중으로 내므로 기준선도 같은 척도여야 한다.
#                        비가중값(PTS 18.9)을 넣으면 9칸 기준선이 170점이 되어 모든
#                        코어가 PTS를 지는 것처럼 나온다 — 23차에 실제로 그렇게 깨졌다)
#   baseline_per_game = cat_model.baselines_per_game() 선수 가중치 등급·M1/M2·value_model 입력
# TOV 방향 플래그는 validate.py가 읽는 키 이름 그대로 lower_is_better 여야 한다.
cb={}
for k in _CM.CATS:
    e={"baseline":_B[k],"baseline_per_game":_BPG[k]}
    if k in summary:
        e["th_w3"]=summary[k]["th3"]; e["th_w2"]=summary[k]["th2"]
        if summary[k].get("threshold_pool"): e["threshold_pool"]=summary[k]["threshold_pool"]
    if k=="A/T": e["use_marginal_lift_field"]="at_marginal_lift"
    if k=="TOV": e["lower_is_better"]=True
    cb[k]=e
c["opponent_baseline"]["cat_baselines"]=cb
c["opponent_baseline"]["unified_definition"]=(
  "기준선 = 지명 풀(시장가 상위 126명) 전체·경기당·비가중(21차 정정 — 9칸 전부 집계되므로 MPG 필터 폐기). "
  "한계기여 = 계수형 실측−기준선(TOV는 반대) · 비율형 (rate−기준선)×시도량×100. "
  "등급 = 자격 풀(GP>=40) 상위 10%/25% 경계값(값 임계) · 한계기여<=0은 미부여. 18차 적용.")
json.dump(c,io.open(f"{BASE}/data/cores.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
tot=sum(v.get("added",0)+v.get("changed",0)+v.get("removed",0) for v in summary.values())
print(f"\n총 변경 {tot}건 · cores.json.opponent_baseline.cat_baselines에 기준선·임계값 기록")
