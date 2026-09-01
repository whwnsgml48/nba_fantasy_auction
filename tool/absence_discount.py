#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`GP 자기상관 0.10` 을 뒤집으면 — **결장 이력을 누가 얼마나 깎는가** (2026-09-01 · 측정만).

전제 (docs/05 §6j 검증)
```
경기당 생산 자기상관   ρ 0.613   유지된다
GP 자기상관            ρ 0.100   **누가 다치는지는 거의 무작위다**
```
뒤집으면: **작년에 많이 결장했지만 지금 건강한 선수를 과도하게 깎으면 손해다.**

🔴 **그러나 구분해야 한다 — 이걸 흐리면 위험한 결론이 된다**
```
ρ 0.10 이 말하는 것      「작년 결장」은 올해 출장을 거의 못 맞힌다
ρ 0.10 이 말하지 않는 것  「현재 부상」이 무의미하다
```
아킬레스 재활 중인 선수에게는 **진짜 정보**가 있다. 과거 결장과 현재 상태는 다르다.
그래서 여기서는 **현재 부상 표기가 있는 선수를 빼고** 잰다.

두 방향
```
(a) 방이 깎는가   이 방의 작년 낙찰가가 **그 이전 시즌(2023-24) 결장**에 반응했나
                  ⚠️ 옥션 표본이 한 해뿐이라 「작년 vs 재작년 가격」은 못 잰다.
                     대신 **한 번의 가격이 직전 결장에 얼마나 반응했나**를 본다
(b) 🔴 우리가 깎는가  우리 투영 GP 가 작년 GP 를 섞어 쓴다 — 얼마나 깎고 있나
                  이쪽이 본체다. ρ 0.10 이 참이면 **우리 상한이 낮아서 싼 값을 걷어찰** 수 있다
```

⚠️ **`my_max` 를 올리지 않는다.** 목록만 낸다 — 상한을 흔드는 것은 40차에서 가장 위험한
   조작이다. 판단은 조율 세션이 한다.
