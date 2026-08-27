#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""players.json 의 **파생 필드**를 다시 계산한다 (40차 신설).

왜 필요한가 🔴
  `surplus` 와 `obtainable` 은 `my_max` · `market_low` · `market_high` 의 함수인데
  **불변식이 없었다.** 그래서 `my_max` 를 손볼 때마다 조용히 낡았다:

      surplus     16명 불일치 — 그중 **부호가 뒤집힌 것이 7명**
                  (LeBron −6→+2 · Porziņģis +2→−3 · Paul George +5→−1 ·
                   Banchero +3→−5 · Fox +2→−2 · Butler +4→−2 · Murray +1→−4)
      obtainable   4명 불일치 — 그중 **3명이 「살 수 있다」고 거짓 표시**
                  (Markkanen mx19 < 하단 28 · Banchero mx22 < 24 · Murray mx3 < 4)

  툴 화면은 차익을 `p.mx − A.mid` 로 **자체 계산**하므로 무사하다. 오염된 곳은
  `docs/03` 의 「잉여 상위」·「잉여 플러스 다트」·「획득 불가」 세 표다 —
  `gen_docs03.py` 가 저장된 필드로 정렬하고 세기 때문이다.
  즉 **문서가 못 사는 선수를 살 수 있다고 적고 있었다.**

  재계산으로 끝내면 같은 일이 또 생긴다. `validate.py` **I32** 가 상시 대조한다.

Westbrook 예외
  `obtainable=false` 인데 가격상으로는 살 수 있다(mx $4 ≥ 하단 $1). **은퇴**라서
  손으로 내린 값이다(39차). 공식에 예외를 숨기지 않고 `obtainable_override` 로
  **이유와 함께** 드러낸다 — I32 는 override 가 있을 때만 공식을 면제한다.
"""
import json, io, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PP = BASE + "/data/players.json"

# 공식으로 설명되지 않는 값. **이유 없이 늘리지 말 것** — 늘어나면 공식이 틀린 것이다.
OVERRIDE = {
    "Russell Westbrook": {"field": "obtainable", "value": False,
                          "reason": "은퇴 — 가격상으로는 획득 가능하나 자산이 아니다 (39차 확인)"},
}


def mid(p):
    return round((p["market_low"] + p["market_high"]) / 2)


def main(apply=True):
    pl = json.load(io.open(PP, encoding="utf-8"))
    ns = no = 0
    for p in pl:
        exp_s = p["my_max"] - mid(p)
        if p.get("surplus") != exp_s:
            print("  surplus    %-24s %4s → %4d" % (p["name"], p.get("surplus"), exp_s))
            p["surplus"] = exp_s
            ns += 1
        ov = OVERRIDE.get(p["name"])
        if ov and ov["field"] == "obtainable":
            if p.get("obtainable_override") != ov["reason"]:
                p["obtainable_override"] = ov["reason"]
            if p.get("obtainable") != ov["value"]:
                p["obtainable"] = ov["value"]
            continue
        exp_o = p["my_max"] >= p["market_low"]
        if p.get("obtainable") != exp_o:
            print("  obtainable %-24s %5s → %5s   (mx $%d %s 하단 $%d)" % (
                p["name"], p.get("obtainable"), exp_o, p["my_max"],
                ">=" if exp_o else "<", p["market_low"]))
            p["obtainable"] = exp_o
            no += 1
    print("surplus %d건 · obtainable %d건 재계산 · override %d건" % (ns, no, len(OVERRIDE)))
    if apply:
        json.dump(pl, io.open(PP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("→ data/players.json 기록. 이어서 gen_docs03 · gen_players_csv · validate")
    return ns + no


if __name__ == "__main__":
    import sys
    main(apply="--dry" not in sys.argv)
