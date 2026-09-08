#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자격 제약이 **몇 경기를 버리게 하는가** (40차 신설).

왜 필요한가 🔴
  `cat_model` 은 9명 전원의 스탯이 집계된다고 본다 — 선발 7칸 × 7일 = 49 슬롯-일이
  주간 29.7 선수-경기를 크게 웃돌기 때문이다. 그 계산에 **포지션 자격이 없다.**
  자격을 넣으면 그날 경기가 있는데도 넣을 칸이 없는 선수가 생기고, 그 경기는
  통째로 버려진다.

  40차에 야후 실자격 19명이 확인되면서 c3 는 SF 자격자 0명, c2 는 C 전용 5명이
  드러났다. 평가 세션은 이를 **「조립 불가」**로 불렀지만 그건 틀린 표현이다 —
  야후는 커버리지를 강제하지 않는다. 로스터는 합법이고, **그 칸이 매일 빌 뿐**이다.
  이진 판정(성립/불성립)이 아니라 **손실 크기**로 재야 한다. 이 스크립트가 그것이다.

무엇을 재는가
  주 7일. 선수 i 는 하루에 확률 `p_i = STD_WEEK_GAMES × (GP_i/82) / 7` 로 경기를 갖는다.
  🔴 **캘린더 주당**(3.279)이다. 매치업 주당(3.577)을 넣으면 하루 경합을 9% 과대평가한다 —
  긴 매치업 주는 14일이라 칸 용량도 2배이고 일일 밀도는 안 변한다.
  단일 소스 = `cat_model.STD_WEEK_GAMES` (42차에 하드코딩 제거)
  그날 경기가 있는 선수들을 선발 7칸(PG SG SF PF C UTIL UTIL)에 최대 매칭한다.
  들어가지 못한 선수의 그날 경기는 **버린다**.

    버림률   = 버린 선수-경기 / 전체 선수-경기        ← 팀 전체 생산 감소율
    사용률 u_i = 선수 i 의 경기 중 칸을 얻은 비율      ← 시뮬 가용률에 곱한다

🔴 **약 0.19%p 는 포지션과 무관한 바닥이다** (40차 경계 검증)
  자격이 전혀 없는 로스터(전원 모든 칸 가능)도 0.19% 를 버린다 — 하루에 8~9명이 동시에
  경기를 가지면 선발 7칸을 넘기 때문이다. **로스터 용량의 문제이지 자격의 문제가 아니다.**
  따라서 코어별 출력에서 그만큼은 자격 탓이 아니다: c2 base 3.16% 중 자격 기여는 ≈2.97%p.
  경계 검증 전체는 `cores.json.lineup_loss_validation_40` 참조 —
  「C 전용 3→4→5 에서 0.19% → 1.01% → 3.38% 로 가속」이 c2 진단을 합성 로스터에서 재현한다.

한계 (과소·과대 양쪽)
  · 요일 상관을 무시한다. 실제로는 팀별 일정이 겹치므로 손실이 이보다 **크다**.
  · 매일 최적 매칭을 가정한다(사람이 완벽히 세팅). 그래서 **하한**이다.
  · 상대 로스터에도 같은 제약이 있으므로 절대값보다 **차이**를 볼 것.
