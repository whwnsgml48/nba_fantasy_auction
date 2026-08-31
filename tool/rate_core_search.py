#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""저분산(비율) 캣 집중 코어 탐색 — 새 관점 (40차 · 사용자 요청 · 탐색만).

가설
  `matchup_sim.py` 머리말: **같은 3% 마진이 캣에 따라 승률 52%~66%다**
  (FT% σ 5.2% vs DD σ 47.8%). 저분산 캣은 작은 우위가 거의 확정 승리로 바뀌고,
  고분산 캣은 큰 우위를 줘도 동전던지기라 돈이 샌다.
  → **비율캣(FT%·FG%·3P%)·A/T·TOV 에 돈을 몰고 누적캣은 싼 몸으로 때운다.**

  그리고 지금 7코어가 전부 반대 모양이다 — REB·OREB·DD 를 다 이기고
  FT%·3PM·TOV 를 다 진다. **빈 구역이 하나 있고 아무도 안 간다.**

🔴 지시받은 난점과, 재 보니 그것이 절반만 맞다는 것
  지시: "싼 몸은 대부분 FT% 가 참혹한 빅맨이라 「싸게 메운다」와 「비율캣을 이긴다」가
        정면으로 싸운다."
  실측: **FT% 에만 맞다.** 비율캣은 볼륨 가중 `(값−기준)×시도량` 인데,
        싼 빅은 FG% 에서 크게 벌고 FT% 에서 잃어 **순합이 양수**인 경우가 많다.
          Kalkbrenner $1-3   FT −11.7  FG +93.9  →  순 +79.1
          Ayton      $3-7    FT −21.2  FG +110.6 →  순 +86.5
          Gobert     $4-12   FT −76.5  FG +116.0 →  순 +37.4   ← FTA 3.9 라 손실이 크다
          Clingan    $8-16   FT −29.7  FG +26.4  →  순 −12.2   ← 유일하게 음수
  즉 **FG% 는 싼 빅이 최대 공급원**이고, 진짜 비싼 것은 **FT% 와 3P%** 다.
  그래서 필러 기준을 「FT% 가 높은가」가 아니라 **「FTA 가 작은가」** 로 둔다.
  3PA 0 인 선수는 3P% 를 **안 깎는다** — 「포기」와 「안 건드림」은 다르다.

