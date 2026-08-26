#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""판단표·임계값의 **가격 조건이 실제로 발동할 수 있는가**를 잰다 (39차 · B-1a).

문제
  `validate.py`는 트리거가 `overheat_thresholds`와 일치하는지, 임계값이 `my_max` 이하인지는
  보지만 **그 조건이 일어날 수 있는 사건인가**는 보지 않는다. 도달 불가능한 분기를 계획에
  넣어두면 드래프트 당일 그 행은 영원히 거짓이고, 아무도 눈치채지 못한다.
  이 저장소의 대표 실패 형태(「빠뜨려도 조용히 통과한다」)와 같은 계열이다.

두 가지 모델로 잰다 — 그리고 **둘이 크게 다르다**

  ① 균등(uniform): 낙찰가가 [market_low, market_high] 안에 균등하다고 본다.
     P = clamp((임계값 − low) / (high − low), 0, 1)
     ⚠️ 이 가정은 **구간 밖을 확률 0으로 못박는다.** market_low/high 는 추정 구간이지
     지지집합(support)이 아니다. 이 모델에서는 `Jokić ≤ $88`(시장 $93-101)이 무조건 0이다.

  ② 실측 산포(empirical): 작년 이 리그 옥션 120건에서 **우리 순위가 틀리는 만큼 가격이
     어긋나는 정도**를 뽑아 쓴다.

실측 산포를 만드는 법 — 순환논리를 피한다
  이 프로젝트의 `market_low/high` 는 작년 실측을 **순위 보존 곡선 재적합**한 값이다
  (`proposed_market_refit.json.method`). 즉 우리 추정치 = 곡선(우리 순위)이고,
  선수 개별 편차는 **구성상 이미 지워져 있다.** 그래서 `실낙찰가 ÷ 현재 추정 중간값`을
  그대로 쓰면 재적합에 쓰인 값으로 재적합을 검증하는 순환이 된다.

  대신 작년 데이터 **안에서** 잔차를 만든다:
    1. 작년 지명자 중 우리 DB에 있는 선수 집합 S를 잡는다
    2. S의 실낙찰가를 내림차순 정렬 → 가격 사다리
    3. 각 선수의 **z-score 모델 순위**(`value_reference.rank_by_value`, 가격과 독립)로
       사다리에서 예측가를 읽는다 — "우리 순위가 맞았다면 받았을 가격"
    4. 잔차비 = 실낙찰가 ÷ 예측가
  이 비율의 분포가 **우리 순위 오차가 가격 오차로 번역된 크기**다. 우리가 어떤 선수의
  가격을 추정할 때 지는 불확실성이 정확히 이것이다.

  ✅ 스케일 문제는 **구성상 소거된다.** 분자·분모가 둘 다 작년 달러이므로
  12팀→14팀 금액 스케일 1.117(`docs/08`)이 비율에 들어오지 않는다. 평가자가 지적한
  "비율을 쓰면 약분되지만 확인하라"는 조건은 여기서 자동으로 충족된다 —
  아래 출력의 잔차비 중앙값이 1.0 근처인지로 재확인한다.

  🔴 **풀링하면 안 된다 — 산포가 순위에 따라 완전히 다르다** (측정값):

      우리 z순위   n    중앙값   사분위
      1~10        10   0.50    0.26~0.86     ← 우리 상위권은 시장이 **안 사준다**
      11~25       15   0.76    0.60~0.97
      26~45       20   0.92    0.55~1.39
      46~70       25   0.83    0.46~1.45
      71~         22   3.75    1.00~5.75     ← 우리 하위권을 시장이 **비싸게 산다**

  전체 풀링(중앙 0.89 · 범위 0.07~17.33)을 쓰면 상위권 조건의 확률이 하위권의
  거대한 상방 꼬리로 오염된다. 그래서 **순위 국소 창**(대상 선수의 z순위 ±W 안의
  선수들)에서만 잔차비를 뽑는다. 표본이 작으므로 확률은 소수 2자리가 아니라
  **구간 판정**으로만 읽어야 한다.

  🔴 **`docs/08` §0 경고를 피하지 못한다** (39차 평가 세션 지적 · 수용):
    > "작년 낙찰가는 **2025-26 프리시즌 기대치**이고 `my_max`는 **2025-26 실측 성적**이다.
    >  두 값을 선수별로 직접 비교하면 '우리 추정이 틀렸다'가 아니라
    >  **'기대 vs 결과'의 차이**를 재게 된다."
    사다리로 분모를 바꿔 *순환*은 끊었지만 이 오염은 그대로다. 잔차의 상당 부분이
    가격 산포가 아니라 **시즌 중 성적 변화**다 — Jamal Murray 0.26 · Barnes·Maxey 등은
    작년 프리시즌에 싸게 팔리고 시즌 중 올라온 선수들이고, **올해 드래프트에서
    재현되지 않는다.** 순위 일치도로 조건화해도 그 집단에 브레이크아웃이 그대로 남는다.
    → 그래서 ③ 엘리트 대조군을 별도로 낸다. 세 모델을 **통합하지 않는다.**

  ⚠️ 남는 편향 2종:
    · S는 **현재 우리 DB(174명)에 있는 선수만**이다(작년 지명 120 중 92). 지금 우리가
      평가하지 않는 선수는 대체로 가치가 떨어진 쪽이라 하방 꼬리가 과소 표현될 수 있다.
    · 잔차의 대부분은 **경매 당일 무작위성이 아니라 우리 모델과 시장의 체계적 불일치**다
      (1~10위 중앙 0.50 = 우리가 상위로 본 선수를 시장이 절반값에 판다). 즉 이 확률은
      "가격이 흔들릴 확률"이 아니라 **"우리 순위가 틀렸을 확률"** 에 가깝다.

