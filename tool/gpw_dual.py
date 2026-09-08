#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주 길이 모형 여러 세계를 **한 실행에서** 나란히 잰다 (42차 신설).

## 왜 필요한가 🔴
`cat_model` 의 종전 `GAMES_PER_WEEK = 3.299` 는 82경기를 시즌 174일에 **균일하게**
퍼뜨린 값이었다. 2026-09-07 에 사용자가 야후 스케줄 탭에서 22주 전체를 읽어 왔고,
올스타 브레이크 무경기일이 **W17 이라는 2주 매치업 안에 격리**돼 있음이 드러났다.
그러면 나머지 19개 표준 주는 그만큼 빽빽하다 — **표준 주 3.417** (종전 대비 +3.6%).

이 스크립트는 그 변경이 **결론을 바꾸는지** 판정한다. 바꾸지 않으면 안 바꾼다고 적는다.

## 세계 목록
    legacy-3.299     종전 세계. 저장된 승률이 만들어진 곳
    standard-3.417   🔴 신 기본값. 코어 비교·우승 확률의 세계
    standard-3.396   브레이크 5일 가정 (구간 하단)
    standard-3.437   브레이크 7일 가정 (구간 상단)
    mixed-3.572      22주 전체(표준 19 + W1 + W7 + W17). **시즌 서술용** — 코어 선택에 안 쓴다

## 비교 규약을 지킨다 (`matchup_sim` 상단 · 40차)
저장값에서 새 값을 빼지 않는다. **모든 세계를 같은 실행·같은 시드·같은 이름 순서로 새로 잰다.**
로스터 이름은 `sorted()` 로 정규화해 `simulate()` 를 집합의 순수 함수로 만든다.

⚠️ 완전한 대응(paired)은 아니다. 주 유형·경기수 추첨이 갈리면 **그 뒤 난수 소비가 갈라진다.**
   같은 시드는 출발점을 맞추는 것이고 몬테카를로 잡음이 상쇄된다는 보장은 없다. 그래서
   ① 상대 12팀에 대한 **차이 벡터의 SE**(상대 강약이 상쇄되는 축)와
   ② **시드 3개**를 함께 낸다. 결론은 세 시드에서 일관될 때만 쓴다.

## 🔴 사용률을 반드시 함께 재추정한다
주당 경기가 늘면 하루 경합이 심해져 선발 7칸 초과가 늘고 **사용률이 떨어진다.**
이 반작용을 빼면 「경기↑ = 분산↓ = 마진 있는 쪽 이득」만 남아 **이득이 과대평가된다.**
40차에 `lineup_feasibility.py` 가 `GAMES_PER_WEEK = 3.299` 를 **복제**해 놓아 그 재추정이
구조적으로 불가능했다(42차에 참조로 교체 · `validate.py [I39]`). 세계를 바꿀 때마다
`matchup_sim._URATE` · `_RND_RATE` 캐시를 비운다.

## 우승 확률 (작업 1c)
플옵 = 2027-03-15~04-04 · **3주 단판** · 14팀 중 **상위 8팀**. 우승 ≈ `p³`.
상위 8팀은 **코어 무관**으로 고정한다 — 7코어 평균에서 우리 승률이 낮은(= 상대가 강한)
8팀. 코어마다 다른 8팀을 쓰면 각 코어가 자기에게 유리한 상대를 고르는 셈이다.
⚠️ **이 지표로 코어 순위가 바뀌길 기대하지 말 것.** 상위 8은 12팀의 부분집합이고
   강약이 모든 코어에 같이 들어가므로 순위는 거의 그대로다(no-op). 넣는 이유는
   **절대값의 정직성**이다 — 「주간 승률 87%」가 아니라 「우승 확률 ~그 세제곱」이 답이다.

## 칸 비움 경계 검증
`cores.json.lineup_loss_validation_40` 의 「자격 무관 바닥 0.19%」는 **주당 경기수의 함수**다.
🔴 그 검증에는 **보존된 생성기가 없었다.** `GP = 76` 이 저장된 세 값(0.0019 · 0.2928 ·
   0.0032)을 재현하므로 그것이 암묵 값이었다고 판단하고 `FLOOR_GP` 로 명시한다. **추론이다.**

