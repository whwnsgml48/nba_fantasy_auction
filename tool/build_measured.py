#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BBRef 전체 스탯을 174명 DB에 매칭해 data/stats_2025_26/measured_full.json 생성.

2025-26 우선 · 없으면(결장) 2024-25 폴백 · 둘 다 없으면 미측정으로 표기.
"""
import json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM   # DD 정규근사 추정 (순수 함수 — 데이터 의존 없음)

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bb=json.load(open(f"{BASE}/data/stats_2025_26/bbref/per_game.json",encoding="utf-8"))
pl=json.load(open(f"{BASE}/data/players.json",encoding="utf-8"))

def nm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    s=s.replace(".","").replace("'","").replace("-"," ").replace("`","")
    s=re.sub(r"\b(jr|sr|iii|ii|iv|v)\b","",s)
    return " ".join(s.split())

IDX={lab:{nm(k):v for k,v in bb[lab].items()} for lab in ("2025-26","2024-25")}
ALIAS={  # DB 표기 → BBRef 표기 (수동 확인분)
 "nicolas claxton":"nic claxton",
 "kelly oubre":"kelly oubre", "alperen sengun":"alperen sengun",
 "nikola vucevic":"nikola vucevic", "kristaps porzingis":"kristaps porzingis",
 "moussa diabate":"moussa diabate", "neemias queta":"neemias queta",
 "dennis schroder":"dennis schroder", "cj mccollum":"cj mccollum",
 "tim hardaway":"tim hardaway", "jaren jackson":"jaren jackson",
 "gary trent":"gary trent", "michael porter":"michael porter",
 "jabari smith":"jabari smith", "trey murphy":"trey murphy",
 "day ron sharpe":"dayron sharpe", "dayron sharpe":"dayron sharpe",
}
RECENCY=1.5   # 2025-26에 주는 가중 배수 (2026-27 예측력이 더 높다)
CATS_NUM=["PTS","REB","OREB","DREB","AST","STL","BLK","TOV","FG%","FGA","3PM","3PA","3P%","FT%","FTA","MPG"]

def blend(name):
    """두 시즌을 GP 가중으로 혼합. 최근 시즌에 RECENCY 배수를 준다.

    ⚠️ 22차: 처음엔 '2025-26에 아예 없을 때만 2024-25 사용'이었다. 그래서
    Walker Kessler(2025-26 **5경기**)가 5경기 표본으로 평가돼 OREB1·BLK1이 됐다
    — 2024-25는 58경기에 BLK 2.4(리그 3위급) · OREB 4.6(리그 1위급)이다.
    그 다음엔 'GP<40이면 2024-25로 전환'으로 고쳤는데, 39경기와 40경기가 전혀 다른
    취급을 받는 불연속이 생긴다. 최종안은 **혼합**이다:

      w25 = GP25 × 1.5 · w24 = GP24
      혼합값 = (s25·w25 + s24·w24) / (w25 + w24)

    Kessler: w25=7.5 · w24=58 → 2024-25가 89% 반영.
    건강한 선수(75/70경기): w25=112.5 · w24=70 → 2025-26이 62% 반영.
    출장 가용성(GP)도 같은 가중으로 혼합해 '작년에 5경기'가 리스크로 남는다.
    """
    k=nm(name); k=ALIAS.get(k,k)
    got={}
    for lab in ("2025-26","2024-25"):
        if k in IDX[lab]: got[lab]=IDX[lab][k]
    if not got:
        # ⚠️ 23차: 원래 폴백은 '성 + 이름 첫글자'였다. 그래서 **Darryn Peterson**
        # (2026 루키, NBA 무경력)이 **Drew Peterson**(CHO/BOS PF, 8.3MPG)에 붙어
        # 1.8P·FG 33.8% 프로필을 갖게 됐다. 성이 같고 첫글자가 같으면 유일해도
        # 동일인이 아니다 — 특히 신인은 BBRef에 아예 없는 것이 정상이다.
        # 이제 폴백은 **이름 전체가 접두/피접두 관계**일 때만 허용한다
        # (Cam↔Cameron, Nic↔Nicolas 같은 축약형만 통과).
        parts=k.split()
        if len(parts)>=2:
            last, first = parts[-1], parts[0]
            for lab in ("2025-26","2024-25"):
                c2=[v for kk,v in IDX[lab].items()
                    if kk.split()[-1]==last
                    and (kk.split()[0].startswith(first) or first.startswith(kk.split()[0]))]
                if len(c2)==1: got[lab]=c2[0]
    if not got: return None
    r25, r24 = got.get("2025-26"), got.get("2024-25")
    w25=(r25.get("GP") or 0)*RECENCY if r25 else 0.0
    w24=(r24.get("GP") or 0) if r24 else 0.0
    if w25+w24==0: return None
    out={}
    for c in CATS_NUM:
        v25=r25.get(c) if r25 else None
        v24=r24.get(c) if r24 else None
        a=w25 if v25 is not None else 0.0
        b=w24 if v24 is not None else 0.0
        if a+b==0: out[c]=None; continue
        out[c]=round(((v25 or 0)*a+(v24 or 0)*b)/(a+b), 4)
    out["GP"]=round(((r25.get("GP") if r25 else 0)*w25+(r24.get("GP") if r24 else 0)*w24)/(w25+w24),1)
    src=(r25 or r24)
    out["team"]=src.get("team"); out["pos"]=src.get("pos")
    out["GS"]=src.get("GS")
    out["bbref_name"]=src.get("name")
    out["seasons"]={"2025-26":{"GP":(r25.get("GP") if r25 else None),"weight":round(w25,1)},
                    "2024-25":{"GP":(r24.get("GP") if r24 else None),"weight":round(w24,1)}}
    out["blend_share_2025_26"]=round(w25/(w25+w24),3)
    return out

CATS=["PTS","REB","OREB","AST","STL","BLK","TOV","FG%","3PM","3P%","FT%"]

def line(name):
    """이름 하나를 measured_full 한 행으로. 없으면 None.

    38차에 함수로 분리했다 — `tool/real_opponents.py`가 DB 밖 선수(작년 옥션 낙찰자
    중 174명 DB에 없는 인원)를 **같은 규칙**으로 보충해야 하는데, 규칙을 두 번 구현하면
    갈라진다(27차 M5·M6 이중 구현 사고). 파일 쓰기는 아래 `__main__`에만 있다.
    """
    r = blend(name)
    if r is None: return None
    at = (r["AST"]/r["TOV"]) if (r.get("AST") and r.get("TOV")) else None
    lift = ((20.0+r["AST"])/(10.0+r["TOV"])-2.0) if (r.get("AST") is not None and r.get("TOV") is not None) else None
    return {
      "season":"blend","bbref_name":r["bbref_name"],"team":r["team"],"pos":r["pos"],
      "GP":r["GP"],"GS":r["GS"],"MPG":r["MPG"],
      **{c:r.get(c) for c in ["PTS","REB","OREB","DREB","AST","STL","BLK","TOV","FG%","3PM","3P%","FT%"]},
      "FGA":r.get("FGA"),"FTA":r.get("FTA"),"3PA":r.get("3PA"),
      "A/T":round(at,2) if at else None,
      # DD는 BBRef 미집계라 per-game PTS·REB·AST의 정규근사로 추정한다.
      # 다른 캣과 같은 척도(경기당)로 넣어야 baselines()·marginal()이 그대로 동작한다.
      # 실측 25명 대상 검증: 절대오차 중앙값 2.13 DD · 평균오차 -0.65 (24차).
      "DD":round(CM.dd_game_prob(r.get("PTS"),r.get("REB"),r.get("AST")),4),
      "DD_est_season":round(CM.dd_estimate(r.get("PTS"),r.get("REB"),r.get("AST"),r.get("GP")) or 0,1),
      "DD_basis":"정규근사 추정 (혼합 per-game 기준)",
      "at_marginal_lift":round(lift,3) if lift is not None else None,
      "seasons":r["seasons"],"blend_share_2025_26":r["blend_share_2025_26"],
    }

if __name__ == "__main__":
    # 174명 DB 전체를 measured_full.json으로 기록한다. import 경로에서는 실행되지 않는다.
    out={}; miss=[]
    for p in pl:
        r2 = line(p["name"])
        if r2 is None: miss.append(p["name"]); continue
        out[p["name"]] = r2
    json.dump({"meta":{
       "source":"basketball-reference per-game (tool/fetch_bbref.py)",
       "method":"2025-26과 2024-25를 GP 가중 혼합 (2025-26에 ×1.5 최근 가중). "
                  "GP도 같은 가중으로 혼합해 '작년 5경기' 같은 출장 리스크가 남는다.",
       "recency_multiplier":RECENCY,
       "matched":len(out),"db_players":len(pl),
       "blend_note":"players[].seasons에 시즌별 GP와 가중치, blend_share_2025_26에 최근 시즌 반영 비율.","unmatched":miss,
       "cats_covered":CATS+["A/T","DD"],
       "cats_not_covered":[],
       "note":("DD는 BBRef 미집계라 per-game PTS·REB·AST 정규근사로 **추정**한다"
               "(cat_model.dd_game_prob · σ=c√μ · c=PTS 1.50/REB 1.10/AST 1.05 · 연속성 보정). "
               "DD 필드는 경기당 확률, DD_est_season은 ×GP. "
               "실측 25명(리더보드) 검증: 절대오차 중앙값 2.13 DD · 평균오차 -0.65 · 23/25명 오차 6 이내. "
               "실측값으로 덮어쓰지 않는다 — 실측은 2025-26 단일 시즌이고 다른 12캣은 2시즌 혼합이라 "
               "기준이 섞인다. 실측은 dd_actual_2025_26에 기록만 남긴다.")},
       "players":out},
      open(f"{BASE}/data/stats_2025_26/measured_full.json","w",encoding="utf-8"),
      ensure_ascii=False,indent=1)
    print(f"매칭 {len(out)}/{len(pl)}명")
    low=[(n,v["blend_share_2025_26"],v["seasons"]) for n,v in out.items() if v["blend_share_2025_26"]<0.5]
    print(f"2024-25가 절반 이상 반영된 선수 {len(low)}명:")
    for n,sh,se in sorted(low,key=lambda x:x[1])[:25]:
        print(f"   {n:<24}2025-26 {sh*100:>5.1f}%  (GP {se['2025-26']['GP']} vs {se['2024-25']['GP']})")
    print(f"미매칭 {len(miss)}명: "+(", ".join(miss) if miss else "없음"))
