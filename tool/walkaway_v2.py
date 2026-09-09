#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""철수가 = **무차별 가격** — 40차에 **채택된** 방법의 구현 (45차 신설).

## 왜 새 파일인가
`tool/walkaway_price.py` 는 **기각된** 방법이다. `rate_of()` 가 후보 여럿을 재고
**환율이 가장 높은 것**을 골랐고(`r > best[0]`), 그것이 `walkaway_40.rejected_attempt`
가 버렸다고 적어 둔 그 방법이다 — 환율이 커지면 분모가 커져 무차별 가격이 **작아지고**,
그래서 `Daniels 철수 $5` 가 나왔다(그를 잃으면 4.5%p 를 잃는 선수다).
🔴 그 파일은 **지우지 않는다.** 기각된 구현이 어떻게 생겼는지가 기록이고
`validate.py [I46]` 이 그 가드가 풀리는지 감시한다. 그래서 여기는 **별 파일**이다.

## 채택된 방법 (`walkaway_40.method` 원문)
```
무차별 가격 = 2순위 취득가 + (그 선수를 잃을 때의 승률 손실) / 환율
환율        = 코어마다 **사전 지정한** 큰 금액차 교체 1건
              (가장 비싼 비앵커 칸 → 그 칸의 가장 싼 적격 대안)
판정        = 손실 > 2×SE 일 때만. 아니면 「판정 불가」
철수선      = min(무차별 가격, 예산 상한) · 어느 쪽이 구속인지 적는다
```

## 🔴 목록이 아니라 **규칙**이 소스다
40차는 `rate_by_core` 에 **목록만** 남기고 규칙을 코드로 남기지 않았다. 그래서 42차에
그 키가 지워졌을 때 채택 방법이 통째로 사라졌다. 여기서는 규칙을 코드로 두고
목록은 그 **출력**으로 만든다.

규칙을 40차 기록에서 재유도했고 **옛 세계(git 668a179)에서 옛 목록을 7/7 재현**한다:
```
from  = 비앵커 칸 중 plan_price 최대인 칸의 1순위
to    = 그 칸에 적격이면서 **market_mid 가 가장 싼** 선수
        (로스터 밖 · obtainable · injury_exclude 아님 · 동률이면 이름 오름차순)
Δ$    = from 의 plan_price − to 의 market_mid
환율  = (교체로 잃는 %p) / Δ$
```
`python3 tool/walkaway_v2.py selftest` 가 그 재현을 매번 다시 확인한다.

