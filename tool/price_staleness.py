#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""관측가 **신선도** — 방이 값을 낸 시점의 정보와 우리가 쓰는 정보가 같은가 (44차).

## 왜 이게 필요한가 — 44차에 두 번 같은 오류를 잡았다

42차가 세운 규칙은 **「관측가가 우리 모델보다 강한 출처다」**(`docs/05 §13`)이고 옳다.
그런데 그 규칙에는 **암묵 전제**가 있다 — *두 출처가 같은 것을 보고 있다*.

작년 옥션(2025-10)은 **2024-25 시즌까지**를 보고 값을 냈다. 우리 스탯 혼합은
**2025-26 을 0.6 안팎으로** 쓴다. 그 사이에 크게 변한 선수는 **두 출처가 다른
정보집합에 서 있고**, 그때 관측가는 「강한 출처」가 아니라 **낡은 출처**다.

```
Jamal Murray  방이 본 것 24-25: 67G 21.4P 3P% 39.3  → $20 지불
              우리가 쓰는 것 25-26: 75G 25.4P 3P% 43.5  → 시뮬 +2.63%p
```
🔴 **승격 논거의 두 반쪽이 서로 다른 시즌에 서 있었다.** 우위(+2.63%p)는 25-26 이
만들고 조달 근거($22)는 24-25 가 만든다. **둘을 동시에 쓸 수 없다** — 방이 우리
시뮬이 보는 것을 봤다면 $20 을 안 냈다.

## 판정 규칙 — **재기 전에 고정했고, 그 규칙은 실패했다** (지우지 않는다)
```
Δz = z(2025-26 한 시즌) − z(2024-25 한 시즌)      같은 13캣 · 같은 표준화 · GP 포함
[기각된 규칙]  |Δz| ≥ 2.0 이면 「낡았다」
```
🔴 **절대 임계는 선별력이 없었다.** 관측 92명 중 **59명(64%)** 이 걸렸고 Jokić·SGA 같은
정상 변동까지 낡은 것으로 찍혔다. |Δz| 중앙값이 **3.27** 이라 임계 2.0 은 중앙값 아래다.
**튜닝하지 않았다** — 5.0 으로 올리면 원하는 답이 나오지만 그것은 측정에 계수를 맞추는
것이고 24차가 금지한 동작이다. 대신 **쓰는 방식을 바꿨다.**

## 고친 설계 — **절대 판정이 아니라 슬롯 안의 비교**
질문은 「이 선수의 관측가가 낡았는가」가 아니다. 그건 모집단 전체에서 답이 안 나온다.
실제 질문은 **「같은 칸의 두 후보를 관측가로 비교할 때, 두 관측이 비교 가능한 정보 위에
서 있는가」** 이다. 그건 슬롯 안에서 Δz 를 나란히 놓으면 바로 보인다:
```
c6 BN   Bane   Δz +1.28   방 $18      ← 두 시즌이 평평. 관측이 지금도 유효
        Murray Δz +6.83   방 $22      ← 🔴 방이 값을 낸 뒤에 이만큼 좋아졌다
```
**Δz 는 숫자로 읽는다. 임계로 찍지 않는다.**
⚠️ 이것은 **진단이다. 어떤 가격도 고치지 않는다.** 관측가를 「보정」하면 우리가
   또 하나의 모델을 만드는 것이고, 42차가 관측가를 채택한 이유가 사라진다.
⚠️ 한 시즌 z 는 혼합 z 가 아니다 — **변화의 방향과 크기**를 보는 용도다.
⚠️ 신인·결장으로 24-25 이 없으면 **판정하지 않는다**(`no_prior`). 없는 것을 0 으로
   읽으면 전원이 stale_low 로 찍힌다.

실행:  python3 tool/price_staleness.py
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest_value as BV
import value_model as VM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 🔴 측정 전 고정했던 임계. **기각됐다**(머리말) — 코드에 남겨 두는 것은
#    다음 사람이 「임계를 안 써 봤나」 묻지 않게 하기 위해서다. 판정에 쓰지 않는다.
REJECTED_ABS_THRESHOLD = 2.0


def enrich(rows):
    """한 시즌 행에 파생 캣을 붙인다 — `backtest_value.blend` 가 혼합 때 하는 것과 같다.
    ⚠️ `load()` 는 원시 스탯만 준다. 안 붙이면 DD·A/T 가 통째로 빠져 z 가 11캣이 된다."""
    import cat_model as CM
    for r in rows.values():
        r["DD"] = CM.dd_game_prob(r["PTS"], r["REB"], r["AST"])
        r["at_marginal_lift"] = ((r["AST"] / r["TOV"] - BV.CB["A/T"]["baseline_per_game"])
                                 if r["TOV"] else None)
    return rows


