#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""작업 6 — **선언 모순 전수 조사** (42차 신설).

## 🔴 왜 — 같은 형태의 버그를 한 라운드에 **두 번** 잡았다
```
① anchor_plan.on_fail  ↔  kat_price_branch     같은 트리거(KAT 가격)에 반대 지시
                                                치환 vs 코어 전환 · 측정하니 9.5%p 차
② 태우기 명단          ↔  c2 UTIL 후보(Turner)  같은 선수에 반대 지시
                                                태워라 vs 사라 · tag_basis 가 null 이라 M5 도 안 걸림
```
**둘 다 「두 선언이 같은 대상/트리거에 반대 지시를 하는데 아무도 대조하지 않는다」다.**
개별 버그가 아니라 **버그의 종류**이고, 이 저장소는 선언이 수십 개다.
**두 개를 우연히 찾았다면 더 있다.**

## 무엇을 하는가
`cores.json` · `players.json` 에서 **「조건 → 행동」 선언을 전부 걷고**, 같은 **선수**에
걸리는 선언 쌍을 뽑아 지시가 상충하는지 본다.

⚠️ 이 스크립트는 **판정하지 않는다.** 상충 후보를 뽑아 사람에게 준다 —
어느 쪽이 옳은지는 **근거의 강도**로 갈라야 하고(측정 > 모형 > 서술) 그건 사람 일이다.
42차의 두 사례도 그렇게 갈랐다(하나는 시뮬 측정으로, 하나는 기록된 근거의 유무로).

## 선언 종류 (여기 없는 새 선언이 생기면 **추가할 것**)
```
BUY        이 선수를 이 가격에 산다            slots[].candidates · pivot final_roster · alternates
BURN       이 선수를 태운다(남이 사가게 한다)   players.json tag=burn
EXCLUDE    이 선수를 어디에도 쓰지 않는다       players.json injury_exclude
WALK       이 가격을 넘으면 철수한다            overheat_thresholds[].threshold
PIVOT_TRIG 이 가격을 넘으면 피벗한다            cores[].pivot_plan.triggers[]
SWITCH     이 조건이면 코어를 바꾼다            decision_table[].cond.rules · kat_price_branch.steps
SUBSTITUTE 이 앵커를 놓치면 코어 안에서 치환한다 slots[].anchor_plan.on_fail(action=substitute)
```

