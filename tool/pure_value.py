#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""순수가치 × GP 벌점 — 세 판본을 나란히 낸다 (43차).

🔴 **사전 등록은 `docs/14-gp-penalty-preregistration.md` 이고 측정 전에 커밋됐다.**
   형태·규칙·채택 기준을 여기서 바꾸지 마라. 바꾸려면 그 문서를 먼저 고치고 이유를 적어라.

## 왜 — 사용자 지시
> *"스탯 기반으로 순수가치 측정하고 GP로 벌점 주는 구조가 맞을 것 같음."*

현행 `value_model.contrib()` 는 `경기당 × GP/82` 를 **먼저 곱하고 그 다음 z 표준화**한다.
그래서 σ 에 **실력 분산과 출장 분산이 섞인다.** GP 가 값 전체에 퍼져 있어
「싼 이유가 실력인가 출장인가」를 분리할 수 없다.

## 세 판본
```
현행(cur)  z(경기당 × a) 합산                          GP 가 z 표준화 **안쪽**
변형 B     v_pure·a + **v_empty**·(1−a)               칸이 빈다
변형 A     v_pure·a + **v_repl(원형)**·(1−a)          교체 가능
```

🔴 **구현 정정 (측정 중 발견 · 2026-09-09)** — 처음에 B 를 `v_pure·a` 로 썼는데 **틀렸다.**
   그건 `v_absence = 0` 이고 **z=0 은 「지명 풀 평균 선수」**다 — 빈 칸이 아니다.
   실제 빈 칸(0 생산)의 z 합은 **−12.70** 이라, `v_pure·a` 는 빈 칸보다 **12.7 z 후하다.**
   그렇게 두면 **결장이 거의 공짜**가 되어 B 가 「무크레딧」이 아니라 최대 크레딧이 된다.
   → `v_empty` 를 실제로 계산해 쓴다. 사전 등록의 **형태는 안 바꿨다**
     (`v_pure·a + v_absence·(1−a)`) — 「크레딧 없음」의 뜻을 고친 것이다.
⚠️ **B 는 현행과 같은 값이 아니다.** 표준화 모집단이 달라 z 의 의미가 다르다.
   세 판본을 다 내야 「표준화 변경」과 「크레딧 도입」의 효과가 분리된다.

## v_repl 은 **발명하지 않고 잰다**
`docs/05 §6c` 가 원형별 FA 깊이를 실측해 뒀다(3PM 25 · STL 20 · OREB·BLK 7 …).
깊이(N명)를 벌점으로 바꾸는 사상함수를 만들면 **그 사상이 발명**이 된다.
대신 **깊이의 원인을 직접 잰다** — 「그 원형 FA 가 실제로 무엇을 주는가」.
그러면 §6c 결론이 자동으로 나온다: 깊은 원형은 v_repl 이 높아 벌점이 가볍고,
얇은 원형은 낮아 가혹하다.

⚠️ **크레딧이 항상 맞는 것은 아니다** — `docs/01:306-312`:
   스트리밍(빈 칸 회전)은 벤치 2칸이라 **불가**하고, 교체(드롭 후 줍기)만 가능하다.
   즉 **장기 결장**은 v_repl 이 맞고 **산발 결장**은 칸이 빌 뿐이라 크레딧 0 이 맞다.
   결장 형태 실측은 게임로그가 필요해 26일 안에 할 일이 아니다 → **두 극단(A·B)을 다 낸다.**

