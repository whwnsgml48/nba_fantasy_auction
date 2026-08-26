#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c2 재설계 탐색 (39차) — Jokić 앵커 고정 · **코어 간 겹침 제약** 하에서 실제 12팀 최적화.

## 왜 겹침 제약이 핵심인가
평가 세션이 준 출발점(91.3%)은 Şengün·Gobert·Okongwu·Hart·Vučević를 쓰는데 이것들이
**c6·c7과 크게 겹칩니다.** 조건부 코어의 존재 이유는 *"다른 시장에서 다른 답"* 이지
*"같은 답을 비싸게"* 가 아닙니다. 옥션에서 한 명만 잡히면 둘 중 하나는 못 씁니다.

→ c6 base ∪ c7 base ∪ c7 pivot 과 **4명 이상 공유 금지**(Jokić 제외 8칸에서 셈).

## 사전 확약 수용 기준 (평가 세션 · 결과 보기 전에 고정)
  ① 실제 12팀 평균 ≥ 현행 + 8%p       ② 최저 ≥ 65% 이고 현행 초과
  ③ 12000시행 이상 · 시드 3종 유지     ④ 예비비 ≥ $8 · BBRef 5슬롯 충족
  ⑤ 겹침 ≤ 3명                        ⑥ 피벗도 함께 제시

## 방법
1. cat_model 한계기여로 **결정론적 프리필터** — 시뮬은 비싸다(랜덤 조합 전수는 불가)
2. 상위 N개만 실제 12팀 저시행 랭킹
3. 상위 3개를 **같은 스트림 고시행**으로 재대조 (34차 승자의 저주)

