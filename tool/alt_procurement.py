#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3 — **대체후보 조달 스크리닝** (2026-09-01 · 조율 승인 · 측정만).

무엇을 재나
  각 코어의 **대체 칸**(candidates[1:])이 「작년 가격 기준으로 실행 가능한가」.
  기준은 `edge_vs_prior = my_max − 작년환산가` 다 (환산 ×1.11 — 예산 +11%).
  음수면 **우리 최대가가 작년 낙찰가에 못 미친다** = 그 값에 못 살 가능성이 크다.

🔴 무엇을 재지 **않나** — 경계는 조율 세션이 박았다
  · 1순위 · 계획가 · 상한 · 판단표는 **손대지 않는다.** 이 스크립트는 아무것도 쓰지 않는다
  · 「이 대체후보는 틀렸다」가 아니다 — **표본이 작년 한 해뿐**이다

⚠️ 그래서 산출의 강도는 이것이다:
     ❌ 「이 대체후보는 실행 불가능하다」
     ✅ **「이 대체후보는 작년 가격 기준으로 실행이 의심스럽다」**

⚠️ 그리고 `market_low/high` 는 시장 관측이 아니다(`docs/05 §6d`) — 작년 곡선에 **우리
   순위**를 얹은 값이다. 그래서 여기서는 시장 중간값이 아니라 **작년 실낙찰가**로만 잰다.
   실낙찰가가 없는 선수는 **판정하지 않는다**(모른다 ≠ 살 수 있다).