쓰기 금지
  이 스크립트는 **아무 파일도 쓰지 않는다.** 표를 찍을 뿐이다.
"""
import json, io, os, sys, unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
PRIOR = json.load(io.open(f"{BASE}/data/prior_auction_2025_26/results.json", encoding="utf-8"))

ALWAYS, NEVER = 0.99, 0.01


def norm(s):
    """이름 정규화 — 발음기호 차이로 매칭이 깨진다(Porziņģis vs Porzingis)."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace(".", "").strip()


NORM = {norm(n): n for n in PL}


def mid(p):
    return (p["market_low"] + p["market_high"]) / 2.0


# ── 실측 잔차비 분포 ────────────────────────────────────────────────
def residual_ratios():
    drafted = [(pl["name_en"], pl["price"]) for t in PRIOR["teams"] for pl in t["players"]]
    S = []
    for n, price in drafted:
        key = NORM.get(norm(n))
        if not key:
            continue
        r = (PL[key].get("value_reference") or {}).get("rank_by_value")
        if r:
            S.append((key, price, r))
    ladder = sorted((p for _, p, _ in S), reverse=True)
    S.sort(key=lambda x: x[2])                       # 우리 z-모델 순위 오름차순
    out = []
    for i, (n, price, _) in enumerate(S):
        pred = ladder[i]
        if pred > 0:
            out.append((n, price, pred, price / pred))
    return out, len(drafted)


RES, N_DRAFTED = residual_ratios()          # 우리 z순위 오름차순
RATIOS = sorted(r for *_, r in RES)
WINDOW = 20                                  # 순위 국소 창 반폭 (양쪽 합쳐 최대 41명)
OUR_RANK = {n: i for i, (n, *_ ) in enumerate(RES)}   # S 안에서의 우리 순위(0-based)


def local_ratios(name):
    """대상 선수의 z순위 근처에서만 잔차비를 모은다. 없으면 시장 중간값 순위로 대신 잡는다."""
    if name in OUR_RANK:
        c = OUR_RANK[name]
    else:
        r = (PL[name].get("value_reference") or {}).get("rank_by_value")
        if not r:
            return RATIOS, "전체"
        # S 밖의 선수 — S 안에서 z순위가 가장 가까운 위치를 찾는다
        c = min(range(len(RES)),
                key=lambda i: abs(((PL[RES[i][0]].get("value_reference") or {}).get("rank_by_value") or 0) - r))
    lo, hi = max(0, c - WINDOW), min(len(RES), c + WINDOW + 1)
    return sorted(r for *_, r in RES[lo:hi]), "순위 %d~%d" % (lo + 1, hi)


# ── ③ 같은 선수의 작년 실낙찰가 (가장 직접적인 앵커) ─────────────────
# 순위 국소 창도 상위권에서는 편향된다 — Jokić를 우리가 top-10으로 본 Duren·Gobert·
# Vučević(시장이 안 사주는 빅)와 같은 창에 넣기 때문이다. 같은 선수의 작년 가격은
# 그 오염이 없다. 작년 12팀·$2400 → 올해 14팀·$2800 이므로 금액 스케일을 곱한다.
# ⚠️ 총액비(2800/2400 = 1.167)를 쓰면 안 된다 — 낙찰 **인원**도 120 → 126으로 늘었다.
# 저장소의 단일 소스는 재적합이 쓴 `money_scale` = 1.117 이다(docs/08 · 총액 제약 하 재적합).
_RF = json.load(io.open(f"{BASE}/data/prior_auction_2025_26/proposed_market_refit.json",
                        encoding="utf-8"))
