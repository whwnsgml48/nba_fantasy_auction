#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""툴 HTML의 임베드 상수를 데이터에서 재생성.

동기화 대상 7종: P(선수 mk·cats·gp·실측라인) · CORES · PIVOTS ·
                 OVERHEAT · OTIERS · DECISION · DECISION_ONELINER
`validate.py`가 이 7종을 cores.json/players.json과 대조하므로,
데이터를 고치면 반드시 이 스크립트를 돌려야 한다.
"""
import json, io, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 39차: 임베드 상수 구조는 tool_embed 가 단일 소스다. validate.py 도 같은 것을 import 해
# 대조하므로, 여기서 직접 dict를 조립하면 두 파일이 갈라진다(실제로 갈라졌다).
import tool_embed as TE
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 39차 갈래 1: 판단표 각 행에 실제 12팀 강도를 얹는다(cores.json엔 안 넣는다 · 32차).
try:
    SIM=json.load(io.open(f"{BASE}/data/matchup_sim.json",encoding="utf-8"))
except Exception:
    SIM=None
pl=json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))
c=json.load(io.open(f"{BASE}/data/cores.json",encoding="utf-8"))
by={p["name"]:p for p in pl}
p=f"{BASE}/tool/auction-console.html"; s=io.open(p,encoding="utf-8").read()

def buildCORES():
    out, problems = TE.build_cores(c)
    if problems:
        # 깨진 상수를 툴에 쓰면 안 된다 — 33차에 이 결손이 KeyError로 죽었고,
        # 조용히 넘기면 툴이 앵커 정보 없는 코어를 표시하게 된다.
        raise SystemExit("anchor_plan 결손 %d건 — recompute_cores.py 를 먼저 돌리십시오:\n  %s"
                         % (len(problems), "\n  ".join(problems)))
    return out
CONST=[("CORES",buildCORES()),("PIVOTS",TE.build_pivots(c)),
       ("OVERHEAT",TE.build_overheat(c)),("OTIERS",TE.build_tiers(c)),
       # ⏸ 39차 갈래 1: TE.build_decision(c,SIM) 로 바꾸면 판단표에 실제 12팀 강도가 실린다.
       #    validate 가 DECISION 을 cores.json.decision_table 원본과 직접 대조하므로
       #    그쪽도 같은 함수를 쓰도록 바뀌기 전까지 보류한다 (B 요청 중).
       ("DECISION",c["decision_table"])]
n=0
for name,val in CONST:
    m=re.search(r'const %s=(\[|\{).*?(\]|\});\n'%re.escape(name), s, re.S)
    assert m, name
    s=s[:m.start()]+("const %s=%s;\n"%(name, json.dumps(val,ensure_ascii=False)))+s[m.end():]
    n+=1
m=re.search(r'const DECISION_ONELINER=".*?";\n', s, re.S); assert m
s=s[:m.start()]+('const DECISION_ONELINER=%s;\n'%json.dumps(c["decision_oneliner"],ensure_ascii=False))+s[m.end():]
n+=1
# P 배열
m=re.search(r'(const P=\[\n)(.*?)(\n\];)', s, re.S); assert m
out=[]; nc=0
for ln in m.group(2).split("\n"):
    mm=re.match(r'^\{n:"((?:[^"\\]|\\.)*)"', ln)
    if not mm: out.append(ln); continue
    q=by.get(mm.group(1).replace('\\"','"'))
    if not q: out.append(ln); continue
    new=ln
    new=re.sub(r'mk:\[\d+,\d+\]','mk:[%d,%d]'%(q["market_low"],q["market_high"]),new,count=1)
    new=re.sub(r'c:"[^"]*"','c:"%s"'%q["cats"],new,count=1)
    # ⚠️ 23차: mx(my_max)가 동기화 목록에 **없었다**. my_max는 22차까지 한 번도 바뀐 적이
    # 없어서 드러나지 않았고, 23차에 10명을 하향한 뒤에도 툴은 옛 값(Kessler mx:18)을
    # 그대로 보여줬다 — 드래프트 당일 그 값으로 입찰했으면 my_max를 $4 초과한다.
    new=re.sub(r'mx:\d+','mx:%d'%q["my_max"],new,count=1)
    ms=q.get("measured_source") or {}
    # gp:null도 갱신 대상이다. \d+ 패턴만 쓰면 혼합 GP가 새로 생겨도 null이 남는다.
    if ms.get("GP"): new=re.sub(r'gp:(?:\d+|null)','gp:%d'%round(ms["GP"]),new,count=1)
    else:            new=re.sub(r'gp:(?:\d+|null)','gp:null',new,count=1)
    lf=(q.get("measured_line_full") or {}).get("line")
    if lf:
        esc=lf.replace('\\','\\\\').replace('"','\\"')
        new=re.sub(r's:"(?:[^"\\]|\\.)*"','s:"%s"'%esc,new,count=1)
    if new!=ln: nc+=1
    out.append(new)
s=s[:m.start(2)]+"\n".join(out)+s[m.end(2):]
io.open(p,"w",encoding="utf-8").write(s)
print(f"툴 동기화: 상수 {n+1}종 재생성 · P 배열 {nc}행 갱신")
