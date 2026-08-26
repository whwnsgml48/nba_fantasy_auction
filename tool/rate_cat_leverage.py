#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""비율 캣(3P% · FG% · FT%) 볼륨 레버리지 — 로스터 실제 시도량 기반 (38차).

무엇이 낡았나
  `docs/05` 5번과 README 「평가자에게」 4번이 이렇게 적혀 있었다:
      "FG%·FT%는 시도량 데이터가 없어 같은 계산을 못 했습니다"
      "팀 3PA 135는 '선발 평균 5.5×3PA'에서 나온 값으로 실측이 아님"
      "레버리지 계산은 로스터 구성에 따라 달라져야 하는데 고정값을 씀"
  **첫 줄은 14차에 낡았다** — `measured_full.json`에 `FGA`·`FTA`가 전원 있다.
  나머지 둘은 유효한 지적이고, 이 스크립트가 **로스터 실제 시도량**으로 대체한다.

공식 (docs/03의 3PT% 표와 같은 정의)
      지분      = 내 주간 시도 / 팀 주간 시도
      레버리지  = 지분 × (내 rate − 기준선) × 100   [단위 pp]
      변동성    = √(p(1−p)/주간시도) × 100          [이항 SD]
  주간 시도 = 경기당 시도 × 3.5경기 × 가용률(GP/82) — `cat_model.avail()`과 같은 가중.
  기준선은 `cat_model.baselines()`(지명 풀 126명 · 시도량 가중)를 그대로 쓴다.
  **팀 주간 시도는 고정값이 아니라 그 코어 9명의 합이다.**

