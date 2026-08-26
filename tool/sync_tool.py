#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""툴 HTML의 임베드 상수를 데이터에서 재생성.

동기화 대상 7종: P(선수 mk·cats·gp·실측라인) · CORES · PIVOTS ·
                 OVERHEAT · OTIERS · DECISION · DECISION_ONELINER
`validate.py`가 이 7종을 cores.json/players.json과 대조하므로,
데이터를 고치면 반드시 이 스크립트를 돌려야 한다.
"""
import json, io, os, re
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pl=json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))
c=json.load(io.open(f"{BASE}/data/cores.json",encoding="utf-8"))
by={p["name"]:p for p in pl}
p=f"{BASE}/tool/auction-console.html"; s=io.open(p,encoding="utf-8").read()

def buildCORES():
    out=[{"id":"c0","n":"— 코어 미선택 —"}]
    for co in c["cores"]:
        plan=[]
        for sl in co["slots"]:
            row=[sl["slot"], sl.get("role") or "",
                 [[x["name"],x["plan_price"]] for x in sl["candidates"]]]
            if sl.get("is_anchor"):
                ap=sl["anchor_plan"]; row.append(True)
                row.append({"ceil":ap["bid_ceiling"],"nom":ap["nominal_margin"],
                            "eff":ap["effective_headroom"],"con":ap["constraint"],
                            "act":ap["on_fail"]["action"],"tgt":ap["on_fail"]["target"],
                            "dual":ap["dual_world_ok"]})
            plan.append(row)
        e={"id":co["id"],"n":co["name"],"prem":co.get("premise") or "",
           "target":co.get("targeted_cats") or [],"punt":co.get("punted_cats") or [],
           "cap":co.get("single_player_cap"),"bigCap":co["big_budget_cap"],
           "slack":co["budget_slack"],"plan":plan}
        if co.get("conditional_on_discount"): e["condDiscount"]=co["conditional_on_discount"]
        out.append(e)
    return out
OH=[{"n":t["player"],"tier":t["tier"],"walk":t["threshold"],
     "exp":t["expected_2026_27"],"oh":t["overheat_at"]} for t in c["overheat_thresholds"]]
TI={k:{"label":v["label"],"c7":v["counts_toward_core7"],"why":v["why"]}
    for k,v in c["overheat_tiers"].items() if not k.startswith("_")}
CONST=[("CORES",buildCORES()),("PIVOTS",{x["id"]:x["pivot_plan"] for x in c["cores"]}),
       ("OVERHEAT",OH),("OTIERS",TI),("DECISION",c["decision_table"])]
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
