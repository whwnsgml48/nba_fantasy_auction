#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""피벗 로스터의 **조달 델타** — 「살 수 있는 최선 vs 못 사는 최선」의 주간 승률 차.

왜 피벗이 다른가
  P3 는 `candidates` 180건만 봤다. 피벗은 **9명 전체가 한꺼번에 바뀌는 탈출구**다.
  한 칸 교체와 계산이 다르다:
    · 라인업 사용률(`usable_rates`)이 **로스터 전체 함수**다 — 한 칸이 아니라 전부 다시 잰다
    · 포지션 매칭이 통째로 바뀐다 — 피벗이 5칸을 못 채울 수 있다
    · 총액·예비비가 base 와 다르다(c3 $175 ~ c4 $193)
  🔴 **피벗은 1순위가 과열됐을 때 가는 탈출구다. 못 사는 선수로 짜여 있으면 탈출구가
     가짜고, 그건 대체 한 칸이 막히는 것과 급이 다르다.**

🔴 순서 정규화 — 이 파일이 고치는 하네스 결함
  `matchup_sim.team_week_prepped` 는 선수 리스트를 **순서대로** 돌며 난수를 뽑는다.
  그래서 **같은 로스터·같은 시드라도 이름 순서가 다르면 값이 달라진다.** 실측:
      원래 87.632 · 정렬 87.692 · 역순 87.677 · 셔플 87.571  → 폭 **0.121%p**
  대응 SE(0.59%p)의 **20%** 다. 조달 델타는 이 SE 안에서 판정하므로 그냥 두면
  「어떻게 만들었는지」가 결과에 섞인다. **여기서는 항상 이름 정렬 후 잰다** —
  measure() 가 집합의 순수 함수가 된다.

판정 규칙 (승격 때와 같다 · 조율 지시)
  차가 SE(0.59%p) 안이면 **승격 권고** · 크면 **「대체 없음」으로 남긴다**
  🔴 조달 위험을 승률로 바꿔치기하지 않는다 — 살 수 없으면 승률이 높아도 못 쓴다.

사용법
  python3 tool/pivot_delta.py baseline [iters]   7개 피벗 로스터 실측 (지금까지 미측정)
  python3 tool/pivot_delta.py pair A.json [iters] {"label":..,"a":[9명],"b":[9명]} 목록
