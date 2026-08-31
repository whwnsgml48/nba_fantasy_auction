#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전원 건강 세계 — 「모두 직전 온전한 시즌만큼 뛴다」면 코어 순위가 어떻게 되는가 (40차).

왜 재는가 🔴
  드래프트(2026-09-05)가 프리시즌(2026-10-06쯤)보다 4.4주 앞서 **복귀 여부를 확인할
  방법이 없다.** 그래서 사용자가 「전원 건강을 가정하고 계획한다」고 결정했다.

  그런데 **지금 데이터는 그 세계가 아니다 — 절반만 그렇다.**
    Haliburton 73.0  이미 건강 가정 (2025-26 전체 결장 → 2024-25 그대로)
    Lillard    58.0  같음
    Sabonis    55.2  🔴 2025-26 의 19경기가 섞여 있다
    Trae Young 62.1  🔴 2025-26 의 15경기가 섞여 있다
    Zubac      64.8  🔴 2025-26 의 48경기가 섞여 있다
  절반은 건강, 절반은 부상 시즌이 섞인 **혼합 세계**다. 그 위에서 내린 판정
  (특히 c5 강등)이 「전원 건강」 가정에서도 유지되는지는 **재 봐야 안다.**

이 스크립트는 `assumption_stress.py` 의 **정확히 반대 방향**이다
  그쪽:  GP × 0.74      — "이만큼 틀리면 순위가 뒤집히는가"
  이쪽:  GP → 건강값    — "전부 건강하면 순위가 어떻게 되는가"

🔴 지어내지 않는다
  「건강 GP」는 **그 선수가 실제로 뛴 직전 온전한 시즌의 출장수**다
  (`measured_source.seasons["2024-25"].GP`). 「아킬레스 복귀면 70쯤」 같은 값을
  만들지 않는다. 2024-25 기록이 없으면 **대상에서 빼고 보고**한다.

⚠️ 이것도 예측이 아니다
  "전원 건강"은 낙관적인 쪽 끝이고 실제로 그렇게 될 거라는 주장이 아니다.
  `assumption_stress` 와 **한 쌍으로** 읽어야 한다 — 두 끝 사이에 진실이 있다.

