#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""**Jokić 없이 c2 의 모양을 만들 수 있는가** (40차 · 재탐색 1회 · 탐색만).

왜 질문이 바뀌었나
  1차 탐색(rate_core_search)은 「비율캣 코어」를 물었고 71.7% 로 실패했다.
  🔴 그런데 그 측정은 **가설의 시험이 아니었다** — 프리필터가 캣별 마진을 원값으로
     합쳐 FG% 의 절대 크기가 나머지를 압도했고, 결과적으로 「FG% 최대화」를 탐색했다.
     A/T 20.2% · FT% 45.3% 로 **목표 캣 둘을 못 이겼다.**

  그리고 구조적 상한이 보인다: **저분산 캣은 다섯뿐**(FG%·FT%·3P%·A/T·TOV)이고
  승리선은 7 이다. 최소 2캣을 누적캣에서 가져와야 하고 그건 결국 싼 빅이다.
  **순수형은 구조적으로 승리선에 붙어 있다** — 1차 결과가 정확히 7캣인 것이 우연이 아니다.

  그런데 이 모양은 이미 포트폴리오에 있다 — **c2** 다.
    A/T 87 · 3PM 70 · FT% 68 · TOV 62 · REB 81 · OREB 86 · DD 68
    **13캣 중 50% 미만이 하나도 없다** · 기대 8.95캣(최다)
  Jokić 한 명이 누적캣을 한 칸에서 공급하므로 나머지 여덟 칸을 저분산 구역에 쓴다.

  🔴 **c2 는 조건부다** — 내가 Jokić 를 $97 이하로 따야 하고 확률은 0.45 미만이다.
     게이트가 안 열리면 **그 모양이 포트폴리오에서 통째로 사라진다.**
     무조건 도달 가능한 c2 형이 있으면 승률과 무관하게 값이 있다.

설계 — 1차의 결함을 막는다
  · 프리필터에서 캣별 마진을 **표준화**한 뒤 합친다 (원값 합은 FG% 가 지배한다)
  · **캣별 하한**: A/T·FT% 마진이 양수여야 후보에 남는다 (합산으로 뭉개지지 않게)
  · FG% 를 사려고 돈을 쓰지 않는다 — **싸게 온다**(Kalkbrenner 순 +79 · Ayton +86)
  · 필러 ≤ $5

