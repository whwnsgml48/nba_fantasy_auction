#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`cores.json` 에서 **선수 이름을 담는 필드를 전수로 걷고 분류한다** (2026-09-01 신설).

🔴 왜 — 같은 형태를 세 번 밟았다
```
1회성 스크립트   4개인 줄 알았는데 **7개 전부**였다
PF 대체          칸 문제인 줄 알았는데 **선정 절차**였다
대체후보 조달    candidates 를 봤는데 **on_fail.target 이 남아 있었다**
```
매번 **밟은 자리만 고쳤고 매번 옆에 더 있었다.** 그래서 자리를 세지 않고 **전부 걷는다.**

🔴 그리고 **분류를 강제한다.** 모든 필드는 아래 넷 중 하나여야 하고, 새 필드가 생기면
   `UNCLASSIFIED` 로 떨어져 **검사가 실패한다.** 「이건 서술이니까」로 조용히 빠지는
   경로를 없앤다 — 그게 `on_fail.target` 이 3주를 숨어 있던 방식이다.

```
BUY     우리가 **그 가격에 사야 하는** 자리 → 🔴 조달 검사 대상
COND    **남의 가격**을 보는 조건 (트리거·과열 임계) → 대상 아님. 우리가 안 산다
RECORD  기록·분석 산출 (과거 구성 · 최악 이름 · 자격 목록) → 대상 아님
DEAD    폐기된 가지 (`c7_old`) → 대상 아님. 실행 경로에 없다
```
이 스크립트는 아무것도 쓰지 않는다.
"""
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 1.11

# 🔴 필드 → 분류. **여기 없는 필드는 UNCLASSIFIED 로 떨어지고 검사가 실패한다.**
#    분류를 바꾸려면 왜 바꾸는지 적을 것 — 「대상 아님」이 가장 위험한 선언이다.
CLASS = {
    # ── BUY : 우리가 그 가격에 사야 하는 자리
    "cores[].slots[].candidates[].name": ("BUY", "코어 1순위·대체 — 이미 검사받는다"),
    "cores[].pivot_plan.final_roster[].name": ("BUY", "피벗 로스터 — 피벗하면 이걸 산다"),
    "cores[].pivot_plan.final_roster[].alternates[].name": ("BUY", "피벗 로스터의 대체"),
    "cores[].pivot_plan.final_roster[].alternates[].redeploy.moves[].player":
        ("BUY", "피벗 대체 치환 시 재배치로 사는 선수"),
    "cores[].pivot_plan.swaps[].in.name": ("BUY", "스왑으로 **들여오는** 선수 — 산다"),
    "cores[].slots[].anchor_plan.on_fail.target":
        ("BUY", "🔴 앵커를 놓쳤을 때 **드래프트 당일 실행하는** 치환 대상"),
    "cores[].slots[].anchor_plan.substitutes_dual_ok[]":
        ("BUY", "🔴 「이중세계에서 유효한 대체」로 선언된 이름 — 못 사면 선언이 거짓이다"),
    "cores[].slots[].candidates[].redeploy.moves[].player":
        ("BUY", "치환 시 남는 돈으로 **사는** 선수"),

    # ── COND : 남의 가격을 보는 조건. 우리가 사지 않는다
    "decision_table[].cond.rules[].player": ("COND", "판단표 트리거 — 남이 얼마에 사갔나"),
    "decision_table[].cond.players[]": ("COND", "판단표 조건이 보는 이름"),
    "decision_table[].threshold_history[].player": ("COND", "트리거 임계 변경 이력"),
    "overheat_thresholds[].player": ("COND", "과열 판정 임계 — 남의 가격을 본다"),
    "cores[].pivot_plan.triggers[].player": ("COND", "피벗 발동 트리거 — 남의 가격"),
    "kat_price_branch.player": ("COND", "KAT 가격 분기 트리거"),

    # ── RECORD : 기록·분석 산출
    "cores[].pivot_plan.swaps[].out.name": ("RECORD", "스왑으로 **내보내는** 선수 — 안 산다"),
    "cores[].lineup_loss.base.worst": ("RECORD", "분석 산출 — 최악 이름"),
    "cores[].lineup_loss.pivot.worst": ("RECORD", "분석 산출 — 최악 이름"),
    "cores[].base_redesign_39.old_base[]": ("RECORD", "39차 이전 구성 기록"),
    "cores[].pivot_plan.redesign_39.was[]": ("RECORD", "39차 이전 구성 기록"),
    "cores[].pivot_plan.redesign_39.now[]": ("RECORD", "39차 재설계 결과 기록 — 실 구성은 final_roster"),
    "kat_single_point.best_without_KAT.roster[]": ("RECORD", "KAT 단일점 분석 산출"),
    "pos_eligibility_40.sf_inference.unconfirmed_sf_candidates[]": ("RECORD", "자격 미확인 목록"),
    "pos_eligibility_40.conflict_open.players[]": ("RECORD", "자격 충돌 미해소 목록"),
}
# c7_old.* 는 전부 DEAD — 폐기된 가지다
DEAD_PREFIX = "c7_old."


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    names = set(pl)
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))

    exact, inside = {}, {}

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + "." + k)
        elif isinstance(node, list):
            for v in node:
                walk(v, path + "[]")
        elif isinstance(node, str):
            if node in names:
                exact.setdefault(path, []).append(node)
            elif any(n in node for n in names):
                inside.setdefault(path, []).extend([n for n in names if n in node])

    for k, v in cj.items():
        walk(v, k)

    def cls(p):
        if p.startswith(DEAD_PREFIX):
            return ("DEAD", "폐기된 c7_old 가지 — 실행 경로에 없다")
        return CLASS.get(p, ("UNCLASSIFIED", "🔴 **분류 안 됨 — 새로 생긴 필드다**"))

    groups = {}
    for p in exact:
        groups.setdefault(cls(p)[0], []).append(p)

    print("cores.json — 선수 이름을 담는 필드 **전수 열거 + 분류**\n")
    print("  값 전체가 선수 이름인 필드 %d개 · 엔트리 %d건"
          % (len(exact), sum(len(v) for v in exact.values())))
    print("  문자열 **안에** 박힌 서술 필드 %d개 · %d건 (조달 대상 아님 · 아래 ④)\n"
          % (len(inside), sum(len(v) for v in inside.values())))

    order = ["UNCLASSIFIED", "BUY", "COND", "RECORD", "DEAD"]
    label = {"BUY": "① BUY — 우리가 그 가격에 **사야 하는** 자리  🔴 조달 검사 대상",
             "COND": "② COND — **남의 가격**을 보는 조건. 우리가 안 산다",
             "RECORD": "③ RECORD — 기록·분석 산출",
             "DEAD": "④ DEAD — 폐기된 가지(c7_old)",
             "UNCLASSIFIED": "🔴 UNCLASSIFIED — **분류되지 않은 필드**"}
    for g in order:
        ps = sorted(groups.get(g, []), key=lambda x: -len(exact[x]))
        if not ps:
            continue
        print(label[g] + "   (%d필드 · %d건)" % (ps and len(ps), sum(len(exact[p]) for p in ps)))
        for p in ps:
            print("     %-62s %4d  %s" % (p[:62], len(exact[p]), cls(p)[1][:40]))
        print("")

    if groups.get("UNCLASSIFIED"):
        print("🔴 분류 안 된 필드가 있다 — `CLASS` 에 추가하고 **왜 그 분류인지** 적을 것.\n")

    # ── BUY 필드 조달 검사
    print("=" * 80)
    print("BUY 필드 조달 검사 — edge = my_max − 작년환산가 (×%.2f)\n" % SCALE)
    bad, unk, ok = [], 0, 0
    for p in sorted(groups.get("BUY", [])):
        rows = []
        for n in sorted(set(exact[p])):
            q = pl[n]
            py = q.get("prior_auction_price")
            if py is None:
                unk += 1
                rows.append((n, None, None))
                continue
            a = round(py * SCALE)
            e = q["my_max"] - a
            rows.append((n, a, e))
            if e < 0:
                bad.append((p, n, a, q["my_max"], e))
            else:
                ok += 1
        neg = [r for r in rows if r[2] is not None and r[2] < 0]
        star = "🔴 못 사는 이름 %d" % len(neg) if neg else "🟢 전원 조달 가능"
        print("  %-62s %s" % (p[:62], star))
        for n, a, e in rows:
            if e is not None and e < 0:
                print("       🔴 %-24s 환산 $%-4d 상한 $%-4d  **%+d**" % (n[:24], a, pl[n]["my_max"], e))
    print("\n" + "=" * 80)
    print("🔴 **BUY 필드에서 조달 불가: %d건** (조달 가능 %d · 작년 미지명 %d)" % (len(bad), ok, unk))
    seen = {}
    for p, n, a, mx, e in bad:
        seen.setdefault(n, []).append(p.split(".")[-1])
    print("\n  선수별 (한 명이 여러 자리를 막는다)")
    for n, ps in sorted(seen.items(), key=lambda kv: -len(kv[1])):
        q = pl[n]
        print("    %-24s %2d자리  환산 $%-4d 상한 $%-4d  %s"
              % (n[:24], len(ps), round(q["prior_auction_price"] * SCALE), q["my_max"],
                 " · ".join(sorted(set(ps)))[:44]))
    print("\n⚠️ 목록만 낸다. **고치지 않는다** — 칸마다 승인 사항이다.")
    print("⚠️ COND·RECORD·DEAD 를 뺀 것은 판단이다. 위 분류표를 보고 이견이 있으면 말할 것.")
    return 1 if groups.get("UNCLASSIFIED") else 0


if __name__ == "__main__":
    sys.exit(main())
