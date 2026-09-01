#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""화면에 남은 철회·낡은 문구 정리 (40차 후반).

발행본을 **실제로 열어 보고** 찾았습니다 — 파일 grep 만으로는 「어느 것이 화면에 뜨는가」를
못 가립니다. 두 계열이 나왔습니다.

① 철회된 순위 주장이 4곳에 살아 있다
   「전 코어 1위」는 라인업 자격 보정으로 **철회**됐습니다(상위 5개가 1.3%p 안 · 오차 ±0.6%p).
   그런데 `players.Bane.note` · `cores.c2.premise` · `cores.c6.premise` ·
   `cores.c5.pivot_plan.rationale` 에 그대로 남아 화면에 뜹니다.
   ⚠️ 감사 추적 필드(`jokic_gp_sensitivity_39.question` · `redesign_39.collapse_reference`)는
     **건드리지 않습니다** — 그건 당시 판단의 기록이고 화면에 안 뜹니다.

② 「야후 자격을 드래프트 당일 확인하라」 경고 4건이 낡았다
   야후 실자격 19명을 확인해 `pos_yahoo` 로 넣었습니다. 그 경고는 **확인 전** 문구이고,
   내용도 이제 틀립니다 — Amen 은 c3 의 SF 가 아니라 SG 이고, Şengün 은 PF 입니다.
   확인이 **끝난** 선수에게는 확인된 자격을 적고, 재확인이 필요한 두 명(Amen·Okongwu,
   기록끼리 충돌)에게만 그 사실을 남깁니다.
"""
import json, io, os

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import oneshot

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PP, CP = BASE + "/data/players.json", BASE + "/data/cores.json"

# 자격 확인이 끝난 선수의 flag 를 대체한다. 충돌 2건만 재확인 문구를 남긴다.
FLAG = {
    "Alperen Şengün": ("⚠ 드래프트 당일 야후 F(PF) 자격 확인 — c3 선발이 여기 걸린다",
                       "야후 자격 확인됨: PF·C"),
    "Desmond Bane":   ("⚠ 드래프트 당일 야후 F(SF) 자격 확인 — c2 선발이 여기 걸린다",
                       "야후 자격 확인됨: SG·SF"),
    "Amen Thompson":  ("⚠ 드래프트 당일 야후 F(SF) 자격 확인 — c3 선발이 여기 걸린다",
                       "🔴 자격 기록 충돌 — 한쪽은 PG·SG, 다른 쪽은 PG·SF·SG. "
                       "좁은 쪽(PG·SG)으로 계획했으니 **드래프트 당일 화면에서 SF 유무만 확인**할 것"),
    "Onyeka Okongwu": ("⚠ 드래프트 당일 야후 F(PF) 자격 확인 — c2 선발이 여기 걸린다",
                       "🔴 자격 기록 충돌 — 한쪽은 C 전용, 다른 쪽은 C·PF. "
                       "좁은 쪽(C)으로 계획했으니 **드래프트 당일 화면에서 PF 유무만 확인**할 것"),
}

NOTE_BANE_OLD = "Bane 채택 후 c6가 전 코어 1위가됐습니다. 3PT 보강 목적으로 되돌리지 마십시오."
NOTE_BANE_NEW = ("Bane 채택 후 c6 실측이 올라갔습니다. 3PT 보강 목적으로 되돌리지 마십시오.")


def main():
    oneshot.spent(
        __file__,
        did='화면에 남은 철회·낡은 문구 정리 (40차 후반) — 발행본을 실제로 열어 보고 찾은 것',
        breaks='지금은 대상 문자열이 이미 없어 0건이다 — 🔴 **그건 가드가 아니라 우연이다.** 비슷한 문구가 다시 생기면 40차 기준으로 고쳐 버린다',
        instead='화면 문구는 tool/auction-console.html 을 직접 고치고 tests/rehearse.mjs 로 확인해라')

    pll = json.load(io.open(PP, encoding="utf-8"))
    n = 0
    for p in pll:
        f = FLAG.get(p["name"])
        if f and f[0] in (p.get("flag") or ""):
            p["flag"] = p["flag"].replace(f[0], f[1]); n += 1
            print("  flag %s" % p["name"])
        if p["name"] == "Desmond Bane" and NOTE_BANE_OLD in (p.get("verdict") or ""):
            p["verdict"] = p["verdict"].replace(NOTE_BANE_OLD, NOTE_BANE_NEW); n += 1
            print("  verdict Desmond Bane — 철회된 순위 주장 제거")
    json.dump(pll, io.open(PP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cj = json.load(io.open(CP, encoding="utf-8"))
    c2 = next(c for c in cj["cores"] if c["id"] == "c2")
    old = ("**공식 시뮬 재실행(6000시행 · seed 20261020) 결과 88.9% / 최저 74.1% 로 "
           "전 코어 1위다** — c6 87.5% / 71.6%. 다만 조건부이므로 기본값은 여전히 c6다.")
    if old in c2["premise"]:
        c2["premise"] = c2["premise"].replace(old,
            "**포지션 자격을 반영해 다시 재니 상위 다섯과 동급이다**(86.5% · 상위 5개가 "
            "1.3%p 안이고 이 시뮬의 오차는 ±0.6%p). 이전에 여기 적혀 있던 「전 코어 1위」는 "
            "자격 제약을 모르는 모델이 만든 값이었다 — C 전용 5명을 매일 다 쓸 수 있다고 "
            "계산했다. 조건부이므로 기본값은 여전히 c6다."); n += 1
        print("  premise c2 — 철회된 순위 주장 제거")
    c6 = next(c for c in cj["cores"] if c["id"] == "c6")
    if "**87.5%(전 코어 1위)**" in c6["premise"]:
        c6["premise"] = c6["premise"].replace("**87.5%(전 코어 1위)**", "**87.6%**"); n += 1
        print("  premise c6 — 순위 표기 제거")
    c5 = next(c for c in cj["cores"] if c["id"] == "c5")
    r = c5["pivot_plan"]["rationale"]
    if "c2는 붕괴 64.5%인데 전 코어 1위다" in r:
        c5["pivot_plan"]["rationale"] = r.replace(
            "c2는 붕괴 64.5%인데 전 코어 1위다",
            "c2는 붕괴 64.5%인데 승률은 상위 동급이다"); n += 1
        print("  rationale c5 — 순위 표기 제거")
    d = next(x for x in cj["decision_table"] if x["core"] == "c2")
    if "39차까지 여기 적혀 있던" in (d.get("note") or ""):
        d["note"] = d["note"].replace("📌 39차까지 여기 적혀 있던 ", "📌 이전에 여기 적혀 있던 "); n += 1
        print("  dt note c2 — 차수 표기 제거")
    json.dump(cj, io.open(CP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("총 %d건" % n)


if __name__ == "__main__":
    main()
