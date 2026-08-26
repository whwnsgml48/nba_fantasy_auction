#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기본 코어 + 모든 피벗 플랜을 한 번에 검증한다.
위반이 1건이라도 있으면 exit 1. 사용: python3 validate.py"""
import io,json,sys,os
D=os.path.dirname(os.path.abspath(__file__))
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
            if v<p["market_low"]: print("  ✗ 대체후보 %s $%d < market_low $%d"%(n,v,p["market_low"])); err+=1
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
    if not pv.get("targeted_cats") or not pv.get("punted_cats"):
        print("  ✗ 피벗에 노리는 캣/포기 캣 미명시"); err+=1
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
    _m1=_re.search(r'const DECISION_ONELINER="(.*?)";\n',_ts,_re.S)
    _one=_m1.group(1) if _m1 else None
    if _dec!=cj["decision_table"]:
        print("✗ 툴 DECISION이 cores.json.decision_table과 불일치 — 재생성 필요"); err+=1
    if _one!=cj["decision_oneliner"]:
        print("✗ 툴 DECISION_ONELINER 불일치 — 재생성 필요"); err+=1
    _ohx=[{"n":t["player"],"tier":t["tier"],"walk":t["threshold"],
           "exp":t["expected_2026_27"],"oh":t["overheat_at"]} for t in cj["overheat_thresholds"]]
    if _oh!=_ohx:
        print("✗ 툴 OVERHEAT이 cores.json.overheat_thresholds와 불일치 — 재생성 필요"); err+=1
    _otx={k:{"label":v["label"],"c7":v["counts_toward_core7"],"why":v["why"]}
          for k,v in (cj.get("overheat_tiers") or {}).items() if not k.startswith("_")}
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
        _exp=[{"id":"c0","n":"— 코어 미선택 —"}]
        for _co in cj["cores"]:
            _plan=[]
            for _sl in _co["slots"]:
                _row=[_sl["slot"],_sl.get("role") or "",
                      [[x["name"],x["plan_price"]] for x in _sl["candidates"]]]
                if _sl.get("is_anchor"):
                    _ap=_sl["anchor_plan"]
                    _row.append(True)
                    _row.append({"ceil":_ap["bid_ceiling"],"nom":_ap["nominal_margin"],
                                 "eff":_ap["effective_headroom"],"con":_ap["constraint"],
                                 "act":_ap["on_fail"]["action"],"tgt":_ap["on_fail"]["target"],
                                 "dual":_ap["dual_world_ok"]})
                _plan.append(_row)
            _e={"id":_co["id"],"n":_co["name"],"prem":_co.get("premise") or "",
                "target":_co.get("targeted_cats") or [],"punt":_co.get("punted_cats") or [],
                "cap":_co.get("single_player_cap"),"bigCap":_co["big_budget_cap"],
                "slack":_co["budget_slack"],"plan":_plan}
            if _co.get("conditional_on_discount"): _e["condDiscount"]=_co["conditional_on_discount"]
            _exp.append(_e)
        if _cs!=_exp:
            print("✗ 툴 CORES가 cores.json과 불일치 — 재생성 필요"); err+=1
    _pv=_const("PIVOTS","{}")
    if _pv!={x["id"]:x["pivot_plan"] for x in cj["cores"]}:
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
    if ids-seen: print("  ✗ 판단표에 누락된 코어: %s"%", ".join(sorted(ids-seen))); err+=1
    if dt[0]["core"]!="c7": print("  ✗ 우선순위 0이 코어 7이 아님"); err+=1
    print("판단 순서: %d행 · 우선 0 = %s (센터 붕괴 시 최우선)"%(len(dt),dt[0]["core"]))
print("장기 부상 제외 대상: %s"%(", ".join(sorted(INJ)) or "없음"))
print("총 위반: %d건%s"%(err, " · 치환필요 %d건(치명 아님)"%warn if warn else ""))
sys.exit(1 if err else 0)