"""
import csv
import io
import json
import os
import statistics as st
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 1.11
MISS = 20          # 「많이 결장」 기준: 직전 시즌 대비 이만큼 이상 덜 뛰었다


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def gp_of(fn):
    out = {}
    with io.open(BASE + "/data/stats_2025_26/bbref/" + fn, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                g = float(r["GP"])
            except (TypeError, ValueError):
                continue
            k = norm(r["name"])
            if k not in out or g > out[k]:
                out[k] = g
    return out


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    meas = json.load(io.open(BASE + "/data/stats_2025_26/measured_full.json",
                             encoding="utf-8"))["players"]
    proj = {}
    for v in meas.values():
        proj[v.get("bbref_name")] = v
    g24, g25, g26 = gp_of("2023-24_per_game.csv"), gp_of("2024-25_per_game.csv"), \
        gp_of("2025-26_per_game.csv")

    # ── (a) 이 방의 작년 가격이 **그 이전 시즌 결장**에 반응했나
    priced = {n: p["prior_auction_price"] for n, p in pl.items()
              if p.get("prior_auction_price") is not None}
    ka = [n for n in priced if norm(n) in g24 and norm(n) in g25]
    hurt = [n for n in ka if g24[norm(n)] - g25[norm(n)] >= MISS]
    fine = [n for n in ka if abs(g24[norm(n)] - g25[norm(n)]) < 8]
    print("결장 이력을 누가 얼마나 깎는가 — GP 자기상관 0.10 을 뒤집어 본다\n")
    print("=" * 78)
    print("(a) **방이 깎는가** — 작년 옥션 가격이 그 직전(2024-25) 결장에 반응했나")
    print("  🔴 분모: 작년가 보유 %d명 중 2023-24·2024-25 GP 가 다 있는 **%d명**"
          % (len(priced), len(ka)))
    print("     그중 직전 시즌에 %d경기 이상 덜 뛴 선수 **%d명** · 출장 안정 %d명"
          % (MISS, len(hurt), len(fine)))
    if hurt and fine:
        print("     결장군 평균 낙찰가 $%.1f · 중앙값 $%.0f"
              % (st.mean([priced[n] for n in hurt]), st.median([priced[n] for n in hurt])))
        print("     안정군 평균 낙찰가 $%.1f · 중앙값 $%.0f"
              % (st.mean([priced[n] for n in fine]), st.median([priced[n] for n in fine])))
        print("     ⚠️ **이 비교만으로는 아무 말도 못 한다** — 결장군에 스타가 더 많으면")
        print("        가격이 높게 나온다. 생산을 통제해야 한다. 아래 (a-2).")

    # (a-2) 같은 생산 수준에서 결장 이력이 가격을 깎았나
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import prior_price_bias as PB
    s25 = PB.load_season("2024-25_per_game.csv")
    keys = [n for n in ka if norm(n) in s25]
    rows = {n: s25[norm(n)] for n in keys}
    # 출장을 제거한 생산(경기당 실력)으로 통제한다
    flat = {k: dict(v, GP=82.0) for k, v in rows.items()}
    z = PB.zscore(flat, keys)
    zr = {k: i for i, k in enumerate(sorted(z, key=lambda x: -z[x]))}
    pr = {k: i for i, k in enumerate(sorted(keys, key=lambda x: -priced[x]))}
    resid = {n: pr[n] - zr[n] for n in keys}     # + = 실력 대비 **싸게** 팔렸다
    hs = [resid[n] for n in keys if g24[norm(n)] - g25[norm(n)] >= MISS]
    fs = [resid[n] for n in keys if abs(g24[norm(n)] - g25[norm(n)]) < 8]
    print("\n  (a-2) **경기당 실력을 통제한** 가격 잔차 (+ = 실력 대비 싸게 팔렸다)")
    print("     결장군 %2d명  평균 %+.1f · 중앙값 %+.1f" % (len(hs), st.mean(hs), st.median(hs)))
    print("     안정군 %2d명  평균 %+.1f · 중앙값 %+.1f" % (len(fs), st.mean(fs), st.median(fs)))
    d = st.mean(hs) - st.mean(fs)
    print("     차 **%+.1f 순위** — %s" % (d,
          "결장 이력이 있으면 **더 싸게 팔린다**(방이 깎는다)" if d > 5 else
          ("결장 이력이 오히려 **비싸게** 팔린다" if d < -5 else
           "**차이가 작다 — 방이 결장 이력으로 깎는다고 말할 수 없다**")))

    # ── (b) 우리가 깎는가
    print("\n" + "=" * 78)
    print("(b) 🔴 **우리가 깎는가** — 투영 GP 가 작년 결장을 얼마나 끌고 있나")
    print("  전제 확인: `measured_full.meta.method` = 「2025-26과 2024-25를 GP 가중 혼합」")
    print("  → **우리 투영 GP 는 작년 GP 를 섞어 쓴다.** (b) 는 성립한다.\n")
    inj = {n for n, p in pl.items() if p.get("injury_exclude")}
    cand = []
    for n, p in pl.items():
        r = proj.get(n)
        if not r or n in inj:
            continue
        k = norm(n)
        if k not in g25 or k not in g26:
            continue
        if g25[k] - g26[k] < MISS:            # 작년에 많이 결장한 선수만
            continue
        pg = r.get("GP") or 0
        healthy = g25[k]                      # 직전 건강 시즌의 출장
        if healthy <= pg:
            continue
        cut = 1 - pg / healthy
        cand.append((n, g25[k], g26[k], pg, healthy, cut, p["my_max"],
                     p.get("prior_auction_price")))
    cand.sort(key=lambda r: -r[5])
    print("  대상: **작년 %d경기 이상 결장 + 현재 부상 표기 없음** — %d명" % (MISS, len(cand)))
    print("  ⚠️ 현재 부상자(`injury_exclude`)는 뺐다: %s" % (", ".join(sorted(inj)) or "없음"))
    print("\n  %-24s %6s %6s %8s %8s %7s %6s" %
          ("선수", "24-25", "25-26", "투영GP", "건강시즌", "삭감", "상한"))
    for n, a, b, pg, h, cut, mx, py in cand:
        print("  %-24s %6.0f %6.0f %8.1f %8.0f %6.0f%% %6d%s"
              % (n[:24], a, b, pg, h, 100 * cut, mx,
                 "   작년 $%d" % py if py else ""))
    if cand:
        print("\n  평균 삭감 **%.0f%%** — 우리 가치는 GP 에 **선형**이므로 상한도 그만큼 낮다"
              % (100 * st.mean([c[5] for c in cand])))
        print("  🔴 GP 자기상관이 0.10 이면 이 삭감의 **근거가 약하다.**")
        print("     그런데 이것이 곧 「상한을 올려라」는 아니다 — 아래 반론을 먼저 읽을 것.")

    # ── 결과: 방은 안 깎는데 우리는 깎는다 → 우리가 **진다**
    have = [c for c in cand if c[7] is not None]
    lose = [c for c in have if c[6] < round(c[7] * SCALE)]
    would = [c for c in lose if c[6] / max(0.01, 1 - c[5]) >= round(c[7] * SCALE)]
    print("\n  ── 🔴 그래서 무슨 일이 일어나나 ──")
    print("     작년가를 아는 %d명 중 **우리 상한 < 작년 환산가 = 못 산다: %d명**"
          % (len(have), len(lose)))
    print("     그중 **삭감이 없었다면 살 수 있었을 선수: %d명**" % len(would))
    for c in would:
        n, _, _, pg, h, cut, mx, py = c
        print("       %-22s 상한 $%-3d < 작년환산 $%-3d · 삭감 없으면 ≈$%d"
              % (n[:22], mx, round(py * SCALE), round(mx / (1 - cut))))
    print("     ⚠️ **거친 환산이다** — my_max 는 z 모델의 순수 함수가 아니다(docs 참조).")
    print("        「이만큼 오른다」가 아니라 **「삭감이 판정을 뒤집을 크기다」**는 뜻이다.")

    print("\n  ── 🔴 올리면 안 되는 이유 (같이 읽을 것) ──")
    print("     ① ρ 0.10 은 **모집단 평균**이다. 아킬레스·무릎 재활은 개별 정보가 있고")
    print("        이 표는 그걸 구분하지 못한다 — 부상 표기만 뺐지 **부상 종류를 안 본다.**")
    print("     ② 우리 혼합은 이미 자기보정을 한다 — 가중치가 GP 라서 결장 시즌은")
    print("        **적게 반영된다**(Sabonis 19경기 → 가중 28.5 vs 70).")
    print("     ③ 상한을 올리면 **예산이 다른 칸에서 나온다.** 한 명을 싸게 사는 기회와")
    print("        아홉 칸 계획이 깨지는 위험은 같은 저울이 아니다.")
    print("\n⚠️ `my_max` 를 바꾸지 않았다. 목록만 낸다 — 판단은 조율 세션.")


if __name__ == "__main__":
    main()
