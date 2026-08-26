#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5·M6 판정 규칙의 단일 소스. validate.py와 tool/track_divergence.py가 함께 쓴다.

⚠️ 27차: 처음엔 두 곳에 규칙을 각각 구현했다. validate의 집합은 tag_basis 보유자를
빼지 않았고 tracker는 뺐다 — 같은 데이터에서 "진입 3건"이라는 **허위 변동**이 나왔다
(M.Robinson·D.Mitchell·Dort, 정확히 tag_basis를 가진 3명). 이 프로젝트에서 반복되는
드리프트 유형(툴 임베드 상수 7회 · plant.py 라벨 퇴행)과 같은 구조라 모듈로 합쳤다.
"""
M5_TH = 20      # tag(burn/buy)과 div 부호가 모순
M6_TH = 40      # tag 무관 · 지명 풀 안에서의 큰 괴리 (div 기준)
M6_EXP = 25     # 또는 달러 노출 기준 (28차 추가)
POOL_N = 126
BAND = (18, 22) # 경계 감시 구간

class MissingHitsFn(RuntimeError):
    """auto basis를 만났는데 core_hits를 셀 방법이 안 넘어왔다."""

def _check_auto(p, meta, hits_fn, field):
    """auto basis의 조건이 여전히 참인지 대조한다.

    ⚠️ 30차: hits_fn 기본값이 None이었다. 안 넘기면 core_hits 검사가 **통째로 사라져서**
    auto basis가 영구 유효가 됐다 — `has_any_basis(p, None)`이 True를 돌려줬고,
    실제로 track_divergence.py가 hits_fn 없이 호출하고 있었다(auto 27건이 그쪽에서
    무조건 유효). 이 프로젝트가 네 번째로 반복한 실패 형태다
    (툴 상수 · plant.py 라벨 · 규칙 이중 구현 · 이번 기본값 None).
    이제 **조용히 통과시키지 않고 예외를 던진다.**"""
    if hits_fn is None:
        raise MissingHitsFn(
            "%s: %s 가 auto basis인데 hits_fn이 없다 — core_hits 검사를 건너뛰면 "
            "이 basis는 영구 유효가 된다. 호출자가 hits_fn을 넘겨야 한다." % (p["name"], field))
    c = meta.get("conditions") or {}
    if bool(c.get("obtainable")) != (p["my_max"] >= p["market_low"]): return False
    if c.get("core_hits") != hits_fn(p["name"]): return False
    return True

def has_tag_basis(p, hits_fn=None):
    tb = p.get("tag_basis")
    if not (isinstance(tb, str) and tb.strip()): return False
    auto = p.get("tag_basis_auto")
    if isinstance(auto, dict) and auto:
        return _check_auto(p, auto, hits_fn, "tag_basis")
    return True

def has_any_basis(p, hits_fn=None):
    """근거 필드 보유 여부. **자동 생성 basis는 조건이 여전히 참일 때만 유효하다.**

    28차: 등장 0회 또는 획득 불가인 건은 사람이 사유를 쓸 가치가 없다(천장이 입찰에
    쓰이지 않으므로). 기계로 닫되, 조건이 바뀌면 **자동 무효화**되어 다시 위반으로
    떠야 한다 — 그게 이 필드의 유일한 가치다. auto basis는 생성 당시의
    core_hits·obtainable을 함께 적어두고, 여기서 현재값과 대조한다."""
    if has_tag_basis(p, hits_fn): return True
    mb = p.get("my_max_basis")
    if not (isinstance(mb, dict) and mb): return False
    if not mb.get("auto"): return True                  # 사람이 쓴 근거는 그대로 유효
    return _check_auto(p, mb, hits_fn, "my_max_basis")

def div_of(p):
    return (p.get("value_reference") or {}).get("rank_divergence")

def exposure(p):
    """달러 노출 — 천장을 잘못 잡았을 때 걸린 돈의 규모($).

        노출 = max(dollar_naive, market_high)

    28차에 추가했다. rank_divergence는 **무차원**이라 돈이 어디 있는지 못 본다:
    Mathurin은 div -103인데 노출이 작고(등장 0회), Gobert·Knueppel은 div가 M6 임계
    미달인데 노출이 크고 등장이 10·9회다. 순위만 보면 정렬이 거꾸로 선다.

    두 항 모두 **my_max를 포함하지 않는다** — my_max를 편집해도 노출이 드리프트하지 않아야
    이 값으로 my_max를 심사할 수 있다(자기참조 방지):
      dollar_naive  가치 모델의 달러 환산. 우리가 그를 놓쳐서 잃는 규모.
      market_high   시장이 청구할 최대액. 우리가 과지불할 수 있는 규모.
      max()         둘 중 하나라도 크면 위험하다 — 싸게 놓치는 것과 비싸게 사는 것 모두.

    ⚠️ **시장 혼입을 분리하지 못했다 → 정렬 전용이다.**
    dollar_naive는 지명 풀(시장가 상위 126명) 안에서 z를 표준화해 얻으므로 **풀 소속 자체가
    시장가로 결정된다**. 즉 "시장이 z순위를 싸게 본다"는 성분이 풀 경계를 통해 들어온다.
    게다가 z 합산은 상단을 압축한다(Jokić $53 vs 시장 $93). 개별 항의 절대액을 신뢰하지 말고
    **순서만** 쓴다. 임계값 M6_EXP=$25도 절대 기준이 아니라 이 정렬 위의 컷이다."""
    dn = (p.get("value_reference") or {}).get("dollar_naive")
    return max(dn or 0, p.get("market_high") or 0)

def pool_names(players):
    """지명 풀 = 시장가 상위 126명 (value_reference 보유자 중)."""
    rows = [q for q in players if q.get("value_reference")]
    rows.sort(key=lambda q: -(q["market_low"] + q["market_high"]) / 2)
    return {q["name"] for q in rows[:POOL_N]}

def m5_violations(players, hits_fn=None):
    """tag=burn/buy 인데 div 부호가 모순 · 유효한 tag_basis 없음."""
    out = []
    for p in players:
        t, d = p.get("tag"), div_of(p)
        if t not in ("burn", "buy") or d is None: continue
        if t == "burn" and d < M5_TH: continue
        if t == "buy" and d > -M5_TH: continue
        if has_tag_basis(p, hits_fn): continue
        out.append(p)
    return out

M6_EXP_MIN_DIV = 20   # 노출 트리거에 붙이는 가드 (28차)

def m6_trigger(p):
    """M6 대상 여부와 발동 사유.

        |div| >= 40  또는  (노출 >= $25 **이면서** |div| >= 20)

    ⚠️ 지시는 "|div| >= 40 또는 노출 >= $25"였다. 문자 그대로 넣으면 30건 → **68건**이 되고
    그중 15건이 **|div| < 10**이다 — Jokić(+0) · Wembanyama(-3) · SGA(-1) · KAT(+0)처럼
    my_max가 가치와 이미 일치하는데 "비싸다"는 이유만으로 잡힌다. 평가 문제가 없는 건에
    근거 필드를 쓰게 만드는 것은 ②(기계 종결로 노이즈를 닫는다)와 ⑤(위생 작업을 더 확장하지
    말라)에 정면으로 반한다.

    그래서 노출 트리거에 |div| >= 20 가드를 붙였다(41건). 지시한 의도 —
    Gobert(div +24 · 노출 $33 · 등장 22회) · Knueppel(div +32 · 노출 $34 · 등장 13회)처럼
    div가 40 미달인데 돈이 걸린 건을 잡는다 — 는 그대로 살아 있다.
    문자 그대로가 필요하면 M6_EXP_MIN_DIV를 0으로 두면 된다."""
    d = div_of(p)
    if d is None: return None
    by_div = abs(d) >= M6_TH
    by_exp = exposure(p) >= M6_EXP and abs(d) >= M6_EXP_MIN_DIV
    if not (by_div or by_exp): return None
    return "div+노출" if (by_div and by_exp) else ("div" if by_div else "노출")

def m6_violations(players, pool=None, hits_fn=None):
    """지명 풀 안에서 M6 발동인데 유효한 근거 필드가 없음. tag은 보지 않는다."""
    pool = pool if pool is not None else pool_names(players)
    out = []
    for p in players:
        if p["name"] not in pool or not m6_trigger(p): continue
        if has_any_basis(p, hits_fn): continue
        out.append(p)
    return out

def flagged_names(players, hits_fn=None):
    """M5 ∪ M6 위반 선수 이름 — 진입/이탈 비교의 기준 집합."""
    return sorted({p["name"] for p in m5_violations(players, hits_fn)} |
                  {p["name"] for p in m6_violations(players, hits_fn=hits_fn)})

def band_watch(players):
    """경계 감시: |div| 18~22. 위반이 아니라 감시 대상."""
    rows = [(abs(div_of(p)), p["name"], div_of(p), p.get("tag"))
            for p in players if div_of(p) is not None and BAND[0] <= abs(div_of(p)) <= BAND[1]]
    return sorted(rows, key=lambda x: -x[0])


def unused_ceiling(p, hits):
    """미사용 천장 판정 — 등장 0회 또는 획득 불가. 사유 문구를 함께 돌려준다.
    M5(tag_basis)와 M6(my_max_basis) 양쪽이 같은 조건을 쓴다(30차 통일)."""
    obtainable = p["my_max"] >= p["market_low"]
    if hits >= 1 and obtainable: return None
    why = []
    if hits == 0: why.append("코어·피벗·대체후보 등장 0회")
    if not obtainable: why.append("획득 불가(my_max $%d < 시장 하단 $%d)" % (p["my_max"], p["market_low"]))
    return "미사용 천장 — " + " / ".join(why) + ". 천장이 입찰에 쓰이지 않음"


# ── 코어 등장 횟수 — 단일 구현 (30차) ────────────────────────────────────
# ⚠️ 처음엔 호출자 3곳이 각자 cores.json 전체를 훑었다. 그 결과
# tool/matchup_sim.py 가 **상대 로스터**를 cores.json(matchup_sim.opponents)에 쓰자
# 상대팀 선수 6명의 등장 횟수가 0 → 1이 되어 auto basis가 무효화됐다.
# 상대 로스터는 **우리 플랜이 아니다** — 그 이름이 있다고 우리가 입찰하지 않는다.
# 이제 우리 플랜 서브트리만 센다.
OUR_PLAN_KEYS = ("cores", "decision_table", "overheat_thresholds", "anchor_policy")

def core_hits(cj, name):
    """cores.json의 **우리 플랜** 안에서 그 이름이 등장하는 노드 수.
    matchup_sim(상대 로스터) 같은 비-플랜 서브트리는 세지 않는다."""
    n = 0
    def w(o):
        nonlocal n
        if isinstance(o, dict):
            for v in o.values(): w(v)
        elif isinstance(o, list):
            for v in o: w(v)
        elif o == name: n += 1
    for k in OUR_PLAN_KEYS:
        if k in cj: w(cj[k])
    return n

def hits_fn_for(cj):
    """core_hits를 cj에 바인딩한 클로저 — 호출자가 이걸 넘긴다."""
    return lambda name: core_hits(cj, name)
