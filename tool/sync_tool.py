#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""툴 HTML의 임베드 상수를 데이터에서 재생성.

동기화 대상 8종(+P 행의 py): P(선수 mk·cats·gp·실측라인) · CORES · PIVOTS ·
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
# (40차: 같은 try/except 가 두 번 있었다 — 하나로 합쳤다. 동작 동일.)
try:
    SIM=json.load(io.open(f"{BASE}/data/matchup_sim.json",encoding="utf-8"))
except Exception:
    SIM=None   # 시뮬 파일이 없으면 강도 없이 생성한다(검증기도 같은 폴백을 쓴다)
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
       # 39차 갈래 1: 판단표에 **실제 12팀 강도**를 싣는다. 강도는 32차 원칙상
       # cores.json 에 넣지 않고 **여기서 툴 상수를 만들 때만** 합친다.
       # validate 도 같은 TE.build_decision(cj, sim) 을 쓰므로 이중 구현이 안 생긴다.
       ("DECISION",TE.build_decision(c,SIM)),("KATBR",TE.build_kat_branch(c,SIM)),
       # 40차 B: 가정 취약성. 승률 1차 지표가 상위 5개를 1.3%p(대응 SE 0.59%p) 안으로
       #   몰아넣었고 2차(maximin)는 5/7 이 value_max 에 지배돼 쓸 수 없다 —
       #   **어떤 승률 측정도 상위 5개를 못 가른다.** 이 표는 −11.3%p 를 만든다.
       #   지금 다섯을 가르는 유일한 측정인데 화면에 없었다.
       # ⚠️ 이것은 **가공 없는 통과(passthrough)** 다 — matchup_sim.json 의 값을
       #   그대로 싣는다. 계산을 여기서 하지 않으므로 tool_embed 와 갈라질 여지가 없다.
       #   ⚠️ 다만 validate.py 의 동기화 대조 목록에는 아직 없다(A 소관 요청 중).
       #      그때까지는 tests/check_stress_sync.py 가 대조한다.
       ("STRESS",(SIM or {}).get("assumption_stress") or {})]
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
    # ⚠️ rfind('}') 뒤를 버리면 행 끝 쉼표가 사라져 const P 배열이 깨진다.
    def ins(txt, frag):
        i=txt.rfind('}');  return txt[:i]+frag+txt[i:]
    # ⚠️ 39차: t(소속)·injOut 이 동기화 목록에 **없었다** — 손으로 유지되는 이중 소스였다.
    # 실제로 DeRozan 소속이 툴에 교정 전 값(GSW)으로 남아 화면에 떴다.
    #
    # ⚠️ note·flag 는 **json 에 값이 있을 때만** 덮어쓴다. 툴에만 있는 손으로 쓴 분석
    #    144건·경고 15건이 있어서 무조건 동기화하면 전부 삭제된다 — 실제로 그렇게 만들어
    #    되돌렸다. 즉 둘은 아직 단일 소스가 아니다(시즌 후 과제).
    new=re.sub(r'\bt:"[^"]*"','t:"%s"'%q.get("team",""),new,count=1)
    # (툴 키, players.json 키). lev 는 19:19 로 정확히 대응한다.
    for _k, _jk in (("flag","flag"), ("note","note"), ("lev","volume_leverage")):
        if not q.get(_jk): continue
        esc=q[_jk].replace('\\','\\\\').replace('"','\\"')
        rep=',%s:"%s"'%(_k,esc)
        pat=re.compile(r',%s:"(?:[^"\\]|\\.)*"'%_k)
        new=pat.sub(lambda _:rep,new,count=1) if pat.search(new) else ins(new, rep)
    # 40차: 작년 실낙찰가(표시 전용). **없는 선수는 필드를 안 넣는다** —
    #   null 을 넣으면 소비자가 깨진다(이번 회차에 walk:null 로 화면이 실제로 깨졌다).
    new=re.sub(r',py:\d+','',new,count=1)
    if q.get("prior_auction_price") is not None:
        new=ins(new, ',py:%d'%q["prior_auction_price"])
    # injOut: 부재가 곧 false다. 은퇴·장기부상 어느 쪽이든 같은 제외 기구를 쓴다.
    new=re.sub(r',injOut:true','',new,count=1)
    if q.get("injury_exclude"):
        new=ins(new, ',injOut:true')
    lf=(q.get("measured_line_full") or {}).get("line")
    if lf:
        esc=lf.replace('\\','\\\\').replace('"','\\"')
        new=re.sub(r's:"(?:[^"\\]|\\.)*"','s:"%s"'%esc,new,count=1)
    if new!=ln: nc+=1
    out.append(new)
s=s[:m.start(2)]+"\n".join(out)+s[m.end(2):]
io.open(p,"w",encoding="utf-8").write(s)
print(f"툴 동기화: 상수 {n+1}종 재생성 · P 배열 {nc}행 갱신")
