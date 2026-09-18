#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""드래프트 리허설 — **도구를 시간 압박 아래 시험한다** (45차 신설).

## 왜 필요한가 🔴
이 저장소는 44차까지 계획을 정교하게 다듬었지만 **사람이 10초 안에 이 도구로 결정할 수
있는지는 한 번도 시험하지 않았다.** `docs/13` 의 자기 검증 5문항은 **작성자가** 답한
것이고 시간 압박이 없었다. 그리고 42차 이후 화면에 올릴 내용이 오히려 **늘었다**
(관측가 열 · 캣 밴드 · 감축표 · 분기 3줄). 분석이 정확해진 만큼 실행 부하가 커졌다.

**이 스크립트가 답하는 질문은 하나다: 부르거나 물러나는 판단을 10초 안에 할 수 있는가.**

## 정답지가 실재한다
`data/prior_auction_2025_26/results.json` 에 **작년 이 방의 실낙찰 120건**이 가격까지 있다.
가격을 만들 필요가 없다 — 이 방이 실제로 낸 돈을 쓴다(×1.117 환산 · `docs/08` §①).

## 채점 기준 (사전 고정)
```
계획 후보  낙찰가 <= 그 칸 bid_ceiling  →  정답은 「잡는다」
계획 후보  낙찰가 >  그 칸 bid_ceiling  →  정답은 「물러난다」
태우기     항상                          →  정답은 「태운다」(내가 사지 않는다)
그 외      채점하지 않는다               →  「자유」. 오답으로 세지 않는다
```
⚠️ **「자유」를 오답으로 세지 않는 이유**: 계획 밖 선수를 싸게 줍는 판단은 남은 칸의
포지션 자격과 잔액에 달렸고, 정답이 하나로 정해지지 않는다(`docs/13 §6`). 그건 이
드릴이 답할 질문이 아니다.

⚠️ **관측가는 예측이 아니다.** 작년 값이고 한 시즌 낡았다(44차 `price_staleness.py`:
관측 92명의 |Δz| 중앙 3.27). 이 드릴은 **가격을 맞히는 연습이 아니라 「그 가격이 나왔을
때 손이 어디로 가는가」의 연습**이다.

## 쓰는 법
    python3 tool/rehearsal.py            # c6 (기본값) · 전체
    python3 tool/rehearsal.py c2         # 다른 코어
    python3 tool/rehearsal.py c6 --fast  # 10초 제한 없음 (읽기 연습)
    python3 tool/rehearsal.py c6 -n 20   # 20명만

