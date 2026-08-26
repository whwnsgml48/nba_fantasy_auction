#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/06-cores.md를 cores.json에서 **전량 생성**한다.

왜 만드는가 (36차)
  README와 HANDOFF는 둘 다 "docs/06은 cores.json에서 전체 재생성된다"고 적어놨는데
  **생성기가 존재하지 않았다.** 손으로 쓴 문서가 '자동 생성'으로 표기돼 있었으므로
  아무도 갱신하지 않았고, 33~35차(코어 재설계·예비비·가격 스키마)를 하나도 반영하지
  못한 채 5차수를 낡았다. 발견 당시 상태:
    - c7이 아직 옛 '반센터 인플레'(빅맨 $25/$36) — 33차에 A1(중가 센터 전환)으로 전면 교체됨
    - 코어 총액 7개 중 6개 불일치 (c1 $187 vs 실제 $182 등)
    - T.J. McConnell 21회 등장 — 현재 그를 1순위로 쓰는 코어는 0개
    - 예비비·승률·maximin 0회 — 34·30차 도입 개념이 통째로 없음
    - "15개 플랜(백업 1종 포함)" — 백업은 33차 c7 교체 때 사라져 **14개**다
  이 프로젝트의 반복 실패("정적으로 적어둔 안내는 반드시 낡는다")의 최신 사례다.

경계
  docs/03과 달리 **부분 교체가 아니라 파일 전체를 쓴다.** docs/06은 표가 본문의 9할이고
  산문도 전부 데이터에서 나오거나(note·rationale·premise·_note) 이 파일의 PROSE에 있다.
  → 문서를 손으로 고치지 말 것. 문구를 바꾸려면 데이터나 이 스크립트를 고친다.

읽는 소스
  data/cores.json        코어·피벗·판단표·임계값·앵커정책 (주 소스)
  data/players.json      포지션(C 자격 표기)·시장가
  data/matchup_sim.json  주간 승률 (있으면 표에 넣고, 없으면 그 절을 생략한다)
"""
import json, io, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC  = f"{BASE}/docs/06-cores.md"
CJ   = json.load(io.open(f"{BASE}/data/cores.json",   encoding="utf-8"))
PL   = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
try:
    SIM = json.load(io.open(f"{BASE}/data/matchup_sim.json", encoding="utf-8"))
except Exception:
    SIM = None

BUDGET = 200

# ── 데이터에 없는 산문만 여기 둔다. 숫자는 절대 여기 쓰지 않는다(전부 f-string 계산) ──
PROSE = {
"header": """> ⚠️ **실전 확정안이 아니라 가설 묶음입니다.** `노리는 캣`은 겨냥하는 캣 목록이며,
> 승리 확률은 별도 지표(`data/matchup_sim.json`의 주간 승률)로 봅니다. 두 개념을 섞지 마십시오.

**이 문서는 `tool/gen_docs06.py`가 `data/cores.json`에서 전량 생성합니다.**
손으로 고치면 다음 생성에 날아갑니다 — 숫자를 바꾸려면 데이터를 바꾸십시오.
검증: `python3 validate.py`""",

"decide_points": """- **센터 시장 붕괴면 코어 7이 무조건 1순위입니다.** 코어 6·4의 *과열 피벗보다 먼저* 전환합니다 —
  피벗은 센터 하나가 비싸질 때의 대응이고, 두 명 이상이면 전제 자체가 깨진 것입니다.
- 34차에 **실행 가능성 제약**(저가 센터 6명을 `overheat_at` 이상으로 강제 매수) 하에서
  재계산한 결과, 그 세계에서 조립 가능한 채택 코어는 **c7 하나뿐**입니다
  (c1 $203 · c6 $209로 예산 초과). 33차의 "우선 0을 c6로" 제안은 이 근거로 철회됐습니다.
