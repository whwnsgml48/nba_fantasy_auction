#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SF 병목 감시목록 · `lineup_loss` 필드 · 판단표 강도 주석 재작성 (40차).

① 계층 규칙 문구 정정
   `low_cost_center.overheat_margin` 이 「기대치 × 1.4 (최소 +$3)」라고 적혀 있는데
   **그 계층 6명 전원이 실제로는 × 1.25** 다(Clingan 12→15 · Gobert 8→10 · Duren 27→34 ·
   M.Robinson 5→6 · Ayton 5→6 · M.Williams 7→9). 데이터가 아니라 **설명문이 낡았다.**
   name_big(× 1.25)와 같은 값이므로 계층 간 차이도 실제로는 없다.

② SF 병목 감시 추가 — 진짜 병목은 센터가 아니다
   확인된 19명에서 **DB `pos` 별 SF 보유율**: G/F 4/5 · F 0/1 · F/C 0/5 · C 0/6 · G 0/2.
   야후 SF 자격은 사실상 `G/F` 표기에서만 나온다. 그런데 기존 감시 13명은
   **센터 9 + 앵커 4, SF 0명**이었다.

   🔴 **철수가는 비워 둔다.** 무차별 가격은 측정해야 나오는 값이고(그 선수를 포기하고
   대안으로 갈 때 잃는 것 = 남는 돈으로 사는 것, 이 지점), 이 저장소는 근거 없는
   임계값이 화면에서 어떻게 작동하는지 이미 겪었다 — 「철수가 $18은 어떤 모델에서도
   발동 확률 0」(Gobert). 숫자를 지어내면 사용자는 보호받는다고 **믿는다**.
   과열선만 넣고 철수가는 `null` + 상태 문자열로 둔다.

③ `lineup_loss` — 자격 제약으로 버리는 선수-경기 비율을 코어마다 싣는다
   `matchup_sim` 은 자격을 모른다. 그 사실을 각주로 숨기지 않고 행마다 보이게 한다.
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pos_elig as PE
import lineup_feasibility as LF

CP = BASE + "/data/cores.json"

TIERS_NEW = {
    "sf_scarcity": {
        "label": "SF 조달 경로",
        "counts_toward_core7": False,
        "evidence": ("확인 19명의 DB pos 별 SF 보유율 — G/F 4/5 · F 0/1 · F/C 0/5 · C 0/6 · G 0/2. "
                     "야후 SF 자격은 사실상 G/F 표기에서만 나온다."),
        "why": ("SF 는 로스터에서 대체가 가장 어려운 칸이다. 잃으면 그 칸이 매일 비고, "
                "센터처럼 '다른 저가로 갈아타기'가 되지 않는다 — 갈아탈 사람이 리그에 적다. "
                "코어 7 전환과는 무관하다(센터 시장 온도가 아니다)."),
        "overheat_margin": "시장 중간값 × 1.25",
    },
    "shared_first": {
        "label": "다수 코어 공유 1순위",
        "counts_toward_core7": False,
        "evidence": "한 선수가 여러 코어의 1순위인 경우. 상실이 코어 하나가 아니라 계획 전체를 흔든다.",
        "why": ("여러 코어가 같은 사람 위에 서 있으면 '코어를 바꿔서 피한다'가 통하지 않는다. "
                "가격이 아니라 **집중도** 때문에 감시한다."),
        "overheat_margin": "시장 중간값 × 1.25",
    },
}

# 철수가 미측정 사유 — 화면에도 이 문장이 그대로 간다.
UNMEASURED = "철수가 미측정 — 무차별 가격(포기하고 대안으로 갈 때의 손익 균형점)을 재야 나온다. 지어내지 않는다."

WATCH = [
    ("Kon Knueppel", "sf_scarcity",
     "c1·c4·c5·c7 의 SF 1순위 · c2·c3·c6 의 SF 대체 — 7코어 전부가 이 사람을 경로에 두고 있다"),
    ("Desmond Bane", "sf_scarcity",
     "c2·c6 의 SF 1순위 · 나머지 5코어의 SF 대체 — Knueppel 과 함께 SF 조달의 두 기둥"),
    ("Josh Hart", "sf_scarcity",
     "c3·c7 의 SF 1순위 · c2·c4·c5·c6 의 SF 대체. 시장 $1-7 로 싸지만 내 최대가가 $5라 "
     "과열선과 최대가가 겹친다 — $5 를 넘으면 대안이 아니라 그냥 못 산다"),
    ("Dyson Daniels", "shared_first",
     "6개 코어의 1순위이고 어느 코어에서도 대체후보로 잡혀 있지 않다. 상실 시 −4.5~5.1%p"),
]

