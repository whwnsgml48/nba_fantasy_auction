#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GP가 **측정치인가 투영치인가**를 구분해 코어 노출을 센다 (39차 · 평가 세션 확장 지적).

문제
  혼합 모델이 GP를 **한 종류로만** 취급한다. 실제로는 두 종류다:

    Şengün      혼합GP 73.7  ← 그가 **실제로 뛴** 경기 수          측정치
    Haliburton  혼합GP 73.0  ← 2024-25에 뛴 경기 수를 2026-27
                               가용성으로 쓴 것 (2025-26 전체 결장)  **투영치**

  `cat_model`은 둘을 구분하지 않고 `avail = GP/82` 로 같이 쓴다.
  `measured_source.seasons` 에 정보가 있지만 **평가 경로 어디에서도 이 구분을 쓰지 않는다.**
  `gp_qualified` 도 GP 임계값이지 출처가 아니다.

  즉 "아킬레스 복귀 시즌에 건강한 73경기"가 다른 선수의 실측 73경기와 **같은 무게**로
  들어간다. 그 가정이 어디에 걸려 있는지 아무도 세어본 적이 없다.

🔴 단위 함정 — `weight` 는 0~1 비율이 **아니다**
  `seasons["2025-26"].weight` 는 **GP 기반 원 가중치**다(Trae Young: 2025-26 w=22.5 / GP=15,
  2024-25 w=76.0 / GP=76). 두 시즌 가중치 합이 우연히 98~99 근처라 **원값이 퍼센트처럼
  보이지만** 그렇게 읽으면 안 된다. 정규화해야 한다:

      실측 비중 = w(2025-26) / (w(2025-26) + w(2024-25))

  이 스크립트를 처음 쓸 때 `weight < 0.15` 로 걸러서 **투영 3명만 잡고 Trae·Sabonis를
  놓쳤다.** 평가 세션의 목록(23% · 29%)이 맞았고 제 필터가 틀렸다.

무엇을 하지 않는가
  · `data/` 를 쓰지 않는다. 파생 플래그를 **산출만** 한다.
  · 불변식을 만들지 않는다 — 헤지 유무 판단에 사람이 필요하고, 넣을지 여부는
    평가 세션에 물어보기로 했다(39차).
"""
import json, io, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))

FULL_PROJ = 0.001   # 실측 비중이 사실상 0 = 완전 투영
MIXED_LO  = 0.30    # 대부분이 옛 시즌
MIXED_HI  = 0.50    # 절반 미만


def measured_share(p):
    """2025-26 실측이 혼합에서 차지하는 **정규화 비중**. 근거가 없으면 None."""
    ss = (p.get("measured_source") or {}).get("seasons") or {}
    a = (ss.get("2025-26") or {}).get("weight") or 0.0
    b = (ss.get("2024-25") or {}).get("weight") or 0.0
    return (a / (a + b)) if (a + b) > 0 else None


def provenance(p):
    """GP 출처 등급. `gp_is_projection` 은 완전 투영만 True."""
    sh = measured_share(p)
    if sh is None:
        return "근거없음", None, False
    if sh <= FULL_PROJ:
        return "투영", sh, True
    if sh < MIXED_LO:
        return "혼합-저", sh, False
    if sh < MIXED_HI:
        return "혼합", sh, False
    return "실측", sh, False


def hedge_declared(cid, name):
    """헤지가 **선언돼 있는가**. 지금은 서술문뿐이라 문자열로 찾는다 —
    그것이 곧 이 감사의 요점이다(규칙이 아니라 서술문이라 재설계에서 사라진다)."""
    where = []
    f = (PL[name].get("flag") or "") + " " + (PL[name].get("verdict") or "")
    if "헤지" in f:
        where.append("players.flag")
    co = next((c for c in CJ["cores"] if c["id"] == cid), None)
    if co and "헤지" in json.dumps(co, ensure_ascii=False):
        where.append("cores.%s" % cid)
    return where


def main():
    print("=" * 92)
    print("GP 출처 감사 — 측정치 vs 투영치")
    print("=" * 92)
    db = [(n, *provenance(p)) for n, p in PL.items()]
    for lab in ("투영", "혼합-저", "혼합"):
        names = [n for n, g, s, _ in db if g == lab]
        print("  %-7s %3d명%s" % (lab, len(names), ("  " + ", ".join(sorted(names)[:6])) if names else ""))
    print()

    print("■ 코어 **1순위 슬롯** 노출 (실측 비중 < %.0f%%)" % (MIXED_HI * 100))
    print("  %-4s %-5s %-24s %8s %8s %-6s %s" % ("코어", "슬롯", "선수", "실측비중", "혼합GP", "등급", "헤지 선언"))
    rows = []
    for co in CJ["cores"]:
        for s in co["slots"]:
            n = s["candidates"][0]["name"]
            if n not in PL:
                continue
            g, sh, isproj = provenance(PL[n])
            if sh is None or sh >= MIXED_HI:
                continue
            rows.append((co["id"], s["slot"], n, sh, g, bool(s.get("is_anchor"))))
    for cid, slot, n, sh, g, anc in sorted(rows, key=lambda r: (r[3], r[0])):
        h = hedge_declared(cid, n)
        print("  %-4s %-5s %-24s %7.1f%% %8s %-6s %s%s" % (
            cid, slot, n, sh * 100, (PL[n].get("measured_source") or {}).get("GP"),
            g, ("★앵커 " if anc else ""), (" · ".join(h) if h else "🔴 없음")))
    cores_hit = sorted({r[0] for r in rows})
    print("  → 슬롯 %d개 · **코어 %d/%d개**(%s)" % (
        len(rows), len(cores_hit), len(CJ["cores"]), ", ".join(cores_hit)))

    print()
    print("■ 헤지 선언이 없는 노출")
    bad = [(c, s, n) for c, s, n, sh, g, a in rows if not hedge_declared(c, n)]
    for c, s, n in bad:
        print("  🔴 %s %s %s" % (c, s, n))
    if not bad:
        print("  없음")
    print()
    print("⚠️ 헤지가 있는 것도 **서술문**이다(`flag` 문자열 · `premise` 문장). 규칙이 아니라서")
    print("   다음 재설계에서 조용히 사라질 수 있다 — c1·c3 피벗 재설계가 예정돼 있다.")
    print("⚠️ 이 감사는 '가정이 어디 걸려 있나'를 셀 뿐, **GP가 실제로 몇일지는 답하지 못한다.**")
    print("   아킬레스·반월판 복귀 시즌 표본이 DB에 없다. 견고성 시험으로만 다룰 것.")


if __name__ == "__main__":
    main()
