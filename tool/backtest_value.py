#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""가치 구조 백테스트 — **정보 집합만 바꾼다** (43차 · 사전 등록 채택기준 ③).

## 왜
`docs/05 §2b-7` 이 이 하네스를 한 번 썼지만 *"이 저장소가 독립 재현하지 않았습니다"* 라고
적어 뒀다. 43차의 새 구조를 채택할지 정하려면 **정직한 조건**에서 옛 구조를 이기는지
봐야 하고, 그 김에 그 각주도 해소한다.

## 설계 — 후견지명을 뺀다
```
정보 집합   2023-24 + 2024-25  (2025-26 옥션 **전에** 알 수 있던 것)
시장        2025-26 실제 낙찰가 (data/prior_auction_2025_26 · 120명)
채점        2025-26 실제 스탯   (그 시즌에 실제로 일어난 것)
상대        같은 12팀 실제 로스터
```
각 구조가 **같은 정보·같은 가격**에서 로스터를 고르고, **일어난 일**로 채점한다.
구조끼리의 차이만 남는다.

⚠️ 우리 세팅(14팀·9칸·$200)으로 조립한다. 작년은 12팀·10칸이었지만 **구조 비교**가
   목적이므로 세 구조에 같은 제약을 걸면 된다.
⚠️ 조립은 탐욕(가치/달러 내림차순 + 포지션 보정)이다. 최적해가 아니다 —
   **세 구조에 같은 조립기**를 쓰므로 비교는 유효하다.

