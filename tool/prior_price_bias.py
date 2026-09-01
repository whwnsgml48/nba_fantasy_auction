#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6j 배율의 **전제 검증** — 작년 낙찰가는 편향된 예측자인가 (2026-09-01 · 측정만).

🔴 왜 이걸 재야 하나
  `docs/05 §6j` 가 「방이 작년처럼 부르면 c6 는 $274 다(1.43배)」를 **화면에 올렸다.**
  그 숫자는 **작년 낙찰가가 올해 낙찰가의 좋은 예측자**라는 전제 위에 있다.
  그런데 `overheat_thresholds` 는 정반대를 말한다:

> **작년 실낙찰가 × 1.117 을 쓰지 않는다** — 작년 가격은 **프리시즌 기대치**라
> 개별 선수 가격 판정에 쓰면 「기대 vs 결과」를 재게 된다 (`docs/08 §0`)

  두 용법이 다르긴 하다:
```
✅ 방의 **입찰 행동**을 예측한다   작년 입찰은 그 행동의 직접 증거다
❌ 선수 **가치**를 매긴다          기대치를 결과로 착각한다
```
  그런데 **방의 기대치는 지난 시즌 결과를 보고 갱신된다.** 그러니 작년 가격은
  편향된 예측자이고, **편향 방향은 그 선수가 기대에 부응했는지가 정한다.**

무엇을 재나
```
작년 낙찰가        2025-26 **시작 전**에 형성된 기대 (근거: 2024-25 성적)
2024-25 생산       방이 그때 **보고 있던 것**
2025-26 생산       실제로 **일어난 것**
```
  가격이 2024-25 와 잘 맞고 2025-26 과 덜 맞으면 → **작년 가격은 기대치가 맞다.**
  그러면 2025-26 에 **미달한 선수**는 올해 덜 불릴 것이고, 그 선수를 많이 담은 코어의
  배율은 **과대**다.

⚠️ 보정하지 않는다. 재서 올린다 — 판단은 조율 세션이 한다.
⚠️ 생산 점수는 **13캣 z 합**이다(`tool/value_model.py` 와 같은 레시피). 코어 무관
   일반 가치이고, 우리 `my_max` 와는 **다른 것**이다 — 여기서 `my_max` 를 쓰면
   우리 모델로 우리 모델을 검증하게 된다.
