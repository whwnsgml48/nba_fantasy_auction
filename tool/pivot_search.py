#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""피벗 로스터의 교체 대상을 재탐색한다 (37차 — 「예비비 과소 편성」 해소용).

배경
  I24 복구로 피벗이 base+swaps 와 다시 일치하게 됐지만, 교체로 **들어오는 선수**는
  옛 설계 그대로다. 트리거가 걸린 자리(과열된 저가 센터)를 $2~5짜리로 때우고 끝내서
  피벗 총액이 낮고 예비비가 남는다 — c6 피벗 $159 · 예비 **$41**.

  34차가 base에 한 것과 같은 작업을 피벗에 한다: **비는 자리에 더 좋은 선수를 넣어
  예비비를 목표 밴드로 되돌린다.** 가격을 올리는 게 아니라 로스터를 바꾼다
  (34차 부록에서 재가격은 실패했다 — docs/05 2b-5).

방법
  1. 피벗에서 **트리거로 빠지는 선수**의 슬롯만 비운다. 나머지는 base 그대로 고정.
  2. 그 자리에 들어갈 조합을 전수 탐색 — 예비비가 $12~25 밴드에 드는 것만.
  3. `rebuild_search.evaluate`로 상대 6종 승률을 내고 **maximin**으로 정렬.
  4. 🔴 상위 후보는 **같은 난수 스트림 고시행으로 재대조**한다. 34차 교훈:
     900시행 순위는 1~2%p 수준에서 신뢰할 수 없다(승자의 저주).

