#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""가드 편향 · **3캣만 포기** 탐색 — 4차 · 마지막 (40차 · 측정만).

왜 이번엔 산수가 다른가
  3차는 **5캣**을 버렸다(REB·OREB·BLK·DD·FG%). 그러면 목표가 8캣이고 승리선이 7이라
  여유 상한이 1.0 이다 — SD 1.7 대비 여유/SD 0.57 이 천장이고 84% 에 못 간다.
  🔴 그런데 3차가 막힌 진짜 이유는 「가드라서」가 아니었다. 목표가 8로 좁혀지면서
     **슈터가 못 주는 셋(STL·TOV·PTS)이 목표 안으로 강제 편입**된 것이다.
  **3캣만 버리면 목표가 10 이고 여유 상한이 3.0 이다.** 산수가 막지 않는다.

포기는 **가장 순수한 빅 캣 셋만** — OREB · BLK · DD
  🔴 REB·FG% 는 버리지 않는다. 빅 한둘로 건질 수 있고, 버리면 3차 꼴이 난다.

앞선 네 실패를 전부 막는다
  ① 캣별 **표준화** 후 합산 — `matchup_sim.z()` 를 쓰지 않는다      (1차: FG% 하이재킹)
  ② 가정 노출 `share < 0.5` 인 1순위 **최대 1명**                    (2차: 조건 이동)
  ③ **MIN_SPEND 180** · 총액 ≤ 200 · 예비 ≥ 4                       (3차: $24 퇴화 해)
  ④ 목표 10캣 중 **7캣 이상 마진 양수**를 하한으로                    (3차: 강제 편입)

⚠️ **사전 등록이 쓰레기를 안 걸러준다.** 3차에서 $24 짜리 해가 기준과 맞아떨어졌다.
   산출물이 말이 되는지(총액·자격·이름) **눈으로** 보고, 이상하면 기준에 맞아도 버린다.
