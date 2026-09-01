#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""코어별 **조달 배율** — 「방이 작년처럼 부르면 이 아홉이 얼마인가」 (2026-09-01 · 측정만).

왜
  승률로는 코어가 안 갈린다(7코어 3.5%p · 전혀 다른 8번째가 그 한가운데 · §6i).
  그런데 **조달로는 갈린다.** 그 축이 화면에도 문서에도 없었다.

🔴 점 추정을 내면 안 된다 — 결측이 코어마다 다르다
  작년 실낙찰가가 없는 선수(작년 옥션 미지명)를 `plan_price` 로 때우면
  **결측이 많은 코어가 유리하게 나온다.** 그래서 **구간**으로 낸다:

```
가정 A  결측 = plan_price            (그 선수는 계획대로 싸게 산다)
가정 B  결측 = 같은 티어 실낙찰 중앙값 (그 선수도 방이 티어 값으로 부른다)
구간    [min(A,B), max(A,B)]  + **결측 인원수를 같이 표시**
```
⚠️ **A 가 항상 작은 게 아니다.** 결측 선수의 티어 중앙값이 계획가보다 쌀 수 있다(c1).
   「하한=A」로 이름 붙이면 c1 에서 상한 < 하한 이 찍힌다. 그래서 min/max 로 잡는다.
🔴 **구간이 겹치면 아무 말도 하지 않는다.** c2 가 낮아 보이는 것이 결측 2명 때문인지
   실제로 싼 계획이어서인지, 겹치면 **가릴 수 없다.**

⚠️ 표본은 작년 한 해뿐이다. 「이렇게 된다」가 아니라 **「작년처럼 가면 이렇다」**이다.
⚠️ 이 스크립트는 아무것도 쓰지 않는다. 기본 계획 교체는 사용자 판단이다.
"""
import io
import json
import os
import statistics as st
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 1.11
TEAMS_NOW, ROSTER = 14, 9


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))

    known = [(p["name"], round(p["prior_auction_price"] * SCALE), p)
             for p in pl.values() if p.get("prior_auction_price") is not None]
    # 🔴 평균 팀 값은 **낙찰 결과 전수(CSV)** 로 낸다. `players.json` 에는 우리가 추적하는
    #   92명만 `prior_auction_price` 가 있어서, 그걸로 나누면 싼 28명이 빠져 평균이
    #   낮게 나온다($174 vs 실제 $188). 분모를 잘못 잡는 그 형태다(docs/11 ⑫).
    import csv as _csv
    with io.open(BASE + "/data/prior_auction_2025_26/results.csv", encoding="utf-8") as _fh:
        _all = [int(r["price"]) for r in _csv.DictReader(_fh)]
    room_total = round(sum(_all) * SCALE)
    avg_team = room_total / TEAMS_NOW

    # 티어 = 우리 시장 중간값 5분위. 결측 상한은 **같은 티어 실낙찰 환산가 중앙값**.
    def mid(p):
        return (p["market_low"] + p["market_high"]) / 2.0
    ks = sorted(known, key=lambda r: mid(r[2]))
    qn = max(1, len(ks) // 5)
    tiers = [ks[i:i + qn] for i in range(0, len(ks), qn)]

    def tier_median(p):
        m = mid(p)
        best, bd = None, None
        for t in tiers:
            lo, hi = mid(t[0][2]), mid(t[-1][2])
            d = 0 if lo <= m <= hi else min(abs(m - lo), abs(m - hi))
            if bd is None or d < bd:
                bd, best = d, t
        return st.median([a for _, a, _ in best])

    print("코어별 조달 배율 — 「방이 작년처럼 부르면 이 아홉이 얼마인가」\n")
    print("  작년 낙찰 환산 총액 $%d · %d팀 → **평균 팀 $%.0f** (로스터 %d인)\n"
          % (room_total, TEAMS_NOW, avg_team, ROSTER))
    print("  %-5s %7s %9s %9s %7s %7s %7s"
          % ("코어", "계획", "구간 하", "구간 상", "배율 하", "배율 상", "결측"))
    rows = []
    for co in cj["cores"]:
        plan = lo = hi = 0
        miss = []
        for s in co["slots"]:
            cd = s["candidates"][0]
            n, pp = cd["name"], cd["plan_price"]
            plan += pp
            py = pl[n].get("prior_auction_price")
            if py is None:
                miss.append(n)
                lo += pp
                hi += tier_median(pl[n])
            else:
                a = round(py * SCALE)
                lo += a
                hi += a
        # 🔴 두 가정 중 **어느 쪽이 큰지 정해져 있지 않다** — 결측 선수의 티어 중앙값이
        #   계획가보다 쌀 수 있다(c1 이 그렇다). 그러니 「하한/상한」이라 부르지 않고
        #   **두 가정을 계산한 뒤 min/max 로 구간을 잡는다.** 이름이 순서를 보장한다고
        #   믿으면 c1 에서 상한 < 하한 이 찍힌다.
        band = (min(lo, hi), max(lo, hi))
        rows.append((co["id"], plan, band[0], band[1], len(miss), miss, lo, hi))
        print("  %-5s %7s %9s %9s %7.2f %7.2f %5d명"
              % (co["id"], "$%d" % plan, "$%.0f" % band[0], "$%.0f" % band[1],
                 band[0] / plan, band[1] / plan, len(miss)))

    print("\n  ── 구간이 겹치는가 (겹치면 코어 간 판정 불가) ──")
    srt = sorted(rows, key=lambda r: r[2])
    best = srt[0]
    print("  최저 하한: %s [$%.0f ~ $%.0f]" % (best[0], best[2], best[3]))
    sep, ovl = [], []
    for r in srt[1:]:
        (ovl if r[2] <= best[3] else sep).append(r)
    if sep:
        print("  🟢 **%s 보다 확실히 비싼 코어** (구간이 안 겹친다): %s"
              % (best[0], ", ".join("%s(하한 $%.0f > %s 상한 $%.0f)" % (r[0], r[2], best[0], best[3])
                                    for r in sep)))
    if ovl:
        print("  ⚪ 구간이 겹쳐 **가릴 수 없는 코어**: %s"
              % ", ".join("%s [$%.0f~$%.0f]" % (r[0], r[2], r[3]) for r in ovl))
    if not sep:
        print("  🔴 전부 겹친다 — **코어 간 조달 우열을 말할 수 없다.**")

    print("\n  ── 결측이 판정을 만드는가 (조율 지적) ──")
    for cid, plan, lo, hi, nm, miss, _a, _b in rows:
        if nm:
            print("     %-4s 결측 %d명 — %s" % (cid, nm, ", ".join(m.split()[-1] for m in miss)))
    print("     ⚠️ 결측은 **작년 옥션에서 지명되지 않은 선수**다(루키·저가 벤치). 방향은")
    print("        「싸다」 쪽이므로 하한이 더 그럴듯하지만, **그래서 하한이 편향돼 있다.**")

    out = {"scale": SCALE, "room_total_adj": room_total, "avg_team": round(avg_team, 1),
           "cores": [{"id": c, "plan": p, "lo": round(l), "hi": round(h),
                      "mult_lo": round(l / p, 3), "mult_hi": round(h / p, 3),
                      "missing": m, "assume_plan": round(a), "assume_tier": round(b)}
                     for c, p, l, h, nm, m, a, b in rows]}
    json.dump(out, io.open(BASE + "/data/core_procurement.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n⚠️ 기본 계획을 바꾸지 않는다 — 사용자 판단이다. data/core_procurement.json 기록")


if __name__ == "__main__":
    main()
