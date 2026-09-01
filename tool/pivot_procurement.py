#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""피벗 계획의 **조달 검사** — 탈출구가 진짜인가 (2026-09-01 · 측정만).

🔴 왜 이게 대체후보보다 급한가
  대체가 가짜면 **한 칸**이 막힌다. 피벗이 가짜면 **계획 전체**가 막힌다.
  피벗은 1순위가 과열돼 못 살 때 가는 곳인데, 그 로스터를 살 수 없으면
  **탈출구가 없는 것**이고 우리는 그 사실을 드래프트 당일에 알게 된다.

무엇을 보나 — 코어별로
  ① `pivot_plan.final_roster[]`  피벗하면 **이걸 산다**
  ② 그 칸의 `alternates[]`       피벗 로스터가 막혔을 때의 대체
  ③ `swaps[].in`                 스왑으로 들여오는 선수
  🔴 ①이 막혔는데 ②도 막혔으면 **그 칸은 피벗에서도 갈 곳이 없다.**

⚠️ 표본은 작년 한 해뿐이다. 산출의 강도는 「틀렸다」가 아니라
   **「작년 가격 기준으로 실행이 의심스럽다」**이다.
⚠️ 그리고 `total` 은 피벗 계획가 합이다 — **작년 가격으로 다시 사면 얼마인지**도 같이 낸다.
   개별 칸이 다 통과해도 **합이 $200 을 넘으면 피벗은 성립하지 않는다.**

이 스크립트는 아무것도 쓰지 않는다.
"""
import io
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 1.11
BUDGET, RESERVE_FLOOR = 200, 4


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))

    def adj(n):
        py = pl[n].get("prior_auction_price")
        return None if py is None else round(py * SCALE)

    def buyable(n):
        a = adj(n)
        return None if a is None else (pl[n]["my_max"] >= a)

    print("피벗 계획 조달 검사 — 탈출구가 진짜인가 (작년 실낙찰가 ×%.2f · 측정만)\n" % SCALE)
    summary = []
    for co in cj["cores"]:
        pp = co.get("pivot_plan")
        if not pp:
            print("  %-4s 피벗 계획 없음\n" % co["id"])
            continue
        fr = pp.get("final_roster") or []
        print("=" * 78)
        print("  %s — 피벗 로스터 %d칸   %s" % (co["id"], len(fr), pp.get("name", "")[:44]))

        dead, plan_sum, prior_sum, unk = [], 0, 0, 0
        for e in fr:
            n = e["name"]
            price = e.get("plan_price") or e.get("price") or 0
            plan_sum += price
            a = adj(n)
            if a is None:
                unk += 1
                prior_sum += price
            else:
                prior_sum += a
            b = buyable(n)
            alts = [x["name"] for x in (e.get("alternates") or [])]
            alt_ok = [x for x in alts if buyable(x) is not False]
            if b is False:
                mark = "🔴 못 산다 (환산 $%d > 상한 $%d)" % (a, pl[n]["my_max"])
                if alts and not alt_ok:
                    mark += "  ⛔ **대체도 전부 못 산다**"
                    dead.append((n, e.get("slot", "?"), a, pl[n]["my_max"], alts))
                elif not alts:
                    mark += "  ⛔ **대체 자체가 없다**"
                    dead.append((n, e.get("slot", "?"), a, pl[n]["my_max"], []))
                else:
                    mark += "  → 대체 가능: %s" % ", ".join(x.split()[-1] for x in alt_ok[:3])
                print("     %-5s %-24s $%-4s %s" % (e.get("slot", "?"), n[:24], price, mark))

        over = prior_sum - (BUDGET - RESERVE_FLOOR)
        print("     ── 계획가 합 $%d · **작년 가격으로 다시 사면 $%d** (미지명 %d명은 계획가로 셈)"
              % (plan_sum, prior_sum, unk))
        if over > 0:
            print("     🔴 **예산 초과 $%d** — 개별 칸이 통과해도 이 피벗은 $%d 안에 안 들어간다"
                  % (over, BUDGET - RESERVE_FLOOR))
        else:
            print("     🟢 예산 안 (여유 $%d)" % (-over))
        if dead:
            print("     ⛔ **갈 곳 없는 칸 %d개**: %s"
                  % (len(dead), " · ".join("%s %s" % (d[1], d[0].split()[-1]) for d in dead)))
        summary.append((co["id"], len(fr), len(dead), prior_sum, over))
        print("")

    print("=" * 78)
    print("  %-5s %6s %10s %14s %10s" % ("코어", "칸", "갈 곳 없음", "작년가 재구매", "초과"))
    for cid, nfr, nd, ps, ov in summary:
        print("  %-5s %6d %10s %14s %10s"
              % (cid, nfr, "🔴 %d" % nd if nd else "🟢 0",
                 "$%d" % ps, "🔴 +$%d" % ov if ov > 0 else "🟢 —"))
    print("\n  🔴 갈 곳 없는 칸이 있는 코어: %d/%d · 예산 초과 피벗: %d/%d"
          % (sum(1 for s in summary if s[2]), len(summary),
             sum(1 for s in summary if s[4] > 0), len(summary)))
    print("\n⚠️ 목록만 낸다. **고치지 않는다** — 칸마다 승인 사항이다.")
    print("⚠️ 표본은 작년 하나다. 「틀렸다」가 아니라 **「실행이 의심스럽다」**로 읽을 것.")


if __name__ == "__main__":
    main()
