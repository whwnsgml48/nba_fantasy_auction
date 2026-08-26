#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사용자 노출 텍스트 정리 — 내부 차수 표기 제거 + 사실 오류 정정 (39차 · 사용자 지시).

사용자 지시: "이런 잘못된 텍스트 남아 있는거 싹 고치라고해라. 막 33차 이런 말도 싹 빼고"

원칙
  · **차수를 지우고 끝내지 않는다.** 그 자리에 "무엇을/왜"를 넣는다.
      ✗ "34차 예비비 재구성 — Knueppel 대체"   (그 슬롯이 뭐 하는 자리인지 0 정보)
      ○ "STL 보조 $5 다트 — 예비비 확보용"
  · 대상은 **화면에 뜨는 필드만**: cores.json 의 slots[].role · premise ·
    pivot_plan.rationale · decision_table[].note, players.json 의 verdict(툴 note).
  · `docs/04-audit-log.md` · `my_max_basis` · `threshold_history` 등 **감사 추적이
    목적인 필드는 그대로 둔다** — 화면에 안 뜬다.
  · c2 premise 는 A가 재탐색 중이므로 **건드리지 않는다.**

실행:  python3 patch_user_text.py --dry    (기본: 미리보기)
       python3 patch_user_text.py --apply  (data/ 기록 — A가 실행)
