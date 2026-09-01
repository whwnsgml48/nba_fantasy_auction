#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기본 코어 + 모든 피벗 플랜을 한 번에 검증한다.
위반이 1건이라도 있으면 exit 1. 사용: python3 validate.py"""
import io,json,sys,os
D=os.path.dirname(os.path.abspath(__file__))
# 39차: 툴 임베드 상수 구조의 단일 소스. 세 곳(DECISION 대조 · OVERHEAT/OTIERS/CORES
# 대조 · I28 라벨 검사)에서 쓰므로 **상단에서 한 번만** import 한다.
# 처음엔 사용 지점마다 지역 import 했다가 I28 자리에서 NameError 로 검증기가 **중단**됐고,
# 그건 38차에 잡은 바로 그 실패(뒤쪽 검사가 통째로 안 도는 조용한 절단)의 재현이었다.
sys.path.insert(0, D+"/tool")
import tool_embed as _TE
pl={p["name"]:p for p in json.load(io.open(D+"/data/players.json",encoding="utf-8"))}
cj=json.load(io.open(D+"/data/cores.json",encoding="utf-8"))
TH={t["player"]:t["threshold"] for t in cj["overheat_thresholds"]}   # 철수 가격(피벗 트리거)
OT={t["player"]:t for t in cj["overheat_thresholds"]}
TIERS={k:v for k,v in (cj.get("overheat_tiers") or {}).items() if not k.startswith("_")}
# 계층별 선수 집합 — decision_table이 이 집합에서 드리프트하지 못하게 검증에 사용
TIER_OF={t["player"]:t.get("tier") for t in cj["overheat_thresholds"]}
BY_TIER={}
for _n,_t in TIER_OF.items(): BY_TIER.setdefault(_t,set()).add(_n)
INJ={n for n,p in pl.items() if p.get("injury_exclude")}
import re as _re2, unicodedata as _ud2
def _nm2(x):
    x=_ud2.normalize("NFKD",x).encode("ascii","ignore").decode().lower()
    x=x.replace(".","").replace("'","").replace("-"," ")
    x=_re2.sub(r"\(\d{4}-\d{2}\)","",x)
    return " ".join(_re2.sub(r"\b(jr|iii|ii|iv|sr)\b","",x).split())
# 재적합(실측 기반 시장 곡선) — 있으면 "이중세계" 검증에 사용. 없으면 건너뜀
_rfp=D+"/data/prior_auction_2025_26/proposed_market_refit.json"
_PRIOR_SCALE=1.11   # 작년 12팀 → 올해 14팀, 방 전체 예산 +11% (docs/08)
RF={}
if os.path.exists(_rfp):
    RF={x["name"]:x for x in json.load(io.open(_rfp,encoding="utf-8"))["players"]}
def dualok(n):
    """현 시장추정과 재적합 양쪽에서 my_max >= 시장하단."""
    q=pl.get(n)
    if not q: return False
    a=q["my_max"]>=q["market_low"]
    return a and (q["my_max"]>=RF[n]["new_low"] if n in RF else True)
SLOTS=sorted(["PG","SG","SF","PF","C","UTIL","UTIL","BN","BN"])
NEED={"PG":"G","SG":"G","SF":"F","PF":"F","C":"C","UTIL":None,"BN":None}
isBig=lambda n:"C" in pl[n]["pos"]

def check(label,roster,cap,bigCap,subs=None,conditional=None):
    """roster: [(slot,name,price)]
    subs: {(slot,name): [(대체명,대체가), ...]} — 1순위가 획득 불가일 때 검사할 대체후보.
    1순위가 획득 불가지만 획득 가능한 대체가 있으면 치명(e)이 아니라 치환필요(w)로 분류한다.
    실제 옥션에서 1순위가 내 최대가를 넘으면 대체로 가는 것이 정상 실행이기 때문이다."""
    e=[]; w=[]
    subs=subs or {}
    conditional=conditional or set()   # conditional_on_discount로 선언된 앵커 — 치명 아님
    if sorted(s for s,_,_ in roster)!=SLOTS: e.append("슬롯구성 불일치")
    if len(roster)!=9: e.append("슬롯 %d개"%len(roster))
    seen=set()
    for slot,n,v in roster:
        if n not in pl: e.append("없는 선수 %s"%n); continue
        p=pl[n]
        if n in seen: e.append("중복 %s"%n)
        seen.add(n)
        if v>p["my_max"]:   e.append("%s 계획가 $%d > my_max $%d"%(n,v,p["my_max"]))
        _unobt = v<p["market_low"] or p["my_max"]<p["market_low"]
        if _unobt:
            _alt=[(an,av) for an,av in subs.get((slot,n),[])
                  if an in pl and pl[an]["my_max"]>=pl[an]["market_low"] and av>=pl[an]["market_low"]]
            _msg="%s 1순위 획득불가 (계획 $%d · market_low $%d · my_max $%d)"%(
                n,v,p["market_low"],p["my_max"])
            if _alt:            w.append(_msg+" → 치환 %s $%d"%(_alt[0][0],_alt[0][1]))
            elif n in conditional: w.append(_msg+" · 조건부 베팅 — 시장 할인 시에만 진입")
            else:                e.append(_msg+" · 대체 없음")
        if n in INJ: e.append("🚑 장기부상 포함 %s"%n)
        k=NEED[slot]
        if k and k not in p["pos"]: e.append("%s(%s) 자격→%s"%(n,p["pos"],slot))
        if cap and v>cap: e.append("%s $%d > 단일상한 $%d"%(n,v,cap))
    tot=sum(v for _,_,v in roster); big=sum(v for _,n,v in roster if isBig(n))
    if tot>200: e.append("총액 $%d > $200"%tot)
    # ⚠️ 35차 스키마 분리: plan_price가 **기대 원가**(expected_cost의 별칭)가 됐으므로
    # "총액 미소진"은 곧 **예비비**다. 하한 위반이 아니라 '과소 편성'으로 재정의한다.
    #   예비비 < $4   → 위반 (앵커 1명이 상단으로 가면 예산 초과)  … I22와 동일 기준
    #   예비비 > $25  → **경고** (예산을 못 쓰는 로스터 = under-built)
    # 상한 $25는 예산의 12.5%다. 이 경고가 34차에 드러난 사실을 그대로 표면화한다 —
    # 피벗 로스터는 시장가로 $200을 쓰지 못한다(c6 피벗은 전원 상단에 사도 $171).
    _rsv=200-tot
    if _rsv<4:  e.append("예비비 $%d < $4"%_rsv)
    elif _rsv>25: w.append("예비비 $%d > $25 — 과소 편성(로스터가 예산을 못 씀)"%_rsv)
    if big>bigCap: e.append("빅맨예산 $%d > 상한 $%d"%(big,bigCap))
    return e,tot,big,sum(1 for _,n,_ in roster if isBig(n)),w

err=0; warn=0
print("%-12s %-6s %-6s %-14s %s"%("대상","총액","빅맨","C자격/상한","결과"))
print("-"*66)
for c in cj["cores"]:
    base=[(s["slot"],s["candidates"][0]["name"],s["plan_price"]) for s in c["slots"]]
    _sb={(s2["slot"],s2["candidates"][0]["name"]):[(x["name"],x["plan_price"]) for x in s2["candidates"][1:]]
         for s2 in c["slots"]}
    _cond={c["conditional_on_discount"]["anchor"]} if c.get("conditional_on_discount") else set()
    e,t,b,nb,w=check(c["id"]+" base",base,c["single_player_cap"],c["big_budget_cap"],_sb,_cond)
    print("%-12s $%-5d $%-5d %-14s %s"%(c["id"]+" base",t,b,"%d / $%d"%(nb,c["big_budget_cap"]),
        ("✗ "+"; ".join(e)) if e else ("△ "+"; ".join(w) if w else "OK"))); err+=len(e); warn+=len(w)
    # 모든 대체 후보도 가격·자격 검사
    for s in c["slots"]:
        for cd in s["candidates"][1:]:
            n,v=cd["name"],cd["plan_price"]; p=pl.get(n)
            if not p: print("  ✗ 대체후보 없는 선수",n); err+=1; continue
            if v>p["my_max"]: print("  ✗ 대체후보 %s $%d > my_max $%d"%(n,v,p["my_max"])); err+=1
            # 🔴 2026-09-01 — `market_low` 는 **시장 관측이 아니다**(docs/05 §6d).
            #   작년 가격 곡선에 **우리 순위**를 얹은 값이고, 작년 실낙찰가와는
            #   ρ 0.773 · 평균 절대차 $11.5 로 어긋난다. 반면 `prior_auction_price` 는
            #   **이 방이 실제로 낸 돈**이다 — 우리 모델과 독립된 유일한 신호다.
            #   둘이 충돌하면 관측이 이긴다. 단 **한 방향으로만** 허용한다:
            #   「작년에 방이 낸 돈(환산) 이상을 계획한다」면 희망가격이 아니다.
            #   그 아래를 계획하면 여전히 위반이다.
            if v<p["market_low"]:
                _pa=p.get("prior_auction_price")
                # 계획가는 정수 달러다 — 환산가도 **반올림해서** 비교한다.
                # 안 그러면 $20×1.11=$22.2 라 「$22 계획」이 0.2 때문에 위반으로 찍힌다.
                _paa=None if _pa is None else round(_pa*_PRIOR_SCALE)
                if _paa is not None and v>=_paa:
                    print("  △ 대체후보 %s $%d < market_low $%d — **작년 실낙찰 환산 $%d 이상이라 허용**"
                          " (market_low 는 우리 순위이고 실낙찰가는 방의 실제 지불이다 · docs/05 §6d·§6h)"
                          %(n,v,p["market_low"],_paa)); warn+=1
                else:
                    print("  ✗ 대체후보 %s $%d < market_low $%d%s"
                          %(n,v,p["market_low"],
                            "" if _paa is None else " (작년 실낙찰 환산 $%d 에도 못 미친다)"%_paa)); err+=1
            k=NEED[s["slot"]]
            if k and k not in p["pos"]: print("  ✗ 대체후보 %s(%s) 자격→%s"%(n,p["pos"],s["slot"])); err+=1
            if n in INJ: print("  ✗ 🚑 대체후보에 장기부상: %s"%n); err+=1
            if c["single_player_cap"] and v>c["single_player_cap"]:
                print("  ✗ 대체후보 %s $%d > 단일상한"%(n,v)); err+=1
        if len(s["candidates"])<2 and not s["is_anchor"]:
            print("  ✗ 비앵커 슬롯 대체안 없음: %s"%s["slot"]); err+=1
    pv=c.get("pivot_plan")
    if not pv: print("  ✗ pivot_plan 없음"); err+=1; continue
    pr=[(r["slot"],r["name"],r["plan_price"]) for r in pv["final_roster"]]
    _sp={(r["slot"],r["name"]):[(x["name"],x["plan_price"]) for x in (r.get("alternates") or [])]
         for r in pv["final_roster"]}
    e2,t2,b2,nb2,w2=check(c["id"]+" pivot",pr,c["single_player_cap"],c["big_budget_cap"],_sp,_cond)
    print("%-12s $%-5d $%-5d %-14s %s"%(c["id"]+" pivot",t2,b2,"%d / $%d"%(nb2,c["big_budget_cap"]),
        ("✗ "+"; ".join(e2)) if e2 else ("△ "+"; ".join(w2) if w2 else "OK"))); err+=len(e2); warn+=len(w2)
    if t2!=pv["final_total"]: print("  ✗ final_total 불일치 %d≠%d"%(t2,pv["final_total"])); err+=1
    if b2!=pv["final_big_budget"]: print("  ✗ final_big_budget 불일치"); err+=1
    for t in pv["triggers"]:
        if t["player"] not in TH: print("  ✗ 트리거가 임계값 소스에 없음: %s"%t["player"]); err+=1
        elif t["rule"]!="> $%d"%TH[t["player"]]: print("  ✗ 트리거 규칙 불일치: %s"%t["player"]); err+=1
    # 두 필드가 **선언돼 있는지**를 본다. 13캣을 전부 이기면 punted가 빈 리스트인 게 정상이고
    # (37차 c3 피벗이 실제로 그랬다), 그걸 미명시로 잡으면 좋아진 로스터가 위반이 된다.
    _tg, _pt = pv.get("targeted_cats"), pv.get("punted_cats")
    if _tg is None or _pt is None:
        print("  ✗ 피벗에 노리는 캣/포기 캣 필드 없음"); err+=1
    elif not _tg:
        print("  ✗ 피벗이 노리는 캣 0개 — 이길 캣이 없는 플랜"); err+=1
    elif len(_tg)+len(_pt)!=13:
        print("  ✗ 피벗 캣 선언 합계 %d ≠ 13"%(len(_tg)+len(_pt))); err+=1
    fb=pv.get("fallback")
    if fb:
        fr=[(r["slot"],r["name"],r["plan_price"]) for r in fb["final_roster"]]
        _sf={(r["slot"],r["name"]):[(x["name"],x["plan_price"]) for x in (r.get("alternates") or [])]
             for r in fb["final_roster"]}
        e3,t3,b3,nb3,w3=check(c["id"]+" fallback",fr,c["single_player_cap"],c["big_budget_cap"],_sf,_cond)
        print("%-12s $%-5d $%-5d %-14s %s"%(c["id"]+" fallbk",t3,b3,"%d / $%d"%(nb3,c["big_budget_cap"]),
            ("✗ "+"; ".join(e3)) if e3 else ("△ "+"; ".join(w3) if w3 else "OK"))); err+=len(e3); warn+=len(w3)
        if t3!=fb["final_total"]: print("  ✗ fallback final_total 불일치"); err+=1
        if not fb.get("targeted_cats") or not fb.get("punted_cats"):
            print("  ✗ fallback 캣 미명시"); err+=1
        cr=fb.get("condition_rules")
        if not cr or not fb.get("condition_logic"):
            print("  ✗ fallback 조건이 구조화되지 않음(condition_rules/condition_logic)"); err+=1
        else:
            for r in cr:
                if r["player"] not in TH:
                    print("  ✗ fallback 조건 선수가 임계값 소스에 없음: %s"%r["player"]); err+=1
                elif TH[r["player"]]!=r["threshold"] or r["rule"]!="> $%d"%r["threshold"]:
                    print("  ✗ fallback 조건 임계값 불일치: %s"%r["player"]); err+=1

print("-"*66)
# ── cat_weights 검증 (18차 — 한계기여 통일 정의) ──
# 14차는 리더보드/player_lines와 하드코딩 리그평균을 섞어 써서 공식이 소스마다 달랐다.
# 18차부터 단일 소스: 값은 measured_full.json · 기준선/임계는 cores.json.opponent_baseline.cat_baselines.
#  M1 자격자(GP>=MINGP) 안에서 가중치는 한계기여의 단조함수
#  M2 한계기여 <= 0 인데 가중치 부여 금지 (모든 캣)
#  M3 GP<MINGP 는 weights_data_verified=false
#  M4 flag/verdict가 가중치와 정면 충돌 금지
#  M5 정정이 tag까지 전파됐는지 — tag(buy/burn)과 value_reference.rank_divergence의
#     부호가 모순이면 위반. 25차 신설 · 26차에 판정 변수 교체(엘리트 개수 → div).
_mfp=D+"/data/stats_2025_26/measured_full.json"
_cb=(cj.get("opponent_baseline") or {}).get("cat_baselines")
if not (os.path.exists(_mfp) and _cb):
    print("cat_weights: 전체 스탯 또는 cat_baselines 없음 — 검증 생략")
else:
    _F=json.load(io.open(_mfp,encoding="utf-8"))["players"]
    _RATE={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
    _MINGP=40
    def _lift(n,cat):
        """선수 한계기여 — 21차: baseline_per_game(경기당·비가중) 기준.
        가중치는 '뛸 때의 실력'을 재므로 출장률을 섞지 않는다.
        팀 한계기여(캣 선언 검증)는 baseline(GP 가중)을 쓴다 — 목적이 다르다."""
        r=_F.get(n)
        if not r or (r.get("GP") or 0)<_MINGP: return None
        b=_cb[cat].get("baseline_per_game", _cb[cat]["baseline"])
        # A/T처럼 볼륨 인지 모델을 쓰는 캣은 원 비율이 아니라 지정된 한계기여 필드를 쓴다
        # (원 비율로 비교하면 저볼륨 선수를 엘리트로 오판 — 오류 패턴 ③)
        _mf=_cb[cat].get("use_marginal_lift_field")
        if _mf: return r.get(_mf)
        if cat in _RATE:
            v,a=r.get(cat),r.get(_RATE[cat])
            return None if (v is None or a is None) else round((v-b)*a*100,2)
        v=r.get(cat)
        if v is None: return None
        return round(b-v,3) if _cb[cat].get("lower_is_better") else round(v-b,3)
    _m1=_m2=_m3=_m4=0; _cov={}
    for cat in _cb:
        obs=[]
        for q in pl.values():
            w=q["cat_weights"].get(cat)
            if w is None: continue
            x=_lift(q["name"],cat)
            if x is None: continue
            obs.append((x,q["name"],w))
        _cov[cat]=len(obs)
        seen=set()
        for x1,n1,w1 in obs:
            for x2,n2,w2 in obs:
                if x2>x1+1e-9 and w1>w2 and (n1,cat) not in seen:
                    seen.add((n1,cat))
                    print("  ✗ [M1] %s: %s 한계기여 %g→w%d 인데 %s는 %g→w%d (단조성 위반)"%(
                        n1,cat,x1,w1,n2,x2,w2)); err+=1; _m1+=1
        for x,n,w in obs:
            if x<=0:
                print("  ✗ [M2] %s: %s 한계기여 %g (<=0)인데 w%d"%(n,cat,x,w)); err+=1; _m2+=1
    for q in pl.values():
        ms=q.get("measured_source")
        if not ms:
            print("  ✗ [M3] %s: measured_source 없음"%q["name"]); err+=1; _m3+=1; continue
        want=bool(ms.get("GP") and ms["GP"]>=_MINGP)
        if bool(ms.get("weights_data_verified"))!=want:
            print("  ✗ [M3] %s: weights_data_verified=%s인데 GP=%s"%(
                q["name"],ms.get("weights_data_verified"),ms.get("GP"))); err+=1; _m3+=1
    _ALIAS={"3P%":["3PT%","3P%"],"FT%":["FT%"],"OREB":["OREB"],"BLK":["BLK"],
            "STL":["STL"],"PTS":["PTS"],"REB":["REB"],"AST":["AST"],"A/T":["A/T"]}
    _NEG=["엘리트 아님","엘리트로 오분류","top-25 밖","진입 실패","반증","엘리트로 잘못"]
    _CITED=["정정","기존","때문이었","누락","재확인","재분류","였습니다","였고","결과","오분류했"]
    def _has(seg,a):
        for m in _re2.finditer(_re2.escape(a),seg):
            if m.start()==0 or not seg[m.start()-1].isalnum(): return True
        return False
    for q in pl.values():
        for fld in ("flag","verdict"):
            t=q.get(fld) or ""
            for sent in _re2.split(r"[·。]\s*|\s\|\s", t):
                if any(x in sent for x in _CITED): continue
                for cat,als in _ALIAS.items():
                    w=q["cat_weights"].get(cat)
                    if w is None or w<3: continue
                    if any(_has(sent,a) for a in als) and any(x in sent for x in _NEG):
                        if sum(1 for c2,a2 in _ALIAS.items() if any(_has(sent,x) for x in a2))!=1: continue
                        print("  ✗ [M4] %s: %s w%d인데 %s에 \"%s\" — 폐기된 근거"%(
                            q["name"],cat,w,fld,sent.strip()[:60])); err+=1; _m4+=1
    # 30차: M5도 공용 규칙을 쓰므로 import와 _core_hits를 M5 앞으로 끌어올렸다.
    import sys as _s
    _s.path.insert(0, D+"/tool"); import divergence_rules as _DR
    _core_hits = _DR.hits_fn_for(cj)   # 30차: 상대 로스터를 세지 않는 단일 구현
    # ── M5 (26차 재작성): 정정이 tag까지 전파됐는지 — **가격 대비 가치** 기준
    #
    # 25차 첫 구현은 "엘리트(w3) 캣 3개 이상 + burn"으로 판정했다. 두 가지가 틀렸다:
    #
    #  (1) **판정 변수가 틀렸다.** burn의 정의는 docs/03에 "이름값 대비 13캣 가치가 낮다"
    #      — 즉 **가격 대비 가치**다. 엘리트 캣 **개수**는 순서 척도(w1/w2/w3)를 세어
    #      합산하는 것이고, docs/05 4번이 바로 그 방식을 부당하다고 적어놨다.
    #      실제로 Luka($52 my_max vs 시장 $83-91, 애초에 획득 불가)와 Edwards가
    #      "엘리트 캣이 많다"는 이유만으로 위반으로 잡혔다 — 가격은 보지 않았으니까.
    #      이제 value_reference.rank_divergence로 판정한다:
    #        div = rank_by_my_max − rank_by_value
    #        div > 0  → 가치순위가 my_max순위보다 높다 = my_max가 **과소**평가
    #      burn(안 산다)인데 과소평가면 모순이고, buy(산다)인데 과대평가면 모순이다.
    #      양방향 대칭으로 검사한다.
    #
    #  (2) **예외 조항이 너무 넓었다.** my_max_basis가 있으면 통과시켰는데,
    #      그 필드는 **가격 사유**(23차 GP 출장 보정)이고 tag 사유가 아니다.
    #      Kessler·Giannis가 그 구멍으로 통과했다. 이제 tag을 명시적으로 다루는
    #      **tag_basis**만 예외로 인정한다. injury_exclude도 예외에서 뺐다 —
    #      부상 제외는 가격/출장 사유이고, 그것을 tag 근거로 쓰려면 tag_basis에 적어야 한다.
    #
    # 미결/신규 구분: tag_review.status == "pending" 이면 사용자 결정을 기다리는 건이고,
    # 그 표시가 없으면 신규 발생이다. 경고 등급으로 내리지 않는다 — 둘 다 err에 가산한다.
    _M5_TH=20
    _m5=0; _m5_pend=0
    for q in sorted(pl.values(), key=lambda x:-abs(((x.get("value_reference") or {}).get("rank_divergence") or 0))):
        t=q.get("tag"); vr=q.get("value_reference") or {}; d=vr.get("rank_divergence")
        if t not in ("burn","buy") or d is None: continue
        if t=="burn" and d< _M5_TH: continue
        if t=="buy"  and d>-_M5_TH: continue
        if _DR.has_tag_basis(q, _core_hits): continue   # 유일한 예외 (auto는 조건 대조 후 유효)
        tr=(q.get("tag_review") or {})
        pend = tr.get("status")=="pending"
        mark = ("미결 판단 대기 중(%s)"%tr.get("since","?")) if pend else "**신규 발생**"
        why = ("과소평가인데 안 산다" if t=="burn" else "과대평가인데 산다")
        print("  ✗ [M5] %s: tag=%s · div %+d (%s) · my_max $%d · 시장 $%d-%d — tag_basis 없음 · %s"%(
            q["name"],t,d,why,q["my_max"],q["market_low"],q["market_high"],mark))
        err+=1; _m5+=1; _m5_pend+=1 if pend else 0
    # ── M5b (26차): tag_basis 자체를 검사한다.
    # M5의 유일한 예외가 tag_basis인데 그 필드는 아무 검사도 받지 않았다 —
    # my_max_basis의 구멍을 막고 **같은 구멍을 새 필드에 다시 만든 것**이다.
    # 실제로 사용자가 준 템플릿을 부호 확인 없이 5건에 복사해서
    # Durant(+19)·Kawhi(+18)에 "my_max가 가치보다 관대"라고 적혔다 — 부호가 반대였다.
    #
    # 검사 세 가지:
    #   (a) 문장이 div를 인용할 것. 여러 번 인용하면 **마지막이 현재값**이다
    #       (결정 시점 값을 남기려면 "div +24(결정 시점) → 현재 div +10" 형식).
    #   (b) 그 현재값이 실제 rank_divergence와 ±2 이내로 일치할 것.
    #       my_max가 어디서든 바뀌면 순위가 밀려 div가 드리프트한다 — ±2는 동점 처리
    #       노이즈만 허용하는 폭이고, 그 이상은 인용이 낡은 것이므로 갱신해야 한다.
    #   (c) 부호 해석이 문장과 모순되지 않을 것.
    #       div > 0 → my_max **과소**평가 → "관대/과대" 표현 금지
    #       div < 0 → my_max **과대**평가 → "인색/과소" 표현 금지
    _GEN=["관대","과대평가","넉넉","후하"]
    _STG=["인색","과소평가","박하"]
    _M5B_TOL=2
    _m5b=0
    for q in pl.values():
        tb=q.get("tag_basis")
        if not (isinstance(tb,str) and tb.strip()): continue
        # 30차: 자동 생성 tag_basis는 div를 인용하지 않는다(드리프트 방지) —
        # 유효성은 tag_basis_auto.conditions 대조로 판정되므로 M5b 대상이 아니다.
        if q.get("tag_basis_auto"): continue
        act=(q.get("value_reference") or {}).get("rank_divergence")
        cites=[int(x) for x in _re2.findall(r"div\s*([+-]\d+)", tb)]
        if not cites:
            print("  ✗ [M5b] %s: tag_basis에 div 인용이 없다 — 근거 검증 불가"%q["name"])
            err+=1; _m5b+=1; continue
        cur=cites[-1]
        if act is None:
            print("  ✗ [M5b] %s: value_reference가 없는데 tag_basis가 div를 인용한다"%q["name"])
            err+=1; _m5b+=1; continue
        if abs(cur-act)>_M5B_TOL:
            print("  ✗ [M5b] %s: tag_basis의 현재 div 인용 %+d ≠ 실제 %+d (드리프트 %+d) — 갱신 필요"%(
                q["name"],cur,act,act-cur)); err+=1; _m5b+=1; continue
        if act>0 and any(g in tb for g in _GEN):
            print("  ✗ [M5b] %s: div %+d(my_max 과소평가)인데 tag_basis가 \"%s\" — 부호 반대"%(
                q["name"],act,next(g for g in _GEN if g in tb))); err+=1; _m5b+=1
        elif act<0 and any(g in tb for g in _STG):
            print("  ✗ [M5b] %s: div %+d(my_max 과대평가)인데 tag_basis가 \"%s\" — 부호 반대"%(
                q["name"],act,next(g for g in _STG if g in tb))); err+=1; _m5b+=1
    # ── M6 (27차 신설 · 28차 달러 노출 재정렬): tag과 **무관한** my_max 괴리 검사
    # 규칙은 tool/divergence_rules.py 단일 소스. 정렬 기준을 |div|에서 **달러 노출**로
    # 바꿨다 — rank_divergence는 무차원이라 돈이 어디 있는지 못 본다.
    _POOL=_DR.pool_names(list(pl.values()))
    _m6=_DR.m6_violations(list(pl.values()), _POOL, _core_hits)
    _m6rows=sorted([(_DR.exposure(q), _core_hits(q["name"]), q) for q in _m6],
                   key=lambda r:(-r[0], -r[1]))
    for exp,hits,q in _m6rows:
        d=_DR.div_of(q)
        sign="우리가 과소" if d>0 else "우리가 과대"
        ob="획득가능" if q["my_max"]>=q["market_low"] else "획득불가"
        print("  ✗ [M6] %-24s 노출 $%-4d div %+4d (%s) · tag=%-5s · my_max $%-3d 시장 $%d-%d · %s · 등장 %2d회 · 발동 %s"%(
            q["name"],exp,d,sign,str(q.get("tag")),q["my_max"],q["market_low"],q["market_high"],ob,hits,_DR.m6_trigger(q)))
        err+=1
    print("M6(tag 무관 괴리): 위반 %d건 · |div|>=%d 또는 (노출>=$%d 이면서 |div|>=%d) · 지명 풀 %d명"%(
        len(_m6rows),_DR.M6_TH,_DR.M6_EXP,_DR.M6_EXP_MIN_DIV,len(_POOL)))
    if _m6rows:
        print("             **달러 노출 내림차순** — 노출 = max(dollar_naive, market_high) · my_max 비의존 · 정렬 전용")
        _live=[r for r in _m6rows if r[2]["my_max"]>=r[2]["market_low"] and r[1]>=1]
        print("             등장>=1회 이면서 획득가능 = %d명 (사람 판단 필요) · 나머지 %d명은 미사용 천장(기계 종결 대상)"%(
            len(_live),len(_m6rows)-len(_live)))
    # ── 경계 감시 (27차): 임계값 하드 엣지
    # John Collins가 -20 → -19 로 밀려 위반 목록에서 **조용히 사라졌다**.
    # 해소가 아니라 드리프트다(다른 선수의 my_max가 바뀌면 순위가 밀린다).
    # |div| 18~22 구간을 위반이 아닌 감시 목록으로 낸다. err에 가산하지 않는다.
    _BAND=(18,22)
    _watch=sorted([(abs(q["value_reference"]["rank_divergence"]),q["name"],
                    q["value_reference"]["rank_divergence"],q.get("tag"))
                   for q in pl.values() if q.get("value_reference")
                   and _BAND[0]<=abs(q["value_reference"]["rank_divergence"])<=_BAND[1]],
                  key=lambda x:-x[0])
    print("경계 감시: |div| %d~%d 구간 %d명 (위반 아님 · err 미가산)"%(_BAND[0],_BAND[1],len(_watch)))
    for a,n,d,t in _watch:
        print("             ~ %-24s div %+3d · tag=%s"%(n,d,t))

    # ── 진입/이탈 (27차): 지난 실행과 비교
    # 비교 기준은 data/divergence_state.json — tool/track_divergence.py가 파이프라인
    # 마지막에 갱신한다. 검증기는 **읽기만** 한다(검증기가 data/를 쓰면 스냅샷 diff가 오염된다).
    _SP=D+"/data/divergence_state.json"
    _cur={q["name"]:q["value_reference"]["rank_divergence"]
          for q in pl.values() if q.get("value_reference")}
    # 27차: 규칙을 tool/divergence_rules.py 단일 소스에 위임한다.
    # 이전에는 여기서 따로 계산했는데 tag_basis 보유자를 빼지 않아, tracker와 집합이
    # 갈라지고 같은 데이터에서 "진입 3건"이라는 허위 변동이 났다.
    _m5set=set(_DR.flagged_names(list(pl.values()), _core_hits))
    if os.path.exists(_SP):
        _prev=json.load(io.open(_SP,encoding="utf-8"))
        _pf=set(_prev.get("flagged") or [])
        _ent=sorted(_m5set-_pf); _ext=sorted(_pf-_m5set)
        print("임계 변동 (지난 실행 %s 대비): 진입 %d · 이탈 %d"%(_prev.get("at","?"),len(_ent),len(_ext)))
        for n in _ent:
            print("             ▲ 진입 %-24s div %+d (이전 %s)"%(
                n,_cur.get(n,0),("%+d"%_prev["div"][n]) if n in (_prev.get("div") or {}) else "기록 없음"))
        for n in _ext:
            print("             ▼ 이탈 %-24s div %+d (이전 %s)"%(
                n,_cur.get(n,0),("%+d"%_prev["div"][n]) if n in (_prev.get("div") or {}) else "기록 없음"))
    else:
        print("임계 변동: 기준 스냅샷 없음 — tool/track_divergence.py 를 한 번 돌려라")
    _nq=sum(1 for q in pl.values() if (q.get("measured_source") or {}).get("gp_qualified"))
    print("cat_weights(통일 정의): M1 %d · M2 %d · M3 %d · M4 %d · M5 %d · M5b %d · 자격자 %d/%d명(GP>=%d)"%(
        _m1,_m2,_m3,_m4,_m5,_m5b,_nq,len(pl),_MINGP))
    if _m5:
        print("             M5: |div| >= %d 기준 · 미결 %d건 · 신규 %d건 · 예외(tag_basis) %d명"%(
            _M5_TH,_m5_pend,_m5-_m5_pend,
            sum(1 for q in pl.values() if isinstance(q.get("tag_basis"),str) and q["tag_basis"].strip())))
    print("             캣별 검증 인원: "+" ".join("%s=%d"%(k,v) for k,v in _cov.items()))
    print("             13캣 전부 커버 · DD는 정규근사 추정(cat_model.dd_game_prob · 24차)")

print("-"*66)
# ── I23 (35차): 가격 두 필드의 정합성
#
# `plan_price` 하나가 '부를 값'과 '낼 값'을 겸하던 것을 분리했다:
#   bid_ceiling   = min(my_max, 단일상한, 철수가)   부를 최대치
#   expected_cost = clamp(시장중간, ·, bid_ceiling)  예산 계산용
#   plan_price    = expected_cost 의 별칭 (툴·기존 검사 하위 호환)
# 이 관계가 깨지면 예산 계산과 입찰 판단이 다시 섞인다. 그래서 상시 검사한다.
_i23=0
def _chk_price(e, where, name=None):
    """⚠️ 35차: 처음엔 name을 e["name"]에서만 읽었다. **슬롯 dict에는 name이 없어서**
    (slot·candidates·plan_price만 있다) 슬롯 레벨 검사가 조용히 전부 통과했다 —
    음성 테스트에서 주입한 별칭 불일치·my_max 초과가 하나도 안 걸렸다.
    슬롯은 candidates[0]의 이름을 넘겨서 검사한다."""
    global _i23, err
    n=name or e.get("name")
    if n not in pl or "bid_ceiling" not in e: return
    p=pl[n]; bc=e["bid_ceiling"]; ec=e.get("expected_cost"); pp=e.get("plan_price")
    if bc>p["my_max"]:
        print("  ✗ [I23] %s %s: bid_ceiling $%d > my_max $%d"%(where,n,bc,p["my_max"])); err+=1; _i23+=1
    if ec is None or ec>bc:
        print("  ✗ [I23] %s %s: expected_cost %s > bid_ceiling $%d"%(where,n,ec,bc)); err+=1; _i23+=1
    if pp!=ec:
        print("  ✗ [I23] %s %s: plan_price $%s ≠ expected_cost $%s (별칭 불일치)"%(where,n,pp,ec)); err+=1; _i23+=1
    if ec is not None and ec>p["market_high"]:
        print("  ✗ [I23] %s %s: expected_cost $%d > 시장 상단 $%d"%(where,n,ec,p["market_high"])); err+=1; _i23+=1
_n23=0
for _co in cj["cores"]:
    for _s in _co["slots"]:
        for _cd in _s["candidates"]: _chk_price(_cd,_co["id"]); _n23+=1
        _chk_price(_s,_co["id"]+"/slot",_s["candidates"][0]["name"]); _n23+=1
    _pv=_co.get("pivot_plan") or {}
    for _blk in [_pv]+([_pv["fallback"]] if _pv.get("fallback") else []):
        for _r in (_blk.get("final_roster") or []):
            _chk_price(_r,_co["id"]+"/pivot"); _n23+=1
            for _a in (_r.get("alternates") or []): _chk_price(_a,_co["id"]+"/pivot"); _n23+=1
        for _sw in (_blk.get("swaps") or []):
            for _side in ("in","out"):
                if isinstance(_sw.get(_side),dict): _chk_price(_sw[_side],_co["id"]+"/swap"); _n23+=1
print("[I23] 가격 두 필드 정합성: %d개 엔트리 검사 · 위반 %d건"%(_n23,_i23))
print("      bid_ceiling <= my_max · expected_cost <= bid_ceiling · plan_price == expected_cost · expected_cost <= 시장상단")

# ── I22 (34차): 예비비(reserve) — 앵커 1명이 시장 상단으로 가도 버티는가
#
# 33차에 c6을 시장 중간값으로 재가격해 I21 패딩을 없앴지만, 완충이 $15 → $2로 사라졌다.
# 시장 상단 전액이면 c6은 $229(+$29)이고 **KAT가 중간 $45 대신 상단 $49에 낙찰되는 것만으로
# 이미 초과**다. docs/08에 "작년 상단을 $11~16 싸게 봤다"는 기록이 있다.
#
#   reserve = $200 − 계획총액
#   목표 >= $12 (앵커 1명이 상단으로 가도 버티는 값)
#   < $8  경고 (err 미가산)
#   < $4  **위반**
_RSV_T, _RSV_W, _RSV_E = 12, 8, 4
print("△ [I22] 예비비 = $200 − 계획총액 · 목표 >=$%d · 경고 <$%d · 위반 <$%d"%(_RSV_T,_RSV_W,_RSV_E))
print("             %-5s%10s%9s%11s%8s   %s"%("코어","계획총액","예비비","상단전액","초과","등급"))
for _co in cj["cores"]:
    _tot=_co["planned_total"]; _r=200-_tot
    _st=[x["candidates"][0]["name"] for x in _co["slots"]]
    _hi=sum(pl[n]["market_high"] for n in _st)
    if _r<_RSV_E:
        _g="✗ 위반"; print("  ✗ [I22] %s: 예비비 $%d < $%d — 앵커 1명이 시장 상단으로 가면 예산 초과"%(
            _co["id"],_r,_RSV_E)); err+=1
    elif _r<_RSV_W: _g="△ 경고"
    elif _r<_RSV_T: _g="목표미달"
    else: _g="OK"
    print("             %-5s%10d%9d%11d%+8d   %s"%(_co["id"],_tot,_r,_hi,_hi-200,_g))

# ── I21 (31차 · **경고 등급 · err 미가산**): 계획가가 시장 상단을 넘는 엔트리
#
# 불변식 1은 `market_low <= plan_price <= my_max`만 본다 — **시장 상단 초과는 미검사**다.
# 그래서 계획총액이 실질 예산이 아니다: 시장가로 사면 남는 돈이 생기는데 그 재배치
# 계획이 없다. John Collins($11 계획 / 시장 상단 $10)가 이 구조를 드러냈다.
#
# ⚠️ 지금 고치지 않는다. 이건 코어 재설계 입력이고 재설계는 승률 지표(30차) 다음이다.
# 여기서는 상시 노출만 한다.
#
# 미배분 = $200 − 시장중간합.  계획총액이 아니라 **예산** 기준이다 —
# 계획총액 자체가 패딩을 포함하므로 그것과 비교하면 패딩을 두 번 세는 셈이다.
_OURK=("cores","decision_table","overheat_thresholds","anchor_policy")
def _pp_entries(o, path=""):
    if isinstance(o,dict):
        _n=o.get("name") or o.get("player")
        if _n in pl and isinstance(o.get("plan_price"),int):
            yield (_n, o["plan_price"], path)
        for k,v in o.items(): yield from _pp_entries(v, f"{path}.{k}")
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from _pp_entries(v, f"{path}[{i}]")
_rows=[r for k in _OURK if k in cj for r in _pp_entries(cj[k], k)]
_over=[(pp-pl[n]["market_high"], n, pp, pl[n]["market_high"], pa)
       for n,pp,pa in _rows if pp > pl[n]["market_high"]]
_real=[]
for _co in cj["cores"]:
    for _sl in _co["slots"]:
        _cd=_sl["candidates"][0]; _real.append((_cd["name"], _cd["plan_price"]))
    _pv=_co.get("pivot_plan") or {}
    for _r in (_pv.get("final_roster") or []): _real.append((_r["name"], _r["plan_price"]))
    _fb=_pv.get("fallback") or {}
    for _r in (_fb.get("final_roster") or []): _real.append((_r["name"], _r["plan_price"]))
_ro=[(pp-pl[n]["market_high"], n, pp) for n,pp in _real if pp > pl[n]["market_high"]]
print("△ [I21 경고] 계획가 > 시장 상단: 전체 엔트리 %d건 중 **%d건** · 초과액 **$%d**"%(
    len(_rows), len(_over), sum(x[0] for x in _over)))
print("             실제 편성(슬롯 1순위 + 피벗·백업 로스터) %d건 중 **%d건** · 초과액 **$%d**"%(
    len(_real), len(_ro), sum(x[0] for x in _ro)))
print("             불변식 1은 시장 상단을 보지 않는다 — err에 가산하지 않는다(31차 · 재설계 입력)")
for _ex,_n,_pp,_mh,_pa in sorted(_over, reverse=True)[:15]:
    print("               +$%-3d %-24s 계획 $%-3d 시장상단 $%-3d  %s"%(_ex,_n,_pp,_mh,_pa[-44:]))
if len(_over)>15: print("               … 그 외 %d건"%(len(_over)-15))
print("             코어별 계획총액 / 시장중간 합 / 미배분($200−시장중간합)")
print("               %-5s%9s%12s%9s%7s"%("코어","계획총액","시장중간합","미배분","비율"))
for _co in cj["cores"]:
    _st=[x["candidates"][0]["name"] for x in _co["slots"]]
    _mid=sum((pl[n]["market_low"]+pl[n]["market_high"])/2 for n in _st)
    print("               %-5s%9d%12.0f%9.0f%6.0f%%"%(
        _co["id"], _co["planned_total"], _mid, 200-_mid, (200-_mid)/200*100))

# ── 캣 선언 검증 (18차 — 전 캣 팀 한계기여) ──
# 16·17차에 TOV·PTS만 검사했던 것을 전 캣으로 일반화한다.
# "가중치 합 >= 6" 규칙은 음수 기여를 표현하지 못하므로 판정 기준이 될 수 없다.
# 코어의 targeted/punted 선언은 선발 7명의 실측 팀 한계기여와 일치해야 한다.
_ob=cj.get("opponent_baseline") or {}
_cbm=_ob.get("cat_baselines")
# ── 인바리언트 19 (23차 신설): cat_baselines 스키마·척도 검사.
# 이 세션에서 두 번 깨졌다.
#  (1) unify_cat_weights.py가 dict를 통째로 교체해 PTS·TOV 항목이 사라졌다.
#      recompute_cores.py는 CATS를 이 dict의 키에서 가져오므로 KeyError로 죽고,
#      팀 한계기여가 stale로 남은 채 판정이 통과할 뻔했다.
#  (2) baseline에 비가중값(PTS 18.9)이 들어가 GP 가중 팀 합(≈117)과 척도가 어긋나,
#      모든 코어가 PTS를 지는 것처럼 나왔다(c7 3캣까지 붕괴).
# 그래서 존재만 보지 않고 **cat_model이 계산한 값과 대조**한다.
if _cbm:
    try:
        import sys as _s; _s.path.insert(0, D+"/tool"); import cat_model as _CMv
        _want=set(_CMv.CATS); _have=set(_cbm)
        if _want-_have:
            print("✗ [I19] cat_baselines 누락 캣: %s"%sorted(_want-_have)); err+=1
        if _have-_want:
            print("✗ [I19] cat_baselines 미지정 캣: %s"%sorted(_have-_want)); err+=1
        _Bv, _Bpv = _CMv.baselines(), _CMv.baselines_per_game()
        for _k in sorted(_want&_have):
            _e=_cbm[_k]
            for _fld,_src,_lbl in [("baseline",_Bv,"GP 가중"),("baseline_per_game",_Bpv,"경기당")]:
                if _fld not in _e:
                    print("✗ [I19] %s: %s 없음"%(_k,_fld)); err+=1
                elif abs(_e[_fld]-_src[_k])>max(1e-4, abs(_src[_k])*0.02):
                    print("✗ [I19] %s.%s = %g 인데 cat_model %s 계산은 %g (척도 불일치)"%(
                        _k,_fld,_e[_fld],_lbl,_src[_k])); err+=1
        if not _cbm.get("TOV",{}).get("lower_is_better"):
            print("✗ [I19] TOV에 lower_is_better 플래그 없음 — 부호가 뒤집힌다"); err+=1
        if not _cbm.get("A/T",{}).get("use_marginal_lift_field"):
            print("✗ [I19] A/T에 use_marginal_lift_field 없음 — 원 비율로 비교하면 저볼륨 오판"); err+=1
    except Exception as _ex:
        print("✗ [I19] cat_baselines 대조 실패: %s"%_ex); err+=1
if not _cbm:
    print("✗ opponent_baseline.cat_baselines 없음 — 캣 판정 기준이 데이터에 없음"); err+=1
elif not os.path.exists(D+"/data/stats_2025_26/measured_full.json"):
    print("캣 선언: 실측 파일 없음 — 검증 생략")
else:
    _MF=json.load(io.open(D+"/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
    _R2={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
    # 21차 정정: 9명 전원 집계 · GP 가중 (야후는 매일 라인업을 세팅하므로 벤치도 기여)
    def _av(r): return (r.get("GP") or 0)/82.0
    def _tm(names,cat):
        b=_cbm[cat]["baseline"]
        if cat=="A/T":
            rr=[_MF[n] for n in names if n in _MF and _MF[n].get("AST") is not None
                and _MF[n].get("TOV") is not None and _MF[n].get("GP")]
            if not rr: return None
            a=sum(r["AST"]*_av(r) for r in rr); t=sum(r["TOV"]*_av(r) for r in rr)
            return round(a/t-b,3)
        if cat in _R2:
            at=_R2[cat]
            rr=[_MF[n] for n in names if n in _MF and _MF[n].get(cat) is not None
                and _MF[n].get(at) is not None and _MF[n].get("GP")]
            if not rr: return None
            num=sum(r[cat]*r[at]*_av(r) for r in rr); den=sum(r[at]*_av(r) for r in rr)
            return round((num/den-b)*den*100,1)
        rr=[_MF[n] for n in names if n in _MF and _MF[n].get(cat) is not None and _MF[n].get("GP")]
        if not rr: return None
        tot=sum(r[cat]*_av(r) for r in rr)
        return round((b*len(rr)-tot) if _cbm[cat].get("lower_is_better") else (tot-b*len(rr)),1)
    _bad=0; _wins={}
    for co in cj["cores"]:
        names=[x["candidates"][0]["name"] for x in co["slots"]]   # 21차: 9명 전원
        rec=co.get("cat_team_marginals")
        if not rec:
            print("  ✗ %s: cat_team_marginals 없음"%co["id"]); err+=1; continue
        w=0; n=0
        for cat in _cbm:
            d=_tm(names,cat)
            if d is None: continue
            n+=1
            if d>0: w+=1
            if cat in rec and rec[cat] is not None and abs(rec[cat]-d)>max(0.15,abs(d)*0.02):
                print("  ✗ %s %s: cat_team_marginals %s ≠ 실계산 %s"%(co["id"],cat,rec[cat],d)); err+=1; _bad+=1
            if cat in co["targeted_cats"] and d<=0:
                print("  ✗ %s: %s를 목표로 선언했으나 팀 한계기여 %+g"%(co["id"],cat,d)); err+=1; _bad+=1
            if cat in co["punted_cats"] and d>0:
                print("  ✗ %s: %s를 포기로 선언했으나 팀 한계기여 %+g (확보)"%(co["id"],cat,d)); err+=1; _bad+=1
        _wins[co["id"]]=(w,n)
    print("캣 선언: 불일치 %d건 · 코어별 승리 캣 %s"%(
        _bad, " ".join("%s=%d/%d"%(k,v[0],v[1]) for k,v in _wins.items())))
    print("             기준선 %d캣 · DD 포함(추정) — 24차부터 선언 가정 없음"%len(_cbm))

print("-"*66)
# ── 앵커 여유 정책 검증 (2026-08-20 신설) ──
# 이전에는 "앵커는 대체후보 면제 · 실패 시 코어 전환"이 서술로만 있어 검증되지 않았다.
# 그 결과 (a) 명목 여유가 예산 여유보다 커서 실효 여력이 허구인 경우 4건,
# (b) 피벗·백업 로스터가 획득 불가 선수를 지나는 경우 6건이 방치돼 있었다.
if not cj.get("anchor_policy"):
    print("✗ anchor_policy 없음 — 앵커 여유 정책 이후 필수"); err+=1
else:
    _ids={x["id"] for x in cj["cores"]}
    _anch={x["id"]:{s["candidates"][0]["name"] for s in x["slots"] if s.get("is_anchor")}
           for x in cj["cores"]}
    _nA=_nB=0
    for co in cj["cores"]:
        _tot=sum(s["candidates"][0]["plan_price"] for s in co["slots"]); _slack=200-_tot
        if co.get("budget_slack")!=_slack:
            print("  ✗ %s: budget_slack %s ≠ 실계산 %d"%(co["id"],co.get("budget_slack"),_slack)); err+=1
        # 파생 합계 필드도 이중 보관 — 계획가를 고치면 조용히 갈라진다
        _bg=sum(x["plan_price"] for x in co["slots"] if isBig(x["candidates"][0]["name"]))
        _ce=sum(1 for x in co["slots"] if isBig(x["candidates"][0]["name"]))
        if co.get("planned_total")!=_tot:
            print("  ✗ %s: planned_total %s ≠ 실계산 %d"%(co["id"],co.get("planned_total"),_tot)); err+=1
        if co.get("big_budget_planned")!=_bg:
            print("  ✗ %s: big_budget_planned %s ≠ 실계산 %d"%(co["id"],co.get("big_budget_planned"),_bg)); err+=1
        if co.get("c_eligible_count")!=_ce:
            print("  ✗ %s: c_eligible_count %s ≠ 실계산 %d"%(co["id"],co.get("c_eligible_count"),_ce)); err+=1
        for s in co["slots"]:
            # 슬롯 plan_price와 candidates[0].plan_price 이중 보관 — 갈라지면 총액이 조용히 틀린다
            if s["plan_price"]!=s["candidates"][0]["plan_price"]:
                print("  ✗ %s/%s: 슬롯 plan_price $%d ≠ candidates[0] $%d (%s)"%(
                    co["id"],s["slot"],s["plan_price"],s["candidates"][0]["plan_price"],
                    s["candidates"][0]["name"])); err+=1
            if not s.get("is_anchor"): continue
            _nA+=1
            ap=s.get("anchor_plan")
            n=s["candidates"][0]["name"]; pp=s["candidates"][0]["plan_price"]; mx=pl[n]["my_max"]
            if not ap:
                print("  ✗ %s/%s: 앵커 %s에 anchor_plan 없음"%(co["id"],s["slot"],n)); err+=1; continue
            if ap.get("bid_ceiling")!=mx:
                print("  ✗ %s %s: bid_ceiling %s ≠ my_max %d"%(co["id"],n,ap.get("bid_ceiling"),mx)); err+=1
            if ap.get("nominal_margin")!=mx-pp:
                print("  ✗ %s %s: nominal_margin 불일치"%(co["id"],n)); err+=1
            _eff=min(mx,pp+_slack)-pp
            if ap.get("effective_headroom")!=_eff:
                print("  ✗ %s %s: effective_headroom %s ≠ 실계산 %d"%(co["id"],n,ap.get("effective_headroom"),_eff)); err+=1
            if ap.get("budget_slack")!=_slack:
                print("  ✗ %s %s: anchor_plan.budget_slack 불일치"%(co["id"],n)); err+=1
            if ap.get("dual_world_ok")!=dualok(n):
                print("  ✗ %s %s: dual_world_ok 불일치"%(co["id"],n)); err+=1
            _subs=[x["name"] for x in s["candidates"][1:] if dualok(x["name"])]
            if sorted(ap.get("substitutes_dual_ok") or [])!=sorted(_subs):
                print("  ✗ %s %s: substitutes_dual_ok 불일치 (실계산 %s)"%(co["id"],n,_subs or "없음")); err+=1
            of=ap.get("on_fail") or {}
            # 치환 시 남는 예산의 재배치가 실행 가능한지 — 없으면 "치환하면 총액 미달"이 된다
            # on_fail=pivot이면 대체후보는 피벗 플랜이 소비하므로 개별 재배치 명세는 불필요
            _tot0=sum(x["plan_price"] for x in co["slots"])
            for cd in (s["candidates"][1:] if of.get("action")=="substitute" else []):
                _nt=_tot0-pp+cd["plan_price"]
                if cd.get("total_if_used")!=_nt:
                    print("  ✗ %s %s: 대체 %s total_if_used %s ≠ %d"%(
                        co["id"],n,cd["name"],cd.get("total_if_used"),_nt)); err+=1
                rd=cd.get("redeploy")
                if _nt>=175:
                    if rd: print("  ✗ %s %s: 대체 %s는 재배치 불필요(총액 $%d)인데 redeploy 존재"%(
                        co["id"],n,cd["name"],_nt)); err+=1
                    continue
                if not rd:
                    print("  △ %s %s: 대체 %s 사용 시 총액 $%d < $175 · redeploy 명세 없음 — 예비비 과다"%(
                        co["id"],n,cd["name"],_nt)); err+=1; continue
                if not rd.get("feasible"):
                    print("  ✗ %s %s: 대체 %s의 재배치 실행 불가 (총액 $%s)"%(
                        co["id"],n,cd["name"],rd.get("total_after"))); err+=1
                _cur=_nt; _big=sum(x["plan_price"] for x in co["slots"] if isBig(x["candidates"][0]["name"]))
                _seen=set()
                for m in rd.get("moves") or []:
                    mn=m["player"]
                    if mn not in pl: print("  ✗ %s %s: 재배치 대상 없는 선수 %s"%(co["id"],n,mn)); err+=1; continue
                    if mn in _seen: print("  ✗ %s %s: 재배치에 %s 중복"%(co["id"],n,mn)); err+=1
                    _seen.add(mn)
                    if m["to"]>pl[mn]["my_max"]:
                        print("  ✗ %s %s: 재배치 %s $%d > my_max $%d"%(co["id"],n,mn,m["to"],pl[mn]["my_max"])); err+=1
                    if co.get("single_player_cap") and m["to"]>co["single_player_cap"]:
                        print("  ✗ %s %s: 재배치 %s $%d > 단일상한"%(co["id"],n,mn,m["to"])); err+=1
                    if m["to"]<=m["from"]:
                        print("  ✗ %s %s: 재배치 %s가 증액이 아님"%(co["id"],n,mn)); err+=1
                    _cur+=m["to"]-m["from"]
                    if isBig(mn): _big+=m["to"]-m["from"]
                if _cur!=rd.get("total_after"):
                    print("  ✗ %s %s: 대체 %s redeploy total_after %s ≠ 실계산 %d"%(
                        co["id"],n,cd["name"],rd.get("total_after"),_cur)); err+=1
                # 35차: 기대원가 체계에서 **미달은 예비비**다 → 경고. 초과만 위반.
                if _cur>200:
                    print("  ✗ %s %s: 대체 %s 재배치 후 총액 $%d > $200"%(co["id"],n,cd["name"],_cur)); err+=1
                elif _cur<175:
                    print("  △ %s %s: 대체 %s 재배치 후 총액 $%d — 예비비 $%d 과다(과소 편성)"%(
                        co["id"],n,cd["name"],_cur,200-_cur)); warn+=1
                if _big>co["big_budget_cap"]:
                    print("  ✗ %s %s: 대체 %s 재배치 후 빅맨 $%d > 상한 $%d"%(
                        co["id"],n,cd["name"],_big,co["big_budget_cap"])); err+=1
            if of.get("action")=="pivot":
                _tr={t["player"] for t in co["pivot_plan"]["triggers"]}
                if n not in _tr:
                    print("  ✗ %s %s: on_fail=pivot인데 피벗 트리거에 없음"%(co["id"],n)); err+=1
                if of.get("target")!="pivot_plan":
                    print("  ✗ %s %s: on_fail=pivot의 target이 pivot_plan이 아님"%(co["id"],n)); err+=1
                # 피벗이 실제로 그 앵커를 빼야 한다 — 남아 있으면 탈출 경로가 아니다
                if n in {r["name"] for r in co["pivot_plan"]["final_roster"]}:
                    print("  ✗ %s %s: on_fail=pivot인데 피벗 로스터에 그대로 남아 있음"%(co["id"],n)); err+=1
            elif of.get("action")=="substitute":
                if not _subs:
                    print("  ✗ %s %s: on_fail=substitute인데 이중세계 유효 대체 0명"%(co["id"],n)); err+=1
                elif of.get("target") not in _subs:
                    print("  ✗ %s %s: on_fail 대상 %s이 이중세계 유효 대체가 아님"%(co["id"],n,of.get("target"))); err+=1
            elif of.get("action")=="switch_core":
                t=of.get("target")
                if t not in _ids: print("  ✗ %s %s: on_fail 목적지 코어 없음 %s"%(co["id"],n,t)); err+=1
                elif t==co["id"]: print("  ✗ %s %s: on_fail 목적지가 자기 코어"%(co["id"],n)); err+=1
                elif n in _anch[t]: print("  ✗ %s %s: on_fail 목적지 %s가 같은 앵커에 의존"%(co["id"],n,t)); err+=1
            else:
                print("  ✗ %s %s: on_fail.action이 substitute/switch_core가 아님"%(co["id"],n)); err+=1
            if not of.get("note"): print("  ✗ %s %s: on_fail.note 없음"%(co["id"],n)); err+=1
            # 재적합 불가 + 대체 0명 → 조건부 베팅 선언 필수
            if not dualok(n) and not _subs:
                cd=co.get("conditional_on_discount")
                if not cd or cd.get("anchor")!=n:
                    print("  ✗ %s: 앵커 %s가 재적합 획득불가·대체0명인데 conditional_on_discount 미선언"%(co["id"],n)); err+=1
        # 피벗·백업 로스터의 이중세계 검증
        pv=co["pivot_plan"]
        for lbl,ros,tk in [("pivot",pv["final_roster"],pv["final_total"])]+(
            [("fallback",pv["fallback"]["final_roster"],pv["fallback"]["final_total"])] if pv.get("fallback") else []):
            _names={r["name"] for r in ros}
            for r in ros:
                n=r["name"]; _nB+=1
                if r.get("dual_world_ok")!=dualok(n):
                    print("  ✗ %s %s %s: dual_world_ok 불일치 (%s)"%(co["id"],lbl,n,dualok(n))); err+=1
                if dualok(n): continue
                alts=[a for a in (r.get("alternates") or []) if dualok(a["name"])]
                cd=co.get("conditional_on_discount")
                if not alts and not (cd and cd.get("anchor")==n):
                    print("  ✗ %s %s: %s가 재적합 획득불가인데 대체후보도 조건부선언도 없음"%(co["id"],lbl,n)); err+=1
                for a in (r.get("alternates") or []):
                    an,ap2=a["name"],a["plan_price"]
                    if an not in pl: print("  ✗ %s %s: 대체후보 없는 선수 %s"%(co["id"],lbl,an)); err+=1; continue
                    need=NEED[r["slot"]]
                    if need and need not in pl[an]["pos"]:
                        print("  ✗ %s %s %s: 대체 %s 포지션 자격 불가"%(co["id"],lbl,r["slot"],an)); err+=1
                    if not (pl[an]["market_low"]<=ap2<=pl[an]["my_max"]):
                        print("  ✗ %s %s: 대체 %s 계획가 $%d 범위 밖 ($%d~$%d)"%(
                            co["id"],lbl,an,ap2,pl[an]["market_low"],pl[an]["my_max"])); err+=1
                    if an in _names:
                        print("  ✗ %s %s: 대체 %s가 같은 로스터에 이미 있음"%(co["id"],lbl,an)); err+=1
                    _nt=tk-r["plan_price"]+ap2
                    if a.get("total_if_used")!=_nt:
                        print("  ✗ %s %s: 대체 %s total_if_used %s ≠ %d"%(co["id"],lbl,an,a.get("total_if_used"),_nt)); err+=1
                    if _nt>200:
                        print("  ✗ %s %s: 대체 %s 사용 시 총액 $%d > $200"%(co["id"],lbl,an,_nt)); err+=1
                    elif _nt<175:
                        print("  △ %s %s: 대체 %s 사용 시 총액 $%d — 예비비 $%d 과다"%(
                            co["id"],lbl,an,_nt,200-_nt)); warn+=1
    # ── I24: 피벗 로스터 == base 1순위 + swaps (37차 신설) ──────────────────
    # 피벗의 정의가 "base + 트리거 대응 교체"인데 그 관계를 아무도 검사하지 않아
    # 33·34차 base 변경이 피벗에 전파되지 않았다(7개 중 6개 드리프트).
    # 증상은 「예비비 과소 편성」으로 나타났다 — 피벗이 옛 base의 싼 선수를 들고 있었다.
    # 복구 도구: tool/rebuild_pivots.py
    print("-"*66)
    _i24=0
    for co in cj["cores"]:
        pv=co["pivot_plan"]
        _bn=[s["candidates"][0]["name"] for s in co["slots"]]
        _sw={x["out"]["name"]:x["in"]["name"] for x in pv["swaps"]}
        for _o in _sw:
            if _o not in _bn:
                print("  ✗ [I24] %s: swap out '%s' 이 base 1순위에 없다 — stale swap"%(co["id"],_o)); err+=1
        _exp=[_sw.get(n,n) for n in _bn]
        _act=[r["name"] for r in pv["final_roster"]]
        if sorted(_exp)!=sorted(_act):
            print("  ✗ [I24] %s 피벗: base+swaps 와 final_roster 불일치"%co["id"])
            print("         빠짐: %s"%(sorted(set(_exp)-set(_act)) or "—"))
            print("         잉여: %s"%(sorted(set(_act)-set(_exp)) or "—"))
            err+=1
        else:
            _i24+=1
        # 트리거 선수가 피벗 로스터에 남아 있으면 안 된다 — 트리거가 걸린 세계에서
        # 그 계획가는 존재하지 않는다(c3가 `Zubac > $16` 트리거인데 Zubac을 $11에 샀다).
        _trg={t["player"] for t in pv["triggers"]}&{r["name"] for r in pv["final_roster"]}
        if _trg:
            print("  ✗ [I24] %s 피벗: 트리거 선수가 로스터에 잔류 — %s"%(co["id"],", ".join(sorted(_trg)))); err+=1
        # 피벗 예비비 — I22는 base만 본다. 임계값은 상수가 아니라 **실제 노출액**으로 낸다:
        # 로스터에서 한 명이 자기 상한까지 올라갈 때 필요한 최대 추가액.
        # (처음엔 $8 상수로 뒀는데 c4는 무앵커 코어라 "앵커가 상단으로 가면"이라는
        #  전제 자체가 성립하지 않았다 — 37차 정정)
        # 노출은 **앵커**에 대해서만 센다. 비앵커는 대체후보가 있어 값이 뛰면 갈아타면 되고,
        # 상한(bid_ceiling)은 my_max에서 오므로 "누구든 상한까지 갈 수 있다"로 재면
        # my_max를 올릴 때마다 경고가 늘어난다(37차에 실제로 4개 피벗이 한꺼번에 걸렸다).
        # I22의 원래 근거대로 "앵커가 **시장 상단**까지 갈 때 얼마가 더 필요한가"로 잰다.
        _pr=200-pv["final_total"]
        _anc=[r for r in pv["final_roster"] if r.get("is_anchor")]
        _exp=0; _who=None
        for r in _anc:
            n=r["name"]
            if n not in pl: continue
            need=min(pl[n]["market_high"], r.get("bid_ceiling") or r["plan_price"])-r["plan_price"]
            if need>_exp: _exp, _who = need, r
        if _who and _pr<_exp:
            print("  △ [I24] %s 피벗: 예비비 $%d < 앵커 노출 $%d (%s $%d → 시장 상단 $%d)"%(
                co["id"],_pr,_exp,_who["name"],_who["plan_price"],pl[_who["name"]]["market_high"])); warn+=1
    print("[I24] 피벗 로스터 = base 1순위 + swaps: %d/%d 코어 일치"%(_i24,len(cj["cores"])))

    # ── I26: 가격 조건이 발동 가능한 사건인가 (39차 신설) ─────────────────────
    # 트리거가 임계값 소스와 일치하는지는 봤지만 **그 조건이 일어날 수 있는가**는
    # 아무도 안 봤다. 도달 불가능한 분기는 드래프트 당일 영원히 거짓이고 조용히 산다.
    #
    # ⚠️ 판정에 **균등 가정을 단독으로 쓰지 않는다.** market_low/high 는 추정 구간이지
    #    지지집합이 아니다. 균등만 쓰면 18건이 "항상 거짓"으로 잡히는데, 같은 선수의
    #    작년 실낙찰가가 그중 여럿을 직접 반증한다(예: Mobley 철수가 >$30 은 균등 P=0
    #    인데 작년 실제 $50(스케일 후)에 팔렸다). 그래서 **균등 AND 실측 국소** 두 모델이
    #    모두 불가라고 할 때만 잡는다. 근거·모델 설명은 tool/trigger_audit.py.
    print("-"*66)
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tool"))
        import trigger_audit as _TA
        _n26=_dead=_nb=0
        for _src,_lbl,_rules in _TA.conditions():
            if not _rules: continue
            _pu=_pe=1.0
            for _nm,_thr,_d in _rules:
                _u=_TA.p_uniform(_nm,_thr); _e=_TA.p_empirical(_nm,_thr)
                if _d=="gt":
                    _u=1.0-_u; _e=None if _e is None else 1.0-_e
                _pu*=_u; _pe=None if (_pe is None or _e is None) else _pe*_e
            _n26+=1
            if _pe is None: continue
            _both_never = _pu<=_TA.NEVER and _pe<=_TA.NEVER
            _both_always= _pu>=_TA.ALWAYS and _pe>=_TA.ALWAYS
            if _src=="판단표" and (_both_never or _both_always):
                print("  ✗ [I26] %s: 가격 조건이 %s — 균등 %.2f · 실측 %.2f (%s)"%(
                    _lbl, "절대 발동 불가" if _both_never else "항상 참이라 게이트 역할 없음",
                    _pu,_pe,_TA.conditions and "죽은 분기"))
                err+=1; _dead+=1
            elif _src!="판단표" and _both_never:
                print("  △ [I26] %s %s: 이 선 아래로는 아무 일도 일어나지 않는다 — 균등 %.2f · 실측 %.2f"%(
                    _src,_lbl,_pu,_pe)); warn+=1; _nb+=1
        print("[I26] 가격 조건 발동 가능성: %d건 검사 · 죽은 분기 %d · 비구속 임계값 %d"%(_n26,_dead,_nb))
        print("      균등(구간 내 균등) **AND** 실측(작년 120건 · 순위 국소 잔차비) 둘 다 불가일 때만 위반")

        # I26b: 앵커 트리거는 **엘리트 대조군**(작년 $60+ · n=11) 확률을 함께 표시한다.
        # 게이트가 아니라 표시다 — 대조군이 엘리트에만 정의되므로 불변식에 쓰면
        # "통과"와 "판정 불가"가 구분되지 않고 그게 곧 조용한 통과다(39차 평가 세션 결정).
        # ⚠️ **행 확률과 선수별 확률을 섞어 읽지 말 것.** 판단표 행은 규칙의 **곱**이다.
        #    39차에 피어가 이 둘을 같은 것으로 읽고 "I26b가 틀렸다"고 보고했다 —
        #    trigger_audit 의 c1 행 0.10 = KAT 0.55 × Hali 0.18 이고, I26b 의 0.55는
        #    KAT 단독이다. 둘 다 맞다. 그래서 행 확률을 함께 찍어 혼동을 없앤다.
        _anchors={s["candidates"][0]["name"] for c in cj["cores"] for s in c["slots"] if s.get("is_anchor")}
        _shown=0
        for _r in cj["decision_table"]:
            _rules=[x for x in ((_r.get("cond") or {}).get("rules") or []) if x["player"] in pl]
            _each=[]
            for _x in _rules:
                if _x["player"] not in _anchors: continue
                _pe3=_TA.p_elite(_x["player"],_x["max"])
                if _pe3 is None: continue
                _shown+=1
                _mk=pl[_x["player"]]
                _tag="△ 얇음" if _pe3<=0.20 else ""
                if _tag: warn+=1
                _each.append(_pe3)
                print("      [I26b] %-6s %-24s 임계 $%-3d · 단독 P=%.2f (시장 $%d-%d) %s"%(
                    _r["core"],_x["player"],_x["max"],_pe3,_mk["market_low"],_mk["market_high"],_tag))
            if len(_each)>1:
                _row=1.0
                for _v in _each: _row*=_v
                print("      [I26b] %-6s %-24s 행 결합 P=%.2f = %s  ← 판단표가 실제로 열릴 확률"%(
                    _r["core"],"(위 %d개 조건의 곱)"%len(_each),_row,
                    " × ".join("%.2f"%v for v in _each)))
        if _shown:
            print("      ↑ 앵커 트리거 %d건 · **표시 전용**(불변식 아님) · n=11 이므로 구간으로만 읽을 것"%_shown)

        # ── I27: 임계값이 my_max보다 낮은데 근거가 없다 (39차 · 경고) ──────────
        # 진짜 실패 모드는 "임계값 < my_max"가 아니라 **"my_max가 움직였는데 임계값이
        # 안 따라간 것"**이다. c3가 그 사례다(37차에 SGA 72→79인데 판단표는 $72 그대로).
        # 의도적 보수성(c1 Hali $48 vs my_max $50)까지 금지하면 안 되므로,
        # `threshold_basis` 필드가 있으면 통과시킨다 — 낡음과 의도를 사람이 구분해 적는다.
        _n27=_w27=0
        for _r in cj["decision_table"]:
            for _x in (_r.get("cond") or {}).get("rules") or []:
                if _x["player"] not in pl: continue
                _n27+=1
                _mm=pl[_x["player"]]["my_max"]
                if _x["max"]<_mm and not _x.get("threshold_basis"):
                    print("  △ [I27] %s %s: 임계값 $%d < my_max $%d 인데 threshold_basis 없음"
                          " — my_max가 움직인 뒤 판단표가 안 따라왔을 수 있다"%(
                        _r["core"],_x["player"],_x["max"],_mm)); warn+=1; _w27+=1
        print("[I27] 판단표 임계값 vs my_max: %d건 검사 · 근거 없는 하향 %d건"%(_n27,_w27))
    except Exception as _ex:
        print("[I26] 건너뜀 — %s: %s"%(type(_ex).__name__,_ex))

    # ── I28: 판단표 `label` 문장이 `cond.rules` 와 어긋나지 않는가 (39차 · 경고) ──
    # A가 rules 만 고치고 label 을 안 고쳐 셋이 낡아 있었다(c3 $72↔85 · c2 $88↔97 ·
    # c5 가격 게이트를 제거했는데 문장에 잔존). **툴은 rules 에서 화면 문자열을 따로
    # 만들기 때문에 화면은 맞았고 데이터만 갈라져** 아무도 못 봤다 —
    # 「정적으로 적어둔 안내는 반드시 낡는다」의 가장 안 보이는 형태다.
    #
    # 라벨 전체를 생성해 비교하지 않는 이유는 tool_embed.label_price_clauses 주석 참조
    # (라벨은 사람 약칭 KAT·Hali·SGA 를 쓰고 툴은 성을 쓴다 — 약칭 사전을 만들면 그게
    #  또 하나의 드리프트 원이 된다). **금액만** 대조한다.
    _n28=_w28=0
    for _r in cj["decision_table"]:
        _lab=sorted(_TE.label_price_clauses(_r.get("label") or ""))
        _rul=sorted(x["max"] for x in ((_r.get("cond") or {}).get("rules") or []))
        _n28+=1
        if _lab!=_rul:
            _why=("가격 게이트가 없는데 라벨에 금액이 남아 있다" if not _rul else
                  "라벨에 금액이 없다" if not _lab else "금액 불일치")
            print("  △ [I28] %s: label %s ↔ rules %s — %s\n         label: %s"%(
                _r["core"],_lab or "없음",_rul or "없음",_why,_r.get("label"))); warn+=1; _w28+=1
    print("[I28] 판단표 label ↔ cond.rules 금액: %d행 검사 · 불일치 %d건"%(_n28,_w28))

    # ── I29: 슬롯 role 이 **캣 공급 목적**을 선언하면 후보 전원이 그 캣을 줘야 한다 ──
    # 사용자가 직접 잡은 결함: c6 BN role 이 "3PT 소스 — 3PM 공백을 메운다" 인데
    # 2순위가 Clingan(3PM 0.8) 이었다. 검사가 없어 조용히 남아 있었다.
    #
    # ⚠️ 범위를 좁힌 이유 — 두 넓은 변형을 먼저 재보고 버렸다:
    #   · "role 에 캣 이름이 있으면 후보 전원 검사" → 92건 중 **52건 발화**. role 은 대개
    #     1순위의 프로필을 적은 것이라(“OREB 3.0 · DD 34 · AST” = Şengün 설명) 대체 후보가
    #     다른 프로필인 것이 정상이다.
    #   · "1순위 본인이 자기 role 의 캣에 약한가" → 18건. 대부분 DD 가중치 척도 문제다
    #     (DD 34인 Şengün 도 w=1). 텍스트 결함이 아니라 가중치 스케일 문제라 오탐이다.
    # → **목적 선언 어휘가 있을 때만** 본다. 지금 데이터에서 정확히 1건 발화한다.
    _PURPOSE=("소스","공급","잠금","전용","메운다")
    _CATS=["3PM","3P%","FT%","FG%","OREB","REB","AST","STL","BLK","DD","A/T","TOV","PTS"]
    def _cats_in(t):
        out=[]; r=t
        for c in sorted(_CATS,key=len,reverse=True):   # 3P% 가 3PM 로 오인되지 않게 긴 것부터
            if c in r: out.append(c); r=r.replace(c,"")
        return out
    _n29=_w29=0
    for co in cj["cores"]:
        for s in co["slots"]:
            _role=s.get("role") or ""
            if not any(k in _role for k in _PURPOSE): continue
            for _c in _cats_in(_role):
                _n29+=1
                _weak=[cd["name"] for cd in s["candidates"]
                       if ((pl.get(cd["name"],{}).get("cat_weights") or {}).get(_c) or 0)<2]
                if _weak:
                    print("  △ [I29] %s %s: role 이 '%s' 공급을 선언했는데 후보가 못 준다 — %s\n         role: %s"%(
                        co["id"],s["slot"],_c,", ".join(_weak),_role)); warn+=1; _w29+=1
    print("[I29] role 의 캣 공급 선언 ↔ 후보: %d건 검사 · 불일치 %d건"%(_n29,_w29))

    # ── I31: 9인이 PG SG SF PF C UTIL UTIL BN BN 에 **이분매칭** 되는가 (40차 신설) ──
    #
    # 왜 기존 검사로 안 잡혔나
    #   슬롯 자격 검사는 있었다 — `NEED={"PG":"G",...}` + `k in p["pos"]`. 규칙은 맞았고
    #   **입력이 넓었다.** `pos` 는 G/F/C 3분 추상이라 `G/F` 가 SF 로도 PF 로도 통과했다.
    #   그래서 SF 충원 0명인 c3, PF 충원 0명인 c2 가 불변식 30개를 전부 통과했다.
    #   40차에 야후 실자격 19명이 들어오자 **11명이 불일치했고 11건 전부 자격을 잃는 방향**
    #   이었다 — 추상화의 계통 편향이다(`tool/pos_elig.py` 참조).
    #
    # 두 층을 함께 본다. 라벨이 유효해도 매칭이 깨질 수 있고, 그 반대도 있다:
    #   (a) 라벨 유효성 — 선언된 자리에 그 선수를 **실제로 넣을 수 있는가**.
    #       매칭이 성립해도 화면이 틀린 자리를 지시하면 10초 시계 아래서 막힌다.
    #   (b) 완전매칭 — 9명이 9칸을 다 채우는가.
    #
    # ⚠️ 이건 **합법성 판정이 아니다.** 야후는 포지션 커버리지를 강제하지 않는다.
    #   매칭이 깨진다는 것은 그 칸이 매일 비어 **선수-경기를 버린다**는 뜻이고,
    #   실측 손실은 0.2~3.2%다(`tool/lineup_feasibility.py` · cores[].lineup_loss).
    #   그래서 위반 등급이되 "조립 불가"라고 쓰지 않는다.
    import pos_elig as _PEV
    _n31=_e31=0
    for co in cj["cores"]:
        for _tag,_ros in (("base",[(s["slot"],s["candidates"][0]["name"]) for s in co["slots"]]),
                          ("pivot",[(r["slot"],r["name"]) for r in
                                    ((co.get("pivot_plan") or {}).get("final_roster") or [])])):
            if not _ros: continue
            _n31+=1
            for _sl,_nm,_el in _PEV.label_errors(_ros,pl):
                print("  ✗ [I31] %s %s: %s 를 %s 에 뒀는데 자격은 %s"%(
                    co["id"],_tag,_nm,_sl,"/".join(_el) or "없음")); err+=1; _e31+=1
            if sorted(s for s,_ in _ros)!=sorted(_PEV.ROSTER_SLOTS):
                print("  ✗ [I31] %s %s: 슬롯 구성 불일치 %s"%(
                    co["id"],_tag,sorted(s for s,_ in _ros))); err+=1; _e31+=1
            elif _PEV.match([pl[n] for _,n in _ros if n in pl]) is None:
                _lack=[sl for sl in _PEV.NAMED
                       if not any(_PEV.can(pl[n],sl) for _,n in _ros if n in pl)]
                print("  ✗ [I31] %s %s: 9인이 9칸을 못 채운다 — 충원 0명인 칸 %s"%(
                    co["id"],_tag,", ".join(_lack) or "(조합 문제)")); err+=1; _e31+=1
        # 대체후보도 그 슬롯에 실제로 들어갈 수 있어야 한다. 1순위를 놓쳤을 때 가는
        # 자리이므로 여기가 비면 **대안이 있다고 화면이 거짓말한다.**
        for s in co["slots"]:
            for cd in s["candidates"][1:]:
                _p=pl.get(cd["name"])
                if _p and not _PEV.can(_p,s["slot"]):
                    print("  ✗ [I31] %s %s 대체 %s: 자격 %s"%(
                        co["id"],s["slot"],cd["name"],"/".join(sorted(_PEV.elig(_p))) or "없음"))
                    err+=1; _e31+=1
    _unconf=sum(1 for co in cj["cores"] for s in co["slots"]
                if not _PEV.confirmed(pl.get(s["candidates"][0]["name"],{})))
    print("[I31] 슬롯 이분매칭: 로스터 %d개 검사 · 위반 %d건 · 1순위 중 자격 미확인 %d명"
          %(_n31,_e31,_unconf))
    print("             ⚠️ 미확인은 추상 pos(G→PG,SG · F→SF,PF)로 판정한다. 확인된 19명에서"
          " **11명이 자격을 잃는 방향으로 틀렸다** — 미확인 판정은 계통적으로 낙관 편향이다.")

    # ── I34 (40차 신설): 대체안이 **예산 안에서 실제로 실행되는가** ─────────────
    #
    # 대체안은 1순위를 놓쳤을 때 가는 자리다. 그런데 전환하면 총액이 $200을 넘어
    # **살 수 없는 대안**이 4건 있었다(c3·c5 의 C 가 Clingan $12 → Duren $27 · c6 UTIL 이
    # Edgecombe $5 → Knueppel/Bane $22). 화면에는 대안이 있다고 뜨고 실제로는 못 산다.
    #
    # 기존 검사들은 대체안의 **가격 정합**(my_max·시장하단·단일상한)만 봤다. 그건 "그 값이
    # 말이 되는가"이고, 여기서 묻는 것은 **"그 값을 낼 돈이 있는가"** 다. 다른 질문이다.
    # 예비비 하한은 I22 와 같은 $4 를 쓴다 — 대안으로 갈아탄 세계도 여전히 앵커를 안고 있다.
    _n34=_e34=_w34=0
    for co in cj["cores"]:
        _tot=co["planned_total"]
        for s in co["slots"]:
            for cd in s["candidates"][1:]:
                _n34+=1
                _t=_tot-s["plan_price"]+cd["plan_price"]; _r=200-_t
                if _r<0:
                    print("  ✗ [I34] %s %s: %s → %s 로 갈아타면 총액 $%d (초과 $%d) — 살 수 없는 대안"%(
                        co["id"],s["slot"],s["candidates"][0]["name"],cd["name"],_t,-_r)); err+=1; _e34+=1
                elif _r<_RSV_E:
                    print("  △ [I34] %s %s: %s → %s 로 갈아타면 예비비 $%d < $%d"%(
                        co["id"],s["slot"],s["candidates"][0]["name"],cd["name"],_r,_RSV_E)); warn+=1; _w34+=1
    print("[I34] 대체안 예산 실행 가능성: %d건 검사 · 실행 불가 %d · 예비비 하한 미달 %d"%(_n34,_e34,_w34))

    # ── I35 (40차 신설): 피벗 서술이 **인용한 금액**이 실제와 맞는가 ──────────────
    #
    # 사용자가 직접 잡은 결함 계열이다 — c6 피벗 서술이 존재하지 않는 교체 2건과
    # 빅맨 $96 을 안내하고 있었다. 39차에 손으로 고쳤는데 c1 은 $78 로 고쳐 놓고
    # 40차 재조립에서 실제가 $82 가 되면서 **틀린 숫자를 고친 문장이 다시 낡았다.**
    #
    # 서술문 전체를 검사할 수는 없다. 하지만 「빅맨 … $NN」은 계산 가능한 값을 인용하는
    # 고정된 형태이고, 실제로 두 번 갈라진 자리다. **좁게 그 형태만** 본다(I29 와 같은 방침).
    import re as _re35
    _P35=_re35.compile(r"빅맨[^.。\n]{0,24}?\$(\d+)")
    _n35=_w35=0
    for co in cj["cores"]:
        _pv=co.get("pivot_plan") or {}
        _big=sum(r["plan_price"] for r in (_pv.get("final_roster") or []) if isBig(r["name"]))
        for _m in _P35.finditer(_pv.get("rationale") or ""):
            _n35+=1
            if int(_m.group(1))!=_big:
                print("  △ [I35] %s 피벗 서술이 빅맨 $%s 라고 적었는데 실제는 $%d\n         …%s…"%(
                    co["id"],_m.group(1),_big,
                    _pv["rationale"][max(0,_m.start()-26):_m.end()+6].replace("\n"," ")))
                warn+=1; _w35+=1
    print("[I35] 피벗 서술의 빅맨 예산 인용: %d건 검사 · 불일치 %d건"%(_n35,_w35))

    _cond=[x["id"] for x in cj["cores"] if x.get("conditional_on_discount")]
    print("앵커 정책: 앵커 %d개 · 피벗/백업 엔트리 %d개 · 조건부 베팅 %s%s"%(
        _nA,_nB,",".join(_cond) or "없음",
        "" if RF else " (재적합 파일 없음 — 이중세계 검증 생략)"))

print("-"*66)
# ── 툴 임베드 상수 ↔ cores.json 동기화 검증 ──
# 이 프로젝트에서 "정적/임베드 데이터가 낡는" 문제가 5번 재발했다(피벗·임계값·백업조건·
# 판단표·전환트리거). 2026-08-20 2계층 분리 때 툴의 DECISION이 낡아 코어 7 판정이
# 4명 목록으로 남아 있던 것을 잡았다. 그래서 검증기가 직접 비교한다.
import re as _re
_tp=D+"/tool/auction-console.html"
if not os.path.exists(_tp):
    print("✗ 툴 파일 없음: tool/auction-console.html"); err+=1
else:
    _ts=io.open(_tp,encoding="utf-8").read()
    def _const(name,brk):
        m=_re.search(r"const %s=(%s.*?%s);\n"%(name,_re.escape(brk[0]),_re.escape(brk[1])),_ts,_re.S)
        return json.loads(m.group(1)) if m else None
    _dec=_const("DECISION","[]")
    _oh=_const("OVERHEAT","[]")
    _ot=_const("OTIERS","{}")
    _m1=_re.search(r'const DECISION_ONELINER=(".*?");\n',_ts,_re.S)
    # 🔴 40차: 여기서 **이스케이프된 JS 문자열**을 그대로 잡아 cores.json 의 원문과
    #   비교하고 있었다. 한 줄짜리일 때는 우연히 같았지만, 문자열에 개행이나 따옴표가
    #   들어가는 순간 툴은 `\n`(두 글자) · 원본은 실제 개행이라 **항상 불일치**가 된다.
    #   실제로 40차에 한 줄 요약이 두 줄이 되자 이 검사가 오탐을 냈다.
    #   JSON 으로 파싱해서 **값끼리** 비교한다.
    try:    _one=json.loads(_m1.group(1)) if _m1 else None
    except Exception: _one=None
    # 39차: DECISION 만 원본과 직접 대조하고 있었다(OVERHEAT·OTIERS·CORES·PIVOTS는 이미
    # tool_embed 경유). A가 판단표에 **실제 12팀 강도**를 얹으려 하자 같은 벽에 막혔다 —
    # 강도는 32차 원칙상 cores.json 에 넣을 수 없어 툴 상수 생성 시점에만 합쳐지는데,
    # 검증기가 원본과 비교하면 그 순간 불일치가 된다.
    try:
        _simj=json.load(io.open(D+"/data/matchup_sim.json",encoding="utf-8"))
    except Exception:
        _simj=None
    if _dec!=_TE.build_decision(cj,_simj):
        print("✗ 툴 DECISION이 cores.json.decision_table과 불일치 — 재생성 필요"); err+=1
    if _one!=cj["decision_oneliner"]:
        print("✗ 툴 DECISION_ONELINER 불일치 — 재생성 필요"); err+=1
    # 39차: 기대 구조를 tool_embed 에서 가져온다. 이전에는 sync_tool.py 와 **같은 dict를
    # 각자 조립**하고 있었고, 필드를 하나 늘리려면 두 파일을 같이 고쳐야 했다 —
    # A가 `binding` 필드를 실었을 때 이쪽만 안 바뀌어 즉시 불일치가 났다.
    _ohx=_TE.build_overheat(cj)
    if _oh!=_ohx:
        print("✗ 툴 OVERHEAT이 cores.json.overheat_thresholds와 불일치 — 재생성 필요"); err+=1
    _otx=_TE.build_tiers(cj)
    if _ot!=_otx:
        print("✗ 툴 OTIERS이 cores.json.overheat_tiers와 불일치 — 재생성 필요"); err+=1
    # 툴이 과열 판정에 철수가를 쓰지 않는지 (계층 분리의 핵심)
    # 툴 P 배열의 시장가(mk) ↔ players.json — 재적합 적용으로 새로 load-bearing이 된 동기화 지점
    _pm=dict(_re.findall(r'\{n:"((?:[^"\\]|\\.)*)".*?mk:\[(\d+,\d+)\]', _ts))
    _bad=[]; _missing=[]
    for _n,_q in pl.items():
        _key=_n.replace('"','\\"')
        if _key not in _pm: _missing.append(_n); continue
        if _pm[_key]!="%d,%d"%(_q["market_low"],_q["market_high"]): _bad.append(_n)
    if _missing:
        print("✗ 툴 P에 없는 선수 %d명: %s"%(len(_missing),", ".join(_missing[:5]))); err+=1
    if _bad:
        print("✗ 툴 P의 시장가가 players.json과 불일치 %d명: %s — 재생성 필요"%(
            len(_bad),", ".join(_bad[:5]))); err+=1
    if len(_pm)!=len(pl):
        print("✗ 툴 P 행 수 %d ≠ players.json %d"%(len(_pm),len(pl))); err+=1
    _cs=_const("CORES","[]")
    if _cs is None:
        print("✗ 툴 CORES 상수 파싱 실패"); err+=1
    else:
        # ⚠️ 38차: 이 블록은 `_sl["anchor_plan"]`과 그 하위 키를 **전부 직접 인덱싱**했다.
        # 앵커 슬롯에 anchor_plan이 없으면 KeyError로 **검증기가 여기서 죽고**, 뒤쪽 검사
        # (I20 P 배열 · 과열 계층 · 판단표)가 한 건도 실행되지 않았다. 조용한 통과가 아니라
        # 조용한 **절단**이다. `tests/negative_tests.py` I13이 이걸 잡아냈다.
        #   · 33차에 같은 형태가 이미 터졌다 — recompute_cores의 `if not ap: continue`에서
        #     빈 dict가 falsy라 anchor_plan이 생성되지 않고 sync_tool이 KeyError로 죽었다
        #     (docs/04 33차 「구현 중 걸린 것」 3번). 지금 고치는 것은 그 사고의 하류다.
        # 방어하되 **조용히 건너뛰지 않는다** — 없으면 위반으로 올리고 상세 비교만 생략한다.
        _exp,_probs=_TE.build_cores(cj)
        _cores_broken=bool(_probs)
        for _p in _probs:
            print("  ✗ 툴 CORES 대조: %s — 상세 비교 생략(뒤쪽 검사는 계속 실행)"%_p); err+=1
        if _cores_broken:
            # 기대값 자체가 결손 데이터로 만들어졌으므로 "재생성 필요"는 오진이다.
            # 위 위반이 이미 err에 가산됐다 — 여기서 중복 가산하지 않고 이유만 남긴다.
            print("  △ 툴 CORES 상세 대조 생략 — anchor_plan 결손 때문(위 위반 참조)")
        elif _cs!=_exp:
            print("✗ 툴 CORES가 cores.json과 불일치 — 재생성 필요"); err+=1
    _pv=_const("PIVOTS","{}")
    if _pv!=_TE.build_pivots(cj):
        print("✗ 툴 PIVOTS가 cores.json과 불일치 — 재생성 필요"); err+=1
    _hcc=_re.search(r"function hotCenterCount\(\)\{(.*?)\n\}",_ts,_re.S)
    if _hcc and "overheated()" not in _hcc.group(1):
        print("✗ 툴 hotCenterCount가 overheated()를 쓰지 않음 — 계층 분리 미반영"); err+=1
    # ── 인바리언트 20 (23차 신설): P 배열의 mx(my_max)·mk(시장가) 전수 대조.
    # sync_tool.py는 22차까지 mx를 **동기화 목록에 넣지 않았다.** my_max가 한 번도
    # 바뀐 적이 없어 드러나지 않았고, 23차에 10명을 하향한 뒤에도 툴은 옛 값을
    # 보여줬다(Kessler mx:18 vs 실제 $14). 드래프트 당일 그 값으로 입찰하면
    # my_max를 초과한다 — 임베드 드리프트가 실제 손해로 이어지는 유일한 경로다.
    _bad=0; _n=0
    for _m in _re.finditer(r'\{n:"((?:[^"\\]|\\.)*)".*?mx:(\d+)', _ts):
        _q=pl.get(_m.group(1).replace('\\"','"'))
        if not _q: continue
        _n+=1
        if _q["my_max"]!=int(_m.group(2)):
            print("  ✗ [I20] 툴 mx 불일치: %s 툴 $%s vs players.json $%d"%(
                _m.group(1),_m.group(2),_q["my_max"])); err+=1; _bad+=1
    for _m in _re.finditer(r'\{n:"((?:[^"\\]|\\.)*)".*?mk:\[(\d+),(\d+)\]', _ts):
        _q=pl.get(_m.group(1).replace('\\"','"'))
        if not _q: continue
        if (_q["market_low"],_q["market_high"])!=(int(_m.group(2)),int(_m.group(3))):
            print("  ✗ [I20] 툴 mk 불일치: %s 툴 $%s-%s vs players.json $%d-%d"%(
                _m.group(1),_m.group(2),_m.group(3),_q["market_low"],_q["market_high"]))
            err+=1; _bad+=1
    print("툴 동기화: DECISION·ONELINER·OVERHEAT·OTIERS·CORES·PIVOTS 7종(P 포함) %s"%("일치" if not err else "확인 필요"))
    print("             P 배열 mx·mk 대조 %d행 · 불일치 %d건"%(_n,_bad))
    # ── I30: 툴 JS 구조 검사 ────────────────────────────────────────────────
    # 39차: sync_tool 이 injOut 을 끼워넣으며 행 끝 쉼표를 잘라먹어 const P 배열이
    # 깨졌고, 툴 전체가 SyntaxError 로 죽었다. 값 대조는 전부 통과했다 — 값이 맞는
    # 것과 파일이 실행되는 것은 다른 질문이다. 이 검사가 그 층을 본다.
    _pm = _re.search(r"const P=\[\n(.*?)\n\];", _ts, _re.S)
    _rows = [l for l in (_pm.group(1).split("\n") if _pm else []) if l.startswith('{n:"')]
    _term = [i for i, l in enumerate(_rows) if not l.endswith("},")]
    if _term != [len(_rows) - 1]:
        _who = ", ".join(_re.match(r'\{n:"([^"]*)"', _rows[i]).group(1)
                         for i in _term if i != len(_rows) - 1)
        print("  ✗ [I30] 툴 const P 행 종결 이상 — 쉼표 누락: %s (배열이 깨져 툴이 실행되지 않는다)" % _who)
        err += 1
    if len(_rows) != len(pl):
        print("  ✗ [I30] 툴 const P 행 %d개 ≠ players.json %d명" % (len(_rows), len(pl)))
        err += 1
    # node 가 있으면 실제 문법까지 본다(없으면 위 구조 검사만).
    import shutil as _sh, subprocess as _sp, tempfile as _tf, os as _os
    if _sh.which("node"):
        _js = "\n".join(_re.findall(r"<script[^>]*>(.*?)</script>", _ts, _re.S))
        _fd, _tmp = _tf.mkstemp(suffix=".js"); _os.close(_fd)
        io.open(_tmp, "w", encoding="utf-8").write(_js)
        _r = _sp.run(["node", "--check", _tmp], capture_output=True, text=True)
        _os.unlink(_tmp)
        if _r.returncode != 0:
            print("  ✗ [I30] 툴 JS 문법 오류 — %s" % (_r.stderr.strip().split("\n")[0] if _r.stderr else "?"))
            err += 1
        else:
            print("             [I30] 툴 JS 문법 OK · const P 행 %d개 종결 정상" % len(_rows))
    else:
        print("             [I30] const P 행 %d개 종결 정상 (node 없음 — 문법 검사 생략)" % len(_rows))


print("-"*66)
# ── 과열 임계값 2계층 검증 (2026-08-20 분리) ──
if not TIERS:
    print("✗ overheat_tiers 없음 — 2계층 분리 이후 필수"); err+=1
else:
    # 선수별 최대 계획가 — 철수 가격이 자기 계획가보다 낮으면 플랜이 자기 피벗을 트리거함
    MAXPLAN={}
    for _c in cj["cores"]:
        for _s in _c["slots"]:
            for _cd in _s.get("candidates",[]):
                MAXPLAN[_cd["name"]]=max(MAXPLAN.get(_cd["name"],0),_cd["plan_price"])
    for t in cj["overheat_thresholds"]:
        n=t["player"]; tier=t.get("tier")
        if tier not in TIERS:
            print("  ✗ %s: tier 미지정 또는 미정의 (%r)"%(n,tier)); err+=1; continue
        # 철수 가격 정합
        # 40차: 철수가는 **null 일 수 있다.** SF 병목 감시 4명은 과열선만 있고 무차별
        # 가격을 아직 재지 않았다. 숫자를 지어 넣으면 사용자가 보호받는다고 믿는다 —
        # 이미 겪은 실패다(Gobert 철수가 $18은 어떤 모델에서도 발동 확률 0).
        # null 을 허용하되 **사유 문자열을 요구**하고, 값이 있으면 기존 검사를 그대로 건다.
        if t["threshold"] is None:
            if not t.get("threshold_status"):
                print("  ✗ %s: 철수가가 null 인데 사유(threshold_status)가 없다"%n); err+=1
            if t.get("rule") is not None or t.get("walk_away") is not None \
               or t.get("walk_away_rule") is not None:
                print("  ✗ %s: 철수가 null 인데 rule/walk_away 가 남아 있다"%n); err+=1
        else:
            if t.get("walk_away")!=t["threshold"] or t.get("walk_away_rule")!=t["rule"]:
                print("  ✗ %s: walk_away가 threshold와 불일치"%n); err+=1
            if t["rule"]!="> $%d"%t["threshold"]:
                print("  ✗ %s: rule 형식 불일치"%n); err+=1
            if n in MAXPLAN and t["threshold"]<MAXPLAN[n]:
                print("  ✗ %s: 철수가 $%d < 최대 계획가 $%d (플랜이 자기 피벗을 트리거함)"%(
                    n,t["threshold"],MAXPLAN[n])); err+=1
        # 과열 신호 정합
        oh, exp = t.get("overheat_at"), t.get("expected_2026_27")
        if TIERS[tier].get("counts_toward_core7"):
            if not oh:
                print("  ✗ %s: 코어 7 반영 계층인데 overheat_at 없음"%n); err+=1
            elif exp is None or oh<=exp:
                print("  ✗ %s: overheat_at $%s가 기대치 $%s 이하 — 과열 신호가 될 수 없음"%(n,oh,exp)); err+=1
        if oh is not None and t.get("overheat_rule")!="> $%d"%oh:
            print("  ✗ %s: overheat_rule 형식 불일치"%n); err+=1
        if tier=="anchor" and oh is not None:
            print("  ✗ %s: anchor 계층은 overheat_at이 null이어야 함"%n); err+=1
        if not t.get("basis"):
            print("  ✗ %s: basis(근거) 미기재"%n); err+=1
    _cnt={k:len(v) for k,v in sorted(BY_TIER.items())}
    print("과열 임계값: %d건 · 계층 %s · 코어7 반영 계층 %s"%(
        len(cj["overheat_thresholds"]), _cnt,
        ",".join(k for k,v in TIERS.items() if v.get("counts_toward_core7")) or "없음"))

print("-"*66)
# ── 판단 순서(decision_table) 검증 ──
dt=cj.get("decision_table")
if not dt:
    print("✗ decision_table 없음"); err+=1
else:
    ids={c["id"] for c in cj["cores"]}
    seen=set()
    for d in dt:
        if d["core"] not in ids: print("  ✗ 판단표가 없는 코어 참조: %s"%d["core"]); err+=1
        if d["core"] in seen: print("  ✗ 판단표에 코어 중복: %s"%d["core"]); err+=1
        seen.add(d["core"])
        if not d.get("label") or not d.get("note"): print("  ✗ 판단표 행 설명 누락: %s"%d["core"]); err+=1
        c=d.get("cond",{})
        for r in c.get("rules",[]):
            if r["player"] not in pl: print("  ✗ 판단표 조건 선수 없음: %s"%r["player"]); err+=1
            elif r["max"]>pl[r["player"]]["my_max"]:
                print("  ✗ 판단표 임계 $%d > my_max $%d: %s"%(r["max"],pl[r["player"]]["my_max"],r["player"])); err+=1
        if c.get("type")=="hot_bigs":
            for n in c["players"]:
                if n not in TH: print("  ✗ 판단표 과열 선수가 임계값 소스에 없음: %s"%n); err+=1
            # 2계층 분리 (2026-08-20): 코어 7 조건은 선언한 계층에서만 센다
            tier=c.get("tier")
            if not tier:
                print("  ✗ hot_bigs 조건에 tier 미선언 — 2계층 분리 이후 필수"); err+=1
            elif tier not in TIERS:
                print("  ✗ hot_bigs tier가 overheat_tiers에 없음: %s"%tier); err+=1
            elif not TIERS[tier].get("counts_toward_core7"):
                print("  ✗ hot_bigs가 counts_toward_core7=false 계층을 참조: %s"%tier); err+=1
            elif set(c["players"])!=BY_TIER.get(tier,set()):
                miss=BY_TIER.get(tier,set())-set(c["players"]); extra=set(c["players"])-BY_TIER.get(tier,set())
                print("  ✗ hot_bigs 선수 목록이 %s 계층과 불일치 (누락 %s / 초과 %s)"%(
                    tier, ",".join(sorted(miss)) or "-", ",".join(sorted(extra)) or "-")); err+=1
            if c.get("signal")!="overheat_at":
                print("  ✗ hot_bigs signal이 overheat_at이 아님: %r"%c.get("signal")); err+=1
    # ── I36 (40차 신설 · 무명 검사에 이름을 붙이고 좁혔다) ──────────────────────
    #  막는 것: **존재하지만 아무도 고를 수 없는 코어**(죽은 플랜). 이 저장소가 여러 번
    #  당한 형태다. 그런데 40차에 c5 를 **의도적으로** 판단표에서 내리자 이 검사가 걸렸다.
    #  지우면 보호가 사라지고, 그대로 두면 정당한 강등이 막힌다 → **좁힌다.**
    #    판단표에 없는 코어는 `status` 가 셋을 다 갖췄을 때만 통과한다:
    #      active:false · reason(왜 내렸나) · revert(어떻게 되돌리나)
    #    하나라도 없으면 위반이다 — 「조용한 고아」는 여전히 걸린다.
    #  🔴 면제 건수를 요약 줄에 찍는다. 조용히 넘어가면 검사가 없는 것과 같다.
    _inactive=[]
    for _cid in sorted(ids-seen):
        _c=next((x for x in cj["cores"] if x["id"]==_cid), None)
        _st=(_c or {}).get("status") or {}
        _miss=[k for k in ("reason","revert") if not _st.get(k)]
        if _st.get("active") is False and not _miss:
            _inactive.append(_cid); continue
        if _st.get("active") is False:
            print("  ✗ [I36] %s: 판단표에 없고 status 에 %s 가 없다 — 비활성 선언은 "
                  "왜 내렸는지와 어떻게 되돌리는지를 함께 적어야 한다"
                  %(_cid,"·".join(_miss))); err+=1
        else:
            print("  ✗ [I36] 판단표에 없는데 비활성 선언도 없는 코어: %s "
                  "(존재하지만 아무도 고를 수 없다)"%_cid); err+=1
    if dt[0]["core"]!="c7": print("  ✗ 우선순위 0이 코어 7이 아님"); err+=1
    print("[I36] 판단표 도달 가능성: 코어 %d개 · 판단표 %d행 · 명시적 비활성 %d개%s"
          %(len(ids),len(dt),len(_inactive),
            (" ("+", ".join(_inactive)+")") if _inactive else ""))
    print("판단 순서: %d행 · 우선 0 = %s (센터 붕괴 시 최우선)"%(len(dt),dt[0]["core"]))
print("-"*66)
# ── I37 (40차 신설): 탈출로가 **도달 가능한가** ────────────────────────────
#
# `core_set_escape_paths_39` 의 규칙 ⑤′ 는 "3회 이상 1순위로 쓰이는 선수마다 그를 안 쓰는
# 코어가 최소 하나 있어야 한다"인데, **도달 가능성을 안 본다.** 40차에 c5 를 판단표에서
# 내리자 그 구멍이 드러났다 — Şengün·Gobert 의 탈출로 둘 중 하나가 c5 였다.
#
# 🔴 그리고 더 중요한 것: **지는 계획은 탈출로가 아니다.** c5 는 모든 스트레스 배율에서
#    최하위이고 가정을 셋 얹는다. 그걸 탈출로로 세는 것은 가짜 안전이고, 드래프트 당일
#    "탈출로가 있다"고 믿게 만드는 쪽이 더 위험하다. → 판단표에 있는 코어만 센다(I36 과 같은 논리).
#
# ⚠️ 등급은 **경고**다. "조건부 코어를 탈출로로 셀 것인가"는 사람 판단이고,
#   위반으로 두면 드래프트 직전에 진행이 막힌다. 숫자를 드러내는 것이 목적이다.
_ESC_MIN = 3      # ⑤′ 의 임계 — 이만큼 이상 1순위로 쓰이면 탈출로를 본다
_dt37 = {r["core"]: r for r in cj["decision_table"]}
_top37 = {c["id"]: [s["candidates"][0]["name"]
                    for s in c["slots"] if s.get("candidates")] for c in cj["cores"]}
_use37 = {}
for _cid, _ns in _top37.items():
    for _n in _ns:
        _use37.setdefault(_n, set()).add(_cid)
_rows37, _w37 = [], 0
for _n, _users in sorted(_use37.items(), key=lambda kv: -len(kv[1])):
    if len(_users) < _ESC_MIN:
        continue
    _esc = [k for k in _top37 if k not in _users]
    _live = [k for k in _esc if k in _dt37]
    _unc = [k for k in _live if (_dt37[k]["cond"].get("type") == "default_normal")]
    _rows37.append((_n, len(_users), _esc, _live, _unc))
    if not _live:
        print("  △ [I37] %s: %d/%d 코어의 1순위인데 **도달 가능한 탈출로가 없다** "
              "(탈출로 %s 는 전부 판단표 밖)"
              % (_n, len(_users), len(_top37), ",".join(sorted(_esc)) or "없음")); warn += 1; _w37 += 1
    elif not _unc and len(_live) <= 1:
        # 날카로운 경우 — 도달 가능한 탈출로가 하나뿐이고 그것마저 조건부다.
        print("  △ [I37] %s: %d/%d 코어의 1순위인데 도달 가능한 탈출로가 %s **하나뿐이고 "
              "그것도 조건부**다 — 그 조건이 안 열리면 갈 곳이 없다"
              % (_n, len(_users), len(_top37), ",".join(sorted(_live)))); warn += 1; _w37 += 1
    elif not _unc:
        # 여러 개지만 전부 조건부 — 동시에 다 닫힐 수는 있으나 위 경우보다 약하다.
        # 경고로 올리면 날카로운 셋이 묻힌다. 아래 요약표에 숫자가 그대로 보인다.
        print("             [I37] %s: 도달 탈출로 %s — 전부 조건부(무조건 경로 없음)"
              % (_n, ",".join(sorted(_live))))
print("[I37] 탈출로 도달 가능성: 다용 선수 %d명(1순위 %d회 이상) · 경고 %d건"
      % (len(_rows37), _ESC_MIN, _w37))
for _n, _u, _esc, _live, _unc in _rows37:
    print("      %-22s %d/%d 코어 · 탈출로 %d개 중 도달 %d개 · 그중 무조건 %d개%s"
          % (_n, _u, len(_top37), len(_esc), len(_live), len(_unc),
             (" (" + ",".join(sorted(_unc)) + ")") if _unc else ""))
print("-" * 66)

# ── I32 (40차 신설): players.json 의 **파생 필드**가 기저와 갈라졌는가 ──────
#
# 왜 필요한가
#   `surplus` 와 `obtainable` 은 `my_max`·`market_low`·`market_high` 의 함수인데
#   불변식이 없어서 `my_max` 를 손볼 때마다 조용히 낡았다. 40차에 실측했더니
#     surplus    16명 불일치 — 그중 **부호가 뒤집힌 것 7명**
#     obtainable  4명 불일치 — 그중 **3명이 「살 수 있다」고 거짓 표시**
#   툴 화면은 차익을 자체 계산해 무사했지만 `docs/03` 의 잉여 상위·잉여 플러스 다트·
#   획득 불가 세 표가 저장된 필드로 정렬·집계되어 **못 사는 선수를 살 수 있다고 적고
#   있었다.** 재계산은 `tool/recompute_derived.py`.
#
# 손수정 예외는 숨기지 않는다
#   Westbrook 은 가격상 획득 가능한데 **은퇴**라 손으로 내렸다. 공식에 if 를 넣는 대신
#   `obtainable_override`(이유 문자열)를 요구한다 — 이 저장소가 반복해 실패한
#   「규칙이 아니라 서술문」의 반대 방향이다. override 가 있으면 면제하고 **세어서 표시**한다.
_n32=_e32=_ov32=0
for _p in pl.values():
    _n32+=1
    _mid=round((_p["market_low"]+_p["market_high"])/2)
    _exp=_p["my_max"]-_mid
    if _p.get("surplus")!=_exp:
        print("✗ [I32] %s: surplus %s ≠ my_max $%d − 시장중간 $%d = %d"%(
            _p["name"],_p.get("surplus"),_p["my_max"],_mid,_exp)); err+=1; _e32+=1
    if _p.get("obtainable_override"):
        _ov32+=1; continue
    _eo=_p["my_max"]>=_p["market_low"]
    if _p.get("obtainable")!=_eo:
        print("✗ [I32] %s: obtainable %s ≠ (my_max $%d %s 시장하단 $%d)%s"%(
            _p["name"],_p.get("obtainable"),_p["my_max"],">=" if _eo else "<",_p["market_low"],
            "  🔴 못 사는 선수를 살 수 있다고 표시" if _p.get("obtainable") else ""))
        err+=1; _e32+=1
print("[I32] 파생 필드(surplus·obtainable): %d명 검사 · 위반 %d건 · 손수정 예외 %d건"
      %(_n32,_e32,_ov32))

# ── I33 (40차 신설): **같은 사실이 두 곳에 있으면 대조한다** ──────────────────
#
# (a) `pos_yahoo` ↔ `yahoo_eligibility_39.listed`
#     40차에 야후 실자격을 `pos_yahoo` 로 넣고 나서야 39차에 이미 같은 사실이
#     `yahoo_eligibility_39` 에 4명분 들어 있었다는 걸 알았다. **넣은 당일 2건이 갈라져
#     있었다** — Amen(PG,SG ↔ PG,SF,SG) · Okongwu(C ↔ C,PF). 그 2건이 하필 수리의
#     근거였다. 이중 보관을 만든 것보다 **대조가 없었다면 못 잡았을 것**이 요점이다.
#     ⚠️ 등급은 **경고**다 — 어느 쪽이 맞는지는 사람이 확인해야 하고,
#       현재 로스터는 두 판독 모두에서 유효하므로 진행을 막을 이유가 없다.
#     🔴 40차(2026-08-31): 사용자가 두 건을 재확인했다 — 실제는 Amen PG·SG · Okongwu C 로
#       **좁은 쪽(pos_yahoo)이 맞았다.** 39차 기록(`listed`)은 **덮어쓰지 않는다** — 그건
#       당시 무엇을 믿었는지의 기록이고, 갈라졌다는 사실 자체가 이 검사가 잡아낸 사례다.
#       지우면 「왜 이 검사가 있는지」가 사라진다. 대신 `superseded_40` 을 얹어 **면제**하되
#       **면제 건수를 요약 줄에 찍는다** — 조용히 넘어가면 검사가 없는 것과 같다.
#
# (b) `overheat_at` ↔ 계층의 `overheat_margin`
#     `low_cost_center` 가 「기대치 × 1.4 (최소 +$3)」라고 선언해 놓고 그 계층 6명 전원이
#     실제로는 × 1.25 였다. 데이터가 아니라 **설명문**이 낡은 경우이고, 검사가 없으면
#     어느 쪽이 진짜인지 아무도 모른다.
import re as _re33
_w33=0
_n33a=0
_fix33=0
for _p in pl.values():
    _y39=_p.get("yahoo_eligibility_39")
    if not _y39 or not _p.get("pos_yahoo"): continue
    _n33a+=1
    _a=set(x.strip() for x in (_y39.get("listed") or "").split(",") if x.strip())
    _b=set(_p["pos_yahoo"])
    if _a==_b: continue
    if _y39.get("superseded_40"):
        # 사람이 확인해서 어느 쪽이 맞는지 판정된 건. 경고는 내리되 **세어서 찍는다.**
        _fix33+=1
        print("             [I33] %s: 39차 기록이 틀린 것으로 확인됨 — 실제 %s (정정 표시 있음)"
              %(_p["name"],",".join(sorted(_b))))
        continue
    print("  △ [I33] %s: pos_yahoo %s ↔ 39차 기록 %s — 같은 사실이 두 곳에서 다르다 (출처: %s)"
          %(_p["name"],",".join(sorted(_b)),",".join(sorted(_a)),
            (_y39.get("source") or "?")[:40])); warn+=1; _w33+=1
_n33b=0
for _t in cj["overheat_thresholds"]:
    _tier=TIERS.get(_t.get("tier")) or {}
    _m=_tier.get("overheat_margin"); _oh=_t.get("overheat_at"); _e=_t.get("expected_2026_27")
    if not _m or _oh is None or _e is None: continue
    _mm=_re33.search(r"×\s*([\d.]+)",_m)
    if not _mm: continue
    _n33b+=1
    _exp=round(_e*float(_mm.group(1)))
    if _exp!=_oh:
        print("  △ [I33] %s: overheat_at $%d ↔ 계층 선언 '%s' 로는 $%d (기대치 $%d)"
              %(_t["player"],_oh,_m,_exp,_e)); warn+=1; _w33+=1
print("[I33] 이중 보관 대조: 자격 %d명 · 과열배율 %d건 · 불일치 %d건 · 정정 확인 %d건"
      %(_n33a,_n33b,_w33,_fix33))

# ── I25 (38차 신설): data/players.csv == 생성기 출력 ─────────────────────
# README는 players.csv를 "같은 데이터 표 형식"이라고 적어놨지만 **생성기가 없었고
# 손으로 유지되는 미러**였다. 그래서 갈라졌다 — 도입 시점에 174행 전부가 달랐다
# (cats는 13차 재산정 미반영 · 스탯은 20차 2시즌 혼합 미반영 · lift는 옛 기준선).
# 38차의 DeRozan 소속 정정도 두 파일을 각각 고쳐야 했다.
# 이 프로젝트의 「같은 값을 두 곳에 두면 반드시 갈라진다」 형태이므로 툴 임베드 상수
# (I12·I15·I20)와 같은 방식으로 **상시 대조**한다. 규칙을 두 번 구현하지 않기 위해
# 생성기의 build()를 그대로 불러 쓴다(27차 M5·M6 이중 구현 사고와 같은 이유).
try:
    import sys as _s25; _s25.path.insert(0, D+"/tool")
    import gen_players_csv as _GC
    _csv_new = _GC.build()
    _csv_old = io.open(D+"/data/players.csv", encoding="utf-8").read()
    if _csv_new != _csv_old:
        _o, _n = _csv_old.split("\n"), _csv_new.split("\n")
        _bad = [k for k in range(max(len(_o), len(_n)))
                if (_o[k] if k < len(_o) else None) != (_n[k] if k < len(_n) else None)]
        print("✗ [I25] players.csv가 생성기 출력과 불일치 — 다른 줄 %d개 · 재생성 필요"
              % len(_bad)); err+=1
        for _k in _bad[:3]:
            _nm = (_n[_k] if _k < len(_n) else _o[_k]).split(",")[0]
            print("             %d행 %s" % (_k+1, _nm or "(헤더)"))
        print("             → python3 tool/gen_players_csv.py")
    else:
        print("[I25] players.csv = 생성기 출력 일치 (%d행 · %d열)"
              % (_csv_new.count("\n")-1, len(_GC.COLS)))
except Exception as _ex25:
    print("✗ [I25] players.csv 대조 실패: %r" % (_ex25,)); err+=1

print("획득 제외 대상(부상·은퇴): %s"%(", ".join(sorted(INJ)) or "없음"))
print("총 위반: %d건%s"%(err, " · 치환필요 %d건(치명 아님)"%warn if warn else ""))
sys.exit(1 if err else 0)