"""
import csv
import io
import json
import math
import os
import statistics as st
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 1.11
COUNT = ["PTS", "REB", "OREB", "AST", "STL", "BLK", "3PM"]
RATE = {"FG%": "FGA", "FT%": "FTA", "3P%": "3PA"}


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def load_season(fn):
    out = {}
    with io.open(BASE + "/data/stats_2025_26/bbref/" + fn, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            def f(k):
                try:
                    return float(r[k])
                except (TypeError, ValueError):
                    return None
            k = norm(r["name"])
            row = {c: f(c) for c in COUNT + ["TOV", "GP", "FGA", "FTA", "3PA"]}
            for c in RATE:
                row[c] = f(c)
            # 같은 이름이 여러 팀에 있으면 GP 가 가장 큰 행(합산 행)을 쓴다
            if k not in out or (row["GP"] or 0) > (out[k]["GP"] or 0):
                out[k] = row
    return out


def zscore(rows, keys):
    """13캣 z 합 — value_model 과 같은 레시피. 주어진 keys 안에서 표준화한다."""
    base = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
    CB = base["opponent_baseline"]["cat_baselines"]
    contrib = {}
    for k in keys:
        r = rows[k]
        gp = (r.get("GP") or 0) / 82.0
        c = {}
        for cat in COUNT:
            c[cat] = (r.get(cat) or 0) * gp
        c["TOV"] = -(r.get("TOV") or 0) * gp
        for cat, att in RATE.items():
            bl = CB.get(cat, {}).get("baseline_per_game")
            if bl is None or r.get(cat) is None or r.get(att) is None:
                c[cat] = 0.0
            else:
                c[cat] = (r[cat] - bl) * r[att] * gp
        # A/T
        tov = (r.get("TOV") or 0)
        c["A/T"] = ((r.get("AST") or 0) / tov if tov else 0) * gp
        contrib[k] = c
    cats = COUNT + ["TOV"] + list(RATE) + ["A/T"]
    tot = {k: 0.0 for k in keys}
    for cat in cats:
        vs = [contrib[k][cat] for k in keys]
        m, s = st.mean(vs), (st.pstdev(vs) or 1.0)
        for k in keys:
            tot[k] += (contrib[k][cat] - m) / s
    return tot


def spearman(a, b):
    n = len(a)
    ra = {k: i for i, k in enumerate(sorted(a, key=lambda x: -a[x]))}
    rb = {k: i for i, k in enumerate(sorted(b, key=lambda x: -b[x]))}
    d2 = sum((ra[k] - rb[k]) ** 2 for k in a)
    return 1 - 6.0 * d2 / (n * (n * n - 1)), ra, rb


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    s26 = load_season("2025-26_per_game.csv")
    s25 = load_season("2024-25_per_game.csv")

    priced = {n: p["prior_auction_price"] for n, p in pl.items()
              if p.get("prior_auction_price") is not None}
    keys = [n for n in priced if norm(n) in s26 and norm(n) in s25]
    print("작년 낙찰가는 편향된 예측자인가 — §6j 배율의 전제 검증\n")
    print("  🔴 분모: 작년 낙찰가 보유 **%d명** 중 두 시즌 실측이 다 있는 **%d명**"
          % (len(priced), len(keys)))
    print("     (제외 %d명 — 루키·미출장. 이들은 이 검증에 안 들어간다)"
          % (len(priced) - len(keys)))

    k26 = {n: s26[norm(n)] for n in keys}
    k25 = {n: s25[norm(n)] for n in keys}
    z26 = zscore(k26, keys)
    z25 = zscore(k25, keys)
    price = {n: priced[n] for n in keys}

    r25, rp, rz25 = spearman(price, z25)
    r26, _, rz26 = spearman(price, z26)
    print("\n  ── 순위 상관 (n=%d) ──" % len(keys))
    print("     작년 낙찰가  vs  **2024-25 생산** (방이 그때 보던 것)   ρ = **%.3f**" % r25)
    print("     작년 낙찰가  vs  **2025-26 생산** (실제로 일어난 것)     ρ = **%.3f**" % r26)
    gap = r25 - r26
    print("     차 %.3f — %s" % (gap,
          "**가격은 기대치다**(그때 본 것에 더 붙는다)" if gap > 0.05 else
          ("가격이 오히려 결과에 더 붙는다 — 기대치 해석이 약해진다" if gap < -0.05 else
           "둘이 비슷하다 — 기대/결과를 이 데이터로 못 가른다")))

    print("\n  ── 계통 편향: 가격 순위 대비 2025-26 생산 순위 잔차 ──")
    res = {n: rz26[n] - rp[n] for n in keys}   # + = 가격보다 못했다(순위가 뒤)
    vs = list(res.values())
    print("     평균 %.1f · 중앙값 %.1f · |잔차| 평균 %.1f (순위 단위 · n=%d)"
          % (st.mean(vs), st.median(vs), st.mean([abs(v) for v in vs]), len(vs)))
    print("     🔴 **평균이 0 근처면 계통 편향은 없다** — 개별로만 갈린다")

    print("\n  ── §6j 의 +$83 을 만드는 이름들 ──")
    print("     %-24s %6s %8s %8s %8s  %s"
          % ("선수", "작년가", "가격순위", "25-26순위", "잔차", "읽는 법"))
    focus = ["Alperen Şengün", "Karl-Anthony Towns", "Dyson Daniels",
             "Domantas Sabonis", "Evan Mobley", "Ivica Zubac", "Josh Hart", "Trae Young"]
    for n in focus:
        if n not in res:
            print("     %-24s %6s  (두 시즌 실측이 없어 검증 불가)"
                  % (n[:24], "$%d" % priced.get(n, 0)))
            continue
        d = res[n]
        read = ("**기대 미달 → 올해 덜 불릴 것**" if d >= 15 else
                ("기대 초과 → 올해 더 불릴 것" if d <= -15 else "기대대로 → 배율 유효"))
        print("     %-24s %6d %8d %8d %+8d  %s"
              % (n[:24], priced[n], rp[n] + 1, rz26[n] + 1, d, read))

    print("\n  ── 잔차가 가장 큰 쪽 (가격보다 못한 순) ──")
    for n in sorted(res, key=lambda x: -res[x])[:8]:
        print("     %-24s $%-4d 가격 %3d위 → 생산 %3d위  %+d"
              % (n[:24], priced[n], rp[n] + 1, rz26[n] + 1, res[n]))
    print("  ── 반대쪽 (가격보다 잘한 순) ──")
    for n in sorted(res, key=lambda x: res[x])[:5]:
        print("     %-24s $%-4d 가격 %3d위 → 생산 %3d위  %+d"
              % (n[:24], priced[n], rp[n] + 1, rz26[n] + 1, res[n]))

    # ── 🔴 천장: 작년 가격이 올해 가격을 얼마나 맞힐 수 있나
    #   올해 가격 ≈ f(2025-26 생산) · 작년 가격 ≈ f(2024-25 생산) 이므로,
    #   **작년 가격이 올해 가격을 맞히는 능력의 상한은 생산의 연도 간 자기상관**이다.
    #   그게 낮으면 「방이 작년처럼 부른다」 자체가 약한 가정이다.
    rprod, _, _ = spearman(z25, z26)
    print("\n  ── 🔴 천장: 생산이 해를 넘어 얼마나 유지되나 ──")
    print("     2024-25 생산  vs  2025-26 생산   ρ = **%.3f**" % rprod)
    print("     올해 가격 ≈ f(25-26 생산) 이고 작년 가격 ≈ f(24-25 생산) 이므로,")
    print("     **작년 가격이 올해 가격을 맞히는 능력의 상한이 이 값**이다.")

    # ── 대안 추정: 방이 「2025-26 생산」을 작년과 같은 방식으로 값매기면?
    #   작년의 (생산순위 → 가격) 곡선을 그대로 두고 **순위만 25-26 으로 갈아끼운다.**
    #   ⚠️ 적용하지 않는다. 「1.43 이 얼마나 흔들리나」를 보이는 용도다.
    curve = sorted(price.values(), reverse=True)           # 작년 가격 분포(곡선)
    order26 = sorted(keys, key=lambda n: -z26[n])          # 25-26 생산 순위
    repriced = {n: curve[i] for i, n in enumerate(order26)}
    cj2 = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
    print("\n  ── 대안 추정: 방이 **25-26 생산**을 작년과 같은 곡선으로 값매기면 ──")
    print("     %-5s %7s %10s %10s %8s" % ("코어", "계획", "작년가 기준", "25-26 기준", "차"))
    for co in cj2["cores"]:
        plan = a1 = a2 = 0
        unk = 0
        for sl in co["slots"]:
            cd = sl["candidates"][0]
            n, pp = cd["name"], cd["plan_price"]
            plan += pp
            if n in price:
                a1 += round(price[n] * SCALE)
                a2 += round(repriced[n] * SCALE)
            else:
                unk += 1
                a1 += pp
                a2 += pp
        print("     %-5s %7s %10s %10s %+8d  (결측 %d)"
              % (co["id"], "$%d" % plan, "$%d" % a1, "$%d" % a2, a2 - a1, unk))
    print("     ⚠️ **적용하지 않는다.** 곡선을 그대로 둔 채 순위만 갈아낀 것이고,")
    print("        올해 방이 25-26 을 어떻게 볼지는 우리가 모른다.")

    json.dump({"n": len(keys), "rho_price_vs_2024_25": round(r25, 4),
               "rho_prod_2024_25_vs_2025_26": round(rprod, 4),
               "rho_price_vs_2025_26": round(r26, 4),
               "residual_mean": round(st.mean(vs), 2),
               "residual_median": round(st.median(vs), 2),
               "residual": {n: res[n] for n in res}},
              io.open(BASE + "/data/prior_price_bias.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n⚠️ 보정하지 않았다. data/prior_price_bias.json 기록 — 판단은 조율 세션.")


if __name__ == "__main__":
    main()