실행:  python3 tool/backtest_value.py [iters]
"""
import csv, io, json, os, random, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM
import matchup_sim as MS
import real_opponents as RO
import value_model as VM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BB = BASE + "/data/stats_2025_26/bbref"
CB = VM.CB
CATS = VM.CATS
RATE = VM.RATE


def load(season):
    rows = {}
    for r in csv.DictReader(io.open(f"{BB}/{season}_per_game.csv", encoding="utf-8")):
        d = {}
        for k in ("GP", "MPG", "PTS", "REB", "OREB", "AST", "STL", "BLK", "TOV",
                  "FGA", "FG%", "3PM", "3PA", "3P%", "FTA", "FT%"):
            try:
                d[k] = float(r[k] or 0)
            except (TypeError, ValueError):
                d[k] = 0.0
        d["pos"] = r.get("pos") or ""
        rows[r["name"]] = d
    return rows


def blend(a, b):
    """GP 가중 혼합 — `build_measured` 와 같은 사상. 최근 시즌 ×1.5."""
    out = {}
    for n in set(a) | set(b):
        ra, rb = a.get(n), b.get(n)
        wa = (ra["GP"] * 1.5) if ra else 0.0        # 최근 시즌
        wb = rb["GP"] if rb else 0.0
        if wa + wb == 0:
            continue
        d = {}
        for k in ("PTS", "REB", "OREB", "AST", "STL", "BLK", "TOV", "FGA", "FG%",
                  "3PM", "3PA", "3P%", "FTA", "FT%", "MPG"):
            va = ra[k] if ra else 0.0
            vb = rb[k] if rb else 0.0
            d[k] = (va * wa + vb * wb) / (wa + wb)
        d["GP"] = ((ra["GP"] if ra else 0) * wa + (rb["GP"] if rb else 0) * wb) / (wa + wb)
        d["pos"] = (ra or rb)["pos"]
        d["DD"] = CM.dd_game_prob(d["PTS"], d["REB"], d["AST"])
        d["at_marginal_lift"] = (d["AST"] / d["TOV"] - CB["A/T"]["baseline_per_game"]) \
            if d["TOV"] else None
        out[n] = d
    return out


def contrib(r, cat, with_gp):
    a = (r["GP"] / 82.0) if with_gp else 1.0
    if cat == "A/T":
        L = r.get("at_marginal_lift")
        return None if L is None else L * a
    if cat in RATE:
        return (r[cat] - CB[cat]["baseline_per_game"]) * r[RATE[cat]] * a
    v = r.get(cat)
    if v is None:
        return None
    x = v * a
    return -x if cat in VM.LOWER else x


def ztable(rows, names, with_gp):
    stats = {}
    for cat in CATS:
        v = [contrib(rows[n], cat, with_gp) for n in names if n in rows]
        v = [x for x in v if x is not None]
        stats[cat] = (st.mean(v), st.pstdev(v) or 1.0)
    Z = {}
    for n in rows:
        t = 0.0
        for cat in CATS:
            x = contrib(rows[n], cat, with_gp)
            if x is None:
                continue
            m, sd = stats[cat]
            t += (x - m) / sd
        Z[n] = t
    return Z, stats


def prices():
    d = json.load(io.open(BASE + "/data/prior_auction_2025_26/results.json", encoding="utf-8"))
    out = {}
    for t in d["teams"]:
        for p in t["players"]:
            if p.get("name_en"):
                out[p["name_en"]] = p["price"]
    return out


def has(pos, ch):
    return ch in (pos or "")


def legal(sel, info):
    g = sum(1 for n in sel if has(info[n]["pos"], "G"))
    f = sum(1 for n in sel if has(info[n]["pos"], "F"))
    c = sum(1 for n in sel if has(info[n]["pos"], "C"))
    return c >= 1 and g >= 2 and f >= 2


def assemble(val, px, info, budget=200, n=9):
    """탐욕 조립 — **세 구조에 같은 조립기**를 쓴다(비교 유효성)."""
    cand = sorted([x for x in px if x in val and x in info],
                  key=lambda x: -val[x] / max(px[x], 1))
    sel, spent = [], 0
    for x in cand:
        if len(sel) >= n:
            break
        if spent + px[x] > budget:
            continue
        sel.append(x)
        spent += px[x]
    for _ in range(40):
        if legal(sel, info):
            break
        need = next((ch for ch, k in (("C", 1), ("G", 2), ("F", 2))
                     if sum(1 for s in sel if has(info[s]["pos"], ch)) < k), None)
        if need is None:
            break
        done = False
        for i in sorted(range(len(sel)), key=lambda i: val[sel[i]]):
            if has(info[sel[i]]["pos"], need):
                continue
            for x in cand:
                if x in sel or not has(info[x]["pos"], need):
                    continue
                if spent - px[sel[i]] + px[x] > budget:
                    continue
                spent += px[x] - px[sel[i]]
                sel[i] = x
                done = True
                break
            if done:
                break
        if not done:
            break
    # 🔴 **업그레이드 — 남은 예산을 가치로 바꾼다.**
    #   이게 없으면 「가치/달러」 탐욕이 싼 선수만 골라 예산을 안 쓴다.
    #   `matchup_sim.greedy` 가 30차에 같은 결함을 기록해 뒀다(가치최대 상대가 $200 중 $61만 씀).
    #   43차 1차 실행에서 **현행 구조가 $90 만 쓰고** 끝나 비교가 무효였다 —
    #   구조의 차이가 아니라 **조립기의 결함**이었다.
    for _ in range(80):
        best = None
        for i, o_ in enumerate(sel):
            for x in cand:
                if x in sel:
                    continue
                ns = spent - px[o_] + px[x]
                if ns > budget:
                    continue
                gain = val[x] - val[o_]
                if gain <= 1e-9:
                    continue
                trial = sel[:i] + [x] + sel[i + 1:]
                if not legal(trial, info):
                    continue
                if best is None or gain > best[0]:
                    best = (gain, i, x, ns)
        if best is None:
            break
        _, i, x, ns = best
        sel[i] = x
        spent = ns
    return sel, spent


def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    s24, s25, s26 = load("2023-24"), load("2024-25"), load("2025-26")
    info = blend(s25, s24)          # 옥션 전에 알 수 있던 것 (최근 = 24-25)
    px = prices()
    pool = [n for n in sorted(px, key=lambda x: -px[x]) if n in info][:126]

    zc, _ = ztable(info, pool, with_gp=True)        # 현행: GP 를 z 안쪽
    zp, stats = ztable(info, pool, with_gp=False)   # 순수: 경기당
    v_empty = sum((0.0 - stats[c][0]) / stats[c][1] for c in CATS)
    # v_repl: 정보 집합(24-25) 기준 풀 밖 중앙값 — 같은 사상
    outside = [n for n in info if n not in px]
    vr_all = st.median([zp[n] for n in outside if info[n]["GP"] >= 30 and info[n]["MPG"] >= 15]) \
        if outside else v_empty

    VAL = {
        "현행 (GP 를 z 안쪽)": zc,
        "B  순수×a + 빈칸": {n: zp[n] * (info[n]["GP"] / 82) + v_empty * (1 - info[n]["GP"] / 82)
                          for n in zp},
        "A  순수×a + FA대체": {n: zp[n] * (info[n]["GP"] / 82) + vr_all * (1 - info[n]["GP"] / 82)
                           for n in zp},
    }

    REAL, _ = RO.build()
    MGRS = sorted(REAL)
    OPP = {m: sorted(REAL[m]) for m in MGRS}
    ROWS = MS.pool()
    CM.configure(model="standard")

    print("백테스트 — 정보 %s · 시장 %s · 채점 %s"
          % ("23-24 + 24-25", "2025-26 실낙찰가", "2025-26 실제 스탯"))
    print("⚠️ 후견지명을 뺐다. 세 구조가 **같은 정보·같은 가격**에서 고르고 일어난 일로 채점한다.")
    print("가격 보유 %d명 · 정보 보유 교집합 %d명 · v_empty %.2f · v_repl %.2f\n"
          % (len(px), sum(1 for n in px if n in info), v_empty, vr_all))
    out = {}
    for label, val in VAL.items():
        sel, spent = assemble(val, px, info)
        scored = [n for n in sel if n in MS.F]
        if len(scored) < 9:
            print("  %-22s 채점 불가 — 25-26 실측이 없는 선수 %d명" % (label, 9 - len(scored)))
        per = {m: MS.simulate(sorted(scored), OPP[m], random.Random(20261020), iters, ROWS)
               for m in MGRS}
        wr = st.mean(per[m]["weekly_win_rate"] for m in MGRS)
        out[label] = {"roster": sel, "spent": spent, "win_rate": round(wr, 4),
                      "scored_n": len(scored)}
        print("%-22s $%-4d %6.2f%%  %s" % (label, spent, 100 * wr,
                                           ", ".join(x.split()[-1] for x in sel)))
    json.dump({"generated_by": "tool/backtest_value.py",
               "design": {"info": "2023-24 + 2024-25 (GP 가중 · 최근 ×1.5)",
                          "market": "2025-26 실제 낙찰가 (120명)",
                          "scoring": "2025-26 실제 스탯 · 실제 12팀 상대",
                          "roster": "14팀 세팅 9칸 $200 · 탐욕 조립(세 구조 공통)"},
               "caveat": ("탐욕 조립은 최적해가 아니다. 세 구조에 같은 조립기를 쓰므로 "
                          "**구조 비교**에는 유효하지만 절대 승률로 읽지 말 것."),
               "v_empty": round(v_empty, 3), "v_repl": round(vr_all, 3),
               "iterations": iters, "results": out},
              io.open(BASE + "/data/backtest_value.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/backtest_value.json 기록")


if __name__ == "__main__":
    main()
