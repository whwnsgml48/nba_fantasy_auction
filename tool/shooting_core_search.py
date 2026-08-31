#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""슈팅캣(3PM·3P%·FT%) 코어 탐색 — 3회차 · 마지막 (40차 · 탐색만).

사용자 질문
  「3PM·3P%·FT% 를 7코어가 공통으로 다 버리는데, 이걸 챙기는 로스터는 없나.」
  실제로 7코어 전부가 그 셋을 진다. **REB·OREB·DD 를 포기한 코어가 하나도 없다.**

🔴 참고값으로 쓸 뻔한 것의 함정 (기록)
  `matchup_sim.guard_stack` 을 후보로 놓고 재니 71.8%(합법화 76.9%)였는데,
  **그것을 문턱으로 삼으면 안 된다.** 이유 셋:
    ① 목적함수가 질문과 다르다 — GUARD = AST·STL·3PM·FT%·A/T·3P% (가드 캣 **전반**)
       이라 D.Mitchell·Rollins 처럼 슈팅과 무관한 이름이 들어간다
    ② `z()` 가 **정규화 없이 캣 z 를 더한다**(그 함수 주석: "조립용 거친 점수")
       → 스케일 큰 캣이 지배한다. **1차 탐색이 FG% 에 하이재킹된 것과 같은 구조다**
    ③ 조립 불가 로스터였다(PF 자격 0명 · 매칭 0/9) · 예산 $201 초과 · 미조정
  그래서 이 스크립트는 **z() 를 쓰지 않고** 캣별 표준화를 직접 한다.

🔴 찾는 것은 승률이 아니라 **여유**다 (조율 세션 사전 등록)
  주간 승률 = P(승리 캣 ≥ 7) 이므로 기대값과 분산이 함께 정한다.
    84% 에 필요한 여유/SD ≈ 0.78 (c4 수준)
    슈팅형 SD ≈ 1.85 — 상대도 쏘므로 낮추기 어렵다
    → 필요한 기대 캣 = 7 + 0.78 × 1.85 = **8.44**
  기대 캣 ≥ 8.44 채택 검토 · 8.2~8.44 천장 · < 8.2 구조적.

설계
  포기 선언   REB · OREB · BLK · DD · FG%
  목표        3PM · 3P% · FT% + PTS · AST · STL · TOV · A/T  (여덟 — 8 ≥ 7 이라 성립 가능)
  하한        cat_model 마진에서 3PM·3P%·FT% **셋 다 양수** (캣별. 합산 금지)
  정규화      프리필터에서 캣별 **표준화** 후 합산
  제약        가정 노출 ≤ 1명 · pos_elig 매칭 성립 · C 자격 ≥ 2 · 예산 ≤ $200
  ⚠️ Jokić 허용 — 금지하면 2차(「Jokić 없는 c2」)를 반복한다. 다만 **그가 뽑히면
     결과는 c2 의 변형**이고 그때 답은 「새 코어」가 아니라 「c2 가 이미 그 답이다」다.