**콘솔과 종이를 띄워 놓고 하십시오.** 그게 시험 대상이다.
입력: `y`(그 호가에 넘긴다) · `n`(보낸다) · `b`(태운다) · 엔터만 = 시간 초과.\n🔴 **호가는 지명과 함께 보입니다.** 초판은 가격을 숨긴 채 물었는데,\n   옥션의 판단은 「이 값에 부를까」이므로 가격 없이는 답이 없다 — 즉시 정정했다.
"""
import io
import json
import os
import random
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 1.117          # 12팀/10칸 → 14팀/9칸 총액 스케일 (docs/08 §①)
LIMIT = 10.0           # 초. 리그 규칙: 최종 입찰 후 10초 무경쟁 시 자동 낙찰
SEED = 20261005        # 드래프트 날짜. 같은 순서를 반복 연습할 수 있게 고정한다


def load():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
    pr = json.load(io.open(BASE + "/data/prior_auction_2025_26/results.json", encoding="utf-8"))
    return pl, cj, pr


def core_map(cj, cid):
    """{선수: (슬롯, 순위, 그 칸 상한)} — 계획 후보만."""
    co = [c for c in cj["cores"] if c["id"] == cid]
    if not co:
        raise SystemExit("코어 %s 없음. c1~c7 중 하나." % cid)
    co = co[0]
    m = {}
    for s in co["slots"]:
        for i, c in enumerate(s.get("candidates", [])):
            # 🔴 **후보별 `bid_ceiling` 을 쓴다. 슬롯 레벨을 쓰면 틀린다.**
            #    슬롯 상한 = 그 칸에 최대 얼마까지 쓸 수 있나
            #    후보 상한 = **그 선수에게** 얼마까지 부를 수 있나 = min(my_max, 단일상한, 철수가)
            #    초판이 슬롯 레벨을 읽어 Josh Hart 에게 $31(실제 $9)을 줬고,
            #    콘솔이 맞고 드릴이 틀린 오답을 만들었다(사용자가 잡음 · 2026-09-18).
            ceil = c.get("bid_ceiling")
            if ceil is None:
                ceil = s.get("bid_ceiling")      # 후보에 없을 때만 폴백
            # 같은 선수가 두 칸에 있으면 **상한이 큰 칸**을 남긴다 —
            # 실전에서 그가 올라오면 더 비싼 칸으로 쓸 수 있으므로 그쪽이 실질 상한이다.
            prev = m.get(c["name"])
            if prev is None or (ceil or 0) > (prev[2] or 0):
                m[c["name"]] = (s["slot"], i + 1, ceil)
    return co, m


def build_queue(pl, pr, cmap, n=None):
    """작년 실낙찰 120건 → 지명 순서 근사.

    🔴 순번 정보는 데이터에 **없다**(팀별로 묶여 있다). 실제 옥션은 비싼 이름이
    앞쪽에 몰리므로 **가격 내림차순 + 국소 흔들기**로 근사한다. 순서를 맞히는
    연습이 아니므로 이 근사로 충분하고, 시드를 고정해 반복 가능하게 둔다.
    """
    rows = []
    for t in pr["teams"]:
        for e in t["players"]:
            nm = e.get("name_en")
            if not nm or nm not in pl:
                continue          # 우리 DB 밖(174명 밖) — 판단 대상이 아니다
            rows.append((nm, round(e["price"] * SCALE)))
    rows.sort(key=lambda r: -r[1])
    rng = random.Random(SEED)
    for i in range(len(rows)):                      # 국소 스왑으로 단조성만 깬다
        j = min(len(rows) - 1, max(0, i + rng.randint(-4, 4)))
        rows[i], rows[j] = rows[j], rows[i]
    if n:
        # 계획 후보를 우선 남긴다 — 채점 대상이 없으면 드릴이 무의미하다
        keep = [r for r in rows if r[0] in cmap][:n]
        rest = [r for r in rows if r[0] not in cmap][: max(0, n - len(keep))]
        rows = keep + rest
        rows.sort(key=lambda r: -r[1])
        for i in range(len(rows)):
            j = min(len(rows) - 1, max(0, i + rng.randint(-3, 3)))
            rows[i], rows[j] = rows[j], rows[i]
    return rows


def answer_of(pl, cmap, nm, price):
    """사전 고정 채점. 반환 (정답, 사유, 채점대상인가)."""
    if pl[nm].get("tag") == "burn":
        return "b", "태우기 명단 — 남의 예산을 태운다", True
    if nm in cmap:
        slot, rank, ceil = cmap[nm]
        if ceil is None:
            return None, "그 칸에 상한이 없다(플랜 결손)", False
        if price <= ceil:
            return "y", "%s칸 %d순위 · 상한 $%d ≥ $%d" % (slot, rank, ceil, price), True
        return "n", "%s칸 %d순위 · 상한 $%d < $%d" % (slot, rank, ceil, price), True
    return None, "계획 밖 — 남은 칸·자격·잔액에 달렸다", False


def ask(prompt, limit):
    """한 줄 입력. limit 초를 넘겼는지 함께 돌려준다."""
    t0 = time.time()
    try:
        v = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit("중단했습니다.")
    return v, time.time() - t0 > limit if limit else False, time.time() - t0


def main():
    args = [a for a in sys.argv[1:]]
    cid = next((a for a in args if a.startswith("c") and a[1:].isdigit()), "c6")
    fast = "--fast" in args
    n = None
    if "-n" in args:
        try:
            n = int(args[args.index("-n") + 1])
        except (IndexError, ValueError):
            raise SystemExit("-n 다음에 숫자를 주십시오.")

    pl, cj, pr = load()
    co, cmap = core_map(cj, cid)
    queue = build_queue(pl, pr, cmap, n)
    limit = 0 if fast else LIMIT
    budget, slots = 200, 9
    plan_total = co.get("planned_total")

    print("\n" + "=" * 68)
    print("드래프트 리허설 — %s (%s)" % (cid, co.get("name", "")))
    print("=" * 68)
    print("지명 %d건 · 채점 대상 %d건 · 제한 %s"
          % (len(queue), sum(1 for nm, p in queue if answer_of(pl, cmap, nm, p)[2]),
             "없음(--fast)" if fast else "%.0f초" % LIMIT))
    print("각 지명에 **호가**가 붙습니다. 그 값에 넘길지만 정하십시오.\n입력  y=넘긴다(내 것)  n=보낸다  b=태운다  (엔터만 = 시간초과와 동일)")
    print("🔴 콘솔과 종이를 띄워 놓고 하십시오 — 그게 시험 대상입니다.")
    print("계획 총액 $%s · 예산 $200 · 칸 9개\n" % plan_total)
    input("준비되면 엔터… ")

    ok = bad = over = free = 0
    wrong, slow = [], []
    spent = 0
    got = []
    t_all = time.time()

    for i, (nm, price) in enumerate(queue, 1):
        p = pl[nm]
        want, why, scored = answer_of(pl, cmap, nm, price)
        tag = " [계획]" if nm in cmap else (" [태우기]" if p.get("tag") == "burn" else "")
        print("─" * 68)
        # 🔴 45차 초판은 **가격을 안 보여주고** y/n 을 물었다. 옥션의 판단은
        #    「이 값에 부를까」이므로 가격 없이는 답이 없다 — 사용자가 즉시 지적했고
        #    첫 4건이 통째로 무효였다. 호가를 지명 줄에 띄운다.
        print("[%d/%d] %s  (%s · %s)%s" % (i, len(queue), nm, p["team"], p["pos"], tag))
        print("        호가 **$%d** — 넘기면 내 것, 안 넘기면 남에게 간다" % price)
        v, late, took = ask("   → ", limit)
        if late or v == "":
            over += 1
            slow.append((nm, took))
            print("   ⏱  %.1f초 — 시간 초과" % took)
        if not scored:
            free += 1
            print("   ⚪ 채점 안 함 — %s" % why)
            continue
        if v == want:
            ok += 1
            print("   ✅ (%.1f초) %s" % (took, why))
        else:
            bad += 1
            wrong.append((nm, v or "무응답", want, price, why))
            print("   ❌ (%.1f초) 정답 %s — %s" % (took, want, why))
        if v == "y" and want == "y":
            spent += price
            got.append((nm, price))
            slots -= 1
            room = budget - spent - (slots - 1 if slots else 0)
            print("      잔액 $%d · 남은 칸 %d · 최대 입찰 $%d"
                  % (budget - spent, slots, max(0, room)))

    el = time.time() - t_all
    tot = ok + bad
    print("\n" + "=" * 68)
    print("결과 — %s · %.1f분" % (cid, el / 60))
    print("=" * 68)
    print("채점 %d건 중 정답 %d · 오답 %d  (%.0f%%)" % (tot, ok, bad, 100 * ok / tot if tot else 0))
    print("시간 초과 %d건 / %d건 (%.0f%%)" % (over, len(queue), 100 * over / len(queue)))
    print("채점 제외(자유) %d건" % free)
    if got:
        print("확보 %d명 · 지출 $%d · 잔액 $%d" % (len(got), spent, budget - spent))
    if wrong:
        print("\n🔴 오답 — 여기가 화면이 답을 못 준 자리입니다")
        for nm, v, want, price, why in wrong:
            print("   %-24s 내 %s / 정답 %s · $%-3d  %s" % (nm, v, want, price, why))
    if slow:
        print("\n⏱  10초를 넘긴 %d건 — 화면에서 찾는 데 오래 걸린 이름입니다" % len(slow))
        for nm, took in sorted(slow, key=lambda x: -x[1])[:10]:
            print("   %-24s %.1f초" % (nm, took))
    print("""
읽는 법
  오답이 났으면 **그 정보가 A층에 없다**는 뜻입니다 — 화면을 고칠 자리입니다.
  10초를 넘겼으면 **찾는 데 걸린 것**입니다 — 검색·정렬을 고칠 자리입니다.
  둘 다 없으면 도구가 통과한 것이고, 더 줄이지 마십시오.
🔴 이 결과는 가격 예측 능력이 아니라 **도구 사용성**의 측정입니다.
   작년 낙찰가는 한 시즌 낡았습니다(44차 price_staleness).""")


if __name__ == "__main__":
    main()
