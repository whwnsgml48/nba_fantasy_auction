#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""가드 편향 구간의 **상한**을 정확 DP 로 센다 (5·6차 신설).

무엇을 왜
  4차까지 「가드 빌드를 찾아라」가 네 번 다 Jokić 으로 수렴했고, 조율 세션의 가설은
  **「빅맨 생산은 C/PF 자격에서만 나온다 → 가드 편향은 5캣 포기를 강제한다」** 였다.
  탐색은 실패를 증명하지 못한다(못 찾은 것과 없는 것이 구분 안 된다). 그래서
  코어를 만들지 않고 **캣별 상한**만 잰다 — 상한이 낮으면 그 캣은 확실히 죽는다.

🔴 결과 — 가설은 기각됐다
  ┌ 캣    (a)Jokić허용  (b)Jokić제외  (c)빅지출≤$40  (대조)제약없음  눈금자 c6
  │ REB      94.1%        94.1%         93.0%          99.8%        95.4%
  │ FG%      92.9%        92.9%         92.1%         100.0%        59.6%
  │ OREB     97.9%        97.9%         97.8%         100.0%        98.2%
  │ BLK      91.0%        91.0%         91.1%          98.4%        80.0%
  │ DD       92.4%        92.4%         92.4%          99.3%        78.2%
  └ 죽는 캣(<50%) : (a) 0/5 · (b) 0/5 · (c) 0/5
  빅맨 캣이 가드에서 나온다 — OREB 는 Amen Thompson·Daniels·Hart·Edgecombe,
  BLK 는 Amen·Daniels·D.White·Sheppard, DD 는 Harden·Trae·Haliburton·Giddey.

🔴 상한은 **낙폭으로** 읽는다 — 절대 바는 상대 집합의 난이도에 따라 무의미해진다
  「상한 < 50% 면 죽는다」는 이 12팀 상대로 **거의 안 걸리는 바**다. c6 자신의 다섯 캣도
  59.6~98.2% 이고 제약 없는 상한은 98~100% 다. 쓸 수 있는 양은 **제약 없는 상한 대비 낙폭**
  이고, 이번 낙폭은 REB −5.7 · FG% −7.1 · OREB −2.1 · BLK −7.4 · DD −6.9 %p 다 —
  **제약은 비용이 있지만 캣을 죽이지 않는다.**

⚠️ Jokić 이 10개 최적해에 하나도 안 든 것으로 「탐색이 구간을 못 찾았다」를 주장하지 말 것
  (조율 세션 반려 · 타당하다). **단일 캣 목적함수는 구조적으로 스페셜리스트를 고르고
  제너럴리스트를 버린다.** Jokić 의 값은 한 칸이 여러 캣을 동시에 주는 것이고 단일 캣
  DP 가 정의상 못 보는 양이다. c2 가 그를 $97 에 쓰고 86.5% 인 것과 모순이 아니다.

하네스 대조 (3000시행 · 저장본 16000) — 다른 경로로 재고 있지 않다
  c6        주간    REB    FG%   OREB   BLK    DD
  이 파일   87.4%  95.4   59.6   98.2   80.0  78.2
  저장본    87.6%  95.4   60.5   98.4   80.0  78.3

방법 — 40차 탐색 4연속 실패(합산 z · 정규화 없는 z · 달러당 정렬 · 한쪽 정렬)의 원인 제거
  · z 를 안 쓴다. 정렬도 그리디도 안 쓴다.
  · 시뮬레이터가 실제로 비교하는 양(주간 팀 합계)을 목적함수로 두고 **정확 DP** 로 센다.
  · 비율캣은 가산이 아니므로 **Dinkelbach**: Σ 시도(비율 − λ) 를 풀고 λ 를 수렴시킨다.
  · 빅 **지출** 제약은 2단계 DP 로 푼다 — 빅을 먼저 처리하면 그 단계의 지출이 곧 빅 지출이라
    차원을 추가할 필요가 없다(여전히 정확해).
  🔴 1차 구현은 **같은 선수를 세 번 뽑았다**(Josh Hart ×3). 상태에 선택 집합이 없는데
     역추적을 최종 dict 에서 했기 때문이다. 이제 선택 튜플을 상태에 들고 가고 매 해에
     중복·자격·예산을 assert 한다.

