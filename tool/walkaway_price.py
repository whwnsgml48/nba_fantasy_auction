#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""철수가 = **무차별 가격** 측정 (40차 · 평가 세션 인계분 E1).

무엇을 재는가
  「이 선수를 $p 에 사는 것」 vs 「포기하고 2순위로 가고 $p−$a 를 남기는 것」이
  같아지는 p. 그 위로는 부르지 않는다.

🔴 왜 「재배치 없이 보수적으로」만 하면 안 되는가
  평가 세션과 처음 합의한 설계는 「절감액을 예비비로만 두고 잰다」였다. 그런데
  **가격을 올려도 로스터가 안 바뀌므로 승률이 그대로**다. 남는 돈의 가치를 0으로 두면
  항상 그 선수를 유지하는 쪽이 이기고, **답이 예산 상한으로 붕괴한다** — 그건
  무차별 가격이 아니라 「예산이 허용하는 상한」이고 측정 없이도 나오는 값이다.

  그래서 남는 돈에 값을 매겨야 하는데, **배분 규칙을 만들면 답이 그 규칙을 반영한다**
  (`recompute_cores.solve_redeploy` 는 room 큰 순서로 채우므로 비싼 슬롯에 돈이 몰린다).
  → 규칙을 만들지 않고 **교환비를 실측한다.** 「이 코어에서 $1 은 몇 %p 인가」를
    실제 업그레이드를 시뮬로 재서 구하고, 그 환율로 절감액을 승률로 환산한다.

    무차별 가격  p* = a + (W_유지 − W_대체) / 환율
                 a  = 2순위 취득가 · 환율 = %p per $

⚠️ 로컬 선형 근사다
  환율은 예비비 범위 안에서 잰 것이라 멀리 외삽하면 깨진다. Hart 에 선형으로 밀었더니
  $26 이 나왔는데 명백히 말이 안 된다. 그래서 **예산 상한에서 자르고 둘을 함께 보고**한다:
      예산이 허용하는 상한 = 예비비가 I22 하한 $4 에 닿는 지점 (결정론적)
      무차별 가격          = 이 스크립트 (측정)
  **작은 쪽이 실질 철수가다.**

⚠️ 코어마다 다르다
  같은 선수도 코어에 따라 가치가 다르다. 한 숫자로 줄이려면 「어느 코어를 돌릴 것인가」를
  먼저 정해야 하는데 그건 드래프트 당일 방이 정한다. 그래서 **코어별로 내고 범위로 보고**한다.
