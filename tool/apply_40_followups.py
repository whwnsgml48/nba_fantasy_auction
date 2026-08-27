#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""40차 후속 4건 — 실행 불가 대체안 · Hart 최대가 · DeRozan 감시 · 목적함수 진단 갱신.

① 실행 불가 대체안 4건
   대체안은 1순위를 놓쳤을 때 **실제로 가는 자리**인데, 전환하면 예산을 넘는 것이 4건 있었다.
   화면에는 대안이 있다고 뜨고 실제로는 못 산다 — 「있다고 거짓말하는 대안」이다.
     c3 C  Clingan $12 → Duren $27    총 $206
     c5 C  Clingan $12 → Duren $27    총 $201
     c6 UTIL Edgecombe $5 → Knueppel $22 / Bane $22   총 $208
   전 코어·전 슬롯 115건을 훑어 이 4건이 전부임을 확인했다. **I34** 가 상시 대조한다.

② Josh Hart `my_max` $5 → $9
   🔴 **무차별 가격이 아니다. 예산 제약이 허용하는 상한이다.** 이 값을 "Hart 의 가치"로
   읽으면 안 된다.
   왜 올리는가: 현재 값이 내부적으로 깨져 있다 — **시장 상단 $7 > my_max $5** 라
   정상 시장에서도 못 산다. $5 는 그가 c7 벤치 잡부였을 때 매긴 값이고, 수리 후
   **c3 의 SF 1순위**가 됐다.
   왜 $9 인가: 로스터가 안 바뀌면 승률도 안 바뀌므로 값을 올리는 비용은 **예비비뿐**이다.
   c3 예비비 $9 가 I22 하한 $4 에 닿는 지점이 $9 이고(c7 은 $16 여유라 c3 가 구속),
   그 위는 다른 칸을 잘라야 해서 **재설계이고 재지 않았다**.
   측정 근거(보정·4000시행·실제 12팀): c3 에서 Hart 를 잃으면
     → DeRozan $8  87.0% (−0.7%p · 오차 안)   → Wiggins $2  84.0% (−3.7%p)
   그런데 DeRozan 은 c2 PF 1순위 · c6 SF 1순위라 **방에 넘어가면 −3.7%p 쪽이 실현된다.**

③ DeRozan 감시 추가 — ②의 측정이 **삼중 예약**을 드러냈다
   c2 PF 1순위 · c6 SF 1순위 · c3 의 Hart 대체 SF. 세 코어가 한 사람을 경로에 두고 있다.

④ 목적함수 진단 40차 갱신
   38차 진단(「maximin 은 단일 상대에 지배된다」)이 라인업 보정 후에도 그대로다.
   그리고 1차 지표가 상위 5개를 못 가르게 되면서 **2차를 타이브레이커로 쓰고 싶은 유혹**이
   새로 생겼다. 그 유혹에 대한 답을 같은 자리에 적어 둔다.
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CP, PP = BASE + "/data/cores.json", BASE + "/data/players.json"

FIX_ALTS = {
    ("c3", "Donovan Clingan"): ["Ivica Zubac", "Rudy Gobert"],
    ("c5", "Donovan Clingan"): ["Rudy Gobert", "Nikola Vučević"],
    ("c6", "VJ Edgecombe"):    ["Onyeka Okongwu", "Josh Hart"],
}
HART_MAX = 9