- **"승률이 높다"와 "그 로스터를 살 수 있다"는 다른 질문입니다.** 아래 승률표를 읽을 때
  발동 조건이 참인 세계의 가격으로 강제 매수시킨 뒤 총액을 확인하십시오.""",

"anchor_head": """`my_max`가 계획가보다 높아도 코어에 남는 돈이 없으면 더 부를 수 없습니다.
그래서 **명목 여유가 아니라 실효 여유(`effective_headroom`)로 판정**합니다.""",

"price_schema": """35차에 `plan_price` 한 필드가 세 가지 뜻(입찰 상한 · 기대 지출 · 입찰 목표)을
겸하던 것을 쪼갰습니다. 이 문서의 **계획가는 `expected_cost`(기대 낙찰가)** 이고,
경매장에서 **부를 수 있는 최대치는 `bid_ceiling`** 입니다 — 두 숫자는 다릅니다.

| 필드 | 계산 | 뜻 |
|---|---|---|
| `bid_ceiling` | `min(my_max, 단일상한, 철수가)` | **부를 최대치** |
| `expected_cost` | `clamp(시장중간, ·, bid_ceiling)` | **예산 계산용 기대 낙찰가** |
| `plan_price` | `expected_cost` 별칭 | 툴·기존 검사 하위 호환 |""",

"reserve": """예비비 = `$200 − 계획총액`. 앵커 한 명이 시장 상단까지 올라가면 예산이 넘으므로
**남겨두는 돈**입니다(34차 · 불변식 I22). 목표 ≥$12 · 경고 <$8 · 위반 <$4 ·
$25 초과는 "과소 편성"(로스터가 예산을 못 씀) 경고입니다.""",

"sim": """상대 6종에 대해 주 단위 표본을 뽑아 낸 **주간 승률**입니다(30·32차 · `tool/matchup_sim.py`).
목적함수는 **maximin** — 상대 6종 중 **최저** 승률, 동률이면 빅5 동시붕괴 확률이 낮은 쪽.