⚠️ 탐색만 한다. cores.json 에 쓰지 않는다. 상위 묶음(84%+) 밖이면 이것으로 닫는다.
"""
import json, io, os, sys, random, itertools, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import real_opponents as RO
import pos_elig as PE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS, PRE_ITERS = 20261020, 4000, 800
BUDGET, RESERVE_FLOOR, FILLER_CAP = 200, 12, 5
BAN = {"Nikola Jokić"}
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
B = CM.baselines()


def price(n):
    p = PL[n]
    return max(1, round((p["market_low"] + p["market_high"]) / 2))


def buildable(names):
    ps = [PL[n] for n in names]
    if len(PE.match(ps) or []) != len(PE.ROSTER_SLOTS):
        return False
    return sum(1 for p in ps if "C" in PE.elig(p)) >= 2


def main():
    REAL, _ = RO.build()
    pool = [n for n, p in PL.items()
            if not p.get("injury_exclude") and n in CM.F and p.get("value_reference")
            and n not in BAN]

    def at_ft(n):
        r = CM.F[n]; av = CM.avail(r)
        ft = ((r.get("FT%") or 0) - B["FT%"]) * (r.get("FTA") or 0) * av * 100
        a, t = (r.get("AST") or 0) * av, (r.get("TOV") or 0) * av
        return ft, a, t

    # ── 역할별 후보 ────────────────────────────────────────────────────
    # A/T·FT% 공급 가드 (저분산 구역) — 싼 것 우선
    guards, bigs, flex = [], [], []
    for n in pool:
        r = CM.F[n]; av = CM.avail(r); pr = price(n)
        ft, a, t = at_ft(n)
        atr = a / max(0.1, t)
        cheap_big = (r.get("OREB") or 0) * av >= 1.6 and (r.get("FG%") or 0) >= 0.55
        if a >= 2.5 and atr >= 2.6 and ft > -5:
            guards.append((n, pr, ft, atr))
        if cheap_big and pr <= 20:
            bigs.append((n, pr, ((r.get("REB") or 0) + 2 * (r.get("OREB") or 0)
                                 + 3 * (r.get("BLK") or 0)) * av))
        if 8 <= pr <= 60 and ft > 10:
            flex.append((n, pr, ft))
    guards.sort(key=lambda x: (-x[3], x[1])); bigs.sort(key=lambda x: -x[2] / max(1, x[1]))
    flex.sort(key=lambda x: -x[2] / max(1, x[1]))
    G = [g[0] for g in guards[:14]]
    Bg = [b[0] for b in bigs[:14]]
    Fx = [f[0] for f in flex[:12]]
    print("가드(A/T·FT%%) %d · 빅(누적·FG%%) %d · 플렉스(FT%%) %d" % (len(G), len(Bg), len(Fx)))
    print("  가드:", ", ".join("%s $%d" % (g[0].split()[-1], g[1]) for g in guards[:8]))
    print("  빅  :", ", ".join("%s $%d" % (b[0].split()[-1], b[1]) for b in bigs[:8]))
    print("  플렉스:", ", ".join("%s $%d" % (f[0].split()[-1], f[1]) for f in flex[:8]))

    # ── 조립: 가드 4 + 빅 3 + 플렉스 2 ────────────────────────────────
    combos, seen = [], set()
    for g4 in itertools.combinations(G[:11], 4):
        cg = sum(price(n) for n in g4)
        if cg > 120:
            continue
        for b3 in itertools.combinations(Bg[:11], 3):
            cb = cg + sum(price(n) for n in b3)
            if cb > BUDGET - RESERVE_FLOOR - 2:
                continue
            for f2 in itertools.combinations(Fx[:9], 2):
                names = tuple(sorted(set(g4 + b3 + f2)))
                if len(names) != 9 or names in seen:
                    continue
                tot = cb + sum(price(n) for n in f2)
                if tot > BUDGET - RESERVE_FLOOR:
                    continue
                seen.add(names)
                if not buildable(names):
                    continue
                combos.append((names, tot))
    print("\n제약 통과 조합 %d개" % len(combos))
    if not combos:
        print("🔴 0개 — 실패 지점: 예산/자격"); return

    # ── 프리필터: **캣별 표준화** 후 합산 + 캣별 하한 ─────────────────
    margins = []
    for names, tot in combos:
        cm, _, _, _ = CM.evaluate(list(names), B)
        margins.append(cm)
    kept = []
    for (names, tot), cm in zip(combos, margins):
        if (cm.get("A/T") or 0) <= 0 or (cm.get("FT%") or 0) <= 0:
            continue                      # 🔴 캣별 하한 — 합산으로 뭉개지지 않게
        kept.append((names, tot, cm))
    print("A/T·FT%% 마진 양수 조합 %d개 (하한 통과)" % len(kept))
    if not kept:
        print("🔴 A/T·FT%% 를 동시에 이기는 조합이 0개 — 이 자체가 결과다".replace("%%","%")); return
    stats = {}
    for c in CM.CATS:
        vs = [(k[2].get(c) or 0) for k in kept]
        mu = sum(vs) / len(vs)
        sd = st.pstdev(vs) or 1.0
        stats[c] = (mu, sd)
    def z(cm):
        return sum(((cm.get(c) or 0) - stats[c][0]) / stats[c][1] for c in CM.CATS)
    kept.sort(key=lambda k: -z(k[2]))
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
                {c: sum(v) / len(v) for c, v in cw.items()})

    pre = sorted(((sim(n, PRE_ITERS)[0], n, t) for n, t, _ in top), reverse=True)[:6]
    print("🔴 최종 후보는 %d시행으로 **다시** 잰다 (승자의 저주)\n" % ITERS)
    out = []
    for _, names, tot in pre:
        mean, mn, cats, cw = sim(names, ITERS)
        below = sorted([c for c, v in cw.items() if v < 0.5], key=lambda c: cw[c])
        out.append({"names": list(names), "total": tot, "reserve": BUDGET - tot,
                    "mean": round(mean, 4), "min": round(mn, 4), "cats": round(cats, 2),
                    "below_50": below, "cat_win": {c: round(v, 3) for c, v in cw.items()}})
        print("  $%-4d 예비$%-3d %5.1f%% / %5.1f%%  %4.2f캣  50%%미만 %d개 %-22s  %s"
              % (tot, BUDGET - tot, 100 * mean, 100 * mn, cats, len(below),
                 ",".join(below) or "없음",
                 " · ".join(n.split()[-1] for n in names)))
    out.sort(key=lambda r: (len(r["below_50"]), -r["mean"]))
    json.dump({"seed": SEED, "iterations": ITERS, "banned": sorted(BAN),
               "question": "Jokić 없이 c2 의 모양(50% 미만 0개)을 만들 수 있는가",
               "candidates": out},
              io.open(f"{BASE}/data/c2_shape_search.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/c2_shape_search.json 기록 (탐색 산출물)")


if __name__ == "__main__":
    main()