실행: python3 tool/c2_search.py [프리필터수] [탐색시행] [확정시행]
파일을 쓰지 않는다 — 후보만 출력한다.
"""
import io, json, os, random, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE + "/tool")
import cat_model as CM, matchup_sim as MS, real_opponents as RO

PRE   = int(sys.argv[1]) if len(sys.argv) > 1 else 40
IT1   = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
IT2   = int(sys.argv[3]) if len(sys.argv) > 3 else 12000
SEEDS = (20261020, 777, 31337)

PL = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
CJ = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
FM = json.load(io.open(BASE + "/data/stats_2025_26/measured_full.json", encoding="utf-8"))["players"]
REAL, _ = RO.build()
ROWS = MS.pool()

ANCHOR = "Nikola Jokić"
RESERVE_MIN = 8                      # 기준 ④
MAXTOT = 200 - RESERVE_MIN
OVERLAP_MAX = 3                      # 기준 ⑤

def mid(n):
    p = PL[n]; return round((p["market_low"] + p["market_high"]) / 2)

def core(cid): return [s["candidates"][0]["name"] for s in
                       next(c for c in CJ["cores"] if c["id"] == cid)["slots"]]
def pivot(cid): return [r["name"] for r in
                        next(c for c in CJ["cores"] if c["id"] == cid)["pivot_plan"]["final_roster"]]

FORBID = set(core("c6")) | set(core("c7")) | set(pivot("c7"))
FORBID.discard(ANCHOR)
CUR = core("c2")

# 후보 풀 — 획득 가능 · 부상 제외 아님 · my_max >= 시장중간(규율)
POOL = [n for n, p in PL.items()
        if n != ANCHOR and p.get("obtainable") and not p.get("injury_exclude")
        and p["my_max"] >= mid(n) and n in FM]

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
    tot = sum(mid(n) for n in names)
    if not (180 <= tot <= MAXTOT): return None
    has = lambda ch: sum(1 for n in names if ch in (PL[n].get("pos") or ""))
    if has("C") < 2 or has("G") < 2 or has("F") < 2: return None
    if len(set(names) & FORBID) > OVERLAP_MAX: return None
    pr = sorted(names, key=mid)
    if sum(mid(n) for n in pr[:2]) > 20: return None            # 벤치 <= $20
    if set(sorted(names, key=lambda n: -mid(n))[:2]) & set(pr[:2]): return None
    if not slot_fit_ok(names): return None
    return tot

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
    """cat_model 점수로 단일 교체 상승 탐색 (결정론적·빠름).

    실제 12팀 시뮬로 등반하면 한 패스에 수 분이 걸린다. **음성 결과를 주장하려면
    탐색이 얕아선 안 되므로** 빠른 대리 점수로 국소 최적까지 밀고, 시뮬은 그 결과에만 쓴다.
    """
    cur = list(names); best = pre_score(cur)
    for _ in range(rounds):
        moved = False
        order = list(range(1, 9)); rng.shuffle(order)      # 0번은 앵커 고정
        for i in order:
            for n in rng.sample(POOL, min(60, len(POOL))):
                if n in cur: continue
                trial = list(cur); trial[i] = n
                if not ok(trial): continue
                sc = pre_score(trial)
                if sc > best:
                    cur, best, moved = trial, sc, True
                    break
            if moved: break
        if not moved: break
    return cur


def build_random(rng, tries=4000):
    """랜덤 그리디 — 제약을 만족하는 조합을 모은다."""
    got = {}
    for _ in range(tries):
        pick = [ANCHOR]
        budget = MAXTOT - mid(ANCHOR)
        pool = rng.sample(POOL, len(POOL))
        for n in pool:
            if len(pick) == 9: break
            if n in pick: continue
            if mid(n) > budget - (8 - len(pick)): continue     # 남은 칸 최소 $1
            if len((set(pick) | {n}) & FORBID) > OVERLAP_MAX: continue
            pick.append(n); budget -= mid(n)
        if len(pick) == 9 and ok(pick):
            got[tuple(sorted(pick))] = pick
    return list(got.values())

if __name__ == "__main__":
    rng = random.Random(20261020)
    cands = build_random(rng, tries=int(os.environ.get("C2_TRIES", "4000")))
    # 🔴 음성 결과("더 나은 조합이 없다")를 주장하려면 탐색이 얕아선 안 된다.
    #    각 조합에서 cat_model 국소 최적까지 등반해 후보 품질을 올린다.
    seen = {tuple(sorted(r)) for r in cands}
    climbed = []
    for r in cands:
        h = hill(r, rng)
        k = tuple(sorted(h))
        if k not in seen:
            seen.add(k); climbed.append(h)
    cands = cands + climbed
    print("등반으로 추가된 국소 최적 %d개" % len(climbed))
    print("겹침 금지 풀 %d명 (c6 base ∪ c7 base ∪ c7 피벗) · 후보 풀 %d명" % (len(FORBID), len(POOL)))
    print("제약 통과 조합 %d개 · 프리필터 상위 %d개만 시뮬\n" % (len(cands), PRE))
    if not cands:
        print("제약을 만족하는 조합이 없다 — 그 자체가 보고 대상이다."); raise SystemExit(1)
    cands.sort(key=pre_score, reverse=True)
    rows = []
    for r in cands[:PRE]:
        a, m = real(r, SEEDS[0], IT1)
        rows.append((a, m, r))
    rows.sort(reverse=True)
    ca, cm = real(CUR, SEEDS[0], IT1)
    print("현행 c2   평균 %.1f%% · 최저 %.1f%% · 총액 $%d · 겹침 %d명"
          % (ca*100, cm*100, sum(mid(n) for n in CUR), len(set(CUR) & FORBID)))
    print("\n[1차 탐색 %d시행] 상위 8" % IT1)
    for a, m, r in rows[:8]:
        print("  평균 %.1f%% 최저 %.1f%% $%-4d 예비 $%-3d 겹침%d  %s"
              % (a*100, m*100, sum(mid(n) for n in r), 200-sum(mid(n) for n in r),
                 len(set(r) & FORBID), ", ".join(n.split()[-1] for n in r if n != ANCHOR)))
    print("\n[🔴 재대조 %d시행 · 시드 3종] 상위 3 + 현행" % IT2)
    for lbl, r in [("후보%d" % (i+1), x[2]) for i, x in enumerate(rows[:3])] + [("현행 c2", CUR)]:
        A = []; M = []
        for s in SEEDS:
            a, m = real(r, s, IT2); A.append(a); M.append(m)
        print("  %-8s 평균 %s | 최저 %s | $%d 예비 $%d 겹침%d"
              % (lbl, " ".join("%.1f" % (v*100) for v in A),
                 " ".join("%.1f" % (v*100) for v in M),
                 sum(mid(n) for n in r), 200-sum(mid(n) for n in r), len(set(r) & FORBID)))
        if lbl.startswith("후보"): print("           " + ", ".join(r))