MONEY_SCALE = _RF["money_scale"]
LAST = {}
for _t in PRIOR["teams"]:
    for _pl in _t["players"]:
        _k = NORM.get(norm(_pl["name_en"]))
        if _k: LAST[_k] = _pl["price"]


def last_year_scaled(name):
    return None if name not in LAST else LAST[name] * MONEY_SCALE


# ── ③ 엘리트 대조군 (39차 평가 세션 제안) ──────────────────────────
# 작년에 **이미 비쌌던** 선수($60+ 스케일 후)로 좁힌다. 시장이 이미 알고 있던 선수라
# 브레이크아웃 아티팩트가 없다. 비율 = 작년 실낙찰가(스케일) ÷ 올해 우리 추정 중간값.
#
# 관측: 진짜 엘리트는 0.81~1.01에 촘촘히 모이고 **위쪽 꼬리는 전부 하락한 선수**다
# (Giannis 1.31 · KAT 1.64 · Trae 1.90 · Şengün 2.58 · Sabonis 3.59).
# 즉 **엘리트는 기대보다 싸지는 일이 거의 없다.**
#
# ⚠️ 이 모델의 고유 한계 3종 — 숫자만 떼어 쓰지 말 것:
#   · **n = 11.** 확정 주장이 불가능한 크기다. 한 명이 들고 나면 P가 0.09씩 움직인다.
#   · **위쪽 꼬리는 시장 노이즈가 아니라 우리 자신의 재평가다.** Sabonis 3.59 는
#     "작년 $68짜리를 우리가 올해 $19로 본다"는 뜻이고, 그 재평가가 맞으면 실제가는
#     우리 추정 쪽에 붙는다. 이걸 '추정 오차 표본'으로 쓰면 상방으로 보수적이 된다.
#   · **엘리트에만 정의된다.** 저가 선수에는 대조군이 없다.
ELITE_MIN = 60.0


def elite_ratios():
    out = []
    for n, price in LAST.items():
        sc = price * MONEY_SCALE
        if sc >= ELITE_MIN and mid(PL[n]) > 0:
            out.append((n, sc, mid(PL[n]), sc / mid(PL[n])))
    out.sort(key=lambda x: x[3])
    return out


ELITE = elite_ratios()
ELITE_R = sorted(r for *_, r in ELITE)


def p_elite(name, thr):
    """엘리트 대조군 기준 P(실낙찰가 <= thr). 대조군이 없으면 None."""
    if not ELITE_R: return None
    m = mid(PL[name])
    if m <= 0: return None
    t = thr / m
    return sum(1 for r in ELITE_R if r <= t) / float(len(ELITE_R))


def q(v):
    if not RATIOS:
        return None
    k = (len(RATIOS) - 1) * v
    lo, hi = int(k), min(int(k) + 1, len(RATIOS) - 1)
    return RATIOS[lo] + (RATIOS[hi] - RATIOS[lo]) * (k - lo)


def p_uniform(name, thr):
    p = PL[name]
    lo, hi = p["market_low"], p["market_high"]
    if thr <= lo: return 0.0
    if thr >= hi: return 1.0
    return (thr - lo) / float(hi - lo)


def p_empirical(name, thr):
    """P(실낙찰가 <= thr) = **순위 국소** 잔차비가 thr/추정중간값 이하인 비율"""
    m = mid(PL[name])
    if m <= 0: return None
    rs, _ = local_ratios(name)
    if not rs: return None
    t = thr / m
    return sum(1 for r in rs if r <= t) / float(len(rs))


def grade(p):
    if p is None: return " "
    if p >= ALWAYS: return "항상참"
    if p <= NEVER:  return "항상거짓"
    return ""


# ── 조건 수집 ──────────────────────────────────────────────────────
def conditions():
    """(출처, 라벨, [(선수, 임계값, 방향)]) — 방향 le = '<= thr' · gt = '> thr'"""
    out = []
    for r in CJ["decision_table"]:
        rules = (r.get("cond") or {}).get("rules") or []
        if rules:
            out.append(("판단표", "우선 %s · %s" % (r["prio"], r["core"]),
                        [(x["player"], x["max"], "le") for x in rules if x["player"] in PL]))
    for t in CJ["overheat_thresholds"]:
        if t["player"] not in PL:
            continue
        if t.get("walk_away") is not None:
            out.append(("철수가", t["player"], [(t["player"], t["walk_away"], "gt")]))
        if t.get("overheat_at") is not None:
            out.append(("과열선", t["player"], [(t["player"], t["overheat_at"], "gt")]))
    return out