`docs/11` ⑦(후보 풀을 한 축으로 정렬하면 반드시 깨진다)과의 관계
  ⑦ 는 `tool/search_pool.mix_axes` 를 거치라고 요구한다. **여기서는 안 쓴다 — 쓰면 오히려
  틀린다.** ⑦ 의 위험은 「후보를 골라서 좁힌다」에서 나오는데 이 파일은 **좁히지 않는다**:
  획득 가능 140명 **전원**을 DP 에 넣고 최적해를 센다. 풀 믹서를 끼우면 후보를 **제거**하게
  되어 정확해가 깨진다. ⑦ 이 막으려는 실패(예산 초과·미소진·조합 0개)는 예산을 DP 상태에
  넣어 구조적으로 막는다. 퇴화 해 방지 `SP.assert_spend_band` 는 그대로 쓴다.

사용법
  python3 tool/guard_ceiling_dp.py caps   [iters]        (a)(b)(c)+대조+눈금자
  python3 tool/guard_ceiling_dp.py weekly [iters] [seed] [max_ls]
        6차 — 주간 승률 직접 최대화. max_ls = 가정 노출(실측비중<0.5) 허용 인원
"""
import json, io, os, sys, random, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cat_model as CM, matchup_sim as MS, pos_elig as PE, real_opponents as RO
import search_pool as SP    # docs/11 ⑦ — 퇴화 해 방지용 assert 만 쓴다(위 머리말 참조)

F, PL = CM.F, MS.PL
REAL, _ = RO.build()
BUD2 = 400                       # $200 을 0.5달러 단위로
C6 = ["Karl-Anthony Towns", "Derrick White", "Alperen Şengün", "Amen Thompson",
      "Desmond Bane", "Dyson Daniels", "DeMar DeRozan", "Rudy Gobert", "VJ Edgecombe"]
RATE_ATT = {"FG%": "FGA", "FT%": "FTA", "3P%": "3PA"}
COUNTC   = ["PTS", "REB", "OREB", "AST", "STL", "BLK", "3PM"]
MIXCATS  = COUNTC + ["TOV", "DD"] + list(RATE_ATT)      # 12캣 (A/T 는 AST·TOV 로 결정)

CAND = []
for _n, _p in PL.items():
    _r = F.get(_n)
    if not _r or _p.get("obtainable") is False:
        continue
    _e = PE.elig(_p)
    if not (_e & {"PF", "C"}) and not (_e & {"PG", "SG"}):
        continue                                   # SF 전용은 제약상 못 넣는다
    _c2 = int(round(_p["market_low"] + _p["market_high"]))
    CAND.append({
        "n": _n, "c2": _c2, "cost": _c2 / 2.0, "e": _e, "r": _r,
        "av": (_r.get("GP") or 0) / 82.0,
        "big": bool(_e & {"PF", "C"}), "hasC": "C" in _e,
        "share": ((_p.get("measured_source") or {}).get("blend_share_2025_26")),
        "edge": (_p.get("my_max") or 0) - round((_p.get("prior_auction_price") or 0) * 1.11)
                if _p.get("prior_auction_price") else None,
    })
BIGS   = [i for i in range(len(CAND)) if CAND[i]["big"]]
GUARDS = [i for i in range(len(CAND)) if not CAND[i]["big"]]
LOWSH  = [i for i in range(len(CAND)) if (CAND[i]["share"] is not None
                                          and CAND[i]["share"] < 0.50)]
_LS = set(LOWSH)


def contrib(x, cat):
    r = x["r"]
    if cat == "DD":
        return x["av"] * CM.dd_game_prob(r.get("PTS"), r.get("REB"), r.get("AST"))
    if cat == "TOV":
        return -x["av"] * (r.get("TOV") or 0.0)
    return x["av"] * (r.get(cat) or 0.0)


def rate_parts(x, cat):
    a = x["av"] * (x["r"].get(RATE_ATT[cat]) or 0.0)
    return a, a * (x["r"].get(cat) or 0.0)


def dp(vals, big2=BUD2, tot2=BUD2, min2=0, max_ls=9, exclude=()):
    """정확 2단계 0/1 DP. 9명 · C 정확히 1 · 빅 ≤3 · 빅지출 ≤big2 · min2 ≤ 총액 ≤ tot2
       · 실측비중<0.5 인 선수 ≤max_ls 명."""
    st = {(0, 0, 0, 0): (0.0, ())}                    # (k, c, spend, lowshare)
    for i in BIGS:
        x = CAND[i]
        if x["n"] in exclude: continue
        v = vals[i]; nx = dict(st)
        for (k, c, s, l), (val, pk) in st.items():
            if k >= 3: continue
            nc = c + (1 if x["hasC"] else 0); ns = s + x["c2"]
            nl = l + (1 if i in _LS else 0)
            if nc > 1 or ns > big2 or nl > max_ls: continue
            key = (k + 1, nc, ns, nl); nv = val + v
            cur = nx.get(key)
            if cur is None or nv > cur[0]: nx[key] = (nv, pk + (i,))
        st = nx
    cur = {(k, s, l): (v, p) for (k, c, s, l), (v, p) in st.items() if c == 1}
    if not cur: return None
    for i in GUARDS:
        x = CAND[i]
        if x["n"] in exclude: continue
        v = vals[i]; nx = dict(cur)
        for (k, s, l), (val, pk) in cur.items():
            if k >= 9: continue
            ns = s + x["c2"]; nl = l + (1 if i in _LS else 0)
            if ns > tot2 or nl > max_ls: continue
            key = (k + 1, ns, nl); nv = val + v
            c0 = nx.get(key)
            if c0 is None or nv > c0[0]: nx[key] = (nv, pk + (i,))
        cur = nx
    out = None
    for (k, s, l), (val, pk) in cur.items():
        if k == 9 and s >= min2 and (out is None or val > out[0]): out = (val, pk)
    if out is None: return None
    sel = [CAND[i] for i in out[1]]
    assert len({x["n"] for x in sel}) == 9, "중복 선수"
    assert sum(1 for x in sel if x["hasC"]) == 1 and sum(1 for x in sel if x["big"]) <= 3
    assert sum(x["c2"] for x in sel if x["big"]) <= big2
    assert min2 <= sum(x["c2"] for x in sel) <= tot2
    assert sum(1 for x in sel if x["n"] in {CAND[i]["n"] for i in LOWSH}) <= max_ls
    return out[0], sel


def solve_cat(cat, **kw):
    """단일 캣 최대화. 비율캣은 Dinkelbach."""
    if cat not in RATE_ATT:
        return dp([contrib(x, cat) for x in CAND], **kw)
    lam, sel = 0.5, None
    for _ in range(25):
        r = dp([rate_parts(x, cat)[1] - lam * rate_parts(x, cat)[0] for x in CAND], **kw)
        if r is None: return None
        _, sel = r
        A = sum(rate_parts(x, cat)[0] for x in sel)
        M = sum(rate_parts(x, cat)[1] for x in sel)
        new = M / A if A else 0.0
        if abs(new - lam) < 1e-9: return new, sel
        lam = new
    return lam, sel


def sim(names, iters, seed=20261020):
    """실제 12팀 각각에 대해 시뮬. 상대별 주간 승률 벡터까지 돌려준다(대응 SE 용)."""
    per, acc, ec, sd = {}, {}, [], []
    for mgr, opp in REAL.items():
        o = MS.simulate(list(names), opp, random.Random(seed), iters, None)
        per[mgr] = o["weekly_win_rate"]
        for k, v in o["cat_win_probs"].items(): acc.setdefault(k, []).append(v)
        ec.append(o["expected_cats_won"]); sd.append(o["cats_won_sd"])
    return {"per": per, "weekly": sum(per.values()) / len(per),
            "cats": {k: sum(v) / len(v) for k, v in acc.items()},
            "cats_min": {k: min(v) for k, v in acc.items()},
            "exp_cats": sum(ec) / len(ec), "sd": sum(sd) / len(sd)}


def paired(a, b):
    """두 로스터의 대응 SE 와 σ. 같은 12팀에 붙였으므로 상대 강약이 상쇄된다."""
    d = [a["per"][m] - b["per"][m] for m in a["per"]]
    md = statistics.mean(d)
    se = statistics.stdev(d) / (len(d) ** 0.5) if len(d) > 1 else 0.0
    return md, se, (abs(md) / se if se else float("inf"))


# ── 모드 1: 캣별 상한 (5차) ──────────────────────────────────────────────
CAP5 = ["REB", "FG%", "OREB", "BLK", "DD"]

def run_caps(iters):
    print("후보 %d명 · 시행 %d × 실제 12팀 · 가격 = 시장 중간값" % (len(CAND), iters))
    g6 = sim(C6, iters)
    print("\n눈금자 c6 — 주간 %.1f%% · " % (100 * g6["weekly"])
          + " · ".join("%s %.1f%%" % (k, 100 * g6["cats"][k]) for k in CAP5))
    res = {}
    modes = [("a", dict(), ()), ("b", dict(), ("Nikola Jokić",)),
             ("c", dict(big2=80), ()), ("free", "FREE", ())]
    for tag, kw, exc in modes:
        print("\n" + "=" * 74)
        print({"a": "(a) 가드 제약 · Jokić 허용", "b": "(b) 가드 제약 · Jokić 제외",
               "c": "(c) 가드 제약 + 빅 지출 ≤$40", "free": "(대조) 제약 없음"}[tag])
        print("=" * 74)
        for cat in CAP5:
            if kw == "FREE":
                r = solve_cat(cat, big2=BUD2, max_ls=9)          # 빅 제약만 사실상 해제
            else:
                r = solve_cat(cat, exclude=exc, **kw)
            if r is None: print("%-5s 조합 없음" % cat); continue
            _, sel = r
            names = [x["n"] for x in sel]
            o = sim(names, iters)
            bs = sum(x["cost"] for x in sel if x["big"])
            res[(tag, cat)] = o["cats"][cat]
            print("\n%-5s 상한 **%.1f%%** (12팀 최저 %.1f) · 총액 $%.1f · 빅지출 $%.0f "
                  "· 이 로스터의 주간 %.1f%% · Jokić %s"
                  % (cat, 100 * o["cats"][cat], 100 * o["cats_min"][cat],
                     sum(x["cost"] for x in sel), bs, 100 * o["weekly"],
                     "포함" if "Nikola Jokić" in names else "없음"))
            for x in sorted(sel, key=lambda y: -y["cost"]):
                print("      $%-5.1f %-24s %-14s%s"
                      % (x["cost"], x["n"], "/".join(sorted(x["e"])),
                         "  ← 빅" if x["big"] else ""))
    print("\n%-6s %9s %9s %9s %9s %9s" % ("캣", "(a)", "(b)", "(c)", "제약없음", "c6"))
    for cat in CAP5:
        print("%-6s %8.1f%% %8.1f%% %8.1f%% %8.1f%% %8.1f%%"
              % (cat, 100*res[("a",cat)], 100*res[("b",cat)], 100*res[("c",cat)],
                 100*res[("free",cat)], 100*g6["cats"][cat]))
    print("낙폭(제약없음 − (c)): " + " · ".join(
        "%s %+.1f%%p" % (c, 100*(res[("c",c)] - res[("free",c)])) for c in CAP5))


# ── 모드 2: 주간 승률 직접 최대화 (6차) ──────────────────────────────────
# 🔴 주간 승률은 가산이 아니라 DP 로 직접 못 푼다. DP 를 **후보 생성기**로만 쓰고
#    판정은 전부 시뮬레이터가 한다. 그리디로 좁히지 않는다(4연속 실패의 형태).
SIX = dict(big2=80, tot2=392, min2=380, max_ls=1)   # 빅≤$40 · 총액 $190~196 · 가정≤1

def _lam(cat):
    a = sum(rate_parts(x, cat)[0] for x in CAND)
    return sum(rate_parts(x, cat)[1] for x in CAND) / a if a else 0.0

def _mixvals(w, lam, norm):
    out = []
    for x in CAND:
        v = 0.0
        for c, wc in w.items():
            if not wc: continue
            if c in RATE_ATT:
                a, m = rate_parts(x, c); v += wc * norm[c] * (m - lam[c] * a)
            else:
                v += wc * norm[c] * contrib(x, c)
        out.append(v)
    return out

def run_weekly(iters, seed, max_ls=1):
    SIX["max_ls"] = max_ls
    rng = random.Random(seed)
    lam = {c: _lam(c) for c in RATE_ATT}
    norm = {}
    for c in MIXCATS:
        if c in RATE_ATT:
            r = dp([rate_parts(x, c)[1] - lam[c] * rate_parts(x, c)[0] for x in CAND], **SIX)
        else:
            r = dp([contrib(x, c) for x in CAND], **SIX)
        norm[c] = 1.0 / abs(r[0]) if r and abs(r[0]) > 1e-9 else 0.0
    # 후보 생성 — 단일캣 + 균등 + 3캣 포기 + 디리클레
    Ws = [{c: (1.0 if c == k else 0.0) for c in MIXCATS} for k in MIXCATS]
    Ws.append({c: 1.0 for c in MIXCATS})
    for _ in range(60):
        drop = set(rng.sample(MIXCATS, 3))
        Ws.append({c: (0.0 if c in drop else 1.0) for c in MIXCATS})
    for _ in range(900):
        g = [rng.gammavariate(0.7, 1.0) for _ in MIXCATS]
        s = sum(g) or 1.0
        Ws.append({c: g[i] / s for i, c in enumerate(MIXCATS)})
    seen, cands = set(), []
    for w in Ws:
        r = dp(_mixvals(w, lam, norm), **SIX)
        if r is None: continue
        key = frozenset(x["n"] for x in r[1])
        if key in seen: continue
        seen.add(key); cands.append(r[1])
    print("가중 벡터 %d개 → 서로 다른 로스터 **%d개** (제약: 빅지출≤$40 · 총액 $190~196 "
          "· C정확히1 · 빅≤3 · 가정≤1)" % (len(Ws), len(cands)))
    t1 = sorted(((sim([x["n"] for x in s], 400)["weekly"], s) for s in cands),
                key=lambda t: -t[0])
    print("1차(400시행) 상위: " + " · ".join("%.1f%%" % (100*w) for w, _ in t1[:8]))
    t2 = sorted(((sim([x["n"] for x in s], 3000)["weekly"], s) for _, s in t1[:30]),
                key=lambda t: -t[0])
    print("2차(3000시행) 상위: " + " · ".join("%.1f%%" % (100*w) for w, _ in t2[:8]))
    fin = [(sim([x["n"] for x in s], iters), s) for _, s in t2[:6]]
    fin.sort(key=lambda t: -t[0]["weekly"])
    g6 = sim(C6, iters); g2 = sim(
        ["Nikola Jokić", "Derrick White", "Desmond Bane", "Onyeka Okongwu",
         "Collin Gillespie", "Donovan Clingan", "DeMar DeRozan",
         "Nikola Vučević", "Immanuel Quickley"], iters)
    print("\n눈금자(%d시행): c6 %.1f%% · c2 %.1f%%" % (iters, 100*g6["weekly"], 100*g2["weekly"]))
    for rank, (o, sel) in enumerate(fin[:3], 1):
        names = [x["n"] for x in sel]
        tot = sum(x["cost"] for x in sel)
        SP.assert_spend_band(tot, 190, 196, "6차 가드 상한")
        md6, se6, s6 = paired(o, g6); md2, se2, s2 = paired(o, g2)
        ls = [x["n"] for x in sel if x["share"] is not None and x["share"] < 0.5]
        edges = [(x["n"], x["edge"]) for x in sel if x["edge"] is not None]
        print("\n" + "=" * 74)
        print("후보 %d — 주간 **%.1f%%** (12팀 최저 %.1f%%) · 총액 $%.1f · 예비 $%.1f"
              % (rank, 100*o["weekly"], 100*min(o["per"].values()), tot, 200-tot))
        print("=" * 74)
        for x in sorted(sel, key=lambda y: -y["cost"]):
            print("  $%-5.1f %-24s %-14s%s" % (x["cost"], x["n"],
                  "/".join(sorted(x["e"])), "  ← 빅" if x["big"] else ""))
        print("  빅 지출 $%.0f · C 자격 %d명 · 슬롯 매칭 %s"
              % (sum(x["cost"] for x in sel if x["big"]),
                 sum(1 for x in sel if x["hasC"]),
                 "성립" if PE.match([PL[n] for n in names]) else "🔴 불성립"))
        print("  13캣: " + " · ".join("%s %.0f%%" % (k, 100*v)
              for k, v in sorted(o["cats"].items(), key=lambda t: -t[1])))
        print("  기대 캣 %.2f · SD %.2f · (기대−7)/SD = **%.2f**"
              % (o["exp_cats"], o["sd"], (o["exp_cats"] - 7) / o["sd"]))
        print("  가정 노출(실측비중<0.5): %s" % (", ".join(ls) if ls else "**0명**"))
        print("  edge_vs_prior 합 %+d · 음수 %d명 %s"
              % (sum(e for _, e in edges), sum(1 for _, e in edges if e < 0),
                 [f"{n}{e:+d}" for n, e in sorted(edges, key=lambda t: t[1])[:3]]))
        print("  vs c6  %+.2f%%p · 대응SE %.2f%%p · **%.2fσ**" % (100*md6, 100*se6, s6))
        print("  vs c2  %+.2f%%p · 대응SE %.2f%%p · **%.2fσ**" % (100*md2, 100*se2, s2))
        print("  c2 와 겹치는 인원 %d · Jokić %s"
              % (len(set(names) & set(g2sel())), "포함" if "Nikola Jokić" in names else "없음"))

def g2sel():
    return ["Nikola Jokić", "Derrick White", "Desmond Bane", "Onyeka Okongwu",
            "Collin Gillespie", "Donovan Clingan", "DeMar DeRozan",
            "Nikola Vučević", "Immanuel Quickley"]

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "caps"
    it = int(sys.argv[2]) if len(sys.argv) > 2 else (3000 if mode == "caps" else 12000)
    if mode == "caps": run_caps(it)
    else: run_weekly(it, int(sys.argv[3]) if len(sys.argv) > 3 else 20261020,
                     int(sys.argv[4]) if len(sys.argv) > 4 else 1)