"""
import csv
import io
import json
import os
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 1.11  # 작년 12팀/$200 → 올해 14팀/$200 : 방 전체 예산 +11%


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
    prior = {}
    with io.open(BASE + "/data/prior_auction_2025_26/results.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            prior[norm(r["name_en"])] = int(r["price"])

    def adj(n):
        p = prior.get(norm(n))
        return None if p is None else p * SCALE

    def edge(n):
        a = adj(n)
        return None if a is None else pl[n]["my_max"] - a

    print("P3 — 대체후보 조달 스크리닝 (작년 실낙찰가 × %.2f 기준 · 측정만)\n" % SCALE)
    print("  edge = my_max − 작년환산가.  음수 = 우리 최대가가 작년 낙찰가에 못 미친다\n")

    suspect, total_alt, unknown = [], 0, 0
    dead_slots = []
    for co in cj["cores"]:
        rows = []
        for s in co["slots"]:
            alts = s["candidates"][1:]
            if not alts:
                continue
            marks, neg, known = [], 0, 0
            for cd in alts:
                n = cd["name"]
                total_alt += 1
                e = edge(n)
                if e is None:
                    unknown += 1
                    marks.append("%s ⬜" % n.split()[-1])
                    continue
                known += 1
                if e < 0:
                    neg += 1
                    suspect.append((co["id"], s["slot"], n, pl[n]["my_max"], adj(n), e,
                                    cd.get("plan_price")))
                    marks.append("%s **%+d**" % (n.split()[-1], round(e)))
                else:
                    marks.append("%s %+d" % (n.split()[-1], round(e)))
            flag = ""
            if known and neg == known:
                # 🔴 「판정 가능한 것이 전부 음수」와 「전부가 음수」는 다르다.
                #   미판정(작년 실낙찰가 없음)이 남아 있으면 그 칸은 아직 죽지 않았다 —
                #   모른다 ≠ 못 산다. 섞어 세면 피해를 부풀린다.
                if known == len(alts):
                    flag = "  🔴 대체 **전원** 음수 (미판정 0)"
                    dead_slots.append((co["id"], s["slot"], known, 0))
                else:
                    flag = "  ⚠️ 판정 가능한 %d명 전부 음수 (미판정 %d명 남음)" % (known, len(alts) - known)
                    dead_slots.append((co["id"], s["slot"], known, len(alts) - known))
            rows.append("    %-5s %s%s" % (s["slot"], " · ".join(marks), flag))
        if rows:
            print("  %s" % co["id"])
            print("\n".join(rows))
            print("")

    print("=" * 72)
    print("대체 칸 엔트리 %d개 · 작년 실낙찰가 있음 %d · **없음 %d(판정 안 함)**"
          % (total_alt, total_alt - unknown, unknown))
    print("🔴 조달 의심(edge 음수): **%d건**" % len(suspect))
    hard = [d for d in dead_slots if d[3] == 0]
    soft = [d for d in dead_slots if d[3] > 0]
    print("🔴 대체가 **전원** 음수인 슬롯(미판정 0): **%d칸** — 이 칸은 물러설 곳이 없다" % len(hard))
    for cid, slot, k, u in hard:
        print("     %s %-5s (대체 %d명 전원)" % (cid, slot, k))
    print("⚠️ 판정 가능한 것만 전부 음수인 슬롯: %d칸 — **모른다 ≠ 못 산다**, 아직 죽지 않았다" % len(soft))
    for cid, slot, k, u in soft:
        print("     %s %-5s (음수 %d · 미판정 %d)" % (cid, slot, k, u))

    print("\n  가장 큰 것부터 (my_max 대비 얼마나 모자라나)")
    print("  %-4s %-5s %-24s %6s %8s %7s" % ("코어", "슬롯", "선수", "my_max", "작년환산", "edge"))
    for cid, slot, n, mx, a, e, plan in sorted(suspect, key=lambda r: r[5])[:15]:
        print("  %-4s %-5s %-24s %6d %8.0f %7d" % (cid, slot, n[:24], mx, a, round(e)))

    # 🔴 음수에는 **성격이 다른 두 가지**가 섞여 있다. 처방이 다르다.
    #   ① my_max < 작년환산      → 철수가 자체가 못 미친다. **살 수 없다**
    #   ② plan_price < 작년환산 ≤ my_max → 살 수는 있지만 계획가를 넘는다. **예산이 깨진다**
    #   ①만 세면 ②를 놓치고, 섞어 세면 ①의 심각도가 희석된다.
    tier2 = []
    for co in cj["cores"]:
        for s_ in co["slots"]:
            for cd in s_["candidates"][1:]:
                n = cd["name"]
                a = adj(n)
                if a is None:
                    continue
                pp = cd.get("plan_price")
                if pp is not None and pl[n]["my_max"] >= a > pp:
                    tier2.append((co["id"], s_["slot"], n, pp, a, pl[n]["my_max"]))
    print("\n  ── 음수를 성격으로 가른다 ──")
    print("  ① 철수가 미달 (my_max < 작년환산) — **살 수 없다**            %d건" % len(suspect))
    print("  ② 계획가 초과 (plan < 작년환산 ≤ my_max) — **살 수는 있으나 예산이 깨진다**  %d건" % len(tier2))
    if tier2:
        print("     %-4s %-5s %-22s %5s %8s %6s" % ("코어", "슬롯", "선수", "계획가", "작년환산", "상한"))
        for cid, slot, n, pp, a, mx in sorted(tier2, key=lambda r: r[3] - r[4])[:10]:
            print("     %-4s %-5s %-22s %5d %8.0f %6d  (계획가에서 %+d 필요)"
                  % (cid, slot, n[:22], pp, a, mx, round(a - pp)))

    # 같은 선수가 여러 코어에 걸쳐 있는가 — 한 명을 고치면 여러 칸이 풀린다
    by_name = {}
    for cid, slot, n, mx, a, e, plan in suspect:
        by_name.setdefault(n, []).append(cid)
    multi = sorted(((n, sorted(set(c))) for n, c in by_name.items() if len(set(c)) > 1),
                   key=lambda x: -len(x[1]))
    if multi:
        print("\n  여러 코어에 걸친 의심 대체후보 (한 명이 여러 칸을 막고 있다)")
        for n, cs in multi[:10]:
            print("    %-24s %d개 코어 — %s" % (n[:24], len(cs), ", ".join(cs)))

    # 🔴 미판정을 「위험」으로 읽지 말 것 — 방향이 반대다.
    #   작년 실낙찰가가 없다 = **작년 12팀/120명 옥션에서 지명되지 않았다**.
    #   즉 싸게 남았던 부류다(루키·저가 벤치). 올해는 126명이라 수요가 조금 늘지만
    #   방향은 여전히 「싸다」 쪽이다. 판정에서 뺀 이유는 **모르기 때문**이지
    #   위험해서가 아니다.
    print("\n  미판정 %d건에 대하여" % unknown)
    print("    작년 실낙찰가가 없다 = **작년 옥션(12팀·120명)에서 지명되지 않았다**.")
    print("    루키와 저가 벤치가 대부분이라 방향은 오히려 **「싸다」 쪽**이다.")
    print("    올해는 126명이라 수요가 조금 늘지만 판정에서 뺀 이유는 모르기 때문이지")
    print("    위험해서가 아니다 — 🔴 **미판정을 위험으로 읽지 말 것.**")

    print("\n⚠️ 표본은 **작년 한 해뿐**이다. 이 목록은 「틀렸다」가 아니라")
    print("   **「작년 가격 기준으로 실행이 의심스럽다」**이다. 교체는 조율 승인 사항이고")
    print("   이 스크립트는 **아무것도 쓰지 않는다.**")


if __name__ == "__main__":
    main()
