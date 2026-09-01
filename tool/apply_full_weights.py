#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전체 스탯(BBRef 172명)으로 cat_weights 재배정.

규칙: 등급별 인원수는 보존하고 순서만 실측으로 교정한다.
      GP >= 40 자격자만 대상 — 5~39경기 표본의 per-game 비율을 엘리트로 볼 수 없다.
      비율 캣(3P%·FT%·FG%)은 레버리지 = (rate − 리그평균) × 시도량 으로 정렬.
      TOV는 낮을수록 좋으므로 역순.
"""
import json, io, os, re

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import oneshot
oneshot.spent(
    __file__,
    did='전체 스탯(BBRef 172명)으로 cat_weights 재배정 — 등급별 인원수는 보존하고 순서만 교정',
    breaks='**data/players.json 을 덮는다** (샌드박스 재실행으로 실측: 1개 파일 변경). 그 뒤에 들어간 손수정 — 예를 들어 my_max 점 수정(Jokić 88→97 · SGA 79→85, 사용자 결정 2026-08-26) — 이 사라질 수 있다',
    instead='가중치를 다시 재려면 docs/11 의 NEXT_SEASON 절차를 따라라. 174명이 연쇄로 움직인다')

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
bb=json.load(io.open(f"{BASE}/data/stats_2025_26/bbref/per_game.json",encoding="utf-8"))["2025-26"]
pl=json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))
def lgavg(m,a):
    M=sum(v[m] or 0 for v in bb.values()); A=sum(v[a] or 0 for v in bb.values()); return M/A
LG={"3P%":lgavg("3PM","3PA"),"FT%":lgavg("FTM","FTA"),"FG%":lgavg("FGM","FGA")}
RATE={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
HIGHER=["PTS","REB","OREB","AST","STL","BLK","3PM","A/T","3P%","FT%","FG%"]
LOWER=["TOV"]; MINGP=40
def val(n,cat):
    r=F.get(n)
    if not r or (r.get("GP") or 0)<MINGP: return None
    if cat=="A/T": return r.get("at_marginal_lift")
    if cat in RATE:
        v,a=r.get(cat),r.get(RATE[cat])
        return None if (v is None or a is None) else round((v-LG[cat])*a*100,2)
    return r.get(cat)

P={p["name"]:p for p in pl}
for p in pl: p.setdefault("cat_weights_prior", dict(p["cat_weights"]))
changes=[]
for cat in HIGHER+LOWER:
    rows=[]
    for p in pl:
        w=p["cat_weights"].get(cat)
        if w is None: continue
        v=val(p["name"],cat)
        if v is None: continue
        rows.append([v,p["name"],w])
    if not rows: continue
    weights=sorted((r[2] for r in rows),reverse=True)
    rows.sort(key=lambda r:(-r[0]) if cat in HIGHER else r[0])
    for i,r in enumerate(rows):
        nw=weights[i]
        if nw!=r[2]:
            P[r[1]]["cat_weights"][cat]=nw
            changes.append((r[1],cat,r[2],nw,r[0]))

# cats 문자열 재생성 + 메타
for p in pl:
    order=re.findall(r"([A-Z/%0-9]+)\d", p["cats"])
    parts=[f"{c}{p['cat_weights'][c]}" for c in order if c in p["cat_weights"]]
    parts+=[f"{c}{v}" for c,v in p["cat_weights"].items() if c not in order]
    p["cats"]=" ".join(parts)
    r=F.get(p["name"])
    p["measured_source"]={
      "provider":"basketball-reference per-game",
      "season":(r or {}).get("season"),
      "GP":(r or {}).get("GP"),
      "gp_qualified": bool(r and (r.get("GP") or 0)>=MINGP),
      "weights_data_verified": bool(r and (r.get("GP") or 0)>=MINGP),
    } if r else {"provider":None,"season":None,"GP":None,
                 "gp_qualified":False,"weights_data_verified":False,
                 "note":"BBRef 미등재 (NBA 무경력)"}
json.dump(pl,io.open(f"{BASE}/data/players.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print(f"변경 {len(changes)}건 · 선수 {len({c[0] for c in changes})}명")
print(f"자격 미달(GP<{MINGP}) {sum(1 for p in pl if not p['measured_source']['gp_qualified'])}명 — 가중치 미검증으로 표기")
print(f"리그 평균: "+" · ".join(f"{k} {v*100:.1f}%" for k,v in LG.items()))
print()
print("2단계 변경:")
for n,c,a,b,v in changes:
    if abs(a-b)>=2: print(f"  {n:<26}{c:<5} w{a}→w{b}  실측 {v:g}  ({F[n]['GP']}경기)")