⚠️ `data/matchup_sim.json`의 `objective.note`: **"값만 산출한다. 이 지표로 코어를 고르지 않는다(32차)."**
같은 3% 마진이 캣에 따라 승률 52~66%라 "이기는 캣 수"만으로는 강약을 못 가립니다.
반대로 승률만 보고 고르면 34차처럼 **조립 불가능한 로스터**를 1등으로 뽑습니다.""",

"footer_checks": """`validate.py`가 기본 코어와 피벗 로스터 전부에 대해 상시 검사합니다.
불변식 전문은 `HANDOFF.md`의 「반드시 지켜야 하는 불변식」을 보십시오.""",
}


# ───────────────────────────── helpers ─────────────────────────────
def is_c(name):
    """야후 C 자격 — players.json의 pos 문자열에 C가 있으면 True"""
    return "C" in (PL.get(name, {}).get("pos") or "")

def cmark(name):
    return " `C`" if is_c(name) else ""

def money(v):
    return "—" if v is None else f"${v}"

def mkt(name):
    p = PL.get(name)
    return f"${p['market_low']}-{p['market_high']}" if p else "—"

def ceil_of(entry):
    """엔트리(후보/로스터 항목)의 bid_ceiling. 없으면 my_max로 폴백."""
    if entry.get("bid_ceiling") is not None:
        return entry["bid_ceiling"]
    p = PL.get(entry.get("name"))
    return p["my_max"] if p else None

def sim_of(cid):
    if not SIM:
        return None
    return (SIM.get("cores") or {}).get(cid)

def pct(x):
    return "—" if x is None else f"{x*100:.1f}%"

def cats_str(lst):
    return " ".join(lst) if lst else "—"

def cid_up(cid):
    return cid.upper()

OPP_LABEL = {"random": "무작위", "value_max": "가치최대", "big_stack": "빅스택",
             "guard_stack": "가드스택", "baseline": "기준선", "benchmark": "벤치마크",
             "overheat_big": "과열빅"}
OPP_ORDER = ["random", "value_max", "big_stack", "guard_stack", "baseline", "benchmark"]

def opp_label(v):
    """min_win_rate_vs 는 동률을 담을 수 있어 **리스트**다 — 스칼라로 가정하지 말 것"""
    if v is None:
        return "—"
    if isinstance(v, str):
        v = [v]
    return " · ".join(OPP_LABEL.get(x, str(x)) for x in v) or "—"


# ───────────────────────────── sections ─────────────────────────────
def sec_decision():
    o = ["## 판단 순서 (조건부 우선순위)", "",
         f"> **{CJ['decision_oneliner']}**", "",
         "| 우선 | 조건 | 선택 | 근거 |", "|---|---|---|---|"]
    byid = {c["id"]: c for c in CJ["cores"]}
    for r in CJ["decision_table"]:
        core = byid[r["core"]]
        nm = core["name"].split("·", 1)[-1].split("—", 1)[-1].strip()
        note = (r.get("note") or "").replace("\n", " ")
        fe = (r.get("cond") or {}).get("feasibility")
        if fe:
            note += f" **실행 조건: {fe['required']}** (실패 시 → {fe['on_fail']})"
        o.append(f"| **{r['prio']}** | {r['label']} | **{cid_up(r['core'])}** — {nm} | {note} |")
    o += ["", "### 판단의 요점", "", PROSE["decide_points"], "",
          "툴 우측 `판단 순서` 카드가 이 표를 행별로 **충족 / 불가 / 미정 / 기본값**으로 실시간",
          "판정하고 현재 권장 코어를 강조합니다.", ""]
    return "\n".join(o)


def sec_injury():
    o = ["## 장기 부상 제외 규칙", "", f"> {CJ['injury_exclude_rule']}", "",
         "| 선수 | 사유 |", "|---|---|"]
    n = 0
    for name, p in PL.items():
        if p.get("injury_exclude"):
            n += 1
            o.append(f"| **{name}** ({p.get('team') or '—'}) | {p.get('flag') or '장기 부상 제외'} |")
    if not n:
        o.append("| — | 현재 제외 대상 없음 |")
    o.append("")
    return "\n".join(o)


def sec_core7_trigger():
    row = next(r for r in CJ["decision_table"] if r["prio"] == "0")
    cond = row["cond"]
    tiers = CJ["overheat_tiers"]
    lbl = tiers[cond["tier"]]["label"]
    o = ["## 코어 7 발동 조건 (저가 센터 전제 붕괴)", "",
         "| 조건 | 판정 |", "|---|---|",
         f"| **{lbl}** 계층 {len(cond['players'])}명 중 **{cond['n']}명 이상**이 "
         f"`{cond['signal']}` 초과 | 툴 `판단 순서` 우선 0 자동 발동 |",
         "| 저가 빅맨 **3명 이상**이 계획가 대비 **25% 이상** 상승 | 툴 `시장가 보정` 계수 ×1.25 이상 |",
         "| `big_budget_cap` 지키며 C 자격 2명 + 유효 7캣 빌드 불가 | `빅맨 예산 초과` + `노리는 캣 미달` 동시 |",
         "",
         "판정 대상: " + " · ".join(cond["players"]), ""]
    nb = tiers["name_big"]
    o += [f"> ⚠️ **{nb['label']} 계층은 판정에 넣지 않습니다.** {nb['why']}", ""]
    if row.get("target_note"):
        o += [f"> 📌 {row['target_note']}", ""]
    return "\n".join(o)


def sec_thresholds():
    t = CJ["overheat_tiers"]
    o = ["## 과열 임계값 · 2계층 (단일 소스)", "", t["_note"], ""]
    for key in ("name_big", "low_cost_center", "anchor"):
        tier = t[key]
        rows = [x for x in CJ["overheat_thresholds"] if x.get("tier") == key]
        mark = "판정 대상" if tier.get("counts_toward_core7") else "코어 7 **무관**"
        o += [f"### {tier['label']} — {mark}", ""]
        if tier.get("evidence"):
            o += [f"> 실측 근거: {tier['evidence']}", ""]
        if tier.get("why"):
            o += [f"{tier['why']}", ""]
        o += ["| 선수 | 철수가 | 기대치 | 과열선 | my_max | 근거 |", "|---|---|---|---|---|---|"]
        for x in sorted(rows, key=lambda r: -(r.get("threshold") or 0)):
            p = PL.get(x["player"], {})
            o.append("| %s | `%s` | %s | %s | %s | %s |" % (
                x["player"], x.get("walk_away_rule") or x.get("rule") or "—",
                money(x.get("expected_2026_27")),
                f"`{x['overheat_rule']}`" if x.get("overheat_rule") else "— (앵커)",
                money(p.get("my_max")), (x.get("basis") or "").replace("\n", " ")))
        o.append("")
    return "\n".join(o)


def sec_anchors():
    o = ["## 앵커 여유 정책 (단일 소스)", "", CJ["anchor_policy"]["_note"], "",
         "| 정의 | 내용 |", "|---|---|"]
    for k, v in CJ["anchor_policy"]["definitions"].items():
        o.append(f"| `{k}` | {v} |")
    o += ["", "### 핵심: 명목 여유는 예산 여유가 없으면 허구다", "", PROSE["anchor_head"], ""]

    rows, cond_bets = [], []
    for c in CJ["cores"]:
        for s in c["slots"]:
            if not s.get("is_anchor"):
                continue
            ap = s.get("anchor_plan") or {}
            of = ap.get("on_fail") or {}
            act = {"substitute": "치환 → %s" % of.get("target"),
                   "switch_core": "**코어 전환 → %s**" % cid_up(str(of.get("target"))),
                   "pivot": "**과열 피벗 실행**"}.get(of.get("action"), of.get("action") or "—")
            rows.append((cid_up(c["id"]), s["slot"], s["candidates"][0]["name"], s["plan_price"],
                         ap.get("bid_ceiling"), ap.get("nominal_margin"), ap.get("effective_headroom"),
                         ap.get("constraint"), act, ap.get("dual_world_ok")))
            if c.get("conditional_on_discount") or (
                    not ap.get("dual_world_ok") and not ap.get("substitutes_dual_ok")):
                cond_bets.append((c, s, ap, of))

    o += [f"### 앵커 {len(rows)}개 현황", "",
          "| 코어 | 슬롯 | 앵커 | 계획 | 상한 | 명목 | 실효 | 제약 | 실패 시 | 실측곡선 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        o.append("| %s | %s | %s | %s | %s | %s | **%s** | `%s` | %s | %s |" % (
            r[0], r[1], r[2], money(r[3]), money(r[4]), money(r[5]), money(r[6]),
            r[7], r[8], "획득 가능" if r[9] else "**획득 불가**"))
    o += ["", "### 규칙 (`validate.py`가 검사)", ""]
    for i, rule in enumerate(CJ["anchor_policy"]["rules"], 1):
        o.append(f"{i}. {rule}")
    o.append("")

    if cond_bets:
        o += ["### 조건부 베팅 (시장 할인 없이는 확보 불가)", "",
              "| 코어 | 앵커 | 사유 | 실패 시 |", "|---|---|---|---|"]
        for c, s, ap, of in cond_bets:
            nm = s["candidates"][0]["name"]
            p = PL.get(nm, {})
            why = f"my_max ${p.get('my_max')} < 재적합 시장하단 ${p.get('market_low')} — 시장 할인 없이는 확보 불가"
            tgt = "**코어 전환 → %s**" % cid_up(str(of.get("target"))) if of.get("action") == "switch_core" else (of.get("note") or "—")
            o.append(f"| **{cid_up(c['id'])}** | {nm} | {why} | {tgt} |")
        o += ["", "이들은 대체후보가 **설계상 없습니다** — 앵커가 곧 코어의 전제입니다.", ""]
    return "\n".join(o)


def sec_summary():
    o = ["## 요약표", "", PROSE["price_schema"], "", PROSE["reserve"], "",
         "| | 코어 | 계획 | 예비비 | 빅맨/상한 | C자격 | 노리는 캣 | 포기 | 승리 캣 | 피벗 총액 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for c in CJ["cores"]:
        nm = c["name"].split("·", 1)[-1].split("—", 1)[-1].strip()
        pv = c["pivot_plan"]
        w = (c.get("cat_win_summary") or {}).get("wins_incl_dd")
        o.append("| %s | %s | $%d | $%d | $%d/$%d | %d | %d개 | %s | %s | $%d |" % (
            c["id"], nm, c["planned_total"], c.get("budget_slack", BUDGET - c["planned_total"]),
            c["big_budget_planned"], c["big_budget_cap"], c["c_eligible_count"],
            len(c["targeted_cats"]), ", ".join(c["punted_cats"]) or "—",
            f"**{w}**/13" if w else "—", pv["final_total"]))
    o.append("")
    return "\n".join(o)


def sec_sim():
    if not SIM:
        return ""
    o = ["## 주간 승률 (몬테카를로)", "", PROSE["sim"], "",
         "시행 %d회 · seed %s · 승리선 %d캣" % (SIM["iterations"], SIM["seed"], SIM["win_line"]), "",
         "| 코어 | " + " | ".join(OPP_LABEL[k] for k in OPP_ORDER) + " | **최소** | 최소 상대 | 빅5붕괴 |",
         "|---|" + "---|" * (len(OPP_ORDER) + 3)]
    order = sorted(CJ["cores"], key=lambda c: -((sim_of(c["id"]) or {}).get("min_win_rate") or 0))
    for c in order:
        s = sim_of(c["id"])
        if not s:
            continue
        cells = [pct((s.get(k) or {}).get("weekly_win_rate")) for k in OPP_ORDER]
        o.append("| %s | %s | **%s** | %s | %s |" % (
            c["id"], " | ".join(cells), pct(s.get("min_win_rate")),
            opp_label(s.get("min_win_rate_vs")),
            pct(s.get("tiebreak_p_big5_collapse"))))
    o += ["", "빅5 = " + " · ".join(SIM["big5"]) + " (동시에 지면 빅맨 전략 자체가 무너지는 묶음). "
          + SIM.get("collapse_note", ""), ""]
    return "\n".join(o)


def sec_core(c):
    pv = c["pivot_plan"]
    row = next((r for r in CJ["decision_table"] if r["core"] == c["id"]), None)
    slack = c.get("budget_slack", BUDGET - c["planned_total"])
    s = sim_of(c["id"])
    o = ["---", "", f"## {c['name']}", ""]
    if row:
        o += [f"**우선 {row['prio']}** — {row['label']}", ""]
    o += [f"> {c['premise']}", "",
          "**계획 $%d** · 예비비 **$%d** · 빅맨 $%d/$%d (C자격 %d명) · 노리는 캣 %d개 `%s` · 포기 `%s`" % (
              c["planned_total"], slack, c["big_budget_planned"], c["big_budget_cap"],
              c["c_eligible_count"], len(c["targeted_cats"]),
              cats_str(c["targeted_cats"]), cats_str(c["punted_cats"])), ""]
    if s:
        o += ["**주간 승률** 최소 **%s** (vs %s) · 빅5 동시붕괴 %s · 기대 승리 캣 %.2f" % (
            pct(s.get("min_win_rate")), opp_label(s.get("min_win_rate_vs")),
            pct(s.get("tiebreak_p_big5_collapse")),
            (s.get("random") or {}).get("expected_cats_won", 0)), ""]
    for key, lab in (("adoption_note", "채택 근거"), ("reserve_note", "예비비 구성")):
        if c.get(key):
            o += [f"> **{lab}** — {c[key]}", ""]

    o += ["### 기본 플랜", "",
          "| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |",
          "|---|---|---|---|---|---|---|---|"]
    for sl in c["slots"]:
        cands = sl["candidates"]
        first = cands[0]
        ap = sl.get("anchor_plan") or {}
        if sl.get("is_anchor"):
            of = ap.get("on_fail") or {}
            hint = {"substitute": "실패→치환 %s" % of.get("target"),
                    "switch_core": "실패→%s" % cid_up(str(of.get("target"))),
                    "pivot": "실패→피벗"}.get(of.get("action"), "")
            head = f"**{money(ap.get('effective_headroom'))}** ({hint})"
        else:
            head = "—"
        alts = [f"{x['name']} ${x.get('expected_cost', x['plan_price'])}" for x in cands[1:3]]
        alts += ["—"] * (2 - len(alts))
        o.append("| **%s**%s | $%d | %s | %s | %s | **%s**%s | %s | %s |" % (
            sl["slot"], " `앵커`" if sl.get("is_anchor") else "", sl["plan_price"],
            money(ceil_of(first)), head, sl.get("role") or "—",
            first["name"], cmark(first["name"]), alts[0], alts[1]))

    o += ["", "### 과열 피벗", "",
          "**트리거**: " + " · ".join(f"`{t['player']} {t['rule']}`" for t in pv["triggers"]), "",
          f"> {pv['rationale']}", "",
          "| 슬롯 | 변경 | 계획가 | 증감 |", "|---|---|---|---|"]
    for sw in pv["swaps"]:
        # c7 처럼 slot·delta 없이 out/in 만 있는 항목이 있다 — 없으면 계산/추론한다
        cost_in  = sw["in"].get("expected_cost",  sw["in"]["plan_price"])
        cost_out = sw["out"].get("expected_cost", sw["out"]["plan_price"])
        slot = sw.get("slot") or next(
            (r["slot"] for r in pv["final_roster"] if r["name"] == sw["in"]["name"]), "—")
        o.append("| %s | %s → **%s** | $%d | %+d |" % (
            slot, sw["out"]["name"], sw["in"]["name"],
            cost_in, sw.get("delta", cost_in - cost_out)))
    pslack = BUDGET - pv["final_total"]
    warn = " ⚠️ **과소 편성** (로스터가 예산을 못 씀)" if pslack > 25 else ""
    o += ["", "**피벗 최종 9인** — 총액 $%d · 예비비 $%d%s · 빅맨 $%d (C자격 %d명) · 노리는 캣 `%s` · 포기 `%s`" % (
              pv["final_total"], pslack, warn, pv["final_big_budget"], pv["final_c_eligible"],
              cats_str(pv["targeted_cats"]), cats_str(pv["punted_cats"])), "",
          "| 슬롯 | 선수 | 계획가 | 상한 |", "|---|---|---|---|"]
    for r in pv["final_roster"]:
        o.append("| %s | %s%s | $%d | %s |" % (
            r["slot"], r["name"], cmark(r["name"]),
            r.get("expected_cost", r["plan_price"]), money(ceil_of(r))))
    o.append("")

    fb = pv.get("fallback")
    if fb:
        o += ["#### 백업 규칙 (1차 피벗 실행 불가 시)", "",
              "**발동 조건** (`%s`): " % fb.get("condition_logic", "AND")
              + " 그리고 ".join(f"`{r['player']} > ${r['threshold']}`" for r in fb.get("condition_rules", [])), "",
              f"> {fb.get('rationale','')}", "",
              "**백업 최종 9인** — 총액 $%d · 노리는 캣 `%s` · 포기 `%s`" % (
                  fb["final_total"], cats_str(fb.get("targeted_cats", [])),
                  cats_str(fb.get("punted_cats", []))), "",
              "| 슬롯 | 선수 | 계획가 |", "|---|---|---|"]
        for r in fb["final_roster"]:
            o.append("| %s | %s%s | $%d |" % (r["slot"], r["name"], cmark(r["name"]),
                                              r.get("expected_cost", r["plan_price"])))
        o.append("")
    return "\n".join(o)


def sec_validate():
    n_base = len(CJ["cores"])
    n_piv = sum(1 for c in CJ["cores"] if c["pivot_plan"].get("final_roster"))
    n_fb = sum(1 for c in CJ["cores"] if c["pivot_plan"].get("fallback"))
    tot = n_base + n_piv + n_fb
    o = ["---", "", "## 자동 검증 (`python3 validate.py`)", "", PROSE["footer_checks"], "",
         "| 규칙 | 적용 대상 |", "|---|---|",
         f"| 9개 슬롯 완성 · 포지션 자격 | 기본 {n_base} + 피벗 {n_piv}" + (f" + 백업 {n_fb}" if n_fb else "") + " |",
         "| `market_low ≤ plan_price ≤ my_max` | 1순위 + 대체 후보 전부 |",
         "| 가격 3필드 정합 (I23) | `bid_ceiling` ≤ my_max · `expected_cost` ≤ `bid_ceiling` ≤ 시장 상단 |",
         "| 예비비 (I22) | 목표 ≥$12 · 경고 <$8 · 위반 <$4 · >$25 과소 편성 |",
         "| 총액 ≤ $200 · 빅맨 예산 ≤ `big_budget_cap` | 전 플랜 |",
         "| 장기 부상 제외 준수 · 선수 중복 없음 | 전 플랜 |",
         "| 캣 선언 = 실측 팀 한계기여 | 전 플랜 |",
         "| 트리거·백업 조건이 임계값 단일 소스와 일치 | 피벗 |",
         "| 툴 임베드 상수 · P 배열 동기화 (I20) | `tool/auction-console.html` |",
         "",
         f"**총 {tot}개 플랜(기본 {n_base} + 피벗 {n_piv}"
         + (f" + 백업 {n_fb}" if n_fb else " · 백업 없음") + ")**", ""]
    if not n_fb:
        o += ["> 📌 백업 로스터는 33차에 c7을 A1으로 전면 교체하면서 사라졌습니다"
              "(구 c7의 백업이었고 `cores.json.c7_old`에 함께 보존). "
              "\"15개 플랜\"이라는 옛 표기를 보면 그 문서가 33차 이전입니다.", ""]
    return "\n".join(o)


def sec_pre_draft():
    return "\n".join([
        "## 드래프트 직전 필수 확인", "",
        "| 항목 | 이유 |", "|---|---|",
        "| **야후 실제 포지션 자격** | 데이터는 G/F/C 수준만 저장 — 슬롯 배치가 유효하려면 실자격 확인 필요 |",
        "| **지명 시 자동 $1 입찰 여부** | 태우기 지명 전략의 전제 |",
        "| **Sabonis · Haliburton 프리시즌 상태** | c5는 Sabonis 건강 확인이 발동 조건 · c1/c5는 Hali 할인이 전제 |",
        "| **소속 미확인 선수** | `team: \"—\"` 로 남은 선수 갱신 |", ""])


def main():
    parts = ["# 코어 %d종 + 과열 피벗 + 판단 순서" % len(CJ["cores"]), "", PROSE["header"], "",
             sec_decision(), sec_injury(), sec_core7_trigger(), sec_thresholds(),
             sec_anchors(), sec_summary(), sec_sim()]
    for c in CJ["cores"]:
        parts.append(sec_core(c))
    parts += [sec_validate(), sec_pre_draft()]
    # 빈 문자열을 걸러내면 블록 사이 빈 줄까지 사라진다(제목 바로 밑에 표가 붙는다).
    # 블록 단위로 양끝 개행을 정규화하고 정확히 한 줄씩 띄운다.
    blocks = [b.strip("\n") for b in parts if b and b.strip()]
    doc = "\n\n".join(blocks) + "\n"
    io.open(DOC, "w", encoding="utf-8").write(doc)
    print("docs/06-cores.md 생성 완료 — %d줄 · 코어 %d · 피벗 %d · 백업 %d" % (
        doc.count("\n") + 1, len(CJ["cores"]),
        sum(1 for c in CJ["cores"] if c["pivot_plan"].get("final_roster")),
        sum(1 for c in CJ["cores"] if c["pivot_plan"].get("fallback"))))


if __name__ == "__main__":
    main()
