#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 **게이트가 전부 닫힌 세계** — 감축 경로가 어디로 착지하는가 (42차 · 작업4a).

## 왜 이 측정이 필요한가
`kat_price_branch` 는 KAT > $57 이면 **Jokić ≤ $97 이면 c2, 아니면 c4** 로 보낸다.
작년 관측이 KAT $74 · Jokić $96 이므로 **c2 로 가고 c2 는 방 $200 = 예산 정확히** 다.
문제는 **Jokić 이 $98 인 세계** — 분기가 c4 로 보내는데 c4 는 방 $302 다(감축 $102 필요).

`escape_paths_40` 이 이미 경고했다: *"Daniels·Şengün·Gobert 의 도달 가능한 탈출로가
c2 하나로 수렴했고 c2 는 조건부다. 게이트가 안 열리면 이 셋의 탈출로는 0 이다."*

## 🔴 개별 Δ 를 더하지 않는다
감축표의 Δ 는 **한 칸씩** 잰 값이다. 두 칸을 동시에 빼면 상호작용이 있다.
42차에 「모형 위에 숫자를 얹었다가 두 번 기각」당했으므로 **합친 로스터를 직접 잰다.**
"""
import io, json, os, random, statistics as st, sys

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
ITERS, SEED = 4000, 20261020
CM.configure(model="standard")


def measure(names):
    us = sorted(names)
    per = {m: MS.simulate(us, OPP[m], random.Random(SEED), ITERS, ROWS) for m in MGRS}
    return {"mean": st.mean(per[m]["weekly_win_rate"] for m in MGRS),
            "by": {m: per[m]["weekly_win_rate"] for m in MGRS}}


def paired(a, b):
    d = [a["by"][m] - b["by"][m] for m in MGRS]
    return st.mean(d), st.stdev(d) / len(MGRS) ** 0.5


def roster(cid):
    return [s["candidates"][0]["name"]
            for s in next(c for c in CJ["cores"] if c["id"] == cid)["slots"]]


def cost_room(names):
    tot = 0
    for n in names:
        rp = PL[n].get("room_price")
        tot += rp if rp is not None else 0
    return tot


def swap(names, pairs):
    out = list(names)
    for a, b in pairs:
        assert a in out, a
        out[out.index(a)] = b
    return out


# 감축 경로 — 감축표의 **효율 순서**대로 쌓는다
PLANS = {
    "c6 원안": (roster("c6"), []),
    "c6 −Şengün": (roster("c6"), [("Alperen Şengün", "LeBron James")]),
    "c6 −Şengün −KAT": (roster("c6"), [("Alperen Şengün", "LeBron James"),
                                       ("Karl-Anthony Towns", "Jalen Duren")]),
    "c4 원안": (roster("c4"), []),
    "c4 −Trae −Mobley": (roster("c4"), [("Trae Young", "Andrew Nembhard"),
                                        ("Evan Mobley", "Walker Kessler")]),
    "c4 −Trae −Mobley −Amen": (roster("c4"), [("Trae Young", "Andrew Nembhard"),
                                              ("Evan Mobley", "Walker Kessler"),
                                              ("Amen Thompson", "Immanuel Quickley")]),
    "c2 원안": (roster("c2"), []),
}

base = {}
res = {}
print("🔴 게이트 전부 닫힌 세계 — 감축 경로 착지점 (실제 12팀 · 4000시행 · 시드 %d)\n" % SEED)
print("⚠️ 개별 Δ 를 더한 값이 아니라 **합친 로스터를 직접 잰** 값이다.\n")
print("%-26s %9s %9s %10s %8s" % ("경로", "방 총액", "승률", "원안 대비", "예산"))
print("-" * 66)
for label, (r0, pairs) in PLANS.items():
    names = swap(r0, pairs)
    assert len(set(names)) == 9, label
    m = measure(names)
    res[label] = {"roster": sorted(names), "room_total": cost_room(names),
                  "win_rate": round(m["mean"], 4), "swaps": pairs}
    cid = label.split()[0]
    if not pairs:
        base[cid] = m
        d = 0.0
    else:
        d, se = paired(m, base[cid])
        res[label]["delta_pp"] = round(100 * d, 3)
        res[label]["se_pp"] = round(100 * se, 3)
    c = cost_room(names)
    print("%-26s %8d$ %8.2f%% %+9.2f%%p %8s" % (
        label, c, 100 * m["mean"], 100 * d, "OK" if c <= 200 else "초과 $%d" % (c - 200)))

out = {"generated_by": "tool/closed_world.py", "seed": SEED, "iterations": ITERS,
       "week_model": CM.WEEK_MODEL,
       "why": ("kat_price_branch 는 KAT > $57 이면 Jokić ≤ $97 → c2, 아니면 c4 로 보낸다. "
               "작년 관측(KAT $74 · Jokić $96)에서는 c2 로 가고 c2 는 방 $200 = 예산이다. "
               "문제는 **Jokić 이 $98 인 세계** — c4 는 방 $302 라 $102 를 감축해야 한다."),
       "method": ("🔴 감축표의 개별 Δ 를 **더하지 않았다.** 두 칸을 동시에 빼면 상호작용이 "
                  "있으므로 **합친 로스터를 직접 쟀다.** 42차에 모형 위에 숫자를 얹었다가 "
                  "두 번 기각당한 뒤의 규율이다."),
       "plans": res}
json.dump(out, io.open(BASE + "/data/closed_world.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\ndata/closed_world.json 기록")
