#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DD 추정기 세계 vs **실계수 세계** — 7코어를 같은 실행에서 잰다 (46차).

🔴 `matchup_sim.py` 를 **고치지 않는다**(팀 총량 경로 불가침). 여기서 `prep` 만
   DD 표를 보는 판본으로 감싸고, 끝나면 되돌린다. 원본 로직은 그대로 베낀다 —
   갈라지면 이 측정이 무효다.
🔴 **양쪽(우리·상대) 모두에 적용한다.** 우리만 실계수를 쓰면 비대칭이라 차이가
   DD 때문인지 비대칭 때문인지 구분이 안 된다.
⚠️ 실계수가 있는 선수만 바뀐다(95/171). 나머지는 추정 그대로 — 그게 채택 후 실제 세계다.

실행:  python3 tool/dd_world.py [iters]
"""
import io, json, os, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import pivot_delta as PD

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DDX = {n: e["DD_exact"] for n, e in
       json.load(io.open(f"{BASE}/data/dd_exact.json", encoding="utf-8"))["players"].items()}
_ORIG = MS.prep


def prep_exact(names, rates=None):
    """`matchup_sim.prep` 와 **같은 로직** · DD 만 표에서 읽는다."""
    if MS.LINEUP_ADJ and rates is None:
        rates = MS.usable_rates(names)
    out = []
    for n in names:
        r = MS.F.get(n)
        if not r:
            continue
        av = (r.get("GP") or 0) / 82.0
        if MS.LINEUP_ADJ and rates:
            av *= (rates.get(n) if n in rates
                   else rates.get(frozenset(MS.PE.elig(MS._pdict(n))), 1.0))
        dd = DDX.get(n)
        if dd is None:
            dd = CM.dd_game_prob(r.get("PTS"), r.get("REB"), r.get("AST"))
        out.append((av,
                    [(k, r.get(k)) for k in MS.COUNT],
                    [(k, a, r.get(a), r.get(k)) for k, a in MS.RATE.items()],
                    dd))
    return out


def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    rost = {c["id"]: [s["candidates"][0]["name"] for s in c["slots"]] for c in CJ["cores"]}

    res = {}
    for world in ("추정", "실계수"):
        MS.prep = prep_exact if world == "실계수" else _ORIG
        MS._URATE.clear()
        for cid, names in rost.items():
            res.setdefault(cid, {})[world] = PD.measure(names, iters=iters, seed=20261020)
    MS.prep = _ORIG

    print("DD 추정 세계 vs 실계수 세계 — 7코어 · 같은 실행 · seed 20261020 · %d시행" % iters)
    print("실계수 적용 %d명 / 우리 풀 171명 (나머지는 추정 유지)\n" % len(DDX))
    print("  %-4s %8s %8s %9s %7s   %s" % ("코어", "추정", "실계수", "차이", "σ", "순위변화"))
    order_a = sorted(res, key=lambda c: -res[c]["추정"]["weekly"])
    order_b = sorted(res, key=lambda c: -res[c]["실계수"]["weekly"])
    rows = []
    for cid in order_a:
        a, b = res[cid]["추정"], res[cid]["실계수"]
        md, se, sig = PD.delta(b, a)
        mv = order_a.index(cid) - order_b.index(cid)
        print("  %-4s %7.2f%% %7.2f%% %+8.2f%%p %6.1f   %s"
              % (cid, 100 * a["weekly"], 100 * b["weekly"], 100 * md, sig,
                 "그대로" if mv == 0 else "🔴 %+d계단" % -mv))
        rows.append({"core": cid, "est": round(a["weekly"], 4), "exact": round(b["weekly"], 4),
                     "delta": round(md, 4), "sigma": round(sig, 2),
                     "rank_est": order_a.index(cid) + 1, "rank_exact": order_b.index(cid) + 1})
    same = order_a == order_b
    print("\n  순위: 추정 %s" % " > ".join(order_a))
    print("        실계수 %s" % " > ".join(order_b))

    # 🔴 **순서가 바뀐 것과 판정이 바뀐 것은 다른 질문이다.**
    #   2~5위는 1.6%p 폭에 대응 SE 0.68%p 라 README 가 「순서를 읽지 마라」고 적어 뒀다.
    #   그 안에서의 자리바꿈을 「순위가 바뀌었다」고 보고하면 **잡음을 발견으로 읽는 것**이다.
    #   바뀐 쌍이 **어느 세계에서든 SE 를 넘었는지**를 본다 — 그게 판정이 바뀌었나이다.
    SE = json.load(io.open(f"{BASE}/data/matchup_sim.json",
                           encoding="utf-8"))["standard_error"]["paired_se_median"]
    R = {r["core"]: r for r in rows}
    swapped, readable = [], []
    for i, c in enumerate(order_a):
        j = order_b.index(c)
        for d in order_a[i + 1:]:
            if order_b.index(d) < j:                       # c 와 d 의 순서가 뒤집혔다
                pair = tuple(sorted((c, d)))
                if pair in swapped:
                    continue
                swapped.append(pair)
                ge = abs(R[c]["est"] - R[d]["est"])
                gx = abs(R[c]["exact"] - R[d]["exact"])
                if ge > SE or gx > SE:
                    readable.append((pair, 100 * ge, 100 * gx))
    print("  자리바꿈 %d쌍 (대응 SE %.2f%%p 기준)" % (len(swapped), 100 * SE))
    for a_, b_ in swapped:
        ge, gx = 100 * abs(R[a_]["est"] - R[b_]["est"]), 100 * abs(R[a_]["exact"] - R[b_]["exact"])
        print("     %s ↔ %s   추정 격차 %.2f%%p · 실계수 %.2f%%p   %s"
              % (a_, b_, ge, gx,
                 "🔴 **읽을 수 있던 차이다**" if (ge > 100 * SE or gx > 100 * SE)
                 else "둘 다 잡음 안 — 애초에 순서를 읽으면 안 되는 쌍"))
    top_same = order_a[0] == order_b[0]
    verdict_ok = top_same and not readable
    print("  → **%s**" % ("1위 유지 · 자리바꿈은 전부 잡음 안 — 채택해도 판단이 안 바뀐다 ✅"
                          if verdict_ok else
                          "🔴 판정이 바뀐다 — 채택 전에 보고할 것"))
    top_gap_a = 100 * (res[order_a[0]]["추정"]["weekly"] - res[order_a[1]]["추정"]["weekly"])
    top_gap_b = 100 * (res[order_b[0]]["실계수"]["weekly"] - res[order_b[1]]["실계수"]["weekly"])
    print("  1-2위 격차: 추정 %.2f%%p → 실계수 %.2f%%p" % (top_gap_a, top_gap_b))

    json.dump({"generated_by": "tool/dd_world.py", "iterations": iters, "seed": 20261020,
               "n_exact": len(DDX),
               "what": "DD 를 추정기 대신 게임로그 실계수(두 시즌 혼합)로 바꾸면 코어 순위가 바뀌는가",
               "rank_unchanged": same, "decision_unchanged": verdict_ok,
               "verdict_note": ("순서가 바뀐 것과 판정이 바뀐 것은 다르다. 2~5위는 대응 SE 안이라 "
                                "README 가 순서를 읽지 말라고 적어 뒀다 — 그 안의 자리바꿈은 "
                                "잡음이다. 1위 유지 + 자리바꿈 쌍이 전부 SE 안이면 판정은 그대로다."),
               "swapped_pairs": [{"pair": list(p), "gap_est_pp": round(g1, 3),
                                  "gap_exact_pp": round(g2, 3)}
                                 for p, g1, g2 in
                                 [((a_, b_), 100*abs(R[a_]["est"]-R[b_]["est"]),
                                   100*abs(R[a_]["exact"]-R[b_]["exact"])) for a_, b_ in swapped]],
               "readable_swaps": [list(p) for p, _, _ in readable],
               "order_est": order_a, "order_exact": order_b,
               "rows": rows},
              io.open(f"{BASE}/data/dd_world.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/dd_world.json 기록")


if __name__ == "__main__":
    main()