실행:  python3 tool/pure_value.py        → data/pure_value.json
"""
import csv, io, json, os, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import value_model as VM

V_EMPTY = 0.0   # main 에서 계산 — 빈 칸(0 생산)의 z 합

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
F = VM.F
CATS = VM.CATS
RATE = VM.RATE
CB = VM.CB

# ── §6c 원형 필터. **그 문서와 같은 값을 쓴다** — 여기서 새로 정하지 않는다.
FA_MIN_GP, FA_MIN_MPG = 30, 15
ARCH = [
    ("OREB·BLK 빅", lambda r: r["OREB"] >= 2.0 and r["BLK"] >= 0.8),
    ("고FG% 저볼륨 빅", lambda r: r["FG%"] >= 0.58 and r["FTA"] <= 2.5),
    ("REB 공급", lambda r: r["REB"] >= 7.0),
    ("STL 가드", lambda r: r["STL"] >= 1.2),
    ("3PM 다트", lambda r: r["3PM"] >= 1.8 and r["3P%"] >= 0.36),
]


def _f(d, k):
    try:
        return float(d.get(k) or 0)
    except (TypeError, ValueError):
        return 0.0


def fa_rows():
    """풀 밖 FA 후보. §6c 와 같은 모집단·같은 필터."""
    rows = list(csv.DictReader(io.open(
        f"{BASE}/data/stats_2025_26/bbref/2025-26_per_game.csv", encoding="utf-8")))
    out = []
    for r in rows:
        if r["name"] in PL:
            continue
        if _f(r, "GP") < FA_MIN_GP or _f(r, "MPG") < FA_MIN_MPG:
            continue
        out.append({k: _f(r, k) for k in
                    ("GP", "MPG", "PTS", "REB", "OREB", "AST", "STL", "BLK", "TOV",
                     "FGA", "FG%", "3PM", "3PA", "3P%", "FTA", "FT%")} | {"name": r["name"]})
    return out


def per_game_contrib(r, cat):
    """**경기당** 기여. GP 를 섞지 않는다 — 그것이 이 판본의 요점이다.

    ⚠️ 비율캣의 시도량 가중은 **유지**한다(사전 등록 §2). 시도량은 실력의 일부이고
       출장률이 아니다 — 저볼륨 고효율 선수를 잘못 잡는 것을 막는다(13차 패턴 ③)."""
    if cat == "A/T":
        return r.get("at_marginal_lift")
    if cat in RATE:
        v, a = r.get(cat), r.get(RATE[cat])
        if v is None or a is None:
            return None
        return (v - CB[cat]["baseline_per_game"]) * a
    v = r.get(cat)
    if v is None:
        return None
    return -v if cat in VM.LOWER else v


def dd_of(r):
    import cat_model as CM
    return CM.dd_game_prob(r.get("PTS"), r.get("REB"), r.get("AST"))


def build():
    pool = [p["name"] for p in VM.pool()]

    # ── z 척도: 지명 풀 126명의 **경기당** 기여로 평균·표준편차 (사전 등록 규칙 5)
    stats = {}
    for cat in CATS:
        v = [per_game_contrib(F[n], cat) for n in pool if n in F]
        v = [x for x in v if x is not None]
        stats[cat] = (st.mean(v), st.pstdev(v) or 1.0)

    def z_of(row):
        tot, per = 0.0, {}
        for cat in CATS:
            x = per_game_contrib(row, cat)
            if x is None:
                continue
            m, sd = stats[cat]
            zz = (x - m) / sd
            per[cat] = round(zz, 3)
            tot += zz
        return tot, per

    # ── 우리 174명의 v_pure
    V = {}
    for n, r in F.items():
        if n not in PL:
            continue
        tot, per = z_of(r)
        V[n] = {"v_pure": round(tot, 3), "z": per}

    # ── FA 대체 수준 (원형별) — **같은 z 척도**로 환산한다
    fas = fa_rows()
    for r in fas:
        r["DD"] = dd_of(r)
        r["at_marginal_lift"] = (r["AST"] / r["TOV"] - CB["A/T"]["baseline_per_game"]) \
            if r["TOV"] else None
        r["v_pure"] = z_of(r)[0]
    arch_pool = {}
    for label, fn in ARCH:
        sel = [r for r in fas if fn(r)]
        arch_pool[label] = {
            "n": len(sel),
            "v_repl_median": round(st.median([r["v_pure"] for r in sel]), 3) if sel else None,
            "v_repl_max": round(max([r["v_pure"] for r in sel]), 3) if sel else None,
            "examples": [r["name"] for r in sorted(sel, key=lambda x: -x["v_pure"])[:3]],
        }
    arch_pool["(원형 없음)"] = {
        "n": len(fas),
        "v_repl_median": round(st.median([r["v_pure"] for r in fas]), 3),
        "v_repl_max": round(max([r["v_pure"] for r in fas]), 3),
        "examples": [r["name"] for r in sorted(fas, key=lambda x: -x["v_pure"])[:3]],
    }

    # ── 우리 선수의 원형 배정: 여러 개면 **FA 가 가장 얇은 쪽** (사전 등록 규칙 3)
    order = sorted([l for l, _ in ARCH], key=lambda l: arch_pool[l]["n"])
    for n in V:
        r = F[n]
        row = {"OREB": r.get("OREB") or 0, "BLK": r.get("BLK") or 0,
               "FG%": r.get("FG%") or 0, "FTA": r.get("FTA") or 0,
               "REB": r.get("REB") or 0, "STL": r.get("STL") or 0,
               "3PM": r.get("3PM") or 0, "3P%": r.get("3P%") or 0}
        hit = [l for l, fn in ARCH if fn(row)]
        V[n]["archetype"] = next((l for l in order if l in hit), "(원형 없음)")
    return V, arch_pool, stats


def censored_flags():
    """절단 판정 — **GP 를 바꾸지 않는다.** 드러내기만 한다(사전 등록 §3).

    판정: 그 시즌 GP 가 **완주 하한(58 = 82×0.7)** 아래이고, 그것이 그 선수의
    **다른 시즌보다 크게 낮으면** 절단으로 본다. 두 시즌 다 낮으면 「추정 불가」.
    ⚠️ 이것은 **부상 이력 조회가 아니라 형태 판정**이다. 오분류가 있을 수 있고,
       그래서 GP 를 고치지 않고 **필드로만** 남긴다."""
    FULL = 58
    out = {}
    for n, p in PL.items():
        ms = p.get("measured_source") or {}
        ss = ms.get("seasons") or {}
        g25 = (ss.get("2025-26") or {}).get("GP")
        g24 = (ss.get("2024-25") or {}).get("GP")
        c25 = g25 is not None and g25 < FULL
        c24 = g24 is not None and g24 < FULL
        both = c25 and c24
        out[n] = {"gp_2025_26": g25, "gp_2024_25": g24,
                  "censored_2025_26": c25, "censored_2024_25": c24,
                  "both_censored": both,
                  "gp_estimable": not both,
                  "why": ("두 시즌 다 완주 하한(%d) 아래 — **GP 추정 불가**. "
                          "점 추정을 만들지 않는다" % FULL) if both else
                         ("한 시즌만 절단 — 나머지 시즌이 기준을 준다" if (c25 or c24)
                          else "절단 없음")}
    return out


def main():
    V, arch_pool, _stats = build()
    # 🔴 빈 칸의 z — 0 생산. **z=0 이 아니다**(그건 풀 평균이다).
    global V_EMPTY
    V_EMPTY = sum((0.0 - _stats[c][0]) / _stats[c][1] for c in CATS)
    cens = censored_flags()
    pool = [p["name"] for p in VM.pool()]
    old, _repl_old = VM.values()

    rows = {}
    for n, d in V.items():
        gp = ((PL[n].get("measured_source") or {}).get("GP")) or 0
        a = gp / 82.0
        arch = d["archetype"]
        vr = arch_pool[arch]["v_repl_median"]
        vr = min(vr, d["v_pure"]) if vr is not None else 0.0     # 규칙 4
        # 규칙: 두 시즌 다 절단이면 **크레딧 없음** (a 가 「추정 불가」다)
        # 🔴 두 시즌 다 절단이면 `a` 자체가 「추정 불가」다.
        #   사전 등록은 **「점이 아니라 밴드로 처리」**였는데 처음 구현이 v_empty 라는
        #   **가장 가혹한 점**을 골랐다 — 그건 밴드가 아니라 또 다른 가짜 확신이다.
        #   → 점을 만들지 않고 **밴드**를 낸다: 낙관 = 건강한 시즌 GP, 비관 = 현행 혼합 GP.
        #   대표값은 밴드 중앙을 쓰되 **`gp_estimable=False` 로 표시**해 화면이 밴드로 읽게 한다.
        if cens[n]["both_censored"]:
            g_hi = max(x for x in (cens[n]["gp_2024_25"], cens[n]["gp_2025_26"]) if x is not None)
            a_hi = g_hi / 82.0
            band = (round(d["v_pure"] * a + vr * (1 - a), 3),
                    round(d["v_pure"] * a_hi + vr * (1 - a_hi), 3))
            credit = None
        else:
            band = None
            credit = vr * (1 - a)
        rows[n] = {"v_pure": d["v_pure"], "a": round(a, 4), "archetype": arch,
                   "v_repl": vr, "v_empty": round(V_EMPTY, 3), "gp": gp,
                   "B": round(d["v_pure"] * a + V_EMPTY * (1 - a), 3),
                   "A": (round(sum(band) / 2, 3) if band else
                         round(d["v_pure"] * a + credit, 3)),
                   "A_band": band,
                   "cur_z": old[n]["z_total"] if n in old else None,
                   "gp_estimable": cens[n]["gp_estimable"]}

    def dollars(key):
        """달러 환산 — 현행과 **같은 레시피**. 총액 보존을 확인한다(사전 등록)."""
        zs = sorted((rows[n][key] for n in pool if n in rows), reverse=True)
        repl = zs[min(len(zs) - 1, VM.DRAFTED - 1)]
        disc = VM.BUDGET - VM.DRAFTED * 1
        above = {n: max(0.0, rows[n][key] - repl) for n in rows}
        tot = sum(above[n] for n in pool if n in above) or 1.0
        return ({n: int(round(1 + (above[n] / tot) * disc)) for n in rows},
                round(repl, 3), round(sum(above[n] for n in pool if n in above), 3))

    dA, replA, sumA = dollars("A")
    dB, replB, sumB = dollars("B")
    for n in rows:
        rows[n]["dollar_A"] = dA[n]
        rows[n]["dollar_B"] = dB[n]
        rows[n]["dollar_cur"] = old[n]["value"] if n in old else None

    # 총액 보존 확인 — 지명 풀 126명 합계가 $2,800 이어야 한다
    def budget_check(dv):
        return sum(dv[n] for n in pool if n in dv)

    out = {
        "generated_by": "tool/pure_value.py",
        "prereg": "docs/14-gp-penalty-preregistration.md (측정 전 커밋 a6b0535 · 수정 7ee33a7)",
        "variants": {
            "cur": "z(경기당 × a) 합산 — 현행. GP 가 z 표준화 안쪽",
            "B": "v_pure·a + v_empty·(1−a) — 칸이 빈다",
            "A": "v_pure·a + v_repl(원형)·(1−a) — 교체 가능",
        },
        "v_empty": None,   # main 에서 채운다
        "v_empty_note": ("빈 칸(0 생산)의 z 합. 🔴 **z=0 이 아니다** — z=0 은 지명 풀 "
                         "평균 선수다. 처음에 B 를 v_pure·a 로 쓴 것이 그 혼동이었고, "
                         "그러면 결장이 빈 칸보다 12.7 z 후해져 **거의 공짜**가 된다."),
        "archetype_fa": arch_pool,
        "budget_check": {"pool_n": len(pool),
                         "sum_dollar_A": budget_check(dA), "sum_dollar_B": budget_check(dB),
                         "sum_dollar_cur": budget_check({n: old[n]["value"] for n in old}),
                         "target": VM.BUDGET,
                         "replacement_A": replA, "replacement_B": replB},
        "censoring": cens,
        "players": rows,
    }
    out["v_empty"] = round(V_EMPTY, 3)
    json.dump(out, io.open(f"{BASE}/data/pure_value.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("원형별 FA 대체 수준 (§6c 모집단 · GP≥%d · MPG≥%d)" % (FA_MIN_GP, FA_MIN_MPG))
    print("%-18s %5s %11s %10s  %s" % ("원형", "FA수", "v_repl중앙", "v_repl최대", "상위 예"))
    for l in sorted(arch_pool, key=lambda x: arch_pool[x]["n"]):
        d = arch_pool[l]
        print("%-18s %5d %11s %10s  %s" % (
            l, d["n"], d["v_repl_median"], d["v_repl_max"], ", ".join(d["examples"][:2])))
    print()
    print("총액 보존 (지명 풀 126명 달러 합 · 목표 $%d)" % VM.BUDGET)
    print("  현행 $%d · 변형 B $%d · 변형 A $%d"
          % (out["budget_check"]["sum_dollar_cur"], budget_check(dB), budget_check(dA)))
    print("  대체 수준 z: A %.3f · B %.3f" % (replA, replB))
    nb = sum(1 for n in cens if cens[n]["both_censored"])
    print("\n🔴 두 시즌 다 절단(GP 추정 불가): %d명 — %s"
          % (nb, ", ".join(sorted(n for n in cens if cens[n]["both_censored"]))[:200]))
    print("\ndata/pure_value.json 기록")


if __name__ == "__main__":
    main()