def build():
    s24, s25 = enrich(BV.load("2024-25")), enrich(BV.load("2025-26"))
    PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json",
                                                  encoding="utf-8"))}
    pool = [p["name"] for p in VM.pool()]
    # 🔴 **같은 표준화**를 두 시즌에 쓴다 — 시즌마다 다시 표준화하면 리그 전체의
    #    이동이 개인의 변화로 둔갑한다.
    # 표준화 모집단은 **25-26 에 존재하는 지명 풀**로 고정한다
    pool = [n for n in pool if n in s25 and n in s24]
    z25, _ = BV.ztable(s25, pool, with_gp=True)
    z24, _ = BV.ztable(s24, pool, with_gp=True)

    out = {}
    for n, p in PL.items():
        rp = p.get("room_price")
        if rp is None:
            continue
        if n not in s24 or n not in s25:
            out[n] = {"room_price": rp, "verdict": "no_prior",
                      "why": "24-25 이 없다(신인·전체 결장) — 판정하지 않는다"}
            continue
        dz = z25[n] - z24[n]
        # 🔴 **verdict 를 안 붙인다.** 절대 임계가 실패했다(머리말). Δz 는 숫자로 낸다.
        out[n] = {"room_price": rp, "my_max": p.get("my_max"),
                  "z_2024_25": round(z24[n], 2), "z_2025_26": round(z25[n], 2),
                  "dz": round(dz, 2),
                  "gp_24_25": s24[n]["GP"], "gp_25_26": s25[n]["GP"]}
    return out


def plan_names():
    """계획이 실제로 기대는 이름 — 코어 1순위 · 대체 후보 · 감축 목적지."""
    CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
    use = {}
    for co in CJ["cores"]:
        for s in co["slots"]:
            for i, c in enumerate(s.get("candidates", [])):
                use.setdefault(c["name"], []).append(
                    "%s %s %s" % (co["id"], s["slot"], "1순위" if i == 0 else "대체%d" % (i + 1)))
    return use


def main():
    st = build()
    CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))

    print("관측가 신선도 — 방은 **24-25 까지** 보고 값을 냈고 우리는 25-26 을 쓴다")
    print("Δz = z(25-26) − z(24-25) · 같은 13캣 · 같은 표준화 · GP 포함")
    print("🔴 절대 임계는 기각됐다(64%% 가 걸렸다). **같은 칸의 후보끼리 나란히** 읽는다.\n")

    flagged = []
    for co in CJ["cores"]:
        for sl in co["slots"]:
            cands = [c["name"] for c in sl.get("candidates", [])]
            have = [n for n in cands if n in st and "dz" in st[n]]
            if len(have) < 2:
                continue
            dzs = [st[n]["dz"] for n in have]
            spread = max(dzs) - min(dzs)
            # 🔴 「이 칸에서 관측가 비교가 위험한가」 = 후보 간 Δz 폭이 큰가.
            #    폭이 작으면 후보들이 같은 정보 위에 있고 관측가 비교가 유효하다.
            if spread < 4.0:
                continue
            worst = have[dzs.index(max(dzs))]
            flagged.append((co["id"], sl["slot"], spread, worst, have))
    flagged.sort(key=lambda x: -x[2])

    print("🔴 후보 간 Δz 폭이 큰 칸 — **관측가로 후보를 비교하지 말 것**")
    for cid, slot, spread, worst, have in flagged:
        print("  %-3s %-5s  폭 %.1f   가장 좋아진 후보 **%s**" % (cid, slot, spread, worst))
        for n in have:
            d = st[n]
            print("       %-24s Δz %+6.2f   방 $%-5s 상한 $%-4s  (%.0fG→%.0fG)"
                  % (n, d["dz"], d["room_price"], d["my_max"],
                     d["gp_24_25"], d["gp_25_26"]))
    print("\n  칸 %d개 — 이 칸들은 「방이 작년에 낸 값」으로 1순위를 정하면 안 된다" % len(flagged))

    json.dump({"generated_by": "tool/price_staleness.py",
               "metric": ("Δz = z(25-26) − z(24-25) · 같은 13캣 · 같은 표준화 · GP 포함. "
                          "방의 관측가는 24-25 까지의 정보로 형성됐다."),
               "rejected_rule": {"abs_threshold": REJECTED_ABS_THRESHOLD,
                                 "why": ("관측 92명 중 59명(64%)이 걸렸다. |Δz| 중앙값 3.27 로 "
                                         "임계가 중앙값 아래였다. **튜닝하지 않고 설계를 바꿨다** "
                                         "— 슬롯 안 비교로 쓴다(24차 원칙).")},
               "does_not": ["가격을 고치지 않는다 — 진단 전용",
                            "관측가를 폐기하지 않는다 — 어디에 쓸 수 없는지만 말한다",
                            "선수를 「낡음/신선」으로 분류하지 않는다 — 절대 임계는 기각됐다"],
               "slot_spread_flag": 4.0,
               "flagged_slots": [{"core": c, "slot": s_, "spread": round(sp, 2),
                                  "most_improved": w,
                                  "candidates": {n: st[n]["dz"] for n in hv}}
                                 for c, s_, sp, w, hv in flagged],
               "players": st},
              io.open(f"{BASE}/data/price_staleness.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\ndata/price_staleness.json 기록")


if __name__ == "__main__":
    main()