이 스크립트는 **cores.json을 쓰지 않는다.** 후보만 출력한다 — 채택은 사람이 한다.
"""
import json, io, os, sys, random, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS
import rebuild_search as RS
import cat_model as CM
import real_opponents as RO   # 39차: 1차 지표는 실제 12팀

# ── 39차: 정렬 기준을 maximin → **실제 12팀 평균**으로 교체 ─────────────
# maximin의 최소값이 7코어 전부 value_max 하나에서 나오고, 그 상대는 우리 z모델의
# 자기 최적해다(작업 A). 조립 상대로 피벗을 고르면 "우리 모델에 가까운 로스터"를
# 고르는 셈이다. 1차는 실제 12팀 평균 · 2차는 maximin(견고성)으로 본다.
REAL, _RREP = RO.build()


def real_mean(names, iters, seed):
    """실제 12팀 평균 주간 승률. 상대마다 같은 시드로 rng를 새로 만든다(34차)."""
    wr = [MS.simulate(list(names), r, random.Random(seed), iters, None)["weekly_win_rate"]
          for r in REAL.values()]
    return round(sum(wr) / len(wr), 4)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL, CJ = MS.PL, MS.CJ
BUDGET = 200
RESERVE_LO, RESERVE_HI = 12, 25


def core(cid):
    return next(c for c in CJ["cores"] if c["id"] == cid)


def pivot_state(cid):
    """피벗에서 (고정 멤버, 비는 슬롯 수, 빠지는 선수) 를 낸다."""
    co = core(cid)
    pv = co["pivot_plan"]
    outs = {sw["out"]["name"] for sw in pv["swaps"] if sw["out"]["name"] != sw["in"]["name"]}
    # 🔴 37차: 트리거 선수는 **무조건** 비운다. c3는 `Ivica Zubac > $16`이 트리거인데
    #    피벗 로스터가 Zubac을 $11에 그대로 사고 있었다 — 트리거가 걸린 세계에서
    #    그 가격은 존재하지 않는다. 트리거의 정의상 그 선수는 포기 대상이다.
    base_names = {s["candidates"][0]["name"] for s in co["slots"]}
    outs |= {t["player"] for t in pv["triggers"]} & base_names
    keep = [s["candidates"][0]["name"] for s in co["slots"]
            if s["candidates"][0]["name"] not in outs]
    return co, pv, keep, sorted(outs)


def pool_for(keep, outs, cid):
    """후보 풀 — 획득 가능 · 부상 제외 아님 · 이미 로스터에 없음 · 트리거 선수 제외.

    트리거로 빠진 선수를 다시 넣으면 피벗의 의미가 없어진다."""
    trig = {t["player"] for t in core(cid)["pivot_plan"]["triggers"]}
    used = set(keep) | set(outs) | trig
    out = []
    for n, p in PL.items():
        if n in used or p.get("injury_exclude") or not p.get("obtainable"):
            continue
        out.append(n)
    return out


def search(cid, iters=1200, top=12, seed=20261020):
    co, pv, keep, outs = pivot_state(cid)
    k = 9 - len(keep)
    base_cost = sum(RS.cost(n) for n in keep)
    cand = pool_for(keep, outs, cid)
    lo = BUDGET - RESERVE_HI - base_cost      # 채워야 할 최소 금액
    hi = BUDGET - RESERVE_LO - base_cost
    print(f"[{cid}] 고정 {len(keep)}명 ${base_cost:.0f} · 빈 슬롯 {k}개 · "
          f"빠지는 선수 {outs}")
    print(f"      채울 금액대 ${lo:.0f}~${hi:.0f} (예비비 ${RESERVE_LO}~${RESERVE_HI}) · 풀 {len(cand)}명")

    combos = []
    for c in itertools.combinations(cand, k):
        s = sum(RS.cost(n) for n in c)
        if not (lo <= s <= hi):
            continue
        names = keep + list(c)
        if RS.feasible(names, grandfather=tuple(keep)) is None:
            continue
        combos.append((c, s))
    print(f"      실행 가능 조합 {len(combos)}개")
    if not combos:
        return []

    # ── 1단계 프리필터 (결정적·빠름) ────────────────────────────────
    # 조합 수천 개를 전부 시뮬하면 몇 시간이 걸린다. cat_model의 팀 한계기여로
    # 먼저 줄인다 — 이기는 캣 수, 동수면 마진 합. 시뮬은 상위 PRE개만 돌린다.
    # ⚠️ 캣별 한계기여는 척도가 제각각이다(FG% 130.9 vs A/T 0.116) — 그냥 더하면 안 된다.
    #    29차가 지적한 그 문제다. 이기는 캣 수를 1순위로, 동수면 rel_margin 합으로 가른다.
    B = CM.baselines()
    def score(names):
        marg, wins, _w, _l = CM.evaluate(names, B)
        rel = 0.0
        for cat, v in marg.items():
            if v is None or v <= 0:
                continue
            r = CM.rel_margin(cat, v, B, names)
            if r: rel += r
        return (wins, rel)
    ranked = sorted(combos, key=lambda cs: score(keep + list(cs[0])), reverse=True)
    PRE = min(30, len(ranked))
    print(f"      프리필터(cat_model 한계기여) 상위 {PRE}개만 시뮬")

    # 탐색 단계는 **1차 지표만** 돈다 — 조립 상대 6종을 함께 돌리면 비용이 두 배이고,
    # 어차피 정렬 기준이 아니다. maximin은 confirm 단계에서 낸다.
    rows = []
    for c, sc in ranked[:PRE]:
        names = keep + list(c)
        rows.append({"fill": list(c), "total": round(base_cost + sc),
                     "reserve": BUDGET - round(base_cost + sc),
                     "real_mean": real_mean(names, iters, seed)})
    rows.sort(key=lambda r: -r["real_mean"])
    return rows[:top]


def confirm(cid, rows, iters=6000, seed=20261020, n=4):
    """🔴 34차 교훈 — 상위 후보를 같은 스트림 고시행으로 재대조한다."""
    co, pv, keep, outs = pivot_state(cid)
    rng = random.Random(seed)
    opps = MS.build_opponents(rng)
    out = []
    cur = [r["name"] for r in pv["final_roster"]]
    for r in rows[:n]:
        names = keep + r["fill"]
        rr = RS.evaluate(names, random.Random(seed), iters, opps)   # 2차 maximin
        rr["real_mean"] = real_mean(names, iters, seed)             # 1차
        rr["fill"] = r["fill"]; rr["total"] = r["total"]; rr["reserve"] = r["reserve"]
        rr["names"] = names
        out.append(rr)
    rr = RS.evaluate(cur, random.Random(seed), iters, opps)
    rr["real_mean"] = real_mean(cur, iters, seed)
    rr["fill"] = ["(현행 피벗)"]; rr["total"] = pv["final_total"]
    rr["reserve"] = BUDGET - pv["final_total"]; rr["names"] = cur
    out.append(rr)
    out.sort(key=lambda r: -r["real_mean"])   # 1차 지표로 정렬 (39차)
    return out


def show(title, rows, full=False):
    print(f"\n{title}")
    if full:
        print("  %-44s %5s %5s %9s %8s %8s" % ("채우는 선수", "총액", "예비", "실제12평균", "maximin", "빅5붕괴"))
        for r in rows:
            mx = RS.mixmax(r)
            print("  %-44s $%-4d $%-4d %8.1f%% %7.1f%% %7.1f%%" % (
                " · ".join(r["fill"])[:44], r["total"], r["reserve"],
                r["real_mean"]*100, r["min_win_rate"]*100, mx["p_big5_collapse"]*100))
    else:
        print("  %-52s %5s %5s %9s" % ("채우는 선수", "총액", "예비", "실제12평균"))
        for r in rows:
            print("  %-52s $%-4d $%-4d %8.1f%%" % (
                " · ".join(r["fill"])[:52], r["total"], r["reserve"], r["real_mean"]*100))


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "c6"
    it1 = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
    it2 = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    rows = search(cid, iters=it1)
    if rows:
        show(f"[{cid}] 1차 탐색 ({it1}시행 · **실제 12팀 평균** 상위)", rows)
        show(f"[{cid}] 🔴 재대조 ({it2}시행 · 같은 스트림 · 현행 포함)",
             confirm(cid, rows, iters=it2), full=True)
        best = confirm(cid, rows, iters=it2)[0]
        print("\n  1위 로스터: " + ", ".join(best["names"]))
        print("  ⚠️ 채택은 사람이 한다 — 이 스크립트는 cores.json을 쓰지 않는다.")