"""
import json, io, os, sys, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pos_elig as PE
import cat_model as CM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 🔴 42차 정정 — 여기 `GAMES_PER_WEEK = 3.299` 가 **하드코딩돼 있었다.**
#   38차가 세 파일에 흩어진 3.5 를 `cat_model` 한 곳으로 모았는데, 40차에 이 파일을
#   신설하면서 「같은 근거」라는 주석과 함께 값을 **복제**했다. 결과:
#   `cat_model.GAMES_PER_WEEK` 를 바꿔도 **사용률(usable_rates)이 따라오지 않았다.**
#   주당 경기가 늘면 하루 경합이 심해져 선발 7칸 초과가 늘고 사용률이 떨어지는데,
#   그 반작용이 빠진 채 승률만 올라간다 → **주당 경기 증가의 이득이 과대평가된다.**
#   이제 참조다. 값을 여기 다시 쓰지 말 것.
DEFAULT_GP = 60.0               # GP 미상 — 상대 로스터 보충분에만 쓰인다


def _gpw():
    """🔴 **표준 주(3.417)** 를 쓴다. 매치업 주 평균도, (구)캘린더 주도 아니다.

    이 스크립트는 「하루 7칸에 몇 명이 겹치나」를 잰다. 그러니 필요한 것은
    **활동일의 밀도**(0.4881 경기/일 = 7일당 3.417)다. 두 오답이 양쪽에 있다:
      · 매치업 주 평균 3.572 → 하루 경합 **4.5% 과대** (긴 주 W7 은 14일이라
        칸 용량도 2배다 — 일일 밀도는 안 변한다)
      · (구)캘린더 주 3.274 → 하루 경합 **4.2% 과소** (올스타 브레이크 무경기일을
        분모에 넣은 값이다. 브레이크는 경합을 만들지 않는다)
    42차에 양쪽 다 하마터면 넣을 뻔했다. 정답은 그 사이다.

    모듈 로드 시점에 상수로 굳히지 않는다 — `gpw_dual.py` 가 한 프로세스 안에서
    여러 값을 번갈아 재기 때문이다."""
    return CM.STD_WEEK_GAMES


def _daily_p(p):
    gp = (p.get("measured_source") or {}).get("GP")
    if gp is None:
        gp = DEFAULT_GP
    return min(1.0, _gpw() * (float(gp) / 82.0) / 7.0)


def measure(players, weeks=20000, seed=7):
    """players: [선수dict]. 반환 (버림률, {이름: 사용률}, 주당 버린 경기수)."""
    rnd = random.Random(seed)
    pd = [_daily_p(p) for p in players]
    n = len(players)
    games = [0] * n
    used = [0] * n
    for _ in range(weeks):
        for _d in range(7):
            idx = [i for i in range(n) if rnd.random() < pd[i]]
            if not idx:
                continue
            for i in idx:
                games[i] += 1
            # 최대 매칭에서 **누가** 들어갔는지가 필요하므로 mt 를 직접 돌린다
            sub = [players[i] for i in idx]
            adj = [[j for j in range(len(PE.START_SLOTS))
                    if PE.can(p, PE.START_SLOTS[j])] for p in sub]
            mt = [-1] * len(PE.START_SLOTS)

            def aug(a, seen):
                for j in adj[a]:
                    if j in seen:
                        continue
                    seen.add(j)
                    if mt[j] < 0 or aug(mt[j], set(seen)):
                        mt[j] = a
                        return True
                return False

            for a in range(len(sub)):
                aug(a, set())
            for j, a in enumerate(mt):
                if a >= 0:
                    used[idx[a]] += 1
    tot_g = sum(games) or 1
    tot_u = sum(used)
    rates = {players[i]["name"]: (used[i] / games[i] if games[i] else 1.0) for i in range(n)}
    return (tot_g - tot_u) / tot_g, rates, (tot_g - tot_u) / float(weeks)


def usable_rates(players, weeks=8000, seed=7):
    """시뮬 가용률에 곱할 선수별 사용률만 돌려준다."""
    return measure(players, weeks=weeks, seed=seed)[1]


def main():
    PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
    CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    print("자격 제약 일일 라인업 손실 — 선발 7칸 · 20000주")
    print("⚠️ 「조립 불가」가 아니다. 로스터는 합법이고 그 칸이 매일 빈다. 손실 크기로 읽을 것.")
    print()
    print("  %-4s %-7s %7s %9s   %-22s %s" % ("코어", "구성", "버림%", "주당버림", "C전용/SF자격", "가장 많이 버리는 선수"))
    for co in CJ["cores"]:
        for tag, names in (("base", [s["candidates"][0]["name"] for s in co["slots"]]),
                           ("pivot", [r["name"] for r in co["pivot_plan"]["final_roster"]])):
            ps = [PL[n] for n in names if n in PL]
            drop, rates, perweek = measure(ps)
            conly = sum(1 for p in ps if PE.elig(p) == {"C"})
            sf = sum(1 for p in ps if "SF" in PE.elig(p))
            worst = sorted(rates.items(), key=lambda kv: kv[1])[:2]
            print("  %-4s %-7s %6.2f%% %9.2f   C전용 %d · SF %d%s   %s" % (
                co["id"], tag, 100 * drop, perweek, conly, sf,
                "  🔴" if sf == 0 else "  ",
                " · ".join("%s %.0f%%" % (n.split()[-1], 100 * r) for n, r in worst)))


if __name__ == "__main__":
    main()
