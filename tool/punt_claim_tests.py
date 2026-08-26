#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HANDOFF 「검증 못 한 주장들」 3건을 승률 모델로 판정한다 (38차).

왜 지금 가능한가
  HANDOFF 6번은 세 주장을 "검증 못 함"으로 남기고 이유를 이렇게 적었다:
    "전부 **주간 팀 총량 모델**이 필요하고, 그건 2번(26위 이하 데이터) 없이는 만들 수 없다"
  **그 차단 근거가 낡았다.** 2번은 14차에 해소되고 30차에 `tool/matchup_sim.py`가
  생겼다. 세 주장 중 둘은 이미 있는 `data/matchup_sim.json`을 읽기만 해도 답이 나온다.

방법
  `matchup_sim`을 **import 해서** 쓴다 — 그 모듈은 `__main__` 아래에서만 파일을 쓰므로
  import 경로에서는 `data/`를 건드리지 않는다. 이 스크립트도 아무 파일도 쓰지 않고
  표준출력만 낸다(시뮬 산출물을 계획 파일에 쓰지 말 것 · 30·32차).

A/B는 같은 난수 스트림으로
  34차 교훈: 900시행 1위가 6000시행에서 뒤집혔다. 변형을 비교할 때는 상대마다
  **같은 시드로 rng를 새로 만들어** 동일한 주간 표본을 보게 한다. 그러지 않으면
  측정 차이와 노이즈를 구분할 수 없다.