"""
import json, io, os, sys, random, itertools, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import real_opponents as RO
import pos_elig as PE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS, PRE_ITERS = 20261020, 4000, 800
BUDGET, RESERVE_FLOOR = 200, 12
SHOOT = ("3PM", "3P%", "FT%")
TARGET = ("3PM", "3P%", "FT%", "PTS", "AST", "STL", "TOV", "A/T")
PUNT = ("REB", "OREB", "BLK", "DD", "FG%")
MAX_SHAKY = 1
NEED_CATS = 8.44
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

    shooters, bigs = [], []
    for n in pool:
        r = CM.F[n]
        av = CM.avail(r)
        pr = price(n)
        tp = ((r.get("3P%") or 0) - B["3P%"]) * (r.get("3PA") or 0) * av * 100
        ft = ((r.get("FT%") or 0) - B["FT%"]) * (r.get("FTA") or 0) * av * 100
        tpm = (r.get("3PM") or 0) * av
        e = PE.elig(PL[n])
        sc = tp + ft + 30 * tpm
        if sc > 20:
            shooters.append((n, pr, sc, sorted(e)))
        # 빅 자리(PF·C)를 채우되 슈팅을 **덜 깎는** 쪽 — 1차의 교훈
        if ("PF" in e or "C" in e) and pr <= 12 and (tp + ft) > -20:
            bigs.append((n, pr, tp + ft, sorted(e)))
    shooters.sort(key=lambda x: -x[2] / max(1, x[1]))
    bigs.sort(key=lambda x: -x[2])
    S = [s[0] for s in shooters[:20]]
    G = [b[0] for b in bigs[:14]]
    print("슈터 %d · 빅(슈팅 비파괴) %d" % (len(S), len(G)))
    print("  슈터:", ", ".join("%s $%d" % (s[0].split()[-1], s[1]) for s in shooters[:10]))
    print("  빅  :", ", ".join("%s $%d" % (b[0].split()[-1], b[1]) for b in bigs[:10]))

    combos, seen = [], set()
    for s6 in itertools.combinations(S[:15], 6):
        if sum(1 for n in s6 if shaky(n)) > MAX_SHAKY:
            continue
        cs = sum(price(n) for n in s6)
        if cs > BUDGET - RESERVE_FLOOR - 3:
            continue
        for g3 in itertools.combinations(G[:12], 3):
            names = tuple(sorted(set(s6 + g3)))
            if len(names) != 9 or names in seen:
                continue
            if sum(1 for n in names if shaky(n)) > MAX_SHAKY:
                continue
            tot = cs + sum(price(n) for n in g3)
            if tot > BUDGET - RESERVE_FLOOR:
                continue
            seen.add(names)
            if not legal(names):
                continue
            combos.append((names, tot))
    print("\n제약 통과 조합 %d개" % len(combos))
    if not combos:
        print("🔴 0개 — 실패 지점: 예산/자격/가정노출")
        return

    kept = []
    for names, tot in combos:
        cm, _, _, _ = CM.evaluate(list(names), B)
        if all((cm.get(c) or 0) > 0 for c in SHOOT):
            kept.append((names, tot, cm))
    print("슈팅 3캣 마진 전부 양수: %d개" % len(kept))
    if not kept:
        print("🔴 슈팅 3캣을 동시에 이기는 조합이 0개 — 이 자체가 결과다")
        return

    # 🔴 캣별 **표준화** 후 합산 (z() 를 쓰지 않는 이유가 여기다)
    stats = {}
    for c in CM.CATS:
        vs = [(k[2].get(c) or 0) for k in kept]
        stats[c] = (sum(vs) / len(vs), st.pstdev(vs) or 1.0)

    def score(cm):
        s = 0.0
        for c in CM.CATS:
            zz = ((cm.get(c) or 0) - stats[c][0]) / stats[c][1]
            s += zz * (1.5 if c in SHOOT else (1.0 if c in TARGET else 0.15))
        return s

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

    # 🔴 프리필터는 **기대 캣**으로 고른다 — 찾는 것이 여유이므로.
    pre = sorted(((sim(n, PRE_ITERS)[2], n, t) for n, t, _ in top), reverse=True)[:6]
    print("🔴 최종 후보는 %d시행으로 **다시** 잰다 (승자의 저주)\n" % ITERS)
    out = []
    for _, names, tot in pre:
        mean, mn, cats, sd, cw = sim(names, ITERS)
        below = sorted([c for c, v in cw.items() if v < 0.5], key=lambda c: cw[c])
        out.append({"names": list(names), "total": tot, "reserve": BUDGET - tot,
                    "mean": round(mean, 4), "min": round(mn, 4), "cats": round(cats, 2),
                    "cats_sd": round(sd, 2), "margin_over_sd": round((cats - 7) / sd, 2),
                    "shooting": {c: round(cw[c], 3) for c in SHOOT},
                    "shaky": [n for n in names if shaky(n)],
                    "has_jokic": "Nikola Jokić" in names,
                    "below_50": below, "cat_win": {c: round(v, 3) for c, v in cw.items()}})
        print("  $%-4d %5.1f%% %4.2f캣 SD%4.2f 여유/SD%5.2f | 3PM %4.1f 3P%% %4.1f FT%% %4.1f | 가정%d | %s"
              % (tot, 100 * mean, cats, sd, (cats - 7) / sd,
                 100 * cw["3PM"], 100 * cw["3P%"], 100 * cw["FT%"],
                 len([n for n in names if shaky(n)]),
                 " · ".join(n.split()[-1] for n in names)))
    out.sort(key=lambda r: -r["cats"])
    best = out[0]
    print("\n최고 기대 캣 %.2f · 사전 등록 문턱 %.2f → %s"
          % (best["cats"], NEED_CATS,
             "채택 검토" if best["cats"] >= NEED_CATS
             else ("천장이 여기다" if best["cats"] >= 8.2 else "구조적 — 여유를 살 수 없다")))
    json.dump({"seed": SEED, "iterations": ITERS, "punt": list(PUNT), "target": list(TARGET),
               "need_cats": NEED_CATS,
               "floors": "슈팅 3캣 마진 전부 양수 · 가정 노출 ≤ %d" % MAX_SHAKY,
               "candidates": out},
              io.open(f"{BASE}/data/shooting_core_search.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("data/shooting_core_search.json 기록")


if __name__ == "__main__":
    main()