## 🔴 독립 대조점 — 없으면 화면에 올리지 않는다
40차가 기각본을 잡은 것은 **독립 대조점이 있었기 때문**이다("없었으면 그대로 화면에
나갔다"). 그 대조점은 `rejected_attempt.why_wrong` 에 적혀 있다:

> "c3 에서 $7 빼니 1.1%p = **0.157%p/$**" — 기각본은 c3 가 1.768%p/$ 로 **11배**였다

**환율의 크기**가 대조점이다. 기각본의 병은 max(잡음)/작은 분모라 환율이 **한 자릿수
배로 부풀고**, 환율은 무차별 가격의 **분모**라 부풀면 철수가가 붕괴한다(Daniels $5).
→ 여기서는 **c3 환율이 0.157%p/$ 의 3배 안**인지 본다. 3배는 튜닝이 아니라
  **자릿수 구분**이다 — 기각본 11배와 채택본 1.18배 사이는 어디를 잘라도 갈린다.
실패하면 `main()` 이 exit 1 하고 아무것도 화면에 못 올린다.

⚠️ **처음 쓴 대조점은 틀렸다. 지우지 않고 적어 둔다.**
「Daniels 가 6코어 전부 예산 구속인가」로 썼다가 c4 에서 실패했다. 원인은 구현이 아니라
**대조점 자체**였다 — 40차 `conclusions` 의 *"6개 코어 전부에서 … 무차별 가격이 $20~44 로
예산 상한을 넘는다"* 라는 **산문이 자기 데이터와 어긋난다.** 같은 기록의 `rows` 를 보면
**c4 는 `binding: "indifference"`** 다(무차별 $20.1 < 상한 $22). 이 구현은 그 예외까지
**6/6 재현**한다. 산문에서 대조점을 만들면 산문의 오류를 물려받는다 — **데이터에서 만든다.**

실행:  python3 tool/walkaway_v2.py [selftest]
"""
import io, json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matchup_sim as MS
import pos_elig as PE
import real_opponents as RO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ITERS, RSV_FLOOR = 20261020, 4000, 4
TARGETS = ["Kon Knueppel", "Desmond Bane", "Josh Hart", "DeMar DeRozan", "Dyson Daniels"]

REAL, _ = RO.build()


def mid(p):
    lo, hi = p.get("market_low"), p.get("market_high")
    return None if lo is None or hi is None else (lo + hi) / 2.0


def wr(names):
    """실제 12팀 평균 주간 승률. 🔴 canon 정렬 — 이름 순서가 값에 새면 안 된다."""
    names = sorted(names)
    MS._URATE.clear()
    v = [MS.simulate(names, REAL[m], random.Random(SEED), ITERS)["weekly_win_rate"]
         for m in sorted(REAL)]
    MS._URATE.clear()
    return sum(v) / len(v)


def pre_specified_swap(co, players):
    """🔴 **규칙**. 목록을 하드코딩하지 않는다 — 로스터가 바뀌면 이 값도 바뀌어야 한다."""
    roster = {s["candidates"][0]["name"] for s in co["slots"]}
    non_anchor = [s for s in co["slots"] if not s.get("is_anchor")]
    if not non_anchor:
        return None
    slot = max(non_anchor, key=lambda s: s["plan_price"])
    cands = sorted(
        (mid(p), p["name"]) for p in players
        if p["name"] not in roster and p.get("obtainable")
        and not p.get("injury_exclude") and PE.can(p, slot["slot"]) and mid(p) is not None)
    if not cands:
        return None
    price, to = cands[0]
    return {"slot": slot["slot"], "from": slot["candidates"][0]["name"], "to": to,
            "from_price": slot["plan_price"], "to_price": price,
            "delta_dollar": slot["plan_price"] - price}


def selftest():
    """옛 세계에서 옛 목록을 재현하는가 — **규칙이 맞다는 증거**."""
    import subprocess
    g = lambda f: json.loads(subprocess.run(["git", "show", "668a179:" + f],
                                            cwd=BASE, capture_output=True, text=True).stdout)
    old_cj, old_pl = g("data/cores.json"), g("data/players.json")
    want = json.load(io.open(f"{BASE}/data/matchup_sim.json",
                             encoding="utf-8"))["walkaway_40"]["rate_by_core"]
    ok = 0
    print("셀프테스트 — 옛 세계(668a179)에서 40차 rate_by_core 재현")
    for co in old_cj["cores"]:
        s, e = pre_specified_swap(co, old_pl), want[co["id"]]
        m = bool(s) and s["from"] == e["from"] and s["to"] == e["to"] \
            and s["delta_dollar"] == e["delta_dollar"]
        ok += m
        print("  %-3s %-18s → %-16s Δ$%-5s %s"
              % (co["id"], s and s["from"], s and s["to"], s and s["delta_dollar"],
                 "✅" if m else "🔴 기록: %s → %s Δ$%s" % (e["from"], e["to"], e["delta_dollar"])))
    print("재현 %d/7" % ok)
    return ok == 7


def promotion_signals(out, thr):
    """🔴 **음수 손실은 「대체가 더 좋다」는 뜻이다.**

    40차는 `significant = loss_pp > 임계` 의 **부호 있는** 비교로 음수 행을 전부
    `below_noise` 로 적고 넘어갔다. 철수가 목적으로는 맞다 — 대체가 더 좋으면
    「얼마까지 낼 것인가」를 물을 이유가 없다. 그런데 그 행들은 **승격 신호**다.
    44차에 c6 BN 을 Bane → Murray 로 뒤집은 것이 정확히 그 신호였고,
    40차 기록에는 `Knueppel c4 −1.50%p` 가 그렇게 버려져 있었다.
    → 여기서는 **버리지 않고 따로 낸다.** 판정은 사람이 한다(조달·자격이 걸린다).
    """
    sig = []
    for who, rs in out["rows"].items():
        for r in rs:
            if r["loss_pp"] < -thr:
                sig.append(r)
    sig.sort(key=lambda r: r["loss_pp"])
    print("\n🔴 승격 신호 — 대체가 1순위보다 **%.2f%%p 넘게** 좋은 칸" % (100 * thr))
    if not sig:
        print("  없음")
    for r in sig:
        print("  %-3s %-5s %-18s → %-18s **+%.2f%%p**  계획 $%s → $%s"
              % (r["core"], r["slot"], r["player"], r["alt"], -100 * r["loss_pp"],
                 r["plan"], r["alt_price"]))
    if sig:
        print("  ⚠️ 승률만 본 것이다 — **조달(관측가·상한)과 자격을 확인하기 전에는 승격하지 말 것.**")
    return sig


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        # 시뮬 없이 저장된 측정만 다시 읽는다
        o = json.load(io.open(f"{BASE}/data/walkaway_v2.json", encoding="utf-8"))
        promotion_signals(o, o["significance_threshold"])
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.stderr.write("🔴 셀프테스트 실패 — 규칙이 40차 목록을 재현하지 못한다. 중단.\n")
        sys.exit(1)
    print()

    CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    players = json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))
    SIM = json.load(io.open(f"{BASE}/data/matchup_sim.json", encoding="utf-8"))
    # 🔴 SE 를 상수로 박지 않는다 — 상대 집합이 바뀌면 이 값이 바뀐다(standard_error.use).
    se = SIM["standard_error"]["paired_se_median"]
    thr = 2 * se
    print("판정 임계 2×SE = %.2f%%p  (paired_se_median %.4f · 매 실행 재읽기)" % (100 * thr, se))

    rate_by_core, rows = {}, {}
    for co in CJ["cores"]:
        names = [s["candidates"][0]["name"] for s in co["slots"]]
        sw = pre_specified_swap(co, players)
        base = wr(names)
        got = wr([sw["to"] if n == sw["from"] else n for n in names])
        loss = base - got
        rate = loss / sw["delta_dollar"] if sw["delta_dollar"] else None
        rate_by_core[co["id"]] = dict(sw, delta_pp=round(loss, 4),
                                      rate=round(rate, 5) if rate else None,
                                      base_wr=round(base, 4))
        print("  %-3s 환율 %-18s → %-16s Δ$%-4s Δ%.2f%%p → **%.5f%%p/$**"
              % (co["id"], sw["from"], sw["to"], sw["delta_dollar"], 100 * loss, rate or 0))

        for s in co["slots"]:
            who = s["candidates"][0]["name"]
            if who not in TARGETS or len(s["candidates"]) < 2:
                continue
            alt = s["candidates"][1]
            drop = base - wr([alt["name"] if n == who else n for n in names])
            cap = s["plan_price"] + (200 - co["planned_total"]) - RSV_FLOOR
            r = {"player": who, "core": co["id"], "slot": s["slot"],
                 "plan": s["plan_price"], "alt": alt["name"],
                 "alt_price": alt["plan_price"], "loss_pp": round(drop, 4),
                 "significant": bool(drop > thr), "rate": rate_by_core[co["id"]]["rate"],
                 "budget_cap": cap}
            if r["significant"] and rate:
                r["indifference"] = round(alt["plan_price"] + drop / rate, 1)
                r["walkaway"] = min(cap, round(r["indifference"]))
                r["binding"] = "예산" if cap <= r["indifference"] else "무차별"
            else:
                r["indifference"] = None
                r["walkaway"] = cap
                r["binding"] = "판정불가 — 손실이 잡음 안(2×SE 미만)"
            rows.setdefault(who, []).append(r)

    print("\n선수별 (손실 > %.2f%%p 일 때만 판정)" % (100 * thr))
    for who in TARGETS:
        rs = rows.get(who, [])
        if not rs:
            print("  %-16s 해당 칸 없음" % who); continue
        sig = [r for r in rs if r["significant"]]
        print("  %-16s %d코어 · 유의 %d건 · 손실 %.2f~%.2f%%p%s"
              % (who, len(rs), len(sig), 100*min(r["loss_pp"] for r in rs),
                 100*max(r["loss_pp"] for r in rs),
                 "" if sig else "  → **판정 불가**"))
        for r in sig:
            print("       %-3s 계획$%-3s 무차별 $%-6s 예산상한 $%-4s → **철수 $%s** (%s 구속)"
                  % (r["core"], r["plan"], r["indifference"], r["budget_cap"],
                     r["walkaway"], r["binding"]))

    # 🔴 독립 대조점 — 40차가 기각본을 잡은 그 지점 (머리말 참조)
    #   기각본 c3 = 1.768%p/$ (대조점의 11배) · 채택본 ≈ 0.19%p/$ (1.2배)
    CONTROL, BAND = 0.00157, 3.0
    c3r = rate_by_core["c3"]["rate"]
    ratio = c3r / CONTROL
    control = bool(c3r) and (1 / BAND) <= ratio <= BAND
    print("\n🔴 독립 대조점 — c3 환율 %.5f%%p/$ = 대조점(0.157%%p/$)의 **%.2f배** → %s"
          % (100 * c3r, ratio, "✅ 통과" if control else "🔴 실패"))
    if not control:
        print("   기각본은 11배였다(max(잡음)/작은 분모). 환율은 무차별 가격의 **분모**라")
        print("   부풀면 철수가가 붕괴한다 — Daniels $5 가 그렇게 나왔다. 화면에 올리지 말 것.")
    # 보조 확인 — 40차 binding 패턴 재현 (c4 만 무차별, 나머지 예산)
    dan = {r["core"]: r for r in rows.get("Dyson Daniels", []) if r["significant"]}
    pat = {c: r["binding"] for c, r in sorted(dan.items())}
    print("   보조 — Daniels binding 패턴: %s"
          % " ".join("%s=%s" % (c, b) for c, b in pat.items()))
    print("          40차 채택본: c4 만 indifference · 나머지 budget "
          "(⚠️ 같은 기록의 conclusions 산문은 「전부 예산」이라고 **잘못** 적었다)")

    out = {"generated_by": "tool/walkaway_v2.py", "seed": SEED, "iterations": ITERS,
           "reserve_floor": RSV_FLOOR, "paired_se": se, "significance_threshold": thr,
           "method": SIM["walkaway_40"]["method"],
           "rule": ("from = 비앵커 칸 중 plan_price 최대인 칸의 1순위 · "
                    "to = 그 칸 적격 중 market_mid 최저(동률 시 이름 오름차순) · "
                    "환율 = 그 교체로 잃는 %p / Δ$. 🔴 목록이 아니라 규칙이 소스다."),
           "selftest": "옛 세계(668a179)에서 40차 rate_by_core 를 7/7 재현한다",
           "control_point": {"what": "c3 환율이 40차 독립 대조점 0.157%p/$ 의 3배 안인가",
                             "why": ("40차가 기각본을 잡은 지점이다 — 기각본 c3 는 1.768%p/$ 로 "
                                     "대조점의 11배였다. 환율은 무차별 가격의 분모라 부풀면 "
                                     "철수가가 붕괴한다(Daniels $5)."),
                             "rejected_control": ("처음엔 「Daniels 가 6코어 전부 예산 구속인가」로 "
                                     "썼다가 c4 에서 실패했다. 40차 conclusions 산문이 "
                                     "자기 rows 와 어긋난 것이고(c4 는 binding=indifference) "
                                     "이 구현은 그 예외까지 6/6 재현한다. 산문이 아니라 "
                                     "데이터에서 대조점을 만들 것."),
                             "passed": control},
           "caveat": SIM["walkaway_40"].get("caveat") or
                     "로컬 선형 근사다. 멀리 외삽하지 말 것 — 예산 상한과 함께 보고한다.",
           "rate_by_core": rate_by_core, "rows": rows}
    out["promotion_signals"] = promotion_signals(out, thr)
    json.dump(out, io.open(f"{BASE}/data/walkaway_v2.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/walkaway_v2.json 기록")
    sys.exit(0 if control else 1)


if __name__ == "__main__":
    main()