이 스크립트는 아무 파일도 쓰지 않는다. 실행: python3 tool/rate_cat_leverage.py
"""
import io, json, math, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE + "/tool")
import cat_model as CM   # noqa: E402

GPW = 3.5                       # 주간 경기수 (matchup_sim의 [3,4] 평균)
RATE = CM.RATE                  # {"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
F = CM.F                        # measured_full 선수별 라인
B = CM.baselines()
CJ = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
CORES = {c["id"]: [s["candidates"][0]["name"] for s in c["slots"]] for c in CJ["cores"]}


def att_week(name, cat):
    """주간 시도량 = 경기당 시도 × 3.5 × 가용률."""
    r = F.get(name)
    if not r or r.get(RATE[cat]) is None or not r.get("GP"):
        return None
    return r[RATE[cat]] * GPW * CM.avail(r)


def rate(name, cat):
    r = F.get(name)
    return None if not r else r.get(cat)


def team_att(names, cat):
    v = [att_week(n, cat) for n in names]
    return sum(x for x in v if x is not None)


def leverage(name, cat, tatt):
    a, p = att_week(name, cat), rate(name, cat)
    if a is None or p is None or not tatt:
        return None
    return (a / tatt) * (p - B[cat]) * 100


def vol(name, cat):
    a, p = att_week(name, cat), rate(name, cat)
    if not a or p is None:
        return None
    return math.sqrt(max(p * (1 - p), 0) / a) * 100


print("비율 캣 볼륨 레버리지 — 로스터 실제 시도량 기반")
print("주간 경기 %.1f · 기준선은 cat_model.baselines() (지명 풀 126명 · 시도량 가중)\n" % GPW)
print("%-6s %-6s %10s" % ("캣", "시도", "기준선"))
for cat in ("3P%", "FG%", "FT%"):
    print("%-6s %-6s %9.1f%%" % (cat, RATE[cat], B[cat] * 100))

# ── 1. 코어별 팀 주간 시도량 — 「고정값 135」가 얼마나 틀렸나 ─────────────
print("\n" + "=" * 74)
print("1. 팀 주간 시도량은 코어마다 다르다 (docs/05 5번의 지적)")
print("=" * 74)
print("%-5s %10s %10s %10s" % ("코어", "3PA/주", "FGA/주", "FTA/주"))
t3 = {}
for cid, r in sorted(CORES.items()):
    t3[cid] = {c: team_att(r, c) for c in ("3P%", "FG%", "FT%")}
    print("%-5s %10.1f %10.1f %10.1f" % (cid, t3[cid]["3P%"], t3[cid]["FG%"], t3[cid]["FT%"]))
lo, hi = min(v["3P%"] for v in t3.values()), max(v["3P%"] for v in t3.values())
print("\n  → 팀 주간 3PA 실측 범위 **%.0f ~ %.0f**. docs/03이 쓴 고정값 **135**는" % (lo, hi))
print("     %s 구간에 있고, 반대편 끝에서는 지분이 %.0f%% 어긋난다."
      % ("범위 안" if lo <= 135 <= hi else "범위 밖", abs(135 - lo) / lo * 100))
print("     같은 선수의 3PT%% 레버리지가 코어에 따라 **최대 %.2f배** 달라진다."
      % (hi / lo))
print("     그리고 135는 실측 최대(%.0f)보다 크므로, docs/03 표의 19명 레버리지는"
      % hi)
print("     전원 **과소 계상**돼 있다 (분모가 실제보다 %.0f~%.0f%% 큼)."
      % ((135 / hi - 1) * 100, (135 / lo - 1) * 100))

# ── 2. 같은 선수, 다른 코어 — 로스터 의존성 실증 ──────────────────────────
print("\n" + "=" * 74)
print("2. 같은 선수의 레버리지가 코어마다 다르다")
print("=" * 74)
for cat in ("3P%", "FG%", "FT%"):
    shared = [n for n in set().union(*CORES.values())
              if sum(1 for r in CORES.values() if n in r) >= 4 and att_week(n, cat)]
    shared = sorted(shared, key=lambda n: -(att_week(n, cat) or 0))[:3]
    if not shared:
        continue
    print("\n  [%s]" % cat)
    print("  %-22s %s" % ("선수", "".join("%8s" % c for c in sorted(CORES))))
    for n in shared:
        cells = []
        for cid in sorted(CORES):
            v = leverage(n, cat, t3[cid][cat]) if n in CORES[cid] else None
            cells.append("%8s" % ("—" if v is None else "%+.2f" % v))
        print("  %-22s %s" % (n[:22], "".join(cells)))

# ── 3. 코어별 상·하위 기여자 ──────────────────────────────────────────────
print("\n" + "=" * 74)
print("3. 코어별 비율 캣 기여자 (pp · 합계가 팀 캣 마진이다)")
print("=" * 74)
for cid, r in sorted(CORES.items()):
    print("\n  %s" % cid)
    for cat in ("3P%", "FG%", "FT%"):
        rows = sorted([(leverage(n, cat, t3[cid][cat]), n) for n in r
                       if leverage(n, cat, t3[cid][cat]) is not None], reverse=True)
        tot = sum(v for v, _ in rows)
        top = " · ".join("%s %+.2f" % (n.split()[-1][:9], v) for v, n in rows[:2])
        bot = " · ".join("%s %+.2f" % (n.split()[-1][:9], v) for v, n in rows[-2:])
        print("    %-5s 합 %+6.2fpp   최고: %-28s 최저: %s" % (cat, tot, top, bot))

# ── 4. FG%와 FT%는 서로 반대로 움직인다 ───────────────────────────────────
print("\n" + "=" * 74)
print("4. FG% ↔ FT% 상충 — 빅맨은 FG%를 올리고 FT%를 내린다")
print("=" * 74)
ref = CORES["c6"]
rows = []
for n in set().union(*CORES.values()):
    g = leverage(n, "FG%", t3["c6"]["FG%"]) if n in ref else None
    f = leverage(n, "FT%", t3["c6"]["FT%"]) if n in ref else None
    if g is not None and f is not None:
        rows.append((g, f, n))
rows.sort(reverse=True)
print("  기준 로스터 c6 (정상 시장 기본값)")
print("  %-22s %10s %10s %10s" % ("선수", "FG% pp", "FT% pp", "합"))
for g, f, n in rows:
    print("  %-22s %+10.2f %+10.2f %+10.2f" % (n[:22], g, f, g + f))
both = [n for g, f, n in rows if g > 0 and f > 0]
tradeoff = [n for g, f, n in rows if g > 0 > f]
print("\n  → 둘 다 플러스: %d명 (%s)" % (len(both), ", ".join(x.split()[-1] for x in both) or "없음"))
print("  → FG%%는 올리고 FT%%는 내림: %d명 (%s)"
      % (len(tradeoff), ", ".join(x.split()[-1] for x in tradeoff) or "없음"))

print("\n" + "-" * 74)
print("파일을 쓰지 않는다. 결론을 남기려면 docs/10-rate-cat-leverage.md 를 갱신할 것.")