def main():
    cj = json.load(io.open(CP, encoding="utf-8"))
    pll = json.load(io.open(PP, encoding="utf-8"))

    # ① 대체안 교체
    for (cid, first), alts in FIX_ALTS.items():
        co = next(c for c in cj["cores"] if c["id"] == cid)
        s = next(x for x in co["slots"] if x["candidates"][0]["name"] == first)
        old = [c["name"] for c in s["candidates"][1:]]
        s["candidates"] = [s["candidates"][0]] + [{"name": a} for a in alts]
        print("  대체 %s %-5s %-22s %s → %s" % (cid, s["slot"], first, ", ".join(old), ", ".join(alts)))

    # ② Hart my_max
    for p in pll:
        if p["name"] == "Josh Hart" and p["my_max"] != HART_MAX:
            print("  Hart my_max $%d → $%d (시장 $%d-%d)" % (p["my_max"], HART_MAX,
                                                            p["market_low"], p["market_high"]))
            p["my_max"] = HART_MAX
            p["my_max_basis_40"] = (
                "🔴 **무차별 가격이 아니라 예산 제약이 허용하는 상한이다.** 수리로 c3 의 SF 1순위가 되면서 "
                "이전 값 $5(c7 벤치 잡부 시절)가 낡았고, 무엇보다 **시장 상단 $7 > $5** 라 정상 시장에서도 "
                "살 수 없는 값이었다. $9 는 c3 예비비가 I22 하한 $4 에 닿는 지점이다(c7 은 $16 여유라 c3 가 "
                "구속 조건). 그 위는 다른 칸을 잘라야 해서 재설계이고 재지 않았다. "
                "잃었을 때 실측: c3 → DeRozan $8 이면 −0.7%p(오차 안)이나 DeRozan 은 c2·c6 의 1순위라 "
                "방에 넘어가면 Wiggins $2 로 −3.7%p 가 실현된다.")
            break
    json.dump(pll, io.open(PP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ③ DeRozan 감시
    PL = {p["name"]: p for p in pll}
    if not any(t["player"] == "DeMar DeRozan" for t in cj["overheat_thresholds"]):
        p = PL["DeMar DeRozan"]
        mid = round((p["market_low"] + p["market_high"]) / 2)
        cj["overheat_thresholds"].append({
            "player": "DeMar DeRozan", "rule": None, "threshold": None, "tier": "sf_scarcity",
            "expected_2026_27": mid, "overheat_at": round(mid * 1.25),
            "overheat_rule": "> $%d" % round(mid * 1.25),
            "basis": ("🔴 **삼중 예약** — c2 의 PF 1순위 · c6 의 SF 1순위 · c3 의 Hart 대체 SF. "
                      "c3 에서 Hart 를 잃었을 때 −0.7%p(오차 안)로 버티는 것이 전적으로 이 사람 덕이고, "
                      "그가 방에 넘어가면 같은 상황이 −3.7%p 가 된다."),
            "walk_away": None, "walk_away_rule": None,
            "threshold_status": ("철수가 미측정 — 무차별 가격(포기하고 대안으로 갈 때의 손익 균형점)을 "
                                 "재야 나온다. 지어내지 않는다."),
            "binding": False,
            "binding_note": "과열선만 있고 철수가가 없다. '이 가격을 넘으면 바꿔라'가 아니라 '비싸지는지 보라'는 뜻이다.",
        })
        print("  감시 추가 DeMar DeRozan  sf_scarcity  과열선 $%d (시장 $%d-%d)"
              % (round(mid * 1.25), p["market_low"], p["market_high"]))
    json.dump(cj, io.open(CP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ④ 목적함수 진단 (matchup_sim.json 은 시뮬 산출물이므로 거기 적는다)
    sp = BASE + "/data/matchup_sim.json"
    sim = json.load(io.open(sp, encoding="utf-8"))
    sim["objective"]["diagnosis_40"] = [
        "라인업 보정을 편입한 뒤에도 38차 진단이 **그대로**다 — 7코어 중 5개가 min_win_rate_vs = value_max.",
        "갈라진 2개(c2·c6)도 도움이 안 된다. 그쪽 최저 상대는 benchmark 인데 그것은 사용자가 "
        "시장 상단 전액으로 지정한 고정 팀이지 실제 12팀의 한 명이 아니다. "
        "**7개 전부 현실 상대가 아닌 팀에서 최저가 나온다.**",
        "maximin 순위는 결국 'value_max 에게 덜 지는 순서'이고 value_max 는 우리 z모델의 자기 최적해다. "
        "그러니 2차 순위는 '우리 모델과 얼마나 닮았는가'를 재고 있다 — 1차(실제 사람들이 짠 로스터)와 "
        "반대로 나오는 것이 오히려 자연스럽고, **둘이 반대라는 사실 자체가 2차를 못 쓴다는 증거**다.",
        "🔴 **새로 생긴 유혹** — 보정 후 1차 지표에서 상위 5개가 1.3%p 안에 들어왔다(SE ±0.8%p). "
        "1차가 다섯을 못 가르므로 2차를 타이브레이커로 쓰고 싶어진다. **쓸 수 없다.** "
        "다음 시즌에 정확히 이 유혹에 빠지는 사람이 나온다.",
        "정직한 결론: **어떤 측정도 상위 5개를 가르지 못한다.** 선택은 시뮬 밖 근거로 간다 — "
        "얹은 가정의 수, 예비비, 조달 경로의 취약성, 그리고 방이 실제로 무엇을 주는가. "
        "그게 판단표가 원래 하던 일이다.",
    ]
    json.dump(sim, io.open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  목적함수 diagnosis_40 기록")
    print("→ 이어서: recompute_derived → recompute_cores → gen_docs03 → gen_players_csv → validate")


if __name__ == "__main__":
    main()
