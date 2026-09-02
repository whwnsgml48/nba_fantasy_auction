#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""남은 BUY 필드의 **조달 델타 쌍**을 만든다 — 05 의 `tool/pivot_delta.py pair` 입력.

무엇을 만드나
  「못 사는 1순위를 살 수 있는 것으로 바꾸면 승률을 얼마나 잃는가」를 재려면
  **9명 로스터 두 벌**이 필요하다. 그래서 엔트리 하나마다 쌍을 만들지 않고,
  **치환 결정 하나마다** 쌍을 만든다:

```
a  그 자리에 **못 사는** 이름이 있는 로스터   (현행)
b  그 자리를 **살 수 있는** 이름으로 바꾼 것
```

🔴 **엔트리 수와 쌍 수는 다르다.** 167 엔트리에서 쌍이 안 나오는 경우가 셋이다:
```
① 그 이름을 **살 수 있다**            → 잴 게 없다
② 살 수 있는 대체가 **하나도 없다**    → 「대체 없음」이다. 쌍이 아니라 **결론**이다
③ 바꾸면 **아홉 칸이 안 선다**         → 자격 실패. 그 대체는 애초에 후보가 아니다
```
셋 다 **개수를 출력한다.** 안 만든 것을 조용히 빼면 「167 중 N 을 쟀다」가 거짓이 된다.

⚠️ 순서 정규화는 하지 않는다 — `pivot_delta.canon()` 이 한다. 여기서 정렬해 버리면
   그쪽 규약과 이중으로 적용돼 「어디서 정렬됐나」가 흐려진다(docs/11 ⑬).

🔴 **`buyable()` 이 이 파일의 전제 스위치다** (docs/05 §6j 검증 참조)
  지금은 「작년 실낙찰 환산가 ≤ 우리 상한」이다. 그래서 **①의 42칸(1순위를 살 수 있는
  칸)은 쌍이 안 나온다** — 작년 가격 모델 안에서만 참인 판단이다.
  방이 다르게 흐른다고 보면 **여기 하나만 바꾸면 그 42칸이 다시 열린다.**
  예: 시장 상단 기준으로 보려면 `pl[n]["my_max"] >= pl[n]["market_high"]`.
  ⚠️ 바꿀 때는 **왜 바꿨는지와 그때 쌍이 몇 개가 됐는지**를 같이 적을 것 —
     기준이 조용히 바뀌면 「31쌍을 쟀다」와 「N쌍을 쟀다」를 비교할 수 없게 된다.