⚠️ players.json 의 GP 는 바꾸지 않는다. 측정만 하고 채택은 사람이 판정한다.
"""
import json, io, os, sys, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS
import real_opponents as RO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS, THRESH, GP_FLOOR = 20261020, 4000, 0.50, 40
HEALTHY_SEASON = "2024-25"


def healthy_gp(name):
    """대상이면 (건강GP, 사유), 아니면 (None, 사유)."""
    ms = (MS.PL.get(name) or {}).get("measured_source") or {}
    sh = ms.get("blend_share_2025_26")
    seas = ms.get("seasons") or {}
    gp25 = (seas.get("2025-26") or {}).get("GP")
    hit = (sh is not None and sh < THRESH) or (gp25 is not None and gp25 < GP_FLOOR)
    if not hit:
        return None, "대상 아님"
    gp24 = (seas.get(HEALTHY_SEASON) or {}).get("GP")
    if gp24 is None:
        return None, "🔴 %s 기록 없음 — 지어내지 않고 제외한다" % HEALTHY_SEASON
    return float(gp24), "share=%s · 25-26 GP=%s" % (sh, gp25)


def main():
    cj = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    REAL, _ = RO.build()

    def run(us, gp=None):
        """(평균, 최저, 상대별 벡터). 벡터는 **쌍별 SE** 계산에 쓴다 —
        중앙값 SE 로 비교하면 안 된다(standard_error.which_to_use)."""
        old = {}
        for n, g in (gp or {}).items():
            if n in MS.F:
                old[n] = MS.F[n]["GP"]; MS.F[n]["GP"] = g
        MS._URATE.clear()
        wr = [MS.simulate(us, REAL[m], random.Random(SEED), ITERS)["weekly_win_rate"]
              for m in REAL]
        for n, g in old.items():
            MS.F[n]["GP"] = g
        MS._URATE.clear()
        return (round(sum(wr) / len(wr), 4), round(min(wr), 4), wr)

    # ── 대상 확정 (전 코어 1순위 합집합) ──────────────────────────────
    firsts = sorted({s["candidates"][0]["name"] for co in cj["cores"] for s in co["slots"]})
    targets, excluded = {}, []
    for n in firsts:
        g, why = healthy_gp(n)
        if g is None:
            if why != "대상 아님":
                excluded.append({"player": n, "why": why})
            continue
        cur = (MS.F.get(n) or {}).get("GP")
        if cur is None:
            excluded.append({"player": n, "why": "시뮬에 GP 없음"}); continue
        targets[n] = {"from": round(cur, 1), "to": g,
                      "moved": abs(g - cur) > 0.05, "why": why}

    print("전원 건강 대상 %d명 (1순위 %d명 중)" % (len(targets), len(firsts)))
    for n, t in sorted(targets.items()):
        print("   %-22s %5.1f → %5.1f %s   %s"
              % (n, t["from"], t["to"], "" if t["moved"] else "(변화 없음)", t["why"]))
    for e in excluded:
        print("   ⊘ %-20s %s" % (e["player"], e["why"]))
    print()

    out = {"seed": SEED, "iterations": ITERS, "healthy_season": HEALTHY_SEASON,
           "share_threshold": THRESH, "gp_floor": GP_FLOOR,
           "what": ("전 코어 1순위 중 GP 가 부상 시즌에 기대는 선수(실측 비중<%.2f 또는 "
                    "2025-26 GP<%d)의 GP 를 **직전 온전한 시즌 실제 출장수**로 올리고 "
                    "실제 12팀 평균/최저 주간 승률을 다시 잰다." % (THRESH, GP_FLOOR)),
           "why": ("드래프트가 프리시즌보다 4.4주 앞서 복귀 여부를 확인할 수 없다. "
                   "사용자가 「전원 건강 가정」으로 계획하기로 했는데, **현행 데이터는 "
                   "그 세계가 아니다** — Haliburton·Lillard 만 건강 가정이고 "
                   "Sabonis·Trae·Zubac 은 부상 시즌이 섞여 있다."),
           "caveat": ("지어낸 값이 없다 — 전부 그 선수가 실제로 뛴 시즌의 출장수다. "
                      "다만 '전원 건강'은 낙관적인 쪽 끝이고 예측이 아니다. "
                      "`assumption_stress`(반대 끝)와 **한 쌍으로** 읽을 것."),
           "not_applied": "players.json 의 GP 는 바꾸지 않았다. 채택은 사람이 판정한다.",
           "targets": {n: t for n, t in sorted(targets.items())},
           "excluded": excluded, "rows": []}

    vecs = {}
    print("  %-4s %16s %16s %8s   %s" % ("코어", "기준(평균/최저)", "전원건강", "평균차", "바뀐 선수"))
    for co in cj["cores"]:
        us = [s["candidates"][0]["name"] for s in co["slots"]]
        mine = {n: targets[n]["to"] for n in us if n in targets and targets[n]["moved"]}
        b_mean, b_min, b_vec = run(us)
        h_mean, h_min, h_vec = run(us, mine) if mine else (b_mean, b_min, b_vec)
        vecs[co["id"]] = h_vec
        row = {"core": co["id"], "base": b_mean, "base_min": b_min,
               "healthy": h_mean, "healthy_min": h_min,
               "delta": round(h_mean - b_mean, 4),
               "delta_min": round(h_min - b_min, 4),
               "changed": [{"player": n, "gp": targets[n]["from"], "gp_healthy": targets[n]["to"]}
                           for n in sorted(mine)]}
        out["rows"].append(row)
        print("  %-4s   %5.1f%% / %5.1f%%   %5.1f%% / %5.1f%%  %+6.1f%%p   %s"
              % (co["id"], 100 * b_mean, 100 * b_min, 100 * h_mean, 100 * h_min,
                 100 * row["delta"],
                 " · ".join("%s %.0f→%.0f" % (n.split()[-1], targets[n]["from"], targets[n]["to"])
                            for n in sorted(mine)) or "없음"))

    # ── 전원건강 세계의 **쌍별** SE ────────────────────────────────────
    # 🔴 중앙값 SE 로 코어를 비교하면 안 된다 — standard_error.which_to_use 가
    #   "비교할 때는 paired 를 쓴다"이고 caveat 이 "쌍마다 다르다"이다.
    #   c4·c5 가 낀 쌍은 이 세계에서 값이 달라지므로 여기서 다시 낸다.
    # 🔴 그리고 21쌍에서 유의한 것을 사후에 고르면 **승자의 저주**다(환율 측정에서
    #   두 번 당했다). Bonferroni(0.05/21) 로 자른 임계를 함께 싣는다.
    import math
    ids = [r["core"] for r in out["rows"]]
    pairs = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            d = [x - y for x, y in zip(vecs[a], vecs[b])]
            n = len(d); mu = sum(d) / n
            sd = math.sqrt(sum((x - mu) ** 2 for x in d) / (n - 1)) if n > 1 else 0.0
            se = sd / math.sqrt(n)
            pairs["%s-%s" % (a, b)] = {"mean_diff": round(mu, 4), "se": round(se, 4),
                                       "sigma": round(abs(mu) / se, 2) if se else None}
    out["paired_se_by_pair"] = pairs
    out["multiple_comparison"] = {
        "n_pairs": len(pairs), "alpha": 0.05,
        "bonferroni_sigma": 2.9,
        "why": ("21쌍에서 유의한 것을 **사후에 고르면** 승자의 저주다 — 이 저장소가 환율 "
                "측정에서 두 번 당한 형태다. Bonferroni(0.05/21)로 자르면 약 2.9σ 다."),
        "survives": sorted([k for k, v in pairs.items()
                            if v["sigma"] and v["sigma"] >= 2.9]),
    }
    print("\n  쌍별 SE — Bonferroni(≈2.9σ) 통과: %s"
          % (", ".join(out["multiple_comparison"]["survives"]) or "없음"))
    for k, v in sorted(pairs.items(), key=lambda kv: -(kv[1]["sigma"] or 0))[:6]:
        print("    %-8s 차이 %+.1f%%p · SE %.2f%%p · %.2fσ%s"
              % (k, 100 * v["mean_diff"], 100 * v["se"], v["sigma"] or 0,
                 "  ✅ 보정 후에도 유의" if (v["sigma"] or 0) >= 2.9 else ""))

    sim = json.load(io.open(f"{BASE}/data/matchup_sim.json", encoding="utf-8"))
    sim["all_healthy"] = out
    json.dump(sim, io.open(f"{BASE}/data/matchup_sim.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/matchup_sim.json 에 all_healthy 기록")


if __name__ == "__main__":
    main()