"""
import json, io, os, re, sys

BASE = "/Users/johnny/personal_work/nba_fantasy_auction_2026"
CP, PP = BASE + "/data/cores.json", BASE + "/data/players.json"
APPLY = "--apply" in sys.argv
ROUND = re.compile(r"\d+차")

# ── 슬롯 role 재작성 (코어 base + 피벗 final_roster 양쪽) ────────────────
# 옛 문구는 "34차 예비비 재구성 — X 대체" 형태로, **그 슬롯이 무엇을 하는 자리인지
# 전혀 말해주지 않고** 이미 로스터에 없는 선수 이름을 가리킨다.
ROLES = {
    ("c2", "BN", "DeMar DeRozan"):
        "A/T +0.142 · FT% 엘리트 — $8 저가 가드",
    ("c3", "BN", "Damian Lillard"):
        "3PM·FT%·AST 동시 공급 — ⚠ 아킬레스 복귀 · 가중치 근거는 2024-25",
    ("c4", "PG", "Trae Young"):
        "AST 10.8 공급 PG — A/T +0.169 · FT% 엘리트",
    ("c5", "BN", "Dyson Daniels"):
        "STL 2.0 리그 공동 1위 · 가드 OREB 2.1",
    ("c6", "UTIL", "VJ Edgecombe"):
        "STL 보조 $5 다트 — 예비비 확보용",
    # 🔴 사용자가 직접 잡은 것: role 이 "3PT 소스"인데 2순위가 3PM 0.8 이었다.
    #    평가 세션 실측(대체 후보 21명 · 12팀 상대): 3PM 상위 셋이 오히려 꼴찌 그룹이고
    #    Bane 이 이긴 이유는 전방위 기여다. 이 자리는 3점 자리가 아니다.
    ("c6", "BN", "Desmond Bane"):
        "전방위 저가 윙 — FT% 엘리트 · 후보 21명 실측 1위",
}

# ── c6 BN 대체 후보 재정렬 (실측 순위) ──────────────────────────────────
# 옛 후보: Clingan(실측 21명 중 13위 · 3PM 0.8) · Knueppel(6위)
# 새 후보: Josh Hart $4 (평균 −0.4%p·최저 −0.2%p 인데 $18 싸다) · Vučević $2 (4위)
C6_BN_ALTS = ["Josh Hart", "Nikola Vučević"]

# ── 전면 재작성 (차수 제거 + 사실 정정) ─────────────────────────────────
PREMISE = {
    # ⚠️ 21차/19차 논쟁 기록이 계획 설명에 남아 있었다 — 지금 무엇을 하는 플랜인지와 무관.
    "c4": ("잉여가 $8~31 구간에 몰려 있으므로 그 구간만으로 9칸을 채운다. 최고가 $31로 "
           "결장 리스크가 분산되고 앵커 실패에 면역 — 앵커를 못 잡았을 때의 안전망이다. "
           "⚠️ PTS·TOV 포기가 실제로 나머지 7캣 승리로 이어지는지는 검증되지 않았다."),
    # "33차 재설계 · A1 후보 채택" = 지금 무엇인지가 아니라 무엇이 **아니었는지**를 설명.
    "c7": ("센터 인플레의 답은 센터를 버리는 것이 아니라 **중가 센터로 갈아타는 것**이다 — "
           "저가 센터(Clingan·Gobert 계층)가 과열되면 Mobley $23 · Okongwu $5 로 옮겨 "
           "OREB·BLK·FG%의 바닥을 지키고 KAT·D.White 축은 그대로 둔다. "
           "저가 센터 노출이 Gobert 한 명뿐이라 **과열 세계에서도 예산 안에 조립된다** "
           "(강제 매수 시 $189 · 예비비 $11) — 그것이 이 코어가 우선 0인 이유다."),
}

RATIONALE = {
    # 🔴 존재하지 않는 교체 2건(Daniels→Ausar · Knueppel→Trey Murphy)을 설명하고 있었고
    #    빅맨 예산도 $96 로 적혀 있었다(실제 $76). 실제 교체는 Gobert→Okongwu 하나뿐이다.
    "c6": ("정상 시장 기본값 코어의 생존 분기. 저가 센터가 과열되면 **Gobert $8 → Okongwu $5** "
           "하나만 바꿔 빅맨을 $76로 낮추고 나머지 8칸은 그대로 둔다 — 이 코어는 저가 센터를 "
           "쓸어담는 축이 아니라 전방위 윙으로 슬롯 효율을 사는 축이라 센터 과열에 노출이 작다. "
           "저가 빅 3명 이상이 과열되면 피벗이 아니라 코어 7로 전환한다."),
    # 빅맨 서술 $96 ≠ 실제 $78.
    "c1": None,   # 아래에서 숫자만 치환
}

# ── 판단표 note 정정 (임계값이 낡았다) ──────────────────────────────────
# "임계 $48 · 내 최대가 $50" 은 둘 다 옛 값이다. 지금은 my_max·철수가·임계값이 전부 $56.
C1_NOTE = ("Hali가 정말 할인되면 코어 1의 천장이 가장 높다. 임계 $56은 철수가와 같은 값이고, "
           "실측 시장이 $54-66이라 **중간값 아래에서 잡아야** 성립한다 — 할인이 없으면 "
           "이 행은 발동하지 않고 기본값 c6로 간다.")


def show(tag, old, new):
    print("  [%s]" % tag)
    print("    - %s" % (old or "")[:150])
    print("    + %s" % (new or "")[:150])


def main():
    cj = json.load(io.open(CP, encoding="utf-8"))
    pl = json.load(io.open(PP, encoding="utf-8"))
    n = 0

    print("=== 1. 슬롯 role 재작성 (base + 피벗 로스터) ===")
    for co in cj["cores"]:
        for s in co["slots"]:
            key = (co["id"], s["slot"], s["candidates"][0]["name"])
            if key in ROLES:
                show("role %s %s" % (co["id"], s["slot"]), s.get("role"), ROLES[key]); n += 1
                s["role"] = ROLES[key]
        for r in co["pivot_plan"].get("final_roster") or []:
            key = (co["id"], r["slot"], r["name"])
            if key in ROLES:
                r["role"] = ROLES[key]

    print("\n=== 2. c6 BN 대체 후보 재정렬 (실측 순위) ===")
    c6 = next(c for c in cj["cores"] if c["id"] == "c6")
    bn = next(s for s in c6["slots"] if s["slot"] == "BN")
    byname = {p["name"]: p for p in pl}
    old = [c["name"] for c in bn["candidates"]]
    keep = bn["candidates"][0]
    new_c = [keep]
    for nm in C6_BN_ALTS:
        p = byname[nm]
        mid = round((p["market_low"] + p["market_high"]) / 2)
        new_c.append({"name": nm, "plan_price": min(mid, p["my_max"])})
    bn["candidates"] = new_c
    show("c6 BN 후보", " · ".join(old), " · ".join(c["name"] for c in new_c)); n += 1

    print("\n=== 3. premise 재작성 ===")
    for cid, txt in PREMISE.items():
        co = next(c for c in cj["cores"] if c["id"] == cid)
        show("premise %s" % cid, co["premise"], txt); co["premise"] = txt; n += 1

    print("\n=== 4. 피벗 rationale 정정 ===")
    c6["pivot_plan"]["rationale"] = RATIONALE["c6"]
    show("rationale c6", "(존재하지 않는 교체 2건 + 빅맨 $96)", RATIONALE["c6"]); n += 1
    c1 = next(c for c in cj["cores"] if c["id"] == "c1")
    r1 = c1["pivot_plan"]["rationale"].replace("($96)", "($78)").replace("$96", "$78")
    r1 = ROUND.sub("", r1).replace("⚠️ 정정:", "⚠️").replace("  ", " ")
    show("rationale c1", c1["pivot_plan"]["rationale"], r1)
    c1["pivot_plan"]["rationale"] = r1; n += 1

    print("\n=== 5. 판단표 note ===")
    d1 = next(x for x in cj["decision_table"] if x["core"] == "c1")
    show("dt note c1", d1["note"], C1_NOTE); d1["note"] = C1_NOTE; n += 1

    print("\n=== 6. 남은 차수 표기 기계 제거 (내용은 보존) ===")
    def strip(t):
        # 문장 맨 앞의 "N차 정정:" 은 통째로 뺀다 — 뒤 문장이 이미 "기존 ~은 ~이었다"로
        # 정정임을 설명한다. "정정:" 만 남기면 무엇의 정정인지 없는 채로 떠 있다.
        # ⚠️ 는 두 코드포인트(U+26A0 U+FE0F)다. `⚠️?` 로 쓰면 **변이 선택자만** 선택적이
        # 되어 ⚠ 자체는 필수가 된다 — 그래서 "22차 정정:" 처럼 이모지 없는 접두가
        # 전부 빗나가고 맨 뒤 포괄 규칙이 "22차 "만 지워 "정정:" 이 홀로 남았다.
        W = r"(?:\u26a0\ufe0f?\s*)?"
        t = re.sub(r"^\s*" + W + r"\d+차\s*정정[:：]\s*", "", t)
        t = re.sub(W + r"\d+차\s*정정[:：]\s*", "⚠️ ", t)
        t = re.sub(W + r"\d+차\s*[:：]\s*", "⚠️ ", t)
        t = re.sub(r"🔄\s*\*\*\d+차\s*변경[:：]\s*", "🔄 **", t)
        t = re.sub(r"\s*\(\d+차\)", "", t)
        t = re.sub(r"\d+차에\s*", "", t)
        t = re.sub(r"\d+차\s*", "", t)
        return re.sub(r"\s{2,}", " ", t).strip()

    for co in cj["cores"]:
        for k in ("premise",):
            if co.get(k) and ROUND.search(co[k]) and co["id"] != "c2":
                new = strip(co[k]); show("%s %s" % (k, co["id"]), co[k], new); co[k] = new; n += 1
        pv = co["pivot_plan"]
        if pv.get("rationale") and ROUND.search(pv["rationale"]):
            new = strip(pv["rationale"]); show("rationale %s" % co["id"], pv["rationale"], new)
            pv["rationale"] = new; n += 1
    for d in cj["decision_table"]:
        for k in ("label", "note"):
            if d.get(k) and ROUND.search(d[k]):
                new = strip(d[k]); show("dt %s %s" % (k, d["core"]), d[k], new); d[k] = new; n += 1
    for p in pl:
        v = p.get("verdict")
        if isinstance(v, str) and ROUND.search(v):
            new = strip(v); show("verdict %s" % p["name"], v, new); p["verdict"] = new; n += 1

    print("\n총 %d건" % n)
    if APPLY:
        io.open(CP, "w", encoding="utf-8").write(json.dumps(cj, ensure_ascii=False, indent=1) + "\n")
        io.open(PP, "w", encoding="utf-8").write(json.dumps(pl, ensure_ascii=False, indent=1) + "\n")
        print("→ data/ 기록. 이어서: recompute_cores → sync_tool → gen_docs06 → "
              "gen_players_csv → validate → 아티팩트 재발행")
    else:
        print("→ 미리보기만. 적용하려면 --apply (data/ 는 A 소유)")


if __name__ == "__main__":
    main()
