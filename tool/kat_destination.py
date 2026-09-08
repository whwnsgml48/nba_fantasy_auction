#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAT $50~57 갈래의 **목적지**를 관측 예산에서 잰다 (42차 · 작업6 후속).

🔴 왜 다시 재는가 — 앞선 기각이 틀렸다
「모순이 아니다」로 기각했는데, $57 에서 배운 것은 **「무모순이어도 목적지가 틀릴 수 있다」**
였다. 그 분기도 논리적으로는 일관됐고(예산 근거) 재보니 9.5%p 나빴다.

🔴 그리고 임계값 자체가 **계획가 예비**의 산물이다
  $50 근거  "c6 는 예비 $9 라 $50 까지"     ← c6 계획 $191 · 예비 $9
  $57 근거  "c7 은 예비 $16 이라 $57 까지"   ← c7 계획 $184 · 예비 $16
**관측 세계에 그 예비는 없다** — c6 는 $71, c7 은 **$111** 이 부족하다.
즉 「c7 은 KAT $57 까지 버틴다」가 관측 세계에서 **거짓**이다.

## 비교는 **같은 예산에서** 해야 한다
A  c7 로 전환해 KAT 유지 → c7 은 $111 부족하므로 **다른 칸에서 그만큼 깎아야 한다**
B  c6 유지 + KAT→Duren   → $63 이 풀리므로 c6 필요 감축 $71 → $8 만 남는다
"""
import io, json, os, random, statistics as st, sys
BASE = os.path.expanduser("~/personal_work/nba_fantasy_auction_2026")
sys.path.insert(0, BASE + "/tool")
import matchup_sim as MS, real_opponents as RO, cat_model as CM
CJ = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
PL = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
REAL, _ = RO.build(); MGRS = sorted(REAL)
OPP = {m: sorted(REAL[m]) for m in MGRS}; ROWS = MS.pool()
ITERS, SEED = 4000, 20261020
CM.configure(model="standard")

def measure(names):
    per = {m: MS.simulate(sorted(names), OPP[m], random.Random(SEED), ITERS, ROWS) for m in MGRS}
    return st.mean(per[m]["weekly_win_rate"] for m in MGRS), {m: per[m]["weekly_win_rate"] for m in MGRS}

def room(names):
    return sum(PL[n].get("room_price") or 0 for n in names)

def roster(cid):
    return [s["candidates"][0]["name"] for s in next(c for c in CJ["cores"] if c["id"] == cid)["slots"]]

def swap(names, pairs):
    out = list(names)
    for a, b in pairs: out[out.index(a)] = b
    return out

PLANS = {
 "A  c7 원안 (KAT 유지 · 감축 전)": (roster("c7"), []),
 "A1 c7 KAT유지 + 4칸 감축":       (roster("c7"), [("Alperen Şengün","Pascal Siakam"),
                                                  ("Evan Mobley","Mark Williams"),
                                                  ("Josh Hart","Andrew Wiggins"),
                                                  ("Dyson Daniels","Ausar Thompson")]),
 "B  c6 원안 (감축 전)":            (roster("c6"), []),
 "B1 c6 KAT→Duren 만":             (roster("c6"), [("Karl-Anthony Towns","Jalen Duren")]),
 "B2 c6 KAT→Duren + Şengün→Mobley":(roster("c6"), [("Karl-Anthony Towns","Jalen Duren"),
                                                   ("Alperen Şengün","Evan Mobley")]),
 "B3 c6 KAT→Duren + Şengün→LeBron":(roster("c6"), [("Karl-Anthony Towns","Jalen Duren"),
                                                   ("Alperen Şengün","LeBron James")]),
}
print("KAT $50~57 갈래 목적지 — **관측 예산**에서 (실제 12팀 · 4000시행 · 시드 %d)\n"%SEED)
print("%-34s %8s %9s %9s"%("경로","방 총액","승률","예산"))
print("-"*64)
res={}
for lbl,(r0,pairs) in PLANS.items():
    ns=swap(r0,pairs); assert len(set(ns))==9,lbl
    m,by=measure(ns); c=room(ns)
    res[lbl]={"roster":sorted(ns),"room_total":c,"win_rate":round(m,4),"swaps":pairs}
    print("%-34s %7d$ %8.2f%% %9s"%(lbl,c,100*m,"OK" if c<=200 else "초과 $%d"%(c-200)))
json.dump({"generated_by":"tool/kat_destination.py","seed":SEED,"iterations":ITERS,
  "why":("$50~57 갈래 목적지를 관측 예산에서 잰다. 임계값 $50·$57 은 **계획가 예비**에서 "
         "나온 값인데 관측 세계에 그 예비가 없다(c6 $71 · c7 $111 부족)."),
  "plans":res}, io.open(BASE+"/data/kat_destination.json","w",encoding="utf-8"),
  ensure_ascii=False,indent=1)
print("\ndata/kat_destination.json 기록")
