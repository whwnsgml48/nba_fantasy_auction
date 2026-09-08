#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""작업 4a — **감축표의 ΔP 측정** (42차).

## 왜 측정부터인가
`docs/05 §6j` 는 *"c6 는 아홉을 $191 에 계획하는데 방은 $274~276 을 냈다. $83 을 어디서
줄일지 드래프트 전에 정해져 있어야 한다"* 고 적고 **그 표를 만들지 않았다.**
그런데 표를 만들려면 **「이 칸을 대체로 바꾸면 얼마를 잃나」**가 필요하고, 그건
모형이 아니라 **측정**이다. 42차에 모형 위에 숫자를 얹었다가 두 번 기각당했다.

## 방법 — 비교 규약 그대로
각 슬롯의 1순위를 **그 슬롯의 실제 대체 후보**로 바꾸고 실제 12팀 상대 주간 승률을
다시 잰다. 양쪽을 **같은 실행·같은 시드·이름 정렬**로 새로 잰다(저장값에서 빼지 않는다).
포지션 자격은 후보 목록이 이미 지킨다.

## 절감액은 두 축이다 — 섞지 말 것
```
계획 기준 절감  = plan_price(1순위) − plan_price(대체)     예산 계산용
관측 기준 절감  = room_price(1순위) − room_price(대체)     🔴 **방이 작년처럼 부르는 세계**
```
§6j 가 말하는 $83 은 **관측 기준**이다. 계획 기준으로 감축표를 만들면 「$191 세계」에서
줄이는 것이고, 그 세계는 §6j 가 일어나지 않는다고 말한 바로 그 세계다.
"""
import io, json, os, random, statistics as st, sys, time

BASE = os.path.expanduser("~/personal_work/nba_fantasy_auction_2026")
sys.path.insert(0, BASE + "/tool")
import matchup_sim as MS
import real_opponents as RO
import cat_model as CM

CJ = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
PL = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
REAL, _ = RO.build()
MGRS = sorted(REAL)
OPP = {m: sorted(REAL[m]) for m in MGRS}
ROWS = MS.pool()
ITERS = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
SEED = 20261020
CORES = sys.argv[2].split(",") if len(sys.argv) > 2 else ["c6", "c7", "c1"]

CM.configure(model="standard")


def measure(names, seed=SEED):
    us = sorted(names)
    per = {m: MS.simulate(us, OPP[m], random.Random(seed), ITERS, ROWS) for m in MGRS}
    return {"mean": st.mean(per[m]["weekly_win_rate"] for m in MGRS),
            "by": {m: per[m]["weekly_win_rate"] for m in MGRS}}


def paired(a, b):
    d = [a["by"][m] - b["by"][m] for m in MGRS]
    return st.mean(d), st.stdev(d) / len(MGRS) ** 0.5


def room(n):
    return PL[n].get("room_price")


out = {"generated_by": "tool/reduction_table.py", "seed": SEED, "iterations": ITERS,
       "week_model": CM.WEEK_MODEL, "standard_week_games": CM.STD_WEEK_GAMES,
       "protocol": ("각 슬롯 1순위를 그 슬롯의 실제 대체 후보로 바꾸고 실제 12팀 평균 "
                    "주간 승률을 **같은 실행·같은 시드·이름 정렬**로 새로 잰다."),
       "savings_note": ("절감액은 두 축이다 — 계획 기준(plan_price 차)과 관측 기준"
                        "(room_price 차). §6j 의 $83 은 **관측 기준**이다."),
       "cores": {}}

for cid in CORES:
    co = next(c for c in CJ["cores"] if c["id"] == cid)
    roster = [s["candidates"][0]["name"] for s in co["slots"]]
    t0 = time.time()
    B = measure(roster)
    rows = []
    for s in co["slots"]:
        first = s["candidates"][0]["name"]
        for alt in s["candidates"][1:]:
            an = alt["name"]
            if an in roster:
                continue                     # 이미 로스터에 있으면 교체가 아니다
            new = [an if n == first else n for n in roster]
            if len(set(new)) != 9:
                continue
            A = measure(new)
            d, se = paired(A, B)
            r_out, r_in = room(first), room(an)
            rows.append({
                "slot": s["slot"], "out": first, "in": an,
                "plan_out": s["candidates"][0]["expected_cost"],
                "plan_in": alt["expected_cost"],
                "save_plan": s["candidates"][0]["expected_cost"] - alt["expected_cost"],
                "room_out": r_out, "room_in": r_in,
                "save_room": (r_out - r_in) if (r_out is not None and r_in is not None) else None,
                "delta_pp": round(100 * d, 3), "se_pp": round(100 * se, 3),
                "sigma": round(abs(d / se), 2) if se else None,
            })
    out["cores"][cid] = {
        "base_win_rate": round(B["mean"], 4),
        "planned_total": co["planned_total"],
        "room_total": sum((room(n) or next(s["candidates"][0]["expected_cost"]
                                           for s in co["slots"]
                                           if s["candidates"][0]["name"] == n))
                          for n in roster),
        "rows": rows,
    }
    print("  %s 완료 (%.0fs · %d행)" % (cid, time.time() - t0, len(rows)))

json.dump(out, io.open(BASE + "/data/reduction_table.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("\n=== 감축 후보 — 관측 기준 절감 / 측정된 손실 ===")
for cid, d in out["cores"].items():
    print("\n══ %s  기준 승률 %.2f%%  계획 $%d → 방 $%d" % (
        cid, 100 * d["base_win_rate"], d["planned_total"], d["room_total"]))
    ok = [r for r in d["rows"] if r["save_room"] is not None and r["save_room"] > 0]
    for r in sorted(ok, key=lambda x: -(x["save_room"] / max(abs(x["delta_pp"]), .05))):
        eff = r["save_room"] / max(abs(r["delta_pp"]), .05)
        print("  %-5s %-22s → %-22s 관측절감 $%-3d 손실 %+6.2f%%p (%.1fσ)  $/%%p %.0f" % (
            r["slot"], r["out"], r["in"], r["save_room"], r["delta_pp"],
            r["sigma"] or 0, eff))
    na = [r for r in d["rows"] if r["save_room"] is None]
    if na:
        print("  ⚠️ 관측 절감 계산 불가(둘 중 하나가 작년 미지명): " +
              ", ".join("%s→%s" % (r["out"], r["in"]) for r in na))
print("\ndata/reduction_table.json 기록")
