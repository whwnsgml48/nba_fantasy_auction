#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cores.json의 파생 필드를 기저 데이터에서 전부 재계산.

기저 = slots[].candidates + plan_price + pivot_plan.final_roster + players.json
파생 = planned_total · big_budget_planned · c_eligible_count · budget_slack
       anchor_plan(bid_ceiling·nominal_margin·effective_headroom·constraint·dual_world_ok
                   ·substitutes_dual_ok·on_fail·redeploy) · conditional_on_discount
       cat_weight_sums · targeted_cats_by_rule · rule_divergence
       cat_team_marginals · cat_win_summary · targeted_cats · punted_cats
       pts_team_marginal · tov_team_marginal · pivot cat_marginals

계획가를 하나 고치면 이 스크립트를 돌려야 한다. 안 돌리면 validate.py가 exit 1.
실행: <venv>/bin/python tool/recompute_cores.py
"""
import json, io, os, sys
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
PLl=json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))
PL={p["name"]:p for p in PLl}
RF=None
_rf=f"{BASE}/data/prior_auction_2025_26/proposed_market_refit.json"
if os.path.exists(_rf):
    RF={x["name"]:x for x in json.load(io.open(_rf,encoding="utf-8"))["players"]}
c=json.load(io.open(f"{BASE}/data/cores.json",encoding="utf-8"))
CB=c["opponent_baseline"]["cat_baselines"]
CB_MODEL={k:v["baseline"] for k,v in CB.items()}
RATE={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
CATS=[k for k in CB]
isBig=lambda n:"C" in PL[n]["pos"]
SWITCH={("c2","Nikola Jokić"):("c6","Jokić를 못 잡으면 스타 집중 전제 자체가 없어진다 → 정상시장 기본값"),
        ("c3","Shai Gilgeous-Alexander"):("c4","판단표 우선 4 '앵커 실패 시 안전망'이 그대로 목적지"),
        ("c5","Domantas Sabonis"):("c6","격리된 조건부 베팅 → 기본값으로 복귀")}
def dual(n):
    q=PL[n]
    a=q["my_max"]>=q["market_low"]
    return a and (q["my_max"]>=RF[n]["new_low"] if (RF and n in RF) else True)

# 21차 정정: 캣 계산은 tool/cat_model.py 단일 소스에 위임 (9명 전원 · GP 가중)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
def marg(names,cat): return CM.marginal(names,cat,CB_MODEL)

# 40차: 철수가가 **미측정(null)** 인 감시 항목이 생겼다(SF 병목 4명).
# null 을 그대로 담으면 ceil_price 의 min() 이 TypeError 로 죽는다 — 걸러 담는다.
WALK={t["player"]:t["threshold"] for t in c["overheat_thresholds"]
      if t.get("threshold") is not None}
def ceil_price(n,cap):
    """입찰 상한 = min(my_max, 단일상한, 철수가). 철수가를 넘으면 자기 피벗을 트리거한다."""
    v=PL[n]["my_max"]
    if cap: v=min(v,cap)
    if n in WALK: v=min(v,WALK[n])
    return v

def exp_cost(n,cap):
    """기대 원가 = 시장 중간값을 [시장 하단, 입찰 상한]으로 클램프.

    ⚠️ 35차 스키마 분리. 그전까지 `plan_price` 하나가 **세 가지 뜻**으로 동시에 쓰였다:
      불변식 1(market_low <= pp <= my_max)  → 입찰 상한
      planned_total · budget_slack · 예비비 → 기대 지출
      anchor_plan.effective_headroom       → 입찰 목표 + 여유
    경매에서 '부르는 값'과 '내는 값'은 다른 숫자다. 한 필드가 둘을 겸하니 슬롯마다
    해석이 갈렸고, 그래서 시장 $1-3 선수에게 계획가 $8이 붙는 일이 생겼다
    (총액 하한을 맞추려 남는 돈을 싼 슬롯에 얹은 결과 — 초과액의 32%가 $1-3 구간).

    이제 두 필드로 나눈다:
      bid_ceiling   = ceil_price()  부를 최대치
      expected_cost = 이 함수       예산 계산용
    `plan_price`는 expected_cost의 **별칭**으로 남긴다(툴·검증기 하위 호환)."""
    p=PL[n]; mid=round((p["market_low"]+p["market_high"])/2)
    # ⚠️ 클램프 순서 주의. max(low, min(mid, ceil)) 로 쓰면 **획득 불가 선수에서 상한을 넘는다**
    # (Haliburton: low $54 > my_max $50 → $54가 나와 불변식 1 위반). 상한이 최종 절단이다.
    # 획득 불가 여부는 기존 '1순위 획득불가' 검사가 별도로 잡는다.
    return min(ceil_price(n,cap), max(p["market_low"], mid))

def write_prices(co):
    """슬롯·후보 전체에 bid_ceiling·expected_cost를 쓰고 plan_price를 별칭으로 맞춘다."""
    cap=co.get("single_player_cap")
    def put(e):
        n=e.get("name")
        if n not in PL: return
        e["bid_ceiling"]=ceil_price(n,cap)
        # 37차: 피벗 전용 가격 오버라이드. 35차에 exp_cost가 **선수당 전역 단일값**이 되면서
        # 피벗의 "가격 상향" 스왑(KAT $45→$56)이 구조적으로 불가능해졌다 — put()이 모든
        # 엔트리를 같은 값으로 덮어썼기 때문이다. 과열 세계에서는 네임밸류 빅을 시장 상단에
        # 사야 하므로 엔트리 단위 예외가 필요하다. 상한은 bid_ceiling(=my_max·철수가 이하)이고,
        # I23이 expected_cost <= 시장 상단도 함께 검사한다.
        oc=e.get("overheat_cost")
        e["expected_cost"]=min(oc,e["bid_ceiling"]) if oc else exp_cost(n,cap)
        e["plan_price"]=e["expected_cost"]
    for s in co["slots"]:
        for cd in s["candidates"]: put(cd)
        s["bid_ceiling"]=s["candidates"][0]["bid_ceiling"]
        s["expected_cost"]=s["candidates"][0]["expected_cost"]
        s["plan_price"]=s["expected_cost"]
    pv=co.get("pivot_plan") or {}
    for blk in [pv]+([pv["fallback"]] if pv.get("fallback") else []):
        for r in (blk.get("final_roster") or []): put(r)
        for sw in (blk.get("swaps") or []):
            for side in ("in","out"):
                if isinstance(sw.get(side),dict): put(sw[side])

# 35차: 하한을 180 → 175로. 기대원가 체계에서 미소진은 곧 **예비비**이므로
# "총액 미소진"이 아니라 "예비비 과다(under-built)"로 재정의된다(상한 $25).
def solve_redeploy(co,skip,freed,FLOOR=175):
    slots=co["slots"]; cap=co.get("single_player_cap"); bigCap=co["big_budget_cap"]
    tot=sum(s["plan_price"] for s in slots)
    big=sum(s["plan_price"] for s in slots if isBig(s["candidates"][0]["name"]))
    cur=tot-freed; curbig=big; moves=[]
    cands=[]
    for s in slots:
        if s is skip: continue
        n=s["candidates"][0]["name"]
        room=ceil_price(n,cap)-s["plan_price"]
        if room>0: cands.append((room,s,n))
    cands.sort(key=lambda x:-x[0])
    for room,s,n in cands:
        if cur>=FLOOR: break
        add=min(room,FLOOR-cur)
        if isBig(n) and curbig+add>bigCap: add=max(0,bigCap-curbig)
        if add<=0: continue
        moves.append({"player":n,"slot":s["slot"],"from":s["plan_price"],"to":s["plan_price"]+add})
        cur+=add
        if isBig(n): curbig+=add
    return moves,cur,curbig

for co in c["cores"]:
    write_prices(co)          # 35차: 가격 두 필드 먼저 확정
    slots=co["slots"]
    # 슬롯/후보 plan_price 동기화
    for s in slots: s["candidates"][0]["plan_price"]=s["plan_price"]
    tot=sum(s["plan_price"] for s in slots)
    co["planned_total"]=tot
    co["budget_slack"]=200-tot
    co["big_budget_planned"]=sum(s["plan_price"] for s in slots if isBig(s["candidates"][0]["name"]))
    co["c_eligible_count"]=sum(1 for s in slots if isBig(s["candidates"][0]["name"]))
    # 앵커
    for s in slots:
        # ⚠️ 33차: `if not ap: continue` 였다. 빈 dict가 falsy라서 **새로 만든 앵커 슬롯의
        # anchor_plan 스텁을 건너뛰었고**, sync_tool이 KeyError('anchor_plan')로 죽었다.
        # 앵커 슬롯이면 스텁이든 없든 생성 대상이다.
        if not s.get("is_anchor"): continue
        ap=s.setdefault("anchor_plan",{})
        n=s["candidates"][0]["name"]; pp=s["plan_price"]; mx=PL[n]["my_max"]
        slack=co["budget_slack"]
        good=[x["name"] for x in s["candidates"][1:] if dual(x["name"])]
        nom=mx-pp; eff=min(mx,pp+slack)-pp
        ap.update({"bid_ceiling":mx,"nominal_margin":nom,"budget_slack":slack,
                   "effective_headroom":eff,
                   "constraint":("my_max" if eff==nom==0 else ("budget" if eff<nom else "none")),
                   "dual_world_ok":dual(n),"substitutes_dual_ok":good})
        trig={t["player"] for t in co["pivot_plan"]["triggers"]}
        if n in trig and n not in {r["name"] for r in co["pivot_plan"]["final_roster"]}:
            ap["on_fail"]={"action":"pivot","target":"pivot_plan",
                           "note":"이 코어의 과열 피벗이 구조화된 재배치를 수행한다 — 단순 치환보다 우선"}
        elif good:
            ap["on_fail"]={"action":"substitute","target":good[0],
                           "note":"코어 내 치환 — 코어 전환 불필요. 이중세계 유효 대체 %d명"%len(good)}
        else:
            d,why=SWITCH[(co["id"],n)]
            ap["on_fail"]={"action":"switch_core","target":d,"note":why}
        if not dual(n) and not good:
            co["conditional_on_discount"]={"anchor":n,
              "reason":"my_max $%d < 실측 시장하단 $%d — 시장 할인 없이는 확보 불가"%(mx,PL[n]["market_low"]),
              "on_fail":ap["on_fail"]}
        elif (co.get("conditional_on_discount") or {}).get("anchor")==n:
            co.pop("conditional_on_discount")
        if ap["on_fail"]["action"]=="substitute":
            for cd in s["candidates"][1:]:
                nt=tot-pp+cd["plan_price"]; cd["total_if_used"]=nt
                if nt>=175: cd["redeploy"]=None; continue   # 35차: 하한 175
                mv,fin,fb=solve_redeploy(co,s,pp-cd["plan_price"])
                cd["redeploy"]={"moves":mv,"total_after":fin,
                                "feasible":175<=fin<=200 and fb<=co["big_budget_cap"]}
        else:
            for cd in s["candidates"][1:]:
                cd.pop("total_if_used",None); cd.pop("redeploy",None)
    # 캣
    tw={k:0 for k in ["PTS","FG%","3PM","3P%","FT%","REB","OREB","AST","STL","BLK","DD","A/T","TOV"]}
    for s in slots:
        for k,v in PL[s["candidates"][0]["name"]]["cat_weights"].items(): tw[k]+=v
    co["cat_weight_sums"]=tw
    co["targeted_cats_by_rule"]=sorted([k for k,v in tw.items() if v>=6])
    st=[s["candidates"][0]["name"] for s in slots]   # 21차: 9명 전원 집계
    cm={cat:marg(st,cat) for cat in CATS}
    co["cat_team_marginals"]=cm
    win=[k for k,v in cm.items() if v is not None and v>0]
    lose=[k for k,v in cm.items() if v is not None and v<=0]
    # 24차: DD도 다른 캣과 동일하게 marginal() 결과로 판정한다.
    # 이전에는 targeted_cats에 DD가 선언돼 있으면 무조건 승리 1캣을 더했다(측정 없음).
    co["targeted_cats"]=sorted(win)
    co["punted_cats"]=sorted(lose)
    co["cat_win_summary"]={"wins":sorted(win),"losses":sorted(lose),
      "wins_measured":len(win),"cats_measured":len(win)+len(lose),
      "dd_declared":("목표" if "DD" in win else "포기"),
      "dd_marginal":cm.get("DD"),
      "wins_incl_dd":len(win),
      "h2h_verdict":("win" if len(win)>=7 else "lose"),
      "bench_spend":sum(s["plan_price"] for s in slots if s["slot"]=="BN"),
      "note":("13캣 전부 실측/추정 기반. DD는 정규근사 추정(실측 25명 검증: 절대오차중앙값 2.13). "
              "승리선 7캣. **9명 전원 집계**(21차 정정) — 벤치도 매일 라인업 로테이션으로 기여한다. "
              "wins_incl_dd는 이제 wins_measured와 같다 — 24차에 DD 공짜 캣을 제거했다.")}
    co["rule_divergence"]={
      "punted_but_rule_says_secured":sorted(set(co["punted_cats"])&set(co["targeted_cats_by_rule"])),
      "declared_but_rule_says_short":sorted(set(co["targeted_cats"])-set(co["targeted_cats_by_rule"])),
      "note":co.get("rule_divergence",{}).get("note","")}
    # PTS·TOV 전용 필드
    for cat,key in [("PTS","pts_team_marginal"),("TOV","tov_team_marginal")]:
        have=[n for n in st if n in F and F[n].get(cat) is not None]
        s2=round(sum(F[n][cat] for n in have),1)
        co[key]={"starters_counted":len(have),
                 ("starters_pts_sum" if cat=="PTS" else "starters_tov_sum"):s2,
                 "vs_opponent_baseline":cm[cat],
                 "weight_sum":tw[cat],
                 "declaration":("목표" if cat in co["targeted_cats"] else "포기"),
                 "verdict":("확보" if (cm[cat] or 0)>0 else "미달"),
                 "note":co.get(key,{}).get("note","")}
    # 35차: 피벗 로스터의 alternates.total_if_used 갱신.
    # 재가격으로 기준 총액이 바뀌면 이 값이 stale이 되어 검증기가 불일치로 잡는다.
    pv0=co.get("pivot_plan") or {}
    for blk in [pv0]+([pv0["fallback"]] if pv0.get("fallback") else []):
        ros=blk.get("final_roster") or []
        tk=sum(r["plan_price"] for r in ros)
        for r in ros:
            for a in (r.get("alternates") or []):
                if a.get("name") in PL:
                    a["plan_price"]=exp_cost(a["name"],co.get("single_player_cap"))
                    a["bid_ceiling"]=ceil_price(a["name"],co.get("single_player_cap"))
                    a["expected_cost"]=a["plan_price"]
                    a["total_if_used"]=tk-r["plan_price"]+a["plan_price"]
    # 피벗·백업
    pv=co["pivot_plan"]
    for lbl,pp2 in [("pivot",pv)]+([("fallback",pv["fallback"])] if pv.get("fallback") else []):
        ros=pp2["final_roster"]
        pp2["final_total"]=sum(r["plan_price"] for r in ros)
        pp2["final_big_budget"]=sum(r["plan_price"] for r in ros if isBig(r["name"]))
        pp2["final_c_eligible"]=sum(1 for r in ros if isBig(r["name"]))
        for r in ros: r["dual_world_ok"]=dual(r["name"])
        st2=[r["name"] for r in ros]   # 21차: 9명 전원 집계
        pm={cat:marg(st2,cat) for cat in CATS}
        w2=[k for k,v in pm.items() if v is not None and v>0]
        l2=[k for k,v in pm.items() if v is not None and v<=0]
        pp2["targeted_cats"]=sorted(w2)
        pp2["punted_cats"]=sorted(l2)
        pp2["cat_marginals"]={"starters":len(st2),
          "PTS":{"sum":round(sum(F[n]["PTS"] for n in st2 if n in F and F[n].get("PTS") is not None),1),
                 "marginal":pm["PTS"],"verdict":"확보" if (pm["PTS"] or 0)>0 else "미달"},
          "TOV":{"sum":round(sum(F[n]["TOV"] for n in st2 if n in F and F[n].get("TOV") is not None),1),
                 "marginal":pm["TOV"],"verdict":"확보" if (pm["TOV"] or 0)>0 else "미달"},
          "all":pm,
          "wins_incl_dd":len(w2)}
json.dump(c,io.open(f"{BASE}/data/cores.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("파생 필드 재계산 완료")
for co in c["cores"]:
    s=co["cat_win_summary"]
    print(f"  {co['id']}: {s['wins_incl_dd']}캣 ({s['h2h_verdict']}) · 계획 ${co['planned_total']}"
          f" · 여유 ${co['budget_slack']} · 벤치 ${s['bench_spend']} · 피벗 {co['pivot_plan']['cat_marginals']['wins_incl_dd']}캣")
