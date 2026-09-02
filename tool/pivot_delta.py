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


def verdict(md):
    """🔴 **부호를 본다.** 판정 규칙 원문은 「차가 SE 안이면 승격 권고 · 크면 대체 없음」인데
    그건 **대체가 더 나쁠 것을 전제**하고 쓴 문장이다. 실제로 `대체 − 원안 > 0` 인 쌍이
    나왔다(c3 피벗 C: Vučević → Duren **+1.30%p · 4.6σ**). 부호를 안 보면 **살 수 있고
    더 강한 대체**를 「대체 없음」으로 찍는다 — `docs/11 ⑪`(비교 기준에 부호를 안 적은
    실패)이 하루 만에 같은 형태로 재발한 것이다. 여기서 갈라 둔다."""
    if md > PAIRED_SE:  return "🟢 **대체가 더 강하다 — 승격**"
    if abs(md) <= PAIRED_SE: return "승격 권고 (SE 안)"
    return "**대체 없음으로 남긴다**"


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


def band(verbose=True):
    """🔴 조달 「경계」 밴드를 **재서** 정한다. 눈으로 고르지 않는다 (조율 지시 · 40차).

    `excess = 작년환산(실낙찰 ×1.11) − my_max` 의 부호를 믿을 수 있는 최소 폭이 필요하다.
      ① excess 분포의 로버스트σ (1.4826 × MAD)                          $11.86
      ② 작년 관측 **1회**의 잡음 = (작년환산 − 우리 적합 시장중간) 로버스트σ   **$9.64**  ← 채택
      ③ 우리가 스스로 밝힌 가격 정밀도 = market_high−low 반폭 중앙값          $3.00

    🔴 **사전 등록을 뒤집었다. 그 사실을 여기 적는다** (조율 판정 · 40차)
      처음에는 「가장 작은 것을 쓴다」를 결과 보기 전에 고정하고 ③ $3.00 을 채택했다.
      결과를 본 뒤 ② 로 바꿨다. 이유는 **③ 이 재려는 것과 다른 것을 재기 때문**이다:

        밴드가 답해야 할 질문   작년 가격 1회가 **올해 방의 호가**를 얼마나 못 맞히는가
        ③ 이 재는 것            **우리가 우리 추정을 얼마나 좁게 선언했는가**

      게다가 `market_low/high` 는 작년 120건으로 **재적합한** 값이라 비교 대상과 독립이
      아니다(이 순환성은 채택 당시 각주로 이미 달려 있었다).

      뒤집기가 허용된 조건 셋 — 하나라도 없으면 뒤집지 않는다:
        (a) 논거가 **사전에 가용**했다 (순환성 각주가 이미 있었다)
        (b) 뒤집는 쪽이 뒤집는 사람에게 **불리하거나 중립**이다
            — 이 변경으로 조율 세션의 승인 하나(Quickley → O'Neale)가 **철회됐다**
        (c) 뒤집는다는 사실 자체를 **기록한다** ← 이 문단

    ⚠️ **KAT 판정은 밴드와 무관하다.** 초과 +$2 는 세 척도 **전부**에서 경계다.
       밴드를 옮겨 그를 구제한 것이 아니라는 증거가 그것이다.
    """
    rows = [p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))
            if p.get("prior_auction_price") and p.get("my_max") is not None]
    adj = lambda p: round(p["prior_auction_price"] * 1.11)
    mid = lambda p: (p["market_low"] + p["market_high"]) / 2
    def mad(v):
        m = statistics.median(v); return statistics.median([abs(x - m) for x in v])
    S = {"① excess 로버스트σ": 1.4826 * mad([adj(p) - p["my_max"] for p in rows]),
         "② 작년 관측 1회 잡음": 1.4826 * mad([adj(p) - mid(p) for p in rows]),
         "③ 우리 가격 구간 반폭": statistics.median(
             [(p["market_high"] - p["market_low"]) / 2 for p in rows])}
    b = S["② 작년 관측 1회 잡음"]          # 🔴 위 머리말의 뒤집기 근거 참조
    if verbose:
        print("모집단 %d명 · 후보 척도:" % len(rows))
        for k, v in S.items():
            print("   %-22s $%.2f%s" % (k, v, "   ← 채택" if abs(v - b) < 1e-9 else ""))
        print("   → 밴드 = **$%.2f**  (재려는 양 = 작년 관측 1회가 올해 호가를 못 맞히는 폭)" % b)
        print("   ⚠️ 사전 등록은 ③ $%.2f 였고 결과를 본 뒤 뒤집었다 — 조건 셋은 머리말에."
              % S["③ 우리 가격 구간 반폭"])
    return b, rows, adj


def classify(b, rows, adj):
    out = {"못 산다": [], "경계": [], "산다": []}
    for p in rows:
        e = adj(p) - p["my_max"]
        out["못 산다" if e > b else ("경계" if e > 0 else "산다")].append((p["name"], e))
    return out


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
    if mode == "band":
        b, rows, adj = band()
        c = classify(b, rows, adj)
        for k in ("못 산다", "경계", "산다"):
            v = sorted(c[k], key=lambda t: -t[1])
            print("\n%s — %d명" % (k, len(v)))
            if k != "산다":
                print("   " + " · ".join("%s +$%d" % (n, e) for n, e in v))
        sys.exit(0)
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
                     verdict(md)))