SNOTE = {
    "c6": "예비비 $9 (목표 $12 미달) · 기본값 · C자격 3 (센터 의존 감소)",
    "c1": "⚠ Hali GP 73 가정 위에서만 — GP 54면 81.9%로 하위권",
    "c7": "Hali 무관 · KAT 의존 · c6와 5명 공유",
    "c2": ("자격 반영 후 상위 5개와 **동급**(87.4 · 이 시뮬의 오차 ±0.8). 이전의 「전 코어 1위」는 "
           "포지션 자격을 모르는 모델이 만든 숫자였다 — C 전용 5명을 매일 다 쓸 수 있다고 계산했다. "
           "⚠ Jokić GP 67 가정 위"),
    "c3": ("⚠ Lillard 투영 GP(직전 시즌 결장) · SF 조달이 Hart 한 사람 · "
           "대체가 비동등(3PM·FT%·AST → OREB·FG%)"),
    "c4": ("⚠ Trae GP 가정 위 (실측 비중 22.8% · 워싱턴 역할 데이터 없음) · "
           "대체가 비동등(FT% w3→w1)"),
    "c5": ("⚠ 가정 **둘**을 동시에 얹는다 — Hali GP 73 + Sabonis 건강. GP 54면 78.7%로 최하위이고, "
           "Sabonis 는 프리시즌 실경기 확인이 필수다 · 격리 베팅"),
}


def main():
    cj = json.load(io.open(CP, encoding="utf-8"))
    PLl = json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))
    PL = {p["name"]: p for p in PLl}

    # ① 계층 규칙 문구
    lcc = cj["overheat_tiers"]["low_cost_center"]
    if lcc.get("overheat_margin") != "기대치 × 1.25":
        print("  계층 문구 정정: low_cost_center overheat_margin %r → '기대치 × 1.25'"
              % lcc.get("overheat_margin"))
        lcc["overheat_margin"] = "기대치 × 1.25"
        lcc["overheat_margin_note"] = ("한때 「× 1.4 (최소 +$3)」로 적혀 있었으나 이 계층 6명 전원이 "
                                       "실제로는 × 1.25 로 계산돼 있었다. 데이터가 아니라 설명문이 낡았던 것이고, "
                                       "name_big 과 같은 배율이므로 계층 간 배율 차이는 실제로 없다.")
    cj["overheat_tiers"].update({k: v for k, v in TIERS_NEW.items()
                                 if k not in cj["overheat_tiers"]})

    # ② 감시목록
    have = {t["player"] for t in cj["overheat_thresholds"]}
    for name, tier, basis in WATCH:
        if name in have:
            print("  이미 감시 중: %s" % name); continue
        p = PL[name]
        mid = round((p["market_low"] + p["market_high"]) / 2)
        cj["overheat_thresholds"].append({
            "player": name, "rule": None, "threshold": None, "tier": tier,
            "expected_2026_27": mid,
            "overheat_at": round(mid * 1.25), "overheat_rule": "> $%d" % round(mid * 1.25),
            "basis": basis, "walk_away": None, "walk_away_rule": None,
            "threshold_status": UNMEASURED,
            "binding": False,
            "binding_note": ("과열선만 있고 철수가가 없다. 이 줄은 '이 가격을 넘으면 계획을 바꿔라'가 "
                             "아니라 **'이 사람이 비싸지는지 보라'** 는 뜻이다."),
        })
        print("  감시 추가 %-16s %-13s 과열선 $%d (시장 $%d-%d)"
              % (name, tier, round(mid * 1.25), p["market_low"], p["market_high"]))

    # ③ lineup_loss
    for co in cj["cores"]:
        out = {}
        for tag, names in (("base", [s["candidates"][0]["name"] for s in co["slots"]]),
                           ("pivot", [r["name"] for r in co["pivot_plan"]["final_roster"]])):
            ps = [PL[n] for n in names if n in PL]
            drop, rates, perweek = LF.measure(ps)
            out[tag] = {"drop_share": round(drop, 4), "per_week": round(perweek, 2),
                        "c_only": sum(1 for p in ps if PE.elig(p) == {"C"}),
                        "sf_capable": sum(1 for p in ps if "SF" in PE.elig(p)),
                        "worst": sorted(rates.items(), key=lambda kv: kv[1])[0][0]}
        out["measured_by"] = "tool/lineup_feasibility.py (선발 7칸 일일 이분매칭 · 20000주)"
        out["means"] = ("포지션 자격 때문에 그날 경기가 있는데도 넣을 칸이 없어 **버려지는 "
                        "선수-경기 비율**. 주간 승률 시뮬은 이 제약을 모르므로 그 숫자에는 "
                        "반영돼 있지 않다.")
        out["not_illegality"] = ("로스터가 불법이라는 뜻이 아니다. 야후는 포지션 커버리지를 "
                                 "강제하지 않는다 — 그 칸이 매일 빌 뿐이다.")
        co["lineup_loss"] = out
        print("  lineup_loss %s base %.2f%% · pivot %.2f%%"
              % (co["id"], 100 * out["base"]["drop_share"], 100 * out["pivot"]["drop_share"]))

    # ④ 판단표 강도 주석
    for cid, note in SNOTE.items():
        if cj["decision_strength_notes"].get(cid) != note:
            print("  snote %s 갱신" % cid)
        cj["decision_strength_notes"][cid] = note

    json.dump(cj, io.open(CP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("data/cores.json 기록")


if __name__ == "__main__":
    main()