"""
import json, io, os, sys, random, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS, pos_elig as PE, real_opponents as RO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
PL = MS.PL
REAL, _ = RO.build()
PAIRED_SE = 0.0059          # matchup_sim.json.standard_error.paired_se_median


def canon(names):
    """🔴 순서 정규화. 위 머리말 참조 — 안 하면 「어떻게 만들었는지」가 값에 섞인다."""
    return sorted(names)


def measure(names, iters=12000, seed=20261020):
    names = canon(names)
    per, acc, ec, sd = {}, {}, [], []
    for mgr, opp in REAL.items():
        o = MS.simulate(list(names), opp, random.Random(seed), iters, None)
        per[mgr] = o["weekly_win_rate"]
        for k, v in o["cat_win_probs"].items(): acc.setdefault(k, []).append(v)
        ec.append(o["expected_cats_won"]); sd.append(o["cats_won_sd"])
    return {"names": names, "per": per, "weekly": sum(per.values()) / len(per),
            "cats": {k: sum(v) / len(v) for k, v in acc.items()},
            "exp_cats": sum(ec) / len(ec), "sd": sum(sd) / len(sd)}


def delta(a, b):
    """대응 차 · 대응 SE · σ. 같은 12팀에 붙였으므로 상대 강약이 상쇄된다."""
    d = [a["per"][m] - b["per"][m] for m in a["per"]]
    md = statistics.mean(d)
    se = statistics.stdev(d) / (len(d) ** 0.5) if len(d) > 1 else 0.0
    return md, se, (abs(md) / se if se else float("inf"))


def procure(name):
    """조달 판정 3층. 어느 층을 쓸지는 사람이 정한다 — 여기서는 전부 보고한다."""
    p = PL.get(name)
    if not p: return {"known": False}
    mx = p.get("my_max"); lo, hi = p.get("market_low"), p.get("market_high")
    mid = (lo + hi) / 2 if lo is not None else None
    return {"known": True, "my_max": mx, "lo": lo, "hi": hi, "mid": mid,
            "obtainable": p.get("obtainable"),
            "over_hi":  (mx is not None and hi is not None and hi > mx),   # 상단에서 놓친다
            "over_mid": (mx is not None and mid is not None and mid > mx), # 정가에서도 못 산다
            "over_lo":  (mx is not None and lo is not None and lo > mx)}   # 하단에서도 못 산다


def pivots():
    out = {}
    for co in CJ["cores"]:
        pv = co.get("pivot_plan") or {}
        fr = pv.get("final_roster") or []
        if len(fr) == 9:
            out[co["id"]] = {"names": [x["name"] for x in fr],
                             "total": pv.get("final_total"),
                             "prices": {x["name"]: x.get("plan_price") for x in fr}}
    return out


def bases():
    return {co["id"]: [s["candidates"][0]["name"] for s in co["slots"]]
            for co in CJ["cores"]}


def report_roster(tag, names, total=None):
    pr = [(n, procure(n)) for n in names]
    bad_lo = [n for n, p in pr if p.get("over_lo")]
    bad_mid = [n for n, p in pr if p.get("over_mid")]
    bad_hi = [n for n, p in pr if p.get("over_hi")]
    ok = PE.match([PL[n] for n in names if n in PL])
    print("  %-4s 총액 %s · 슬롯매칭 %s · 조달: 하단초과 %d · 정가초과 %d · 상단초과 %d"
          % (tag, ("$%s" % total) if total else "?", "성립" if ok else "🔴 불성립",
             len(bad_lo), len(bad_mid), len(bad_hi)))
    if bad_mid: print("        🔴 정가에서도 못 사는 선수: " + ", ".join(bad_mid))
    elif bad_hi: print("        ⚠️ 상단에서 놓칠 수 있는 선수: " + ", ".join(bad_hi))
    return bad_lo, bad_mid, bad_hi


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    # 🔴 argv[2] 의 뜻이 모드마다 다르다 — baseline 은 iters, pair 는 파일 경로다.
    #    여기서 무조건 int() 하면 pair 가 파일명에서 죽는다(실제로 죽었다).
    if mode == "baseline":
        it = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
        PV, BS = pivots(), bases()
        print("피벗 %d개 · %d시행 × 실제 12팀 · 이름 정렬 정규화 적용" % (len(PV), it))
        print("🔴 피벗 로스터는 지금까지 **한 번도 시뮬에 안 걸렸다**"
              " (matchup_sim.json.cores[].* 에 pivot 키가 없다)\n")
        print("조달 스크리닝 — base vs 피벗")
        for cid in sorted(PV):
            report_roster(cid + " base", BS[cid])
            report_roster(cid + " piv ", PV[cid]["names"], PV[cid]["total"])
        print("\n승률 — base vs 피벗 (대응)")
        print("%-5s %9s %9s %9s %8s %7s" % ("코어", "base", "피벗", "차", "대응SE", "σ"))
        for cid in sorted(PV):
            a = measure(BS[cid], it); b = measure(PV[cid]["names"], it)
            md, se, sg = delta(b, a)
            mark = "" if abs(md) <= PAIRED_SE else ("  🔴 SE 초과" if md < 0 else "  △ SE 초과(+)")
            print("%-5s %8.2f%% %8.2f%% %+8.2f%%p %7.2f%%p %6.2f%s"
                  % (cid, 100*a["weekly"], 100*b["weekly"], 100*md, 100*se, sg, mark))
    else:
        # 🔴 a/b 의 뜻 — `gen_delta_pairs.py` 정의를 그대로 따른다. 뒤집으면 결론이 뒤집힌다.
        #    a = **원안** (못 사는 이름을 그대로 둔 로스터)
        #    b = 그 자리를 **살 수 있는** 이름으로 바꾼 로스터
        #    보고 부호는 **대체 − 원안** 이다. 음수 = 살 수 있는 것으로 바꾸면 그만큼 잃는다.
        #    (1차 구현이 이 둘을 반대로 찍었다. 숫자는 같았고 **말이 반대**였다.)
        rows = json.load(io.open(sys.argv[2], encoding="utf-8"))
        it = int(sys.argv[3]) if len(sys.argv) > 3 else 12000
        print("원안 = 못 사는 이름 유지 · 대체 = 살 수 있는 이름 · 부호는 **대체 − 원안**")
        for r in rows:
            a = measure(r["a"], it); b = measure(r["b"], it)
            md, se, sg = delta(b, a)                      # 대체 − 원안
            print("%-46s 원안 %.2f%% → 대체 %.2f%% · %+.2f%%p (SE %.2f · %.2fσ) → %s"
                  % (r.get("label", "?"), 100*a["weekly"], 100*b["weekly"], 100*md,
                     100*se, sg,
                     "승격 권고" if abs(md) <= PAIRED_SE else "**대체 없음으로 남긴다**"))