이 스크립트는 쌍 목록만 쓴다. **승률은 재지 않는다** — 05 가 잰다.
"""
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pos_elig as PE  # noqa: E402

SCALE = 1.11
OUT = BASE + "/data/delta_pairs.json"


def main():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))

    def adj(n):
        py = pl[n].get("prior_auction_price")
        return None if py is None else round(py * SCALE)

    def buyable(n):
        a = adj(n)
        return True if a is None else pl[n]["my_max"] >= a   # 미지명 = 작년 안 팔림 = 싼 쪽

    def legal(names):
        return len(PE.match([pl[x] for x in names]) or []) == len(PE.ROSTER_SLOTS)

    pairs = []
    skip_buyable = skip_noalt = skip_illegal = 0
    no_fallback = []

    def emit(label, roster, idx, alts):
        """roster[idx] 가 못 사는 이름일 때, 살 수 있는 대체마다 쌍을 만든다."""
        nonlocal skip_noalt, skip_illegal
        cur = roster[idx]
        ok = [x for x in alts if x not in roster and buyable(x)]
        if not ok:
            skip_noalt += 1
            no_fallback.append((label, cur))
            return
        made = 0
        for x in ok:
            b = list(roster)
            b[idx] = x
            if not legal(b):
                skip_illegal += 1
                continue
            pairs.append({"label": "%s :: %s → %s" % (label, cur, x),
                          "a": list(roster), "b": b,
                          "meta": {"out": cur, "in": x,
                                   "out_prior_adj": adj(cur), "out_max": pl[cur]["my_max"],
                                   "in_prior_adj": adj(x), "in_max": pl[x]["my_max"]}})
            made += 1
        if not made:
            no_fallback.append((label, cur))

    # ── ① 피벗 로스터 + 그 칸의 alternates (101건의 출처)
    for co in cj["cores"]:
        pp = co.get("pivot_plan") or {}
        fr = pp.get("final_roster") or []
        if len(fr) != 9:
            continue
        roster = [e["name"] for e in fr]
        for i, e in enumerate(fr):
            if buyable(e["name"]):
                skip_buyable += 1
                continue
            emit("%s pivot %s" % (co["id"], e.get("slot", "?")), roster, i,
                 [x["name"] for x in (e.get("alternates") or [])])

    # ── ② base 로스터 + anchor_plan (on_fail.target · substitutes_dual_ok)
    for co in cj["cores"]:
        base = [s["candidates"][0]["name"] for s in co["slots"]]
        for i, s in enumerate(co["slots"]):
            ap = s.get("anchor_plan") or {}
            # ⚠️ `on_fail.target` 은 **선수 이름이 아닐 수 있다** — action 이
            #   "switch_core" 면 코어 id("c6")가 들어온다. 이름으로 가정하면 KeyError 다.
            #   (이 자리가 `name_fields` 에서 BUY 로 분류됐지만, BUY 인 것은
            #    action=="substitute" 인 경우뿐이다.)
            #   🔴 `on_fail.target` 은 대개 `substitutes_dual_ok` 에도 들어 있다 —
            #      두 경로에서 같은 이름을 넣으면 **완전히 동일한 쌍이 두 번** 나온다.
            #      실제로 3건 났고(05 가 값이 소수점까지 같아서 발견) 「31쌍」이 거짓이 됐다.
            #      순서는 유지한 채 중복만 제거한다(on_fail 우선).
            names = []
            of = ap.get("on_fail") or {}
            if of.get("action") == "substitute" and of.get("target") in pl:
                names.append(of["target"])
            names += [x for x in (ap.get("substitutes_dual_ok") or []) if x in pl]
            names = list(dict.fromkeys(names))
            if not names:
                continue
            if buyable(base[i]):
                skip_buyable += 1
                continue
            emit("%s base %s(앵커)" % (co["id"], s["slot"]), base, i, names)

    # ── ③ swaps[].in — 스왑으로 들여오는 선수
    #   ⚠️ **`in` 과 `out` 이 같은 이름인 스왑이 있다** — 선수 교체가 아니라 **가격 상향**
    #      이다(`kind: "가격 상향 (과열 세계 · 시장 상단)"`). 그걸 「들여올 수 없는 선수」로
    #      찍으면 KAT 를 KAT 로 못 바꾼다는 무의미한 말이 된다. 갈라서 센다.
    swap_dead, reprice_short = [], []
    for co in cj["cores"]:
        for sw in (co.get("pivot_plan") or {}).get("swaps") or []:
            i_, o_ = sw.get("in") or {}, sw.get("out") or {}
            n = i_.get("name")
            if not n or buyable(n):
                continue
            if n == o_.get("name"):
                # 가격 상향: 과열 세계의 계획가조차 작년 실낙찰가에 못 미치는가
                reprice_short.append((co["id"], n, i_.get("plan_price"),
                                      adj(n), pl[n]["my_max"]))
            else:
                swap_dead.append((co["id"], o_.get("name"), n, adj(n), pl[n]["my_max"]))

    # ── ④ redeploy.moves[].player — 치환 후 남는 돈으로 사는 선수
    redeploy_dead = []
    for co in cj["cores"]:
        for s in co["slots"]:
            for cd in s["candidates"]:
                for mv in ((cd.get("redeploy") or {}).get("moves") or []):
                    n = mv.get("player")
                    if n and not buyable(n):
                        redeploy_dead.append((co["id"], s["slot"], cd["name"], n,
                                              adj(n), pl[n]["my_max"]))

    print("조달 델타 쌍 생성 — 05 의 tool/pivot_delta.py pair 입력\n")
    print("  🟢 쌍 **%d개** 생성" % len(pairs))
    print("  ── 쌍이 안 나온 것 (조용히 빼지 않는다) ──")
    print("     ① 그 이름을 **살 수 있다** — 잴 게 없다            %d칸" % skip_buyable)
    print("     ② 살 수 있는 대체가 **없다** — 쌍이 아니라 결론이다  %d칸" % len(no_fallback))
    print("     ③ 바꾸면 **아홉 칸이 안 선다**(자격 실패)           %d건" % skip_illegal)
    if no_fallback:
        print("\n  ⛔ 「대체 없음」 — 재도 답이 안 나온다. 그 자체가 결론이다")
        for lab, cur in no_fallback:
            print("       %-22s %s (환산 $%s > 상한 $%d)"
                  % (lab, cur, adj(cur), pl[cur]["my_max"]))
    if swap_dead:
        print("\n  ⛔ 스왑으로 **들여올 수 없는** 선수 — 그 스왑 자체가 불가 (쌍으로 못 잰다)")
        for cid, out, n, a, mx in swap_dead:
            print("       %-4s %s → **%s** (환산 $%d > 상한 $%d)" % (cid, out, n, a, mx))
    if reprice_short:
        print("\n  ⛔ **가격 상향 스왑이 그래도 모자란다** (선수 교체가 아니다 — 같은 선수 재가격)")
        for cid, n, pp, a, mx in reprice_short:
            print("       %-4s %-24s 과열 세계 계획가 $%s · 작년 환산 **$%d** · 우리 상한 $%d"
                  % (cid, n[:24], pp, a, mx))
        print("       → 과열 대응으로 값을 올려도 **작년 방 가격에 못 미친다.** 상한 자체가 낮다")
    if redeploy_dead:
        print("\n  ⛔ 재배치로 **살 수 없는** 선수")
        for cid, slot, cd, n, a, mx in redeploy_dead:
            print("       %-4s %-5s %s 치환 시 → **%s** (환산 $%d > 상한 $%d)"
                  % (cid, slot, cd, n, a, mx))

    # 🔴 최종 안전망 — 위 수정으로 충분하지만, **중복은 조용히 지나간다.**
    #   05 가 값이 소수점까지 같아서 눈치챘을 뿐 다음엔 못 본다. 여기서 세고 죽인다.
    seen_k, dedup, dups = set(), [], 0
    for x in pairs:
        k = (x["label"], tuple(x["a"]), tuple(x["b"]))
        if k in seen_k:
            dups += 1
            continue
        seen_k.add(k)
        dedup.append(x)
    if dups:
        print("\n  ⚠️ 중복 %d쌍 제거 (같은 label·a·b) — 생성 경로가 겹쳤다는 뜻이다" % dups)
    pairs = dedup

    # 🔴 **파일 모양을 바꾸지 않는다.** `pivot_delta.py pair` 가 최상위를 리스트로 순회한다
    #   (`for r in rows: r["a"]`). dict 로 감싸면 **남의 도구가 죽는다.**
    #   한 번 그렇게 만들었다가 되돌렸다 — 소비자를 확인하고 나서 형식을 바꾼다.
    #   스탬프는 **곁파일**에 둔다. 소비자는 안 보고, 필요한 사람은 찾을 수 있다.
    json.dump(pairs, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import roster_hash as _RH
    json.dump({"for": os.path.relpath(OUT, BASE),
               "roster_hash": _RH.roster_hash(), "file_hash": _RH.file_hash(),
               "pairs": len(pairs),
               "note": "🔴 재측정 필요 여부는 **roster_hash** 로 판정한다. file_hash 는 "
                       "근거 문구만 바뀌어도 달라지므로 쓰지 말 것 (tool/roster_hash.py)."},
              io.open(OUT.replace(".json", ".stamp.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 🔴 스탬프를 붙인다 — 이 쌍들이 **어느 계획 상태에서 만들어졌는지**.
    #   05 가 재측정 필요를 파일 해시로 판정하다 헛돌았다(주석만 바뀌어도 달라진다).
    #   **로스터 해시**를 같이 찍으면 「계획이 바뀌었나」를 그 자리에서 알 수 있다.
    import roster_hash as RH
    print("\n" + RH.stamp())

    print("\n  %s 기록 (%d쌍)" % (os.path.relpath(OUT, BASE), len(pairs)))
    print("  → python3 tool/pivot_delta.py pair data/delta_pairs.json [iters]")
    print("\n⚠️ 승률은 재지 않았다 — 05 가 잰다. 순서 정규화도 pivot_delta.canon() 이 한다.")


if __name__ == "__main__":
    main()