def main():
    print("=" * 96)
    print("가격 트리거 발동 확률 감사 — 판단표 · 철수가 · 과열선")
    print("=" * 96)
    print("작년 지명 %d명 중 DB·z순위 보유 **%d명**으로 잔차비 분포 구성" % (N_DRAFTED, len(RES)))
    if RATIOS:
        print("  잔차비 = 실낙찰가 ÷ (우리 z순위가 맞았다면 받았을 가격)")
        print("  중앙값 %.2f · 평균 %.2f · 사분위 %.2f~%.2f · 10%%/90%% %.2f/%.2f · 범위 %.2f~%.2f" % (
            q(.5), sum(RATIOS) / len(RATIOS), q(.25), q(.75), q(.10), q(.90), RATIOS[0], RATIOS[-1]))
        chk = abs(q(.5) - 1.0)
        print("  스케일 소거 확인: 중앙값이 1.0에서 %.2f 떨어짐 — %s" % (
            chk, "OK (비율이 연도 스케일에 오염되지 않음)" if chk < 0.15 else "⚠️ 편향 의심"))
    print()

    print("금액 스케일 %.3f (proposed_market_refit.money_scale · 총액비 1.167이 아님 — 인원도 120→126)"
          " · 같은 선수 작년 기록 %d명" % (MONEY_SCALE, len(LAST)))
    print()
    print("엘리트 대조군: 작년 $%d+ (스케일 후) **%d명** · 비율 %.2f~%.2f — 위쪽 꼬리는 하락 선수" % (
        ELITE_MIN, len(ELITE), ELITE_R[0], ELITE_R[-1]))
    print()
    hdr = "%-7s %-22s %-27s %6s %6s %6s %10s  %s" % (
        "출처", "조건", "선수 · 시장", "균등P", "국소P", "엘리트", "작년실적", "판정")
    print(hdr); print("-" * 108)
    flagged = []
    for src, label, rules in conditions():
        if not rules:
            continue
        pu = pe = 1.0
        desc = []
        for name, thr, d in rules:
            p = PL[name]
            u = p_uniform(name, thr); e = p_empirical(name, thr)
            if d == "gt":
                u = 1.0 - u
                e = None if e is None else 1.0 - e
            pu *= u
            pe = None if (pe is None or e is None) else pe * e
            desc.append("%s %s $%d (시장 $%d-%d)" % (
                name.split()[-1], "≤" if d == "le" else ">", thr, p["market_low"], p["market_high"]))
        # 작년 앵커 — 단일 규칙일 때만 의미가 있다
        ly = ""
        if len(rules) == 1:
            nm, thr, d = rules[0]
            sc = last_year_scaled(nm)
            if sc:
                hit = (sc <= thr) if d == "le" else (sc > thr)
                ly = "$%.0f %s" % (sc, "✓" if hit else "✗")
            else:
                ly = "미지명"
        pel = 1.0
        for name, thr, d in rules:
            e3 = p_elite(name, thr)
            if e3 is None: pel = None; break
            pel *= (1.0 - e3) if d == "gt" else e3
        g = grade(pe if pe is not None else pu)
        print("%-7s %-22s %-27s %6.2f %6s %6s %10s  %s" % (
            src, label[:22], " + ".join(desc)[:27], pu,
            "—" if pe is None else "%.2f" % pe,
            "—" if pel is None else "%.2f" % pel, ly, g))
        if g:
            flagged.append((src, label, " + ".join(desc), pu, pe, g))
    print("-" * 96)

    print("\n■ 균등 모델과 실측 모델이 갈리는 지점")
    n_diff = 0
    for src, label, rules in conditions():
        if not rules: continue
        pu = pe = 1.0
        for name, thr, d in rules:
            u = p_uniform(name, thr); e = p_empirical(name, thr)
            if d == "gt":
                u = 1.0 - u; e = None if e is None else 1.0 - e
            pu *= u
            pe = None if (pe is None or e is None) else pe * e
        if pe is not None and (grade(pu) != grade(pe) or abs(pu - pe) >= 0.15):
            n_diff += 1
            print("  %-8s %-24s 균등 %.2f(%s) → 실측 %.2f(%s)" % (
                src, label[:24], pu, grade(pu) or "가변", pe, grade(pe) or "가변"))
    if not n_diff:
        print("  없음")

    print("\n■ 발동 불가/무의미 판정 (실측 기준 · 없으면 균등)")
    if not flagged:
        print("  없음")
    for src, label, desc, pu, pe, g in flagged:
        print("  [%s] %-24s %-44s %s" % (src, label[:24], desc[:44], g))
    return flagged


if __name__ == "__main__":
    main()
