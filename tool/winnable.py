#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""관측 세계에서 **우리 상한으로 이길 수 있는 칸**을 가른다 (42차 · §14 정정에서 나왔다).

## 🔴 왜 — 감축표가 「싸다」와 「이길 수 있다」를 섞었다
42차 §14 의 감축표는 절감액을 `room_price(out) − room_price(in)` 로 냈다.
**그 계산은 대체 선수를 방 가격에 우리가 산다고 전제한다.** 그런데 `bid_ceiling` 은
우리가 **스스로 그은 선**이고, 여러 대체가 그 선 위에 있다:

    c6 PF  Şengün → LeBron   상한 $16  vs  방 $35   🔴 **못 산다**
    c6 PF  Şengün → Mobley   상한 $30  vs  방 $48   🔴 **못 산다**

즉 §14 의 감축 ①(Şengün→LeBron $32 절감)은 **실행 불가능**했다.
`cores.json` 의 `no_reachable_fallback_40b` 가 **이미 그렇게 적어 뒀는데**
(*"아래 둘 다 작년 환산가가 우리 상한을 넘는다"*) 감축표를 만들 때 그 필드를 안 봤다.

## 두 가지를 가른다 — 섞으면 안 된다
```
예산 문제   이길 수는 있는데 아홉을 다 못 산다      → 감축으로 푼다
상한 문제   그 값에는 안 사겠다고 우리가 선언했다    → **감축으로 안 풀린다**
```
「전멸」은 두 번째다. 그 칸은 **감축 대상이 아니라 「잃는 칸」**이다.

## ⚠️ 그리고 §6j 배율의 해석도 좁혀진다
「방 총액 $276」은 **우리가 낼 돈이 아니다.** 우리 상한이 그 값을 막는다 —
못 사고 그 칸을 잃을 뿐이다. 그러니 그 숫자는 **예산 전망이 아니라 조달 난이도**다.

실행:  python3 tool/winnable.py
"""
import io, json, os, sys, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}


def scan():
    out = {}
    for co in CJ["cores"]:
        slots = []
        for s in co["slots"]:
            cands = []
            for i, cd in enumerate(s["candidates"]):
                rp = PL[cd["name"]].get("room_price")
                ceil = cd.get("bid_ceiling")
                cands.append({"name": cd["name"], "rank": i + 1, "ceiling": ceil,
                              "room": rp,
                              "winnable": None if rp is None else (ceil >= rp)})
            # 🔴 세 갈래다. **「관측 없음」을 「못 이긴다」로 세면 안 된다** —
            #    작년 미지명은 정보가 없는 것이지 진 것이 아니다.
            w0 = cands[0]["winnable"]
            fallback = next((c for c in cands[1:] if c["winnable"] is not False), None)
            slots.append({"slot": s["slot"], "candidates": cands,
                          "first_status": ("win" if w0 is True else
                                           "lose" if w0 is False else "unknown"),
                          "fallback": fallback["name"] if fallback else None,
                          "fallback_unknown": bool(fallback and fallback["winnable"] is None),
                          "wipeout": (w0 is False) and fallback is None})
        out[co["id"]] = {
            "slots": slots,
            "first_win": sum(1 for x in slots if x["first_status"] == "win"),
            "first_lose": sum(1 for x in slots if x["first_status"] == "lose"),
            "first_unknown": sum(1 for x in slots if x["first_status"] == "unknown"),
            "wipeout_slots": [x["slot"] for x in slots if x["wipeout"]],
            "unknown_slots": [x["slot"] for x in slots if x["fallback_unknown"]],
        }
    return out


def main():
    R = scan()
    print("관측 세계 조달 판정 — `bid_ceiling ≥ room_price` 인가")
    print("⚠️ 예산 문제가 아니다. **상한은 우리가 스스로 그은 선**이고 감축으로 안 풀린다.")
    print("⚠️ 작년 미지명 선수는 판정 불가(관측 없음) — 「모른다」로 센다.\n")
    print("%-5s %8s %8s %10s %12s" % ("코어", "1순위✓", "1순위✗", "관측없음", "🔴 전멸 칸"))
    print("-" * 52)
    for cid, d in sorted(R.items(), key=lambda kv: (-kv[1]["first_win"], kv[1]["first_lose"])):
        print("%-5s %7d/9 %7d/9 %9d/9 %12s" % (
            cid, d["first_win"], d["first_lose"], d["first_unknown"],
            ",".join(d["wipeout_slots"]) or "—"))
    print()
    for cid, d in R.items():
        bad = [x for x in d["slots"] if x["first_status"] == "lose"]
        if not bad:
            continue
        print("══ %s" % cid)
        for x in bad:
            c0 = x["candidates"][0]
            if x["wipeout"]:
                tag = "🔴 **전멸 — 감축 대상이 아니라 「잃는 칸」**"
            elif x["fallback_unknown"]:
                tag = "→ %s (작년 미지명 · **판정 불가**)" % x["fallback"]
            else:
                tag = "→ %s (이길 수 있다)" % x["fallback"]
            print("   %-5s %-22s 상한 $%-3s 방 %-7s %s" % (
                x["slot"], c0["name"], c0["ceiling"],
                ("$%d" % c0["room"]) if c0["room"] is not None else "미지명", tag))
    json.dump({"generated_by": "tool/winnable.py",
               "test": "bid_ceiling >= room_price (작년 실낙찰 × 1.117)",
               "why": ("감축표가 「싸다」와 「이길 수 있다」를 섞었다. bid_ceiling 은 우리가 "
                       "스스로 그은 선이고 여러 대체가 그 위에 있다 — 그 칸은 감축으로 "
                       "풀리지 않는다."),
               "caveat": ("작년 관측은 **한 해 표본**이다. 「올해도 그 값」이 아니라 "
                          "「작년처럼 가면 이 칸을 잃는다」로 읽을 것. "
                          "작년 미지명 선수는 판정 불가다."),
               "cores": R},
              io.open(f"{BASE}/data/winnable.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/winnable.json 기록")
    return 0


if __name__ == "__main__":
    sys.exit(main())