⚠️ 탐색만 한다. cores.json 에 쓰지 않는다.
"""
import json, io, os, sys, random, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import real_opponents as RO
import pos_elig as PE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS = 20261020, 4000
PRE_ITERS = 800                    # 프리필터용 — 최종 후보는 다시 잰다
BUDGET, RESERVE_FLOOR, FILLER_CAP = 200, 12, 5
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
B = CM.baselines()


def rate_contrib(n):
    """비율캣 3종의 볼륨 가중 기여. 양수 = 팀 비율을 끌어올린다."""
    r = CM.F.get(n)
    if not r:
        return None
    av = CM.avail(r)
    out = {}
    for c, at in CM.RATE.items():
        out[c] = 0.0 if (r.get(c) is None or r.get(at) is None) \
            else (r[c] - B[c]) * r[at] * av * 100
    return out


def at_contrib(n):
    """A/T·TOV — 저분산 캣 나머지 둘. AST·TOV 절대량으로 본다."""
    r = CM.F.get(n)
    if not r or r.get("AST") is None or r.get("TOV") is None:
        return (0.0, 0.0)
    av = CM.avail(r)
    return (r["AST"] * av, r["TOV"] * av)


def price(n):
    """계획가 = 시장 중간값(정수). 상한은 my_max."""
    p = PL[n]
    return max(1, round((p["market_low"] + p["market_high"]) / 2))


def buildable(names):
    """9인이 포지션 이분매칭으로 채워지는가 + C 자격 2명 이상."""
    ps = [PL[n] for n in names]
    if len(PE.match(ps) or []) != len(PE.ROSTER_SLOTS):
        return False
    return sum(1 for p in ps if "C" in PE.elig(p)) >= 2


def main():
    REAL, _ = RO.build()
    pool = [n for n, p in PL.items()
            if not p.get("injury_exclude") and n in CM.F and p.get("value_reference")]

    # ── 후보군 ────────────────────────────────────────────────────────
    scored = []
    for n in pool:
        rc = rate_contrib(n)
        if rc is None:
            continue
        ast, tov = at_contrib(n)
        r = CM.F[n]
        scored.append({
            "n": n, "price": price(n), "mx": PL[n]["my_max"],
            "rate": sum(rc.values()), "ft": rc["FT%"], "tp": rc["3P%"], "fg": rc["FG%"],
            "ast": ast, "tov": tov,
            "fta": r.get("FTA") or 0, "tpa": r.get("3PA") or 0,
            "cnt": sum((r.get(c) or 0) * CM.avail(r) for c in ("REB", "OREB", "BLK", "STL")),
        })
    for s in scored:
        s["rate_per_$"] = s["rate"] / max(1, s["price"])

    # 집중군: 비율캣 기여 상위 · A/T 기여자 포함
    focus = sorted(scored, key=lambda s: -s["rate"])[:26]
    focus += [s for s in sorted(scored, key=lambda s: -(s["ast"] / max(0.1, s["tov"])))[:10]
              if s not in focus]
    # 필러군: **계획가 ≤ $5** (사용자 하드 제약 · 2026-08-31)
    # 🔴 선정 기준이 「최고」가 아니라 **「흔함」**이다 — 다치면 버리고 FA 에서 줍는
    #   전제이므로, 가치는 그 선수가 아니라 **그 원형이 얼마나 흔한가**에 있다.
    #   같은 값이면 대체재가 많은 쪽. FA 깊이는 아래 fa_depth() 로 실측한다.
    filler = [s for s in scored if s["price"] <= FILLER_CAP]
    filler = sorted(filler, key=lambda s: -(s["rate"] * 0.5 + s["cnt"] * 8))[:16]

    print("집중군 %d명 · 필러군 %d명" % (len(focus), len(filler)))
    print("  집중 상위 8:", ", ".join("%s $%d(%.0f)" % (s["n"].split()[-1], s["price"], s["rate"])
                                     for s in focus[:8]))
    print("  필러 상위 8:", ", ".join("%s $%d(비율%.0f 누적%.0f)"
                                     % (s["n"].split()[-1], s["price"], s["rate"], s["cnt"])
                                     for s in filler[:8]))

    # ── 조립 ──────────────────────────────────────────────────────────
    # 집중 5 + 필러 4 · 예산·자격 통과만 남긴다.
    by = {s["n"]: s for s in scored}
    combos, seen = [], set()
    for f5 in itertools.combinations([s["n"] for s in focus[:12]], 5):
        c5 = sum(by[n]["price"] for n in f5)
        if c5 > BUDGET - RESERVE_FLOOR - 4:
            continue
        rest = BUDGET - RESERVE_FLOOR - c5
        for f4 in itertools.combinations([s["n"] for s in filler[:11]], 4):
            if len(set(f5) | set(f4)) != 9:
                continue
            tot = c5 + sum(by[n]["price"] for n in f4)
            if tot > BUDGET - RESERVE_FLOOR:
                continue
            names = tuple(sorted(f5 + f4))
            if names in seen:
                continue
            seen.add(names)
            if not buildable(names):
                continue
            combos.append((names, tot))
    print("\n제약 통과 조합 %d개" % len(combos))
    if not combos:
        print("🔴 조립 가능한 조합이 0개다 — 실패 지점: 예산/자격")
        return

    # 프리필터 — cat_model 로 저분산 캣 마진 합이 큰 순
    def rate_margin(names):
        cm, _, _, _ = CM.evaluate(list(names), B)
        return sum((cm.get(c) or 0) for c in ("FT%", "FG%", "3P%")) \
            + 40 * (cm.get("A/T") or 0) + 8 * (cm.get("TOV") or 0)
    combos.sort(key=lambda x: -rate_margin(x[0]))
    top = combos[:24]

    def sim(names, iters):
        MS._URATE.clear()
        wr = [MS.simulate(list(names), REAL[m], random.Random(SEED), iters) for m in REAL]
        MS._URATE.clear()
        return (sum(w["weekly_win_rate"] for w in wr) / len(wr),
                min(w["weekly_win_rate"] for w in wr),
                sum(w["expected_cats_won"] for w in wr) / len(wr))

    print("프리필터 상위 %d개를 %d시행으로 좁힌다" % (len(top), PRE_ITERS))
    pre = sorted(((sim(n, PRE_ITERS)[0], n, t) for n, t in top), reverse=True)[:6]
    print("🔴 최종 후보는 %d시행으로 **다시** 잰다 (34차 승자의 저주)" % ITERS)
    print("\n  %-6s %-6s %-7s %-7s  %s" % ("총액", "예비", "평균", "최저", "로스터"))
    final = []
    for _, names, tot in pre:
        mean, mn, cats = sim(names, ITERS)
        final.append({"names": list(names), "total": tot, "reserve": BUDGET - tot,
                      "mean": round(mean, 4), "min": round(mn, 4), "cats": round(cats, 2)})
        print("  $%-5d $%-5d %6.1f%% %6.1f%%  %s"
              % (tot, BUDGET - tot, 100 * mean, 100 * mn,
                 " · ".join(n.split()[-1] for n in names)))
    final.sort(key=lambda r: -r["mean"])
    json.dump({"seed": SEED, "iterations": ITERS, "candidates": final},
              io.open(f"{BASE}/data/rate_core_search.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/rate_core_search.json 기록 (탐색 산출물 — cores.json 은 안 건드린다)")


if __name__ == "__main__":
    main()