실행:  python3 tool/gpw_dual.py [iters] [seed,seed,...]
"""
import json, io, os, sys, random, statistics as st, itertools, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import lineup_feasibility as LF
import real_opponents as RO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (라벨, configure 인자, 시드 전부 돌리나)
WORLDS = [
    ("legacy-3.299",   dict(model="legacy",   flat=3.299),                 True),
    ("standard-3.417", dict(model="standard"),                             True),
    ("standard-3.396", dict(model="standard", standard_week_games=3.396),   False),
    ("standard-3.437", dict(model="standard", standard_week_games=3.437),   False),
    ("mixed-3.572",    dict(model="mixed"),                                False),
]
PRIMARY = "standard-3.417"       # 신 기본값
BASELINE = "legacy-3.299"        # 종전 세계
PLAYOFF_TEAMS = 8
FLOOR_GP = 76
ALL_SLOTS = ["PG", "SG", "SF", "PF", "C"]


def reset_caches():
    """🔴 세계를 바꿀 때마다 부른다. 사용률은 주당 경기수의 함수다."""
    MS._URATE = {}
    MS._RND_RATE = None


def synth(n, elig, gp=FLOOR_GP, off=0):
    return [{"name": "s%d" % (off + i), "pos_yahoo": list(elig),
             "measured_source": {"GP": gp}} for i in range(n)]


def floor_cases(weeks=20000):
    cases = {
        "전원 모든 칸 가능": synth(9, ALL_SLOTS),
        "C전용 3 + 만능 6": synth(3, ["C"]) + synth(6, ALL_SLOTS, off=3),
        "C전용 4 + 만능 5": synth(4, ["C"]) + synth(5, ALL_SLOTS, off=4),
        "C전용 5 + 만능 4": synth(5, ["C"]) + synth(4, ALL_SLOTS, off=5),
        "전원 C전용": synth(9, ["C"]),
        "GP82 전원 만능": synth(9, ALL_SLOTS, gp=82),
    }
    return {k: round(LF.measure(ps, weeks=weeks)[0], 4) for k, ps in cases.items()}


def measure_world(ROSTER, OPP, mgrs, rows, seed, iters, with_floor):
    cores = {}
    for cid, us in ROSTER.items():
        drop, rates, perweek = LF.measure([MS._pdict(n) for n in us])
        per = {m: MS.simulate(us, OPP[m], random.Random(seed), iters, rows) for m in mgrs}
        wr = [per[m]["weekly_win_rate"] for m in mgrs]
        cores[cid] = {
            "roster_sorted": us,
            "real_mean_win_rate": round(st.mean(wr), 4),
            "real_min_win_rate": round(min(wr), 4),
            "real_by_manager": {m: per[m]["weekly_win_rate"] for m in mgrs},
            "cat_win_probs_real_mean": {c: round(st.mean(per[m]["cat_win_probs"][c]
                                                         for m in mgrs), 4) for c in MS.CATS},
            "expected_cats_won_mean": round(st.mean(per[m]["expected_cats_won"]
                                                    for m in mgrs), 3),
            "p_big5_collapse_mean": round(st.mean(per[m]["p_big5_collapse"] for m in mgrs), 4),
            "lineup_drop_rate": round(drop, 5),
            "lineup_drop_per_week": round(perweek, 3),
            "usable_rate_mean": round(st.mean(rates.values()), 5),
            "usable_rate_min": round(min(rates.values()), 5),
            "usable_rate_min_player": min(rates, key=lambda n: rates[n]),
        }
    # ── 작업 1c: 상위 8팀 (코어 무관 고정) + p³
    strength = {m: st.mean(cores[c]["real_by_manager"][m] for c in cores) for m in mgrs}
    top8 = sorted(mgrs, key=lambda m: strength[m])[:PLAYOFF_TEAMS]   # 우리 승률 낮은 = 강한
    for cid in cores:
        w8 = [cores[cid]["real_by_manager"][m] for m in top8]
        p = st.mean(w8)
        cores[cid]["playoff_mean_win_rate"] = round(p, 4)
        cores[cid]["p_title_3wins"] = round(p ** 3, 4)
    # 코어 쌍 대응 SE
    V = {cid: [cores[cid]["real_by_manager"][m] for m in mgrs] for cid in cores}
    pairs = {}
    for a, b in itertools.combinations(sorted(cores), 2):
        d = [x - y for x, y in zip(V[a], V[b])]
        pairs["%s-%s" % (a, b)] = round(st.stdev(d) / len(mgrs) ** 0.5, 4)
    out = {"cores": cores,
           "playoff_top8": top8,
           "playoff_top8_basis": ("7코어 평균에서 우리 승률이 낮은 = 상대가 강한 8팀. "
                                  "**코어 무관 고정** — 코어마다 다른 8팀을 쓰면 각 코어가 "
                                  "자기에게 유리한 상대를 고르는 셈이다."),
           "paired_se_between_cores_median": round(st.median(pairs.values()), 4),
           "paired_se_between_cores": pairs}
    if with_floor:
        out["floor_cases"] = floor_cases()
    return out


def tiers(cores, cut):
    o = sorted(cores, key=lambda c: -cores[c]["real_mean_win_rate"])
    g = [[o[0]]]
    for a, b in zip(o, o[1:]):
        if cores[a]["real_mean_win_rate"] - cores[b]["real_mean_win_rate"] > cut:
            g.append([b])
        else:
            g[-1].append(b)
    return g


def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    seeds = ([int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2
             else [20261020, 20261021, 20270315])

    CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    REAL, RREP = RO.build()
    mgrs = sorted(REAL)
    rows = MS.pool()
    ROSTER = {co["id"]: sorted(s["candidates"][0]["name"] for s in co["slots"])
              for co in CJ["cores"]}
    OPP = {m: sorted(REAL[m]) for m in mgrs}

    print("주 길이 모형 비교 — 시행 %d · 시드 %s · 실제 상대 %d팀"
          % (iters, ",".join(str(s) for s in seeds), len(mgrs)))
    print("세계: " + " / ".join(w[0] for w in WORLDS))
    print("⚠️ 사용률을 각 세계에서 재추정 · 칸 비움 경계도 다시 잼 · 이름 순서 정규화(sorted)\n")

    res = {}
    for label, cfg, all_seeds in WORLDS:
        res[label] = {"config": CM.configure(**cfg), "by_seed": {}}
        for seed in (seeds if all_seeds else seeds[:1]):
            t0 = time.time()
            CM.configure(**cfg)
            reset_caches()
            res[label]["by_seed"][str(seed)] = measure_world(
                ROSTER, OPP, mgrs, rows, seed, iters, with_floor=(seed == seeds[0]))
            print("  %-16s seed %d 완료 (%.0fs)" % (label, seed, time.time() - t0))

    # ── 헤드라인 표: PRIMARY 세계 · 시드 평균
    def avg_over_seeds(label, cid, key):
        v = [res[label]["by_seed"][s]["cores"][cid][key] for s in res[label]["by_seed"]]
        return st.mean(v)

    print("\n=== 🔴 헤드라인: %s (신 기본값 · 코어 비교·우승 확률의 세계) ===" % PRIMARY)
    ns = len(res[PRIMARY]["by_seed"])
    h = f"{'코어':<5}{'12팀평균':>10}{'시드폭':>8}{'상위8팀':>9}{'p³(우승)':>10}{'기대캣':>8}{'사용률':>9}{'칸비움':>8}"
    print(h); print("-" * len(h))
    for cid in sorted(ROSTER, key=lambda c: -avg_over_seeds(PRIMARY, c, "real_mean_win_rate")):
        sv = [res[PRIMARY]["by_seed"][s]["cores"][cid]["real_mean_win_rate"]
              for s in res[PRIMARY]["by_seed"]]
        f = res[PRIMARY]["by_seed"][str(seeds[0])]["cores"][cid]
        print("%-5s%9.1f%%%7.2f%%p%8.1f%%%9.1f%%%8.2f%9.4f%7.3f%%" % (
            cid, 100 * st.mean(sv), 100 * (max(sv) - min(sv)),
            100 * avg_over_seeds(PRIMARY, cid, "playoff_mean_win_rate"),
            100 * avg_over_seeds(PRIMARY, cid, "p_title_3wins"),
            avg_over_seeds(PRIMARY, cid, "expected_cats_won_mean"),
            f["usable_rate_mean"], 100 * f["lineup_drop_rate"]))
    print("  상위 8팀(고정): " + ", ".join(
        res[PRIMARY]["by_seed"][str(seeds[0])]["playoff_top8"]))

    # ── 세계 간 비교
    print("\n=== 세계 간 코어 승률 (12팀 평균 · 시드 평균) ===")
    labels = [w[0] for w in WORLDS]
    h2 = f"{'코어':<5}" + "".join(f"{l.replace('standard-','s').replace('legacy-','L').replace('mixed-','M'):>10}" for l in labels)
    print(h2); print("-" * len(h2))
    for cid in sorted(ROSTER):
        print("%-5s" % cid + "".join(
            "%9.1f%%" % (100 * avg_over_seeds(l, cid, "real_mean_win_rate")) for l in labels))

    print("\n=== 🔴 결론 후보: %s − %s (시드별 · 대응 SE) ===" % (PRIMARY, BASELINE))
    print(f"  {'코어':<5}" + "".join(f"{'seed'+str(s):>12}" for s in seeds) + f"{'평균Δ':>9}{'ΔSE':>7}{'일관':>6}")
    deltas = {}
    for cid in sorted(ROSTER):
        row, ses = [], []
        for s in seeds:
            A = res[BASELINE]["by_seed"][str(s)]["cores"][cid]["real_by_manager"]
            B = res[PRIMARY]["by_seed"][str(s)]["cores"][cid]["real_by_manager"]
            d = [B[m] - A[m] for m in mgrs]
            row.append(st.mean(d)); ses.append(st.stdev(d) / len(mgrs) ** 0.5)
        same = "○" if (all(x > 0 for x in row) or all(x < 0 for x in row)) else "✗"
        deltas[cid] = {"by_seed": [round(x, 4) for x in row],
                       "mean": round(st.mean(row), 4),
                       "se_mean": round(st.mean(ses), 4),
                       "sign_consistent": same == "○"}
        print("  %-5s" % cid + "".join("%+11.2f%%p" % (100 * x) for x in row)
              + "%+8.2f%%p%6.2f%6s" % (100 * st.mean(row), 100 * st.mean(ses), same))

    print("\n=== 동급 묶음 — 세계마다 판정이 바뀌는가 ===")
    for l in labels:
        s0 = str(seeds[0])
        C = res[l]["by_seed"][s0]["cores"]
        med = res[l]["by_seed"][s0]["paired_se_between_cores_median"]
        cut = 1.25 * med
        print("  %-16s SE %.2f 컷 %.2f  %s" % (
            l, 100 * med, 100 * cut,
            "  |  ".join(" ".join("%s %.1f" % (c, 100 * C[c]["real_mean_win_rate"])
                                  for c in g) for g in tiers(C, cut))))
    print("  ⚠️ 같은 시드 1개 기준이다. 시드 폭은 위 헤드라인 표의 '시드폭' 열을 볼 것.")

    print("\n=== 칸 비움 경계 검증 (자격 무관 바닥은 주당 경기수의 함수다) ===")
    fl = {l: res[l]["by_seed"][str(seeds[0])].get("floor_cases") for l in labels}
    ks = list(fl[PRIMARY])
    print("  %-22s" % "경우" + "".join("%10s" % l.split("-")[-1] for l in labels))
    for k in ks:
        print("  %-22s" % k + "".join("%9.2f%%" % (100 * fl[l][k]) for l in labels))

    out = {
        "generated_by": "tool/gpw_dual.py",
        "iterations": iters, "seeds": seeds, "n_opponents": len(mgrs),
        "primary_world": PRIMARY, "baseline_world": BASELINE,
        "schedule_confirmed": {
            "source": "사용자가 야후 스케줄 탭에서 22주 전체 확인 (2026-09-07)",
            "week_types": [list(t) for t in CM.WEEK_TYPES],
            "long_weeks": {"W7": "11-30~12-13 (14일 · 브레이크 없음 · 6.83경기)",
                           "W17": "02-15~02-28 (14일 중 6일 무경기 · 3.90경기)"},
            "playoffs": "W20~W22 03-15~04-04 = 21일 · **전부 표준 주** · 상위 8/14팀",
            "why_standard_is_headline": ("긴 주 2개는 전부 정규시즌 안에 있고 플옵 3주는 "
                                         "전부 표준 주다. 8/14 진출이라 정규시즌 성적은 "
                                         "사실상 공짜이므로 우승은 표준 주 세계에서 결정된다."),
            "why_old_value_was_low": ("종전 3.299 는 82경기를 시즌 174일에 균일하게 퍼뜨린 값이다. "
                                      "올스타 브레이크 무경기일이 W17 안에 격리돼 있어 나머지 19개 "
                                      "표준 주는 그만큼 빽빽하다 → 3.417 (**+3.6%**)."),
            "break_days_uncertainty": ("브레이크 정확한 일수 미확인(5~7 가정). 표준 주를 "
                                       "3.396~3.437 로 움직인다 — 창 안 총량 78.6 이 고정이라 "
                                       "구간이 좁다. 양 끝을 다 쟀다."),
        },
        "protocol": ("모든 세계를 같은 실행·같은 시드·같은 이름 순서(sorted)로 새로 잰다. "
                     "저장값에서 빼지 않는다(matchup_sim 상단 규약). 추첨이 갈리면 난수 소비가 "
                     "갈라지므로 완전한 대응은 아니다 — 상대 12팀 차이 벡터의 SE + 시드 3개로 본다."),
        "urate_note": ("🔴 사용률을 각 세계에서 재추정했다. 40차에 lineup_feasibility 가 3.299 를 "
                       "복제해 놓아 이 재추정이 구조적으로 불가능했다(42차에 참조로 교체)."),
        "floor_gp_note": ("칸 비움 경계 검증의 합성 GP=%d 는 **추론값**이다 — 40차 "
                          "lineup_loss_validation_40 에 생성기가 보존돼 있지 않고, 76 이 "
                          "저장된 세 값을 재현한다." % FLOOR_GP),
        "delta_primary_minus_baseline": deltas,
        "worlds": res,
        "real_opponents_report": RREP,
    }
    json.dump(out, io.open(f"{BASE}/data/gpw_dual.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/gpw_dual.json 기록")


if __name__ == "__main__":
    main()
