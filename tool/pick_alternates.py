#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""슬롯 대체후보 재선정 — **자격이 맞고 값이 되는** 후보를 캣으로 줄 세운다 (40차).

왜 필요한가 🔴
  40차에 야후 실자격이 들어오면서 대체후보 층이 무너졌다. 부적격 5건이 **전부 SF 칸**이다:
    c3 SF(AJ Green·Isaiah Joe) · c4 SF(Merrill) · c5 SF(Merrill) · c6 SF(Schröder·Russell) · c7 SF(Amen)
  1순위 SF를 잃으면 **갈 곳이 없다**. 평가 세션 ③의 「SF가 진짜 병목」을 대체후보 층이
  독립적으로 증명한 셈이다.

무엇으로 고르는가
  후보를 그 슬롯 1순위 자리에 넣고 `cat_model.evaluate` 로 로스터 전체를 재판정한다.
  1차 승리 캣 수, 동률이면 상대마진 합. **몬테카를로가 아니다** — 대체후보는 1순위를
  놓쳤을 때 가는 자리라 순위만 있으면 되고, 시뮬은 이 해상도를 주지 않는다.

제약
  · 슬롯 자격(`pos_elig`) · 이미 로스터에 있는 선수 제외 · `obtainable`
  · 계획가 = 시장 중간값, `market_low <= 계획가 <= my_max`
  · 계획가 <= (1순위 계획가 + 예비비)   — 갈아탈 돈이 실제로 있어야 한다
  · `injury_exclude` 제외
"""
import json, io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import pos_elig as PE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
B = CM.baselines()


def mid(p):
    return round((p["market_low"] + p["market_high"]) / 2)


def score(names):
    cm, nwin, win, lose = CM.evaluate(names, B)
    tot = 0.0
    for c, v in cm.items():
        if v is None:
            continue
        tot += CM.rel_margin(c, v, B, names) or 0.0
    return nwin, round(tot, 1)


def rank(roster, slot, out_name, reserve, cap=None, top=8):
    """roster: [이름] 9명. slot 자리의 out_name 을 대신할 후보를 줄 세운다."""
    others = [n for n in roster if n != out_name]
    budget = PL[out_name]["plan_price"] if "plan_price" in PL[out_name] else None
    base_price = next((p for p in [None]), None)
    rows = []
    for n, p in PL.items():
        if n in roster or n not in CM.F:
            continue
        if not p.get("obtainable") or p.get("injury_exclude"):
            continue
        if not PE.can(p, slot):
            continue
        v = mid(p)
        if v < p["market_low"] or v > p["my_max"]:
            continue
        if cap and v > cap:
            continue
        if budget is not None and v > budget + reserve:
            continue
        nw, tot = score(others + [n])
        rows.append((nw, tot, n, v, "확정" if PE.confirmed(p) else "추정"))
    rows.sort(key=lambda r: (-r[0], -r[1]))
    return rows[:top]


def main():
    CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    targets = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
    for t in targets:
        co = next(c for c in CJ["cores"] if c["id"] == t["core"])
        roster = t.get("roster") or [s["candidates"][0]["name"] for s in co["slots"]]
        out = t["out"]
        for n in roster:
            PL[n].setdefault("plan_price", t.get("price", {}).get(n))
        PL[out]["plan_price"] = t["price"]
        base_nw, base_tot = score(roster)
        print("■ %s  %s 칸 — 현 1순위 %s $%d  (로스터 승리캣 %d · 마진합 %.1f · 예비비 $%d)"
              % (t["core"], t["slot"], out, t["price"], base_nw, base_tot, t["reserve"]))
        for nw, tot, n, v, conf in rank(roster, t["slot"], out, t["reserve"], co.get("single_player_cap")):
            print("    %-24s $%-3d  승리캣 %2d  마진합 %8.1f  자격 %s" % (n, v, nw, tot, conf))
        print()


if __name__ == "__main__":
    main()