"""
import json, io, os, sys, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS
import real_opponents as RO
import cat_model as CM
import pos_elig as PE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS, RSV_FLOOR = 20261020, 4000, 4
TARGETS = ["Kon Knueppel", "Desmond Bane", "Josh Hart", "DeMar DeRozan", "Dyson Daniels"]

CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
PL = MS.PL
REAL, _ = RO.build()
B = CM.baselines()


def wr(names):
    MS._URATE.clear()
    v = [MS.simulate(names, REAL[m], random.Random(SEED), ITERS)["weekly_win_rate"]
         for m in REAL]
    MS._URATE.clear()
    return sum(v) / len(v)


def mid(p):
    return round((p["market_low"] + p["market_high"]) / 2)


def rate_of(co, names, reserve, tries=3):
    """이 코어에서 $1 이 몇 %p 인가 — **실제 업그레이드를 재서** 구한다.

    싼 슬롯을 예비비 안에서 더 비싼 적격 선수로 올려 보고, 가장 좋은 결과를 쓴다.
    '가장 좋은 것'을 쓰는 이유: 무차별 가격은 「이 돈이 **다른 데서 더 벌 수 있는가**」를
    묻는 것이므로, 돈의 값은 **최선의 대안 용도**로 재는 것이 맞다.
    """
    base = wr(names)
    slots = sorted(co["slots"], key=lambda s: s["plan_price"])[:3]
    best = None
    for s in slots:
        out = s["candidates"][0]["name"]
        budget = s["plan_price"] + reserve - RSV_FLOOR
        cands = []
        for n, p in PL.items():
            if n in names or n not in MS.F or not p.get("obtainable") or p.get("injury_exclude"):
                continue
            if not PE.can(p, s["slot"]):
                continue
            v = mid(p)
            if v <= s["plan_price"] or v > min(budget, p["my_max"]):
                continue
            cm, nwin, _, _ = CM.evaluate([x for x in names if x != out] + [n], B)
            cands.append((nwin, sum((CM.rel_margin(c, x, B) or 0) for c, x in cm.items()
                                    if x is not None), n, v))
        cands.sort(key=lambda r: (-r[0], -r[1]))
        for _nw, _tt, n, v in cands[:tries]:
            d = v - s["plan_price"]
            if d <= 0:
                continue
            g = wr([x if x != out else n for x in names]) - base
            r = g / d
            if best is None or r > best[0]:
                best = (r, out, n, d, g)
    return base, best


def main():
    out = {"seed": SEED, "iterations": ITERS, "reserve_floor": RSV_FLOOR, "rows": [],
           "method": ("무차별 가격 p* = a + (W_유지 − W_대체) / 환율. "
                      "환율은 그 코어에서 예비비로 살 수 있는 **최선의 업그레이드**를 "
                      "시뮬로 재서 구한다 — 배분 규칙을 만들지 않기 위해서다."),
           "caveat": ("로컬 선형 근사이므로 멀리 외삽하면 깨진다. 예산 상한과 함께 보고하고 "
                      "**작은 쪽이 실질 철수가**다.")}
    for who in TARGETS:
        for co in CJ["cores"]:
            s = next((x for x in co["slots"] if x["candidates"][0]["name"] == who), None)
            if not s or len(s["candidates"]) < 2:
                continue
            names = [x["candidates"][0]["name"] for x in co["slots"]]
            reserve = 200 - co["planned_total"]
            alt = s["candidates"][1]
            keep, best = rate_of(co, names, reserve)
            drop = keep - wr([x if x != who else alt["name"] for x in names])
            cap = s["plan_price"] + reserve - RSV_FLOOR       # 예산이 허용하는 상한
            row = {"player": who, "core": co["id"], "plan": s["plan_price"],
                   "alt": alt["name"], "alt_price": alt["plan_price"],
                   "keep_wr": round(keep, 4), "drop_pp": round(drop, 4),
                   "budget_cap": cap, "reserve": reserve}
            if best and best[0] > 0:
                r = best[0]
                row["rate_pp_per_dollar"] = round(r, 5)
                row["rate_from"] = "%s → %s (+$%d · %+.2f%%p)" % (
                    best[1], best[2], best[3], 100 * best[4])
                row["indifference"] = round(alt["plan_price"] + drop / r, 1)
                row["walkaway"] = min(cap, round(alt["plan_price"] + drop / r))
                row["binding"] = "예산" if cap <= row["indifference"] else "무차별"
            else:
                row["rate_pp_per_dollar"] = None
                row["note"] = "예비비로 살 수 있는 개선이 없다 — 환율을 못 잰다. 예산 상한만 유효"
                row["walkaway"] = cap
                row["binding"] = "예산"
            out["rows"].append(row)
            print("  %-16s %-3s 계획$%-3d 대체 %-18s 상실 %+.2f%%p  환율 %s  무차별 %s  상한 $%-3d → 철수 $%-3d (%s)"
                  % (who, co["id"], s["plan_price"], alt["name"], -100 * drop,
                     ("%.3f%%p/$" % (100 * row["rate_pp_per_dollar"])) if row["rate_pp_per_dollar"] else "  ―   ",
                     ("$%.0f" % row["indifference"]) if row.get("indifference") else " ― ",
                     cap, row["walkaway"], row["binding"]), flush=True)
    json.dump(out, io.open(f"{BASE}/data/walkaway_prices.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("data/walkaway_prices.json 기록")


if __name__ == "__main__":
    main()
