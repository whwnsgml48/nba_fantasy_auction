#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""피벗 로스터를 base + swaps 로 다시 조립한다 (불변식 I24 복구).

왜 필요한가 (37차)
  피벗 플랜의 정의는 **base 로스터 + 트리거 대응 교체(swaps)** 다. 그런데 그 관계를
  아무도 검사하지 않아서, 33·34차에 base를 고칠 때 피벗이 따라오지 않았다.
  결과: 7개 피벗 중 **6개**가 옛 base 멤버를 그대로 들고 있었다.

    c1  McConnell 잔류      (33차에 BN → VJ Edgecombe)
    c2  DeRozan 누락        (34차에 Drummond → DeRozan)
    c3  Mark Williams 잔류  (34차에 → Damian Lillard)
    c4  McConnell 잔류      (34차에 BN → Trae Young)
    c5  McConnell 잔류      (34차에 BN → Dyson Daniels)
    c6  D.White·Edgecombe 누락 (33차 PG · 34차 SF)
    c7  OK — 33차에 통째로 새로 만들었으므로 드리프트가 생길 시간이 없었다

  「예비비 과소 편성」 경고 5건(c6 피벗 $149 · 예비 $51 등)의 직접 원인이다.
  피벗이 옛 base의 싼 선수를 들고 있으니 총액이 낮게 나온 것이다.

무엇을 하는가
  1. base 1순위 9명을 슬롯 순서대로 놓는다
  2. `out` 이 현재 base 에 있는 swap 만 적용한다
  3. `out` 이 base 에 없는 swap 은 **stale** 로 보고 버린다 — 이미 없는 선수를
     빼는 교체는 의미가 없다. 버린 목록을 반드시 출력한다(조용히 버리지 않는다).
  4. 가격은 `expected_cost`(기대 낙찰가)를 쓴다 — 35차 가격 스키마

보존하는 것 — `alternates`
  로스터 항목의 `alternates`(11차에 주입한 **이중세계 유효 대체후보**)는 큐레이션 값이고
  어떤 스크립트도 생성하지 않는다(`recompute_cores`는 그 안의 `total_if_used`만 갱신한다).
  재조립하면서 이걸 떨어뜨리면 `my_max < 재적합 시장하단`인 선수(Haliburton 등)가
  **"대체후보도 조건부선언도 없음"** 위반으로 뜬다 — 실제로 첫 시도에서 4건 냈다.
    · 기존 피벗에 같은 이름이 있으면 그 항목의 `alternates`를 그대로 옮긴다
    · 새로 들어온 선수는 base 슬롯의 2순위 이하를 대체후보로 쓴다 (같은 슬롯의 같은 후보군)

무엇을 하지 않는가
  파생 필드(final_total · cat_marginals · targeted/punted)는 손대지 않는다.
  **`recompute_cores.py`를 반드시 이어서 돌릴 것.**

  예비비가 밴드($12~25)를 벗어나는 것도 고치지 않는다 — 그건 로스터 재설계이고
  34차처럼 탐색·승률 대조가 필요하다. 이 스크립트는 **정합성만** 복구한다.
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CP   = f"{BASE}/data/cores.json"
BUDGET = 200

def cost(entry):
    """35차 스키마 — 예산 계산은 expected_cost 로 한다"""
    return entry.get("expected_cost", entry["plan_price"])

def main(apply=True):
    cj = json.load(io.open(CP, encoding="utf-8"))
    changed = 0
    for co in cj["cores"]:
        pv = co["pivot_plan"]
        base = [(s["slot"], s["candidates"][0], bool(s.get("is_anchor")), s.get("role"))
                for s in co["slots"]]
        base_names = {c["name"] for _, c, _, _ in base}

        live  = {sw["out"]["name"]: sw for sw in pv["swaps"] if sw["out"]["name"] in base_names}
        stale = [sw for sw in pv["swaps"] if sw["out"]["name"] not in base_names]

        prev = {r["name"]: r for r in pv["final_roster"]}
        slot_cands = {s["slot"]: s["candidates"] for s in co["slots"]}

        roster = []
        for slot, cand, anchor, role in base:
            sw = live.get(cand["name"])
            src = sw["in"] if sw else cand
            r = {"slot": slot, "name": src["name"], "plan_price": cost(src)}
            if role:   r["role"] = role
            if anchor: r["is_anchor"] = True
            for k in ("bid_ceiling", "expected_cost", "dual_world_ok", "is_big"):
                if k in src: r[k] = src[k]
            r.setdefault("expected_cost", cost(src))

            # alternates 보존 — 기존 피벗 항목 우선, 없으면 base 슬롯의 2순위 이하
            old = prev.get(src["name"])
            if old and old.get("alternates"):
                r["alternates"] = old["alternates"]
            else:
                alts = [dict(x) for x in slot_cands[slot][1:] if x["name"] != src["name"]]
                if alts:
                    r["alternates"] = alts
            roster.append(r)

        old_names = [r["name"] for r in pv["final_roster"]]
        new_names = [r["name"] for r in roster]
        old_tot = pv["final_total"]
        new_tot = sum(r["plan_price"] for r in roster)

        if old_names == new_names and old_tot == new_tot and not stale:
            print(f"[{co['id']}] OK — 변경 없음 (${old_tot} · 예비 ${BUDGET-old_tot})")
            continue

        changed += 1
        print(f"[{co['id']}] 재조립 ${old_tot} → ${new_tot} · 예비 ${BUDGET-old_tot} → ${BUDGET-new_tot}")
        add = [n for n in new_names if n not in old_names]
        rm  = [n for n in old_names if n not in new_names]
        if add: print(f"        + {', '.join(add)}")
        if rm:  print(f"        − {', '.join(rm)}")
        for sw in stale:
            print(f"        ⚠️ stale swap 버림: {sw['out']['name']} → {sw['in']['name']}"
                  f"  ({sw['out']['name']} 은 현재 base 에 없다)")
        if apply:
            pv["final_roster"] = roster
            pv["swaps"] = [sw for sw in pv["swaps"] if sw["out"]["name"] in base_names]

    if apply and changed:
        io.open(CP, "w", encoding="utf-8").write(
            json.dumps(cj, ensure_ascii=False, indent=1) + "\n")
        print(f"\n{changed}개 피벗 재조립 · cores.json 기록")
        print("→ 반드시 이어서: recompute_cores.py → sync_tool.py → gen_docs06.py → validate.py")
    elif not changed:
        print("\n드리프트 없음 — 변경 없음")

if __name__ == "__main__":
    main(apply="--dry" not in sys.argv)