"""
import json, io, os, sys, random, itertools, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import real_opponents as RO
import pos_elig as PE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS, PRE_ITERS = 20261020, 4000, 800
BUDGET, RESERVE_FLOOR, MIN_SPEND = 200, 4, 180
PUNT = ("OREB", "BLK", "DD")
TARGET = tuple(c for c in CM.CATS if c not in PUNT)
MAX_SHAKY = 1
MIN_POSITIVE = 7
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
B = CM.baselines()


def price(n):
    p = PL[n]
    return max(1, round((p["market_low"] + p["market_high"]) / 2))


def shaky(n):
    ms = (MS.PL.get(n) or {}).get("measured_source") or {}
    s = ms.get("blend_share_2025_26")
    return s is not None and s < 0.50


def legal(names):
    ps = [PL[n] for n in names]
    if len(PE.match(ps) or []) != len(PE.ROSTER_SLOTS):
        return False
    return sum(1 for p in ps if "C" in PE.elig(p)) >= 2


def main():
    REAL, _ = RO.build()
    pool = [n for n, p in PL.items()
            if not p.get("injury_exclude") and n in CM.F and p.get("value_reference")]

    # 역할: 가드/윙(목표 10캣 공급) · 빅(PF·C 를 채우되 목표캣을 덜 깎는)
    gw, bigs = [], []
    for n in pool:
        r = CM.F[n]
        av = CM.avail(r)
        pr = price(n)
        e = PE.elig(PL[n])
        # 목표캣 기여의 거친 점수 — 캣별 표준화는 아래 프리필터에서 한다
        g = ((r.get("AST") or 0) * 3 + (r.get("STL") or 0) * 12 + (r.get("3PM") or 0) * 6
             + (r.get("PTS") or 0) - (r.get("TOV") or 0) * 5) * av
        if g > 25:
            gw.append((n, pr, g, sorted(e)))
        if ("PF" in e or "C" in e) and pr <= 30:
            big = ((r.get("REB") or 0) + (r.get("FG%") or 0) * 20) * av
            bigs.append((n, pr, big, sorted(e)))
    # 🔴 **한 기준으로만 정렬하면 가격대가 한쪽으로 몰린다.** 첫 실행이 그랬다 —
    #   가드는 절대 점수로 정렬해 전부 $35~97 이 됐고, 빅은 달러당으로 정렬해 전부 $2 가 됐다.
    #   그 둘로는 $180~196 구간을 만들 수 없어 **제약 통과 조합이 0개**였다.
    #   이 저장소가 40차에만 네 번 밟은 형태다(1차 FG% · guard_stack · 3차 $24 · 여기).
    #   → **절대 점수 상위**와 **달러당 상위**를 섞고, 빅에 중가 구간을 강제로 넣는다.
    def mix(rows, k):
        a = sorted(rows, key=lambda x: -x[2])[:k]
        b = sorted(rows, key=lambda x: -x[2] / max(1, x[1]))[:k]
        return list(dict.fromkeys([x[0] for x in a] + [x[0] for x in b]))
    G = mix(gw, 11)
    Bg = mix(bigs, 7)
    mid = [x[0] for x in sorted(bigs, key=lambda x: -x[2]) if 8 <= x[1] <= 30][:6]
    Bg = list(dict.fromkeys(Bg + mid))
    print("가드/윙 %d · 빅(REB·FG%% 유지용) %d" % (len(G), len(Bg)))
    print("  가드:", ", ".join("%s $%d" % (x[0].split()[-1], x[1]) for x in gw[:10]))
    print("  빅  :", ", ".join("%s $%d" % (x[0].split()[-1], x[1]) for x in bigs[:10]))

    combos, seen = [], set()
    for g6 in itertools.combinations(G[:16], 6):
        if sum(1 for n in g6 if shaky(n)) > MAX_SHAKY:
            continue
        cg = sum(price(n) for n in g6)
        if cg > BUDGET - RESERVE_FLOOR - 3:
            continue
        for b3 in itertools.combinations(Bg[:13], 3):
            names = tuple(sorted(set(g6 + b3)))
            if len(names) != 9 or names in seen:
                continue
            if sum(1 for n in names if shaky(n)) > MAX_SHAKY:
                continue
            tot = cg + sum(price(n) for n in b3)
            if tot > BUDGET - RESERVE_FLOOR or tot < MIN_SPEND:
                continue
            seen.add(names)
            if not legal(names):
                continue
            combos.append((names, tot))
    print("\n제약 통과 조합 %d개  (MIN_SPEND $%d · 가정노출 ≤%d · 자격 성립)"
          % (len(combos), MIN_SPEND, MAX_SHAKY))
    if not combos:
        print("🔴 0개 — 실패 지점: 예산/자격/가정노출")
        return

    # ④ 하한: 목표 10캣 중 7캣 이상 마진 양수
    kept = []
    for names, tot in combos:
        cm, _, _, _ = CM.evaluate(list(names), B)
        pos = sum(1 for c in TARGET if (cm.get(c) or 0) > 0)
        if pos >= MIN_POSITIVE:
            kept.append((names, tot, cm, pos))
    print("목표 10캣 중 %d캣 이상 양수: %d개" % (MIN_POSITIVE, len(kept)))
    if not kept:
        print("🔴 하한 통과 0개 — 이 자체가 결과다")
        return

    # ① 캣별 표준화 후 합산
    stats = {}
    for c in CM.CATS:
        vs = [(k[2].get(c) or 0) for k in kept]
        stats[c] = (sum(vs) / len(vs), st.pstdev(vs) or 1.0)

    def score(cm):
        return sum(((cm.get(c) or 0) - stats[c][0]) / stats[c][1] * (1.0 if c in TARGET else 0.1)
                   for c in CM.CATS)

    kept.sort(key=lambda k: -score(k[2]))
    top = kept[:24]

    def sim(names, iters):
        MS._URATE.clear()
        rs = [MS.simulate(list(names), REAL[m], random.Random(SEED), iters) for m in REAL]
        MS._URATE.clear()
        cw = {}
        for r in rs:
            for c, v in r["cat_win_probs"].items():
                cw.setdefault(c, []).append(v)
        return (sum(r["weekly_win_rate"] for r in rs) / len(rs),
                min(r["weekly_win_rate"] for r in rs),
                sum(r["expected_cats_won"] for r in rs) / len(rs),
                sum(r["cats_won_sd"] for r in rs) / len(rs),
                {c: sum(v) / len(v) for c, v in cw.items()})

    pre = sorted(((sim(n, PRE_ITERS)[0], n, t) for n, t, _, _ in top), reverse=True)[:6]
    print("🔴 최종 후보는 %d시행으로 **다시** 잰다 (승자의 저주)\n" % ITERS)
    out = []
    c2 = next(c for c in json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))["cores"]
              if c["id"] == "c2")
    c2n = set(s["candidates"][0]["name"] for s in c2["slots"])
    for _, names, tot in pre:
        mean, mn, cats, sd, cw = sim(names, ITERS)
        sh = [n for n in names if shaky(n)]
        ov = len(set(names) & c2n)
        eds = []
        for n in names:
            py = PL[n].get("prior_auction_price")
            if py is not None:
                eds.append(PL[n]["my_max"] - py * 1.11)
        out.append({"names": list(names), "total": tot, "reserve": BUDGET - tot,
                    "mean": round(mean, 4), "min": round(mn, 4), "cats": round(cats, 2),
                    "cats_sd": round(sd, 2), "margin_over_sd": round((cats - 7) / sd, 2),
                    "shaky": sh, "c2_overlap": ov, "has_jokic": "Nikola Jokić" in names,
                    "edge_sum": round(sum(eds), 1), "edge_neg": sum(1 for e in eds if e < 0),
                    "below_50": sorted([c for c, v in cw.items() if v < 0.5], key=lambda c: cw[c]),
                    "cat_win": {c: round(v, 3) for c, v in cw.items()}})
        print("  $%-4d %5.1f%% %4.2f캣 SD%4.2f 여유/SD%5.2f | 가정%d · c2겹침%d · edge합%+6.0f(음수%d)"
              % (tot, 100 * mean, cats, sd, (cats - 7) / sd, len(sh), ov,
                 sum(eds), sum(1 for e in eds if e < 0)))
        print("        %s" % " · ".join(n.split()[-1] for n in names))
    out.sort(key=lambda r: -r["mean"])
    json.dump({"seed": SEED, "iterations": ITERS, "punt": list(PUNT), "target": list(TARGET),
               "min_spend": MIN_SPEND, "max_shaky": MAX_SHAKY, "min_positive": MIN_POSITIVE,
               "candidates": out},
              io.open(f"{BASE}/data/guard_tilt_search.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    b = out[0]
    print("\n최선 %5.1f%% · 기대 %.2f캣 · 여유/SD %.2f · 가정 %d · c2 겹침 %d · 총액 $%d"
          % (100 * b["mean"], b["cats"], b["margin_over_sd"], len(b["shaky"]),
             b["c2_overlap"], b["total"]))
    print("사전 등록 판정: %s"
          % ("채택 검토" if (b["mean"] >= 0.84 and len(b["shaky"]) <= 1 and b["total"] >= 180)
             else ("「답은 c2」" if (b["has_jokic"] or b["c2_overlap"] >= 6) else "미달 — 기록하고 닫는다")))
    print("data/guard_tilt_search.json 기록")


if __name__ == "__main__":
    main()