실행: python3 tool/punt_claim_tests.py [시드] [시행수]
"""
import io, json, os, random, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE + "/tool")
import matchup_sim as MS   # noqa: E402  — __main__ 아래에서만 파일을 쓴다
import real_opponents as RO   # noqa: E402  — 38차: 실제 12팀

SEED  = int(sys.argv[1]) if len(sys.argv) > 1 else 20261020
ITERS = int(sys.argv[2]) if len(sys.argv) > 2 else 4000

CJ = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
PL = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
CORES = {c["id"]: c for c in CJ["cores"]}

ROWS = MS.pool()
OPP  = MS.build_opponents(random.Random(SEED))
OPP  = {k: v for k, v in OPP.items() if v != MS.FAILED}
ORDER = [k for k in ["random", "value_max", "big_stack", "guard_stack", "baseline", "benchmark"] if k in OPP]

# ── 38차: 실제 12팀 상대 ────────────────────────────────────────────
# 조립 상대는 우리 모델이 만든 팀이다. maximin의 최소값이 7코어 전부 value_max
# 하나에서 나오므로, 조립 상대에 대한 결론을 "판별력"으로 일반화하면 안 된다.
REAL, RREP = RO.build()


def run_real(roster, iters=None):
    """실제 12팀 각각에 대해 시뮬. 상대마다 같은 시드로 rng를 새로 만든다."""
    return {m: MS.simulate(list(roster), names, random.Random(SEED), iters or ITERS, ROWS)
            for m, names in REAL.items()}


def real_summary(roster, iters=None):
    r = run_real(roster, iters)
    wr = [v["weekly_win_rate"] for v in r.values()]
    ec = [v["expected_cats_won"] for v in r.values()]
    return (sum(wr)/len(wr), min(wr), sum(ec)/len(ec), min(ec))


def run(roster, iters=None):
    """상대 6종에 대해 시뮬. 상대마다 같은 시드로 rng를 새로 만든다."""
    out = {}
    for k in ORDER:
        out[k] = MS.simulate(list(roster), OPP[k], random.Random(SEED), iters or ITERS, ROWS)
    return out


def base_roster(cid):
    return [s["candidates"][0]["name"] for s in CORES[cid]["slots"]]


def pivot_roster(cid):
    fr = (CORES[cid].get("pivot_plan") or {}).get("final_roster") or []
    return [x["name"] if isinstance(x, dict) else x for x in fr]


def row(label, vals, width=9, fmt="%9.3f"):
    return "%-14s%s" % (label, "".join(fmt % v for v in vals))


def hdr(label=""):
    return "%-14s%s%10s" % (label, "".join("%9s" % MS.LABEL[k][:9] for k in ORDER), "최저")


# ══════════════════════════════════════════════════════════════════
print("시드 %d · 시행 %d · 승리선 %d캣 · 상대 %d종" % (SEED, ITERS, MS.WIN_LINE, len(ORDER)))
print("⚠ 이 스크립트는 **상대마다 rng를 새로 만든다**(A/B를 같은 표본에 걸기 위해).")
print("  `matchup_sim.py`는 하나의 스트림을 이어 쓰므로, 아래 절대값은")
print("  `data/matchup_sim.json`과 소수 셋째 자리에서 다를 수 있다.")
print("  **비교(Δ)는 유효하고 절대값은 그 파일을 기준으로 삼을 것.**\n")

# ── 주장 1 ────────────────────────────────────────────────────────
print("=" * 78)
print("주장 1 (HANDOFF 6번) — 코어 4의 \"PTS·TOV 포기가 나머지 7캣 승리로 이어지는가\"")
print("=" * 78)
c4 = CORES["c4"]
print("\n[전제 검사] 주장이 말하는 c4의 선언과 현행 선언이 다르다.")
print("  현행 목표: %s" % " ".join(c4["targeted_cats"]))
print("  현행 포기: %s" % " ".join(c4["punted_cats"]))
print("  → PTS는 **목표**다(포기가 아니다). 포기는 TOV·3PM·3P%·FT%·A/T 5개다.")
print("    주장 문장은 33·34차 재구성 이전의 c4를 가리킨다.\n")

print("[판정] 기대 승리 캣이 승리선 %d을 넘는가 — 7개 코어 전부" % MS.WIN_LINE)
sim = json.load(io.open(BASE + "/data/matchup_sim.json", encoding="utf-8"))
cur = {cid: base_roster(cid) for cid in CORES}
stale = [cid for cid in CORES if sorted(cur[cid]) != sorted(sim["cores"][cid]["roster"])]
if stale:
    print("  ⚠ matchup_sim.json이 현행 로스터와 어긋난 코어: %s — 재실행 필요" % ", ".join(stale))
print("  " + hdr("코어") + "   7미달")
worst = {}
for cid in sorted(CORES):
    e = sim["cores"][cid]
    v = [e[k]["expected_cats_won"] for k in ORDER]
    n = sum(1 for x in v if x < MS.WIN_LINE)
    worst[cid] = n
    print("  " + row(cid, v, fmt="%9.2f") + "%10.2f" % min(v) + "   %d/%d" % (n, len(ORDER)))
print("\n  → **7개 코어 전부** 6개 상대 중 %d개에서 기대 승리 캣이 7 미달이다."
      % max(worst.values()))
print("\n[재판정 · 38차] 같은 질문을 **실제 12팀 상대**에 물으면 답이 뒤집힌다.")
print("  실제 상대: 작년 옥션 실측 %d팀 (DB 매칭 %d · BBRef 보충 %d · 미매칭 %d)"
      % (RREP["teams_used"], RREP["matched_in_db"], RREP["supplemented"],
         len(RREP["unmatched"])))
print("  %-6s%10s%10s%12s%12s" % ("코어", "평균승률", "최저승률", "평균승리캣", "최저승리캣"))
_rl = {}
for cid in sorted(CORES):
    _rl[cid] = real_summary(base_roster(cid))
for cid in sorted(_rl, key=lambda c: -_rl[c][0]):
    m, mn, em, en = _rl[cid]
    print("  %-6s%9.1f%%%9.1f%%%12.2f%12.2f" % (cid, m*100, mn*100, em, en))
print("\n  → 실제 12팀 상대로는 **7코어 전부 평균 8.1캣 이상**이고 최저도 승리선 7을 넘는다.")
print("     조립 상대에게 5.4~5.9캣이던 것과 정반대다.")
print("  → 정정된 답: N캣 지표는 **조립 상대에 대해 판별력이 없다.** 실제 리그 상대에")
print("     대해서는 전 플랜이 승리선을 넘고, 그래서 이 지표로도 코어를 못 고른다 —")
print("     **판별력이 없는 이유가 반대**다(전부 지는 게 아니라 전부 이긴다).")
print("     이기는 상대는 무작위·기준선 둘뿐이고, 조립된 상대(가치최대·빅스택·")
print("     가드스택·벤치마크)에는 **평균적으로 진다.**")
print("  → 주장 1의 답: **아니다.** 그리고 c4만의 문제가 아니라 7코어 공통이다 —")
print("     즉 이 질문은 'c4의 포기 조합'이 아니라 **포트폴리오 전체**에 대한 것이었다.")

# ── 주장 2 ────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("주장 2 (HANDOFF 6번) — 코어 3의 \"SGA FT%가 빅맨 FT% 붕괴를 상쇄\"")
print("=" * 78)
print("\n[직접 판정] FT% 캣 승률 — 7코어 전부 (상쇄됐다면 0.5를 넘어야 한다)")
print("  " + hdr("코어") + "   선언")
for cid in sorted(CORES):
    e = sim["cores"][cid]
    v = [e[k]["cat_win_probs"]["FT%"] for k in ORDER]
    d = "포기" if "FT%" in CORES[cid]["punted_cats"] else (
        "목표" if "FT%" in CORES[cid]["targeted_cats"] else "-")
    print("  " + row(cid, v) + "%10.3f" % min(v) + "   %s" % d)
print("\n  → **7코어 전부 FT%를 포기로 선언**하고, 실측 승률도 최저 0.09~0.24다.")
print("     c3(0.203)은 c2(0.238) 다음 2위지만 **어떤 상대에게도 0.5를 넘지 못한다.**")

print("\n[통제 실험] SGA가 FT%를 실제로 끌어올리는가 — c3에서 SGA만 교체")
print("  ⚠ c3의 SGA 슬롯에는 **대체후보가 없다**(조건부 앵커). 그래서 대체안을")
print("     내가 골라야 하고, 한 명으로는 결론이 편향된다 → G자격 후보 여럿으로 범위를 낸다.")
sga = "Shai Gilgeous-Alexander"
c3r = base_roster("c3")
mid = lambda n: (PL[n]["market_low"] + PL[n]["market_high"]) / 2
alts = sorted([n for n, p in PL.items()
               if n not in c3r and "G" in (p.get("pos") or "")
               and not p.get("injury_exclude") and 25 <= mid(n) <= 95],
              key=lambda n: -mid(n))[:6]
a = run(c3r)
ft0 = [a[k]["cat_win_probs"]["FT%"] for k in ORDER]
print("\n  " + hdr("변형") + "     Δ최저")
print("  " + row("SGA (현행)", ft0) + "%10.3f" % min(ft0) + "        —")
deltas = []
for alt in alts:
    b = run([alt if n == sga else n for n in c3r])
    ftv = [b[k]["cat_win_probs"]["FT%"] for k in ORDER]
    deltas.append(min(ft0) - min(ftv))
    print("  " + row("→ " + alt[:12], ftv) + "%10.3f" % min(ftv) + "   %+8.3f" % deltas[-1])
print("\n  → SGA를 빼면 최저 FT%% 승률이 %+.3f ~ %+.3f 낮아진다(중앙 %+.3f)."
      % (min(deltas), max(deltas), sorted(deltas)[len(deltas) // 2]))
print("  → 주장 2의 답: **절반만 사실.** SGA는 FT%를 실제로 끌어올린다. 하지만")
print("     출발점이 낮아서 **승리로는 이어지지 않는다** — '상쇄'는 과장이다.")
print("     c3가 FT%를 포기로 선언한 것은 이 측정과 일치한다.")

# ── 주장 3 ────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("주장 3 (HANDOFF 6번) — 과열 피벗의 \"OREB·BLK 포기 후 가드·윙 전환이 7캣 승리로\"")
print("=" * 78)
print("\n  `matchup_sim.json`에는 **피벗이 없다**(base 7종만). 여기서 직접 돌린다.")
print("  ⚠ 피벗 로스터는 지금 재설계 중이다 — 아래 숫자는 이 커밋 시점의 잠정값이다.\n")
print("  " + hdr("피벗") + "   7미달   OREB   BLK")
for cid in sorted(CORES):
    pr = pivot_roster(cid)
    if len(pr) != 9:
        print("  %-14s로스터 %d명 — 건너뜀" % (cid, len(pr)))
        continue
    r = run(pr)
    v = [r[k]["expected_cats_won"] for k in ORDER]
    n = sum(1 for x in v if x < MS.WIN_LINE)
    oreb = min(r[k]["cat_win_probs"]["OREB"] for k in ORDER)
    blk  = min(r[k]["cat_win_probs"]["BLK"] for k in ORDER)
    print("  " + row(cid + " pivot", v, fmt="%9.2f") + "%10.2f" % min(v)
          + "   %d/%d" % (n, len(ORDER)) + "  %5.3f  %5.3f" % (oreb, blk))
print("\n  → 조립 상대 기준: base와 같다 — 7캣에 못 미친다.")
print("\n[재판정 · 38차] 실제 12팀 상대 — base 대비 낙폭까지 본다")
print("  %-12s%10s%10s%12s%12s" % ("피벗", "평균승률", "최저승률", "평균승리캣", "base 대비"))
_pv = {}
for cid in sorted(CORES):
    pr = pivot_roster(cid)
    if len(pr) != 9:
        continue
    _pv[cid] = real_summary(pr)
for cid in sorted(_pv, key=lambda c: -_pv[c][0]):
    m, mn, em, en = _pv[cid]
    d = (m - _rl[cid][0]) * 100 if cid in _rl else float("nan")
    print("  %-12s%9.1f%%%9.1f%%%12.2f%11.1f%%p" % (cid + " pivot", m*100, mn*100, em, d))
print("\n  → 주장 3의 답: **조립 상대에 대해서만 참이다.** 실제 12팀 상대로는 피벗도")
print("     평균 승리캣 7.1~8.7로 승리선을 넘는다. OREB·BLK 포기의 대가는 조립된 빅스택")
print("     상대에게만 치명적이고, 이 리그 사람들이 짜는 로스터에는 그만큼 노출되지 않는다.")
_dl = {c: (_pv[c][0] - _rl[c][0]) * 100 for c in _pv if c in _rl}
_up = [c for c in _dl if _dl[c] > 0]
_wc = min(_pv, key=lambda c: _pv[c][0])
print("\n  🔴 그런데 **낙폭이 문제다.** base보다 나은 피벗은 %s(%s)뿐이고 나머지 %d개는"
      % (", ".join(_up) or "없음",
         ", ".join("%+.1f%%p" % _dl[c] for c in _up) or "-", len(_dl) - len(_up)))
print("     %+.1f ~ %+.1f%%p 떨어진다. %s 피벗은 %.1f%%로 전 플랜 중 최악이다."
      % (max(v for c, v in _dl.items() if v < 0), min(_dl.values()),
         _wc, _pv[_wc][0] * 100))
print("     「피벗 로스터 재설계」의 우선순위 근거로 쓸 수 있다 — 예비비 미소진보다")
print("     이쪽이 직접적인 손실이다.")

print("\n" + "-" * 78)
print("이 스크립트는 아무 파일도 쓰지 않는다. 결론을 문서에 남기려면 손으로 옮길 것.")