실행:  python3 tool/declaration_conflicts.py
"""
import io, json, os, sys, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))


def collect():
    """(선수, 종류, 상세, 출처) 튜플 전수."""
    D = []

    def add(name, kind, detail, where):
        if name in PL:
            D.append({"player": name, "kind": kind, "detail": detail, "where": where})

    for co in CJ["cores"]:
        cid = co["id"]
        for s in co["slots"]:
            for i, cd in enumerate(s["candidates"]):
                add(cd["name"], "BUY",
                    {"rank": i + 1, "price": cd.get("expected_cost"),
                     "ceiling": cd.get("bid_ceiling")},
                    "%s/%s cand%d" % (cid, s["slot"], i + 1))
            ap = s.get("anchor_plan") or {}
            of = ap.get("on_fail") or {}
            if of:
                add(s["candidates"][0]["name"], "SUBSTITUTE" if of.get("action") == "substitute"
                    else "SWITCH" if of.get("action") == "switch_core" else "PIVOT_TRIG",
                    {"action": of.get("action"), "target": of.get("target")},
                    "%s/%s anchor_plan.on_fail" % (cid, s["slot"]))
        pv = co.get("pivot_plan") or {}
        for t in (pv.get("triggers") or []):
            add(t["player"], "PIVOT_TRIG", {"rule": t.get("rule")},
                "%s pivot_plan.triggers" % cid)
        for blk, lbl in [(pv, "pivot")] + ([(pv.get("fallback"), "fallback")]
                                           if pv.get("fallback") else []):
            for r in (blk.get("final_roster") or []):
                add(r["name"], "BUY", {"rank": 1, "price": r.get("plan_price")},
                    "%s %s roster" % (cid, lbl))
                for a in (r.get("alternates") or []):
                    if a.get("name"):
                        add(a["name"], "BUY", {"rank": 2, "price": a.get("plan_price")},
                            "%s %s alternate" % (cid, lbl))
    for t in CJ.get("overheat_thresholds") or []:
        add(t["player"], "WALK", {"threshold": t.get("threshold"), "tier": t.get("tier")},
            "overheat_thresholds")
    for d in CJ.get("decision_table") or []:
        for r in ((d.get("cond") or {}).get("rules") or []):
            if r.get("player"):
                add(r["player"], "SWITCH", {"max": r.get("max"), "go": d.get("core")},
                    "decision_table[%s]" % d.get("core"))
    kb = CJ.get("kat_price_branch") or {}
    for st in (kb.get("steps") or []):
        add(kb.get("player"), "SWITCH", {"over": st.get("over"), "go": st.get("go")},
            "kat_price_branch")
    for n, p in PL.items():
        if p.get("tag") == "burn":
            add(n, "BURN", {"my_max": p["my_max"], "room": p.get("room_price")},
                "players.json tag")
        if p.get("injury_exclude"):
            add(n, "EXCLUDE", {}, "players.json injury_exclude")
    return D


# ── 상충 규칙. **여기 없는 조합은 검사되지 않는다** — 새 종류가 생기면 추가할 것.
def conflicts(byp):
    out = []
    for name, ds in byp.items():
        kinds = {d["kind"] for d in ds}
        buy = [d for d in ds if d["kind"] == "BUY"]

        # (1) 태운다 ↔ 산다  — 42차 Turner 사례. [I42] 가 상시 검사한다.
        if "BURN" in kinds and buy:
            out.append((name, "BURN↔BUY",
                        "태우기 명단인데 계획 후보다 — 태우면 우리 탈출로를 닫는다",
                        [d["where"] for d in ds if d["kind"] in ("BURN", "BUY")]))

        # (2) 제외한다 ↔ 산다 — I7 이 이미 검사하지만 여기서도 걷는다(누락 방지)
        if "EXCLUDE" in kinds and buy:
            out.append((name, "EXCLUDE↔BUY", "제외 선언인데 계획에 있다",
                        [d["where"] for d in ds if d["kind"] in ("EXCLUDE", "BUY")]))

        # (3) 앵커 치환 ↔ 코어 전환 — 42차 KAT 사례.
        #     같은 선수에 「코어 안에서 치환한다」와 「코어를 바꾼다」가 동시에 있으면
        #     드래프트 당일 화면이 **반대 지시 둘**을 준다.
        sub = [d for d in ds if d["kind"] == "SUBSTITUTE"]
        sw = [d for d in ds if d["kind"] == "SWITCH"]
        if sub and sw:
            out.append((name, "SUBSTITUTE↔SWITCH",
                        "「코어 안에서 치환」과 「코어를 바꾼다」가 같은 선수에 동시에 걸려 있다",
                        [d["where"] for d in sub + sw]))

        # (4) 철수가 ↔ 계획가 — 계획가가 철수가를 넘으면 자기 피벗을 트리거한다(I11d 와 같은 형태)
        walk = [d for d in ds if d["kind"] == "WALK" and d["detail"].get("threshold") is not None]
        if walk and buy:
            w = min(d["detail"]["threshold"] for d in walk)
            over = [d for d in buy if (d["detail"].get("price") or 0) > w]
            if over:
                out.append((name, "WALK↔BUY",
                            "계획가 $%s 가 철수가 $%d 를 넘는다" %
                            (max(d["detail"].get("price") or 0 for d in over), w),
                            [d["where"] for d in over] + [d["where"] for d in walk]))

        # (5) 가격 조건이 **여러 개**인데 임계가 다르다 — 같은 선수에 서로 다른 선을 긋고 있다
        thr = {}
        for d in ds:
            v = d["detail"].get("max") if d["kind"] == "SWITCH" else (
                d["detail"].get("threshold") if d["kind"] == "WALK" else None)
            if v is not None:
                thr.setdefault(v, []).append(d["where"])
        if len(thr) > 1:
            out.append((name, "THRESHOLD∆",
                        "같은 선수에 **다른 가격 임계**가 %d개 있다: %s" %
                        (len(thr), " · ".join("$%s(%s)" % (k, ",".join(v))
                                              for k, v in sorted(thr.items()))),
                        sorted({w for ws in thr.values() for w in ws})))
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴 판정된 상충 — **이유 없이 여기 넣지 말 것**
#
# 42차에 3건을 판정하면서 **한 번도 적힌 적 없던 규칙**이 드러났다:
#
#   🔴 **선언은 「적용 시점」으로 갈린다.**
#        「비싸지만 **잡을 수 있다**」  → 예산 문제 → **코어 전환**(SWITCH)
#        「**못 잡았다**」              → 조달 실패 → **코어 안 치환**(SUBSTITUTE)
#      같은 선수에 둘 다 걸려도 **영역이 다르면 모순이 아니다.**
#      🔴 **영역이 겹치는 순간 모순이 된다.**
#
#   42차의 KAT $57 갈래가 정확히 그랬다 — $57 위에서는 **어떤 코어도 KAT 을 못 산다**
#   (c1 $53 · c7 $57 이 한계). 즉 「못 잡았다」 영역인데 분기가 **코어 전환**을 지시했고,
#   `anchor_plan.on_fail` 은 **치환**을 지시했다. 측정하니 치환 쪽이 **9.5%p** 나았다.
#   그래서 그 갈래만 고쳤고 $50 갈래는 손대지 않았다 — 그쪽은 영역이 안 겹친다.
#
# ⚠️ 이 규칙이 적혀 있지 않아서 42차까지 아무도 두 선언을 대조하지 않았다.
#    새 상충이 뜨면 **먼저 영역을 물어라**: 「잡을 수 있는데 비싼가」 vs 「못 잡았는가」.
# ══════════════════════════════════════════════════════════════════════
RESOLVED = {
    ("Karl-Anthony Towns", "SUBSTITUTE↔SWITCH"): (
        "**영역이 다르다.** `kat_price_branch` $50 갈래는 「비싸지만 잡을 수 있다」다 — "
        "c6 는 예비 $9 라 $50 까지지만 c7 은 예비 $16 이라 **$57 까지 KAT 을 산다.** "
        "그 구간에서 우리는 KAT 을 **잃지 않았으므로** on_fail(치환) 영역이 아니다. "
        "🔴 $57 **위**에서는 어떤 코어도 못 사므로 그때부터 on_fail 영역인데, 42차 이전에는 "
        "분기가 거기서도 코어 전환(c4)을 지시했다 — 그것이 진짜 모순이었고 측정으로 "
        "고쳤다(c6+감축 84.57% vs c4+감축 75.03%). 지금은 두 선언이 영역을 나눠 갖는다."),
    ("Tyrese Haliburton", "SUBSTITUTE↔SWITCH"): (
        "**영역이 다르다.** `decision_table[c1]` 의 `Hali ≤ $56` 은 **진입 게이트**다 — "
        "「c1 을 고를 것인가」를 정한다. `anchor_plan.on_fail`(치환)은 **c1 을 고른 뒤 "
        "그를 놓쳤을 때**다. 시점이 다르므로 반대 지시가 아니다. "
        "⚠️ 다만 `$56` 은 철수가와 같은 값이라, 그가 $57 에 팔리면 게이트도 닫히고 "
        "조달도 실패한다 — 그때는 **양쪽이 같은 방향**(c1 을 안 간다)이라 여전히 무모순이다."),
    ("Karl-Anthony Towns", "THRESHOLD∆"): (
        "**층이 다른 네 숫자다. 의도된 것이고 문서화돼 있다.**\n"
        "  $71  `anchor_plan.bid_ceiling` — my_max 상한. 이 위로는 절대 안 부른다\n"
        "  $55  `overheat_thresholds` 철수가 — 넘으면 산다는 생각 자체를 접는다\n"
        "  $53  `kat_price_branch.ceilings.c1` — c1 예비비를 I22 위반선까지 짠 실제 한계\n"
        "  $50  `decision_table[c1]` 게이트 — $53 보다 **보수적으로** 잡은 진입선. "
        "그 이유가 `threshold_basis` 에 적혀 있다(39차 평가 세션 A안).\n"
        "⚠️ 사람이 10초 안에 볼 숫자는 **분기표 하나**여야 한다. 네 개를 다 보여주면 안 된다."),
}


def unresolved(C):
    """판정 안 된 상충만. 판정하려면 RESOLVED 에 **이유와 함께** 넣는다."""
    return [c for c in C if (c[0], c[1]) not in RESOLVED]


def main():
    D = collect()
    byp = collections.defaultdict(list)
    for d in D:
        byp[d["player"]].append(d)
    C = conflicts(byp)
    kinds = collections.Counter(d["kind"] for d in D)
    print("선언 전수 %d건 · 선수 %d명 · 종류 %s" % (len(D), len(byp), dict(kinds)))
    print("⚠️ 이 스크립트는 **판정하지 않는다.** 상충 후보를 뽑아 사람에게 준다 —")
    print("   어느 쪽이 옳은지는 근거의 강도(측정 > 모형 > 서술)로 갈라야 한다.\n")
    U = unresolved(C)
    print("상충 후보 %d건 · 판정됨 %d건 · **미판정 %d건**\n" % (len(C), len(C) - len(U), len(U)))
    if not C:
        print("상충 후보 0건")
        return 0
    bykind = collections.defaultdict(list)
    for c in C:
        bykind[c[1]].append(c)
    for k in sorted(bykind):
        print("── %s (%d건)" % (k, len(bykind[k])))
        for name, _k, why, where in sorted(bykind[k]):
            mark = "  " if (name, _k) in RESOLVED else "🔴"
            print("   %s %-24s %s" % (mark, name, why))
            print("      %s" % " · ".join(sorted(set(where))[:6]))
            if (name, _k) in RESOLVED:
                print("      ✅ 판정: %s" % RESOLVED[(name, _k)].split("\n")[0][:110])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
