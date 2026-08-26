#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAT 비의존 로스터 탐색 (39차) — 실제 12팀 목적함수.

## 왜 필요한가
KAT은 **c1·c6·c7 세 코어의 앵커**다. 그가 비싸지면 예산이 먼저 막는다:

```
코어   계획가  총액   예비비   I22 위반선까지 KAT 상한   우선
c6     $45   $191   $9      **$50**                 2 (기본값)
c1     $45   $188   $12     $53                     1
c7     $45   $184   $16     $57                     0
```

**KAT > $57 이면 세 코어 전부 깨진다.** 그런데 판단표에는 갈 곳이 없다 —
c4는 "앵커를 못 잡았을 때"이지 "KAT이 비쌀 때"가 아니고, c7은 `hot_bigs` 분기로만
도달하므로 **정상 시장에서 KAT이 비싸면 표가 무력하다.**

기존 `cores.json.kat_single_point.noKAT-N1`은 **maximin으로 탐색된** 로스터다.
39차에 1차 지표를 실제 12팀으로 바꿨으므로 그 목적함수로 다시 탐색한다.

실행: python3 tool/nokat_search.py [프리필터] [탐색시행] [확정시행]
파일을 쓰지 않는다.
"""
import io, json, os, random, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE + "/tool")
import cat_model as CM, matchup_sim as MS, real_opponents as RO

PRE   = int(sys.argv[1]) if len(sys.argv) > 1 else 40
IT1   = int(sys.argv[2]) if len(sys.argv) > 2 else 800
IT2   = int(sys.argv[3]) if len(sys.argv) > 3 else 12000
TRIES = int(os.environ.get("NOKAT_TRIES", "40000"))
SEEDS = (20261020, 777, 31337)

PL = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
CJ = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
FM = json.load(io.open(BASE + "/data/stats_2025_26/measured_full.json", encoding="utf-8"))["players"]
REAL, _ = RO.build(); ROWS = MS.pool()

BAN = {"Karl-Anthony Towns"}          # 이 탐색의 정의
RESERVE_MIN, MAXTOT = 8, 192

def mid(n):
    p = PL[n]; return round((p["market_low"] + p["market_high"]) / 2)

def slot_fit_ok(names):
    """9슬롯(PG SG SF PF C UTIL×2 BN×2)을 **야후 자격**으로 동시에 채울 수 있는가.

    🔴 39차 정정: 처음엔 BBRef 주 포지션(PG/SG/SF/PF/C)을 1:1로 강제했다. **틀렸다** —
    BBRef는 선수당 주 포지션 1개만 주고 야후 자격은 다중이다(Bane BBRef `SG` ↔ 야후 `G/F`).
    그 결과 SF가 24명뿐인 BBRef 분류에서 SF 슬롯이 병목이 되어, **실측 84.0%인 noKAT-N1이
    제약에서 걸러졌다.** 검증기(`validate.py` NEED)와 툴(`slotOK`)이 쓰는 규칙으로 통일한다:
        PG·SG → G · SF·PF → F · C → C · UTIL·BN 무제약
    """
    need = ["PG", "SG", "SF", "PF", "C"]
    req = {"PG": "G", "SG": "G", "SF": "F", "PF": "F", "C": "C"}
    used = set()
    def go(i):
        if i == len(need): return True
        for n in names:
            if n in used: continue
            if req[need[i]] not in (PL[n].get("pos") or ""): continue
            used.add(n)
            if go(i + 1): return True
            used.discard(n)
        return False
    return go(0)


def ok(names):
    if len(set(names)) != 9: return None
    if set(names) & BAN: return None
    tot = sum(mid(n) for n in names)
    if not (180 <= tot <= MAXTOT): return None
    has = lambda ch: sum(1 for n in names if ch in (PL[n].get("pos") or ""))
    if has("C") < 2 or has("G") < 2 or has("F") < 2: return None
    pr = sorted(names, key=mid)
    if sum(mid(n) for n in pr[:2]) > 20: return None
    if set(sorted(names, key=lambda n: -mid(n))[:2]) & set(pr[:2]): return None
    if not slot_fit_ok(names): return None
    return tot

POOL = [n for n, p in PL.items()
        if n not in BAN and p.get("obtainable") and not p.get("injury_exclude")
        and p["my_max"] >= mid(n) and n in FM]

B = CM.baselines()
def pre_score(names):
    marg, wins, _w, _l = CM.evaluate(names, B)
    rel = 0.0
    for cat, v in marg.items():
        if v is None or v <= 0: continue
        r = CM.rel_margin(cat, v, B, names)
        if r: rel += r
    return (wins, rel)

def real(names, seed, iters):
    wr = [MS.simulate(list(names), r, random.Random(seed), iters, ROWS)["weekly_win_rate"]
          for r in REAL.values()]
    return sum(wr) / len(wr), min(wr)

def hill(names, rng, rounds=6):
    cur = list(names); best = pre_score(cur)
    for _ in range(rounds):
        moved = False
        order = list(range(9)); rng.shuffle(order)
        for i in order:
            for n in rng.sample(POOL, min(60, len(POOL))):
                if n in cur: continue
                t = list(cur); t[i] = n
                if not ok(t): continue
                sc = pre_score(t)
                if sc > best: cur, best, moved = t, sc, True; break
            if moved: break
        if not moved: break
    return cur

def build(rng):
    got = {}
    for _ in range(TRIES):
        pick = []; budget = MAXTOT
        for n in rng.sample(POOL, len(POOL)):
            if len(pick) == 9: break
            if n in pick: continue
            if mid(n) > budget - (8 - len(pick)): continue
            pick.append(n); budget -= mid(n)
        if len(pick) == 9 and ok(pick): got[tuple(sorted(pick))] = pick
    return list(got.values())

if __name__ == "__main__":
    rng = random.Random(20261020)
    cands = build(rng)
    # 🔴 무앵커 탐색은 랜덤 그리디의 적중률이 낮다(40,000시행 → 224조합). 「얕은 탐색이
    #    답을 놓친다」 함정 그대로다. **알려진 최선(구 noKAT-N1)을 등반 시작점으로 넣는다** —
    #    거기서 올라가는 것이 무작위 재시작보다 훨씬 강하다.
    known = CJ["kat_single_point"]["best_without_KAT"]["roster"]
    if ok(known):
        cands.insert(0, list(known))
        for _ in range(40):                     # 같은 시작점에서 여러 번 등반(무작위 순서)
            cands.append(list(known))
    else:
        print("⚠ 구 noKAT-N1이 현재 제약을 통과하지 않는다 — 시작점 제외")
    seen = {tuple(sorted(r)) for r in cands}
    climbed = []
    for r in cands:
        h = hill(r, rng); k = tuple(sorted(h))
        if k not in seen: seen.add(k); climbed.append(h)
    cands += climbed
    print("KAT 제외 · 후보 풀 %d명 · 제약 통과 %d개(등반 추가 %d) · 프리필터 상위 %d 시뮬"
          % (len(POOL), len(cands), len(climbed), PRE))
    if not cands: print("조합 없음"); raise SystemExit(1)
    cands.sort(key=pre_score, reverse=True)
    rows = sorted([(real(r, SEEDS[0], IT1), r) for r in cands[:PRE]], reverse=True)
    print("\n[1차 %d시행] 상위 6" % IT1)
    for (a, m), r in rows[:6]:
        print("  %5.1f%% / %5.1f%%  $%-4d 예비 $%-3d  %s"
              % (a*100, m*100, sum(mid(n) for n in r), 200-sum(mid(n) for n in r),
                 ", ".join(n.split()[-1] for n in r)))
    # 기준선: c6 / c7 / 기존 noKAT-N1
    def core(cid): return [s["candidates"][0]["name"] for s in
                           next(c for c in CJ["cores"] if c["id"] == cid)["slots"]]
    old = CJ["kat_single_point"]["best_without_KAT"]["roster"]
    print("\n[🔴 재대조 %d시행 · 시드 3종]" % IT2)
    print("  %-18s %-22s %-22s %s" % ("안", "평균 (3시드)", "최저 (3시드)", "총액/예비"))
    for lbl, r in ([("c6 (기준선)", core("c6")), ("c7", core("c7")),
                    ("구 noKAT-N1", old)]
                   + [("신 후보%d" % (i+1), x[1]) for i, x in enumerate(rows[:3])]):
        A = []; M = []
        for s in SEEDS:
            a, m = real(r, s, IT2); A.append(a); M.append(m)
        t = sum(mid(n) for n in r)
        print("  %-18s %-22s %-22s $%d/$%d"
              % (lbl, " ".join("%.1f" % (v*100) for v in A),
                 " ".join("%.1f" % (v*100) for v in M), t, 200-t))
        if lbl.startswith("신 후보"): print("      " + ", ".join(r))
