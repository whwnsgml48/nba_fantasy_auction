#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""드래프트 당일 종이 — **인쇄용 A4 한 장**을 데이터에서 생성한다 (47차 신설).

## 왜 생성기인가 🔴
`docs/13-draft-day-sheet.md` 는 사람이 읽는 문서이고 **4,200자로 A4 한 장을 넘긴다**
(9pt 2단 기준 한 장 ≈ 3,500자). 즉 「A4 한 장. 넘기면 실패다」라는 자기 규칙을 위반한
상태였다. 그리고 손으로 HTML 을 따로 쓰면 `docs/13` 과 **반드시 갈라진다** — 이 저장소가
반복해서 당한 형태다(37차 `docs/06` 생성기 없음 · 42차 README 표 두 번 손수정).

그래서 **값을 데이터에서 읽는다.** 사람이 정하는 것은 **무엇을 넣고 무엇을 뺄지**이고
그건 자동화할 수 없으므로 아래 `INCLUDE` 에 명시한다.

## 무엇을 뺐나 — 「그날 부르거나 물러난다」에 안 쓰는 것
```
§0 드래프트 전(9/29~10/4)   → 10/05 에는 **이미 끝난 일**이다. 종이에 둘 이유가 없다
자기 검증 10문항             → 종이를 **만들 때** 쓰는 QA 다. 그날 읽지 않는다
근거·측정치·차수 참조         → σ · %p · docs 링크. 그날 판단을 바꾸지 않는다
```
🔴 **뺐다고 없어진 게 아니다.** `docs/13` 이 전문이고 이 파일은 **그날의 발췌**다.

## 쓰는 법
    python3 tool/gen_print_sheet.py         # → tool/draft-sheet-print.html
    브라우저로 열고 **Cmd+P** → A4 · 배율 100% · 배경 그래픽 끔

⚠️ 데이터가 바뀌면 **다시 돌려야 한다.** `sync_tool.py` 와 같은 성질이다.
"""
import html
import io
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = BASE + "/tool/draft-sheet-print.html"
SCALE = 1.117
CORE = "c6"


def load():
    pl = {p["name"]: p for p in json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))}
    cj = json.load(io.open(BASE + "/data/cores.json", encoding="utf-8"))
    return pl, cj


def room(pl, n):
    pa = pl.get(n, {}).get("prior_auction_price")
    return round(pa * SCALE) if pa else None


def rs(pl, n):
    r = room(pl, n)
    return "$%d" % r if r else "—"


def short(n):
    """성만. 종이 폭이 좁다."""
    p = n.split()
    return p[-1] if p[-1] not in ("Jr.", "III", "II", "IV") else p[-2]


# 관측가가 상한을 **$2 이내**로 넘으면 버리지 않고 `!` 를 붙인다 — `docs/13` 이
# 그 구간을 ⚠️경계로 남긴다(M.Williams −1 · Wiggins −1 · Ausar −4). 한 해 표본이라
# $1~2 는 올해 반대로 갈 수 있고, 버리면 실재하는 선택지를 잃는다.
MARGIN = 2


def alts(pl, cands):
    """살 수 있는 대체만. 상한을 $2 넘게 초과하면 **못 산다** — 종이에 올리지 않는다.
    미지명(—)은 그대로 둔다: 방이 값을 안 불렀다는 관측이고 좋은 신호다."""
    out = []
    for c in cands:
        ce = c.get("bid_ceiling")
        r = room(pl, c["name"])
        if r is None:
            out.append("%s(—)" % short(c["name"]))
        elif ce is None:
            continue
        elif r <= ce:
            out.append("%s(%d)" % (short(c["name"]), r))
        elif r - ce <= MARGIN:
            out.append("%s(%d!)" % (short(c["name"]), r))
    return " → ".join(out) if out else "<b>없음</b>"


def snake_row():
    return [min(29 - 2 * p, 2 * p - 1) for p in range(1, 15)]


def build():
    pl, cj = load()
    co = [c for c in cj["cores"] if c["id"] == CORE][0]
    slots = co["slots"]
    plan_total = sum((s["candidates"][0].get("plan_price") or 0) for s in slots)
    room_total = sum(room(pl, s["candidates"][0]["name"]) or
                     (s["candidates"][0].get("plan_price") or 0) for s in slots)

    # 🔴 분기 임계값이 후보 상한보다 작으면 **그쪽이 실질 상한**이다.
    #    KAT 은 후보 상한 $55 인데 c6 예산이 $50 에서 먼저 막는다
    #    (`kat_price_branch.ceil.c6`). `docs/13` 이 「작은 쪽을 쓴다」로 통일해 뒀고,
    #    종이가 $55 를 보여주면 **$52 에서 문서와 화면이 갈린다.**
    br = cj.get("kat_price_branch") or {}
    br_ceil = (br.get("ceilings") or {}).get(CORE)   # ⚠️ `ceil` 이 아니다 —
    #    그 이름은 `tool_embed.build_kat_branch` 가 만드는 **임베드 형태**이고
    #    cores.json 의 소스 키는 `ceilings` 다. 초판이 헷갈려 조용히 안 걸렸다.
    br_player = br.get("player")

    rows = []
    for s in slots:
        c = s["candidates"][0]
        n = c["name"]
        ce = c.get("bid_ceiling")
        if n == br_player and br_ceil is not None and br_ceil < (ce or 10 ** 9):
            ce = br_ceil
        rows.append((s["slot"], short(n), c.get("plan_price"), ce, rs(pl, n),
                     alts(pl, s["candidates"][1:])))

    # 태우기 — 관측 기준 my_max − room 내림차순 상위 5
    burn = []
    for n, q in pl.items():
        if q.get("tag") != "burn":
            continue
        r = room(pl, n)
        if r is None:
            continue
        burn.append((q["my_max"] - r, short(n), q["my_max"], r))
    burn.sort()
    burn = burn[:5]

    # 남은 칸 계획가 누적 — 안전선 표
    asc = sorted(((s["candidates"][0].get("plan_price") or 0), s["slot"]) for s in slots)
    cum, safety = 0, []
    for pr, sl in asc:
        cum += pr
    running = plan_total
    safety.append(("아홉 전부", plan_total))
    desc = sorted(slots, key=lambda s: -(s["candidates"][0].get("plan_price") or 0))
    for k in (2, 6, 8):
        rest = sum((s["candidates"][0].get("plan_price") or 0) for s in desc[k:])
        safety.append(("%d칸 확보 후 %d칸" % (k, 9 - k), rest))

    gaps = snake_row()
    tight = [str(p) for p in range(1, 15) if gaps[p - 1] <= 5]
    wide = [str(p) for p in range(1, 15) if gaps[p - 1] >= 7]

    def tr(cells, th=False):
        t = "th" if th else "td"
        return "<tr>" + "".join("<%s>%s</%s>" % (t, c, t) for c in cells) + "</tr>"

    slot_tbl = ("<table class=sl>" + tr(["칸", "1순위", "계획", "철수", "방", "대체(살 수 있는 것)"], True)
                + "".join(tr([a, "<b>%s</b>" % b, "$%s" % c, "<b>$%s</b>" % d, e, f])
                          for a, b, c, d, e, f in rows)
                + tr(["", "", "<b>$%d</b>" % plan_total, "", "<b>$%d</b>" % room_total, ""])
                + "</table>")
    burn_tbl = ("<table class=bn>" + tr(["선수", "내 상한", "방", "차"], True)
                + "".join(tr([b, "$%d" % m, "$%d" % r, "<b>%+d</b>" % d]) for d, b, m, r in burn)
                + "</table>")
    safe_tbl = ("<table class=bg>" + tr(["남은 칸", "계획가 합"], True)
                + "".join(tr([a, "<b>$%d</b>" % b]) for a, b in safety) + "</table>")
    gap_tbl = ("<table class=sn>"
               + tr(["순번"] + [str(i) for i in range(1, 15)], True)
               + tr(["최단"] + ["<b>%d</b>" % g for g in gaps]) + "</table>")

    return f"""<title>드래프트 당일 한 장 — 인쇄용</title>
<style>
@page {{ size: A4 portrait; margin: 7mm; }}
* {{ box-sizing: border-box; }}
body {{ font: 8.2px/1.32 -apple-system, "Helvetica Neue", Arial, sans-serif;
  color: #000; background: #fff; margin: 0; padding: 6px 8px;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.wrap {{ column-count: 2; column-gap: 9px; column-fill: auto; }}
h1 {{ font-size: 11px; margin: 0 0 1px; letter-spacing: -.2px; column-span: all; }}
h1 small {{ font-weight: 400; font-size: 8px; color: #555; }}
h2 {{ font-size: 8.6px; margin: 6px 0 2px; padding: 1px 3px; background: #111; color: #fff;
  break-after: avoid; }}
table {{ width: 100%; border-collapse: collapse; margin: 0 0 2px; }}
th, td {{ border: .4px solid #999; padding: .8px 2px; text-align: left; vertical-align: top; }}
th {{ background: #e8e8e8; font-weight: 600; }}
td:nth-child(n+3) {{ text-align: right; white-space: nowrap; }}
.sl td:last-child, .sl th:last-child {{ text-align: left; white-space: normal; font-size: 7.4px; }}
.sn td, .sn th {{ text-align: center; padding: .8px 0; font-size: 7.4px; }}
.n {{ margin: 1px 0 3px; font-size: 7.6px; }}
.n b {{ background: #ffe8e0; }}
.r {{ border-left: 2.5px solid #000; padding-left: 4px; margin: 2px 0 4px; font-size: 7.6px; }}
code {{ font: 7.6px/1.35 ui-monospace, Menlo, monospace; display: block;
  white-space: pre-wrap; background: #f2f2f2; padding: 2px 3px; margin: 1px 0 3px; }}
.k {{ font-weight: 700; }}
</style>
<h1>드래프트 당일 · 코어 6 기본 <small>· 14팀 $200 9칸 13캣 · 전문은 docs/13 · 이 장에 없는 숫자는 그날 보지 않는다</small></h1>
<div class=wrap>

<h2>1 · 분기 — 이 셋만 본다</h2>
<table><tr><th>보는 것</th><th>조건</th><th>간다</th></tr>
<tr><td>Jokić 낙찰가</td><td class=k>≤ $97</td><td><b>코어 2</b> 즉시 · 다른 줄보다 앞선다</td></tr>
<tr><td>KAT 낙찰가</td><td class=k>&gt; $50</td><td><b>KAT 포기</b> → Jokić 열렸으면 c2, 아니면 c6+감축①</td></tr>
<tr><td>저가 센터</td><td class=k>2명+ 과열</td><td><b>코어 7</b> — 2칸 내놓을 각오(−4.0%p)</td></tr>
<tr><td>그 외</td><td>—</td><td><b>코어 6</b></td></tr></table>
<div class=n><b>KAT $50 이 행동 기준</b>이다(상한 $55 보다 예산이 먼저 막는다 · 작은 쪽을 쓴다).
지키러 c7 로 가면 −6.0%p. 대체는 <b>Duren</b>. c7 은 3칸부터 무너진다(80.3 → 75.8%).</div>

<h2>2 · 코어 6 아홉 칸</h2>
{slot_tbl}
<div class=n><b>PF 는 잃는 칸이다</b> — Şengün $67 · Mobley $48 · LeBron $35, 셋 다 상한 위.
가짜 대체를 세우지 않았다. 비면 비는 대로 간다.<br>
「방 —」은 <b>작년 미지명</b>이고 그건 좋은 신호다(방이 값을 안 불렀다).</div>
<div class=r><b>BN 칸이 승부처다.</b> Murray · Bane · Brunson <b>셋 다 상한 $31 · 셋 다 살 수 있다.</b>
$31 넘으면 즉시 다음 이름. <b>Bane 이 먼저 오면 잡는다 — Murray 를 기다리며 넘기지 마라</b>
(둘 다 놓치면 −12.97%p).</div>

<h2>3 · 사전 등록 감축 — 하나뿐</h2>
<table><tr><th>칸</th><th>대체</th><th>절감</th><th>손실</th></tr>
<tr><td>C · KAT</td><td><b>Duren</b></td><td><b>−$63</b></td><td><b>−1.92%p</b></td></tr></table>
<div class=n><b>행을 더하지 마라</b> — 두 칸 동시는 손실이 합보다 크다(−2.99 vs −3.41%p).
<b>D.White 를 줄이지 마라</b> — $9 아끼고 −4.77%p. 우리가 $17 싸게 잡은 유일한 칸이다.</div>

<h2>4 · 예산 — 두 줄</h2>
<code>① 최대 입찰 = 잔액 − (남은 칸 − 1)
② 안전선    잔액 ≥ 남은 칸 계획가 합</code>
{safe_tbl}
<div class=r><b>안전선을 깼다면</b><br>
KAT 미보유 → <b>감축 ①</b>. $63 이 풀린다. 유일한 사전 등록 수단이다.<br>
KAT 보유 → <b>c6 안에 더 줄일 곳이 없다.</b> 계획 밖에서 줍거나(자격 먼저) <b>빈 칸으로 끝낸다.</b>
$1 짜리를 억지로 채우지 않는다.</div>
<div class=n><b>계획 예비 $9 는 실탄이 아니다</b> — 7코어 중 6개가 작년 가격 기준 예비 마이너스(c6 −$80).</div>

<h2>5 · 태우기 — 상위 5</h2>
{burn_tbl}
<div class=n><b>어느 코어 후보도 태우지 않는다</b> — 태우면 내 탈출로를 닫는다.
다섯 다 <b>내가 못 사는 선수</b>라 떠안아도 손해가 아니다.
Kawhi·JJJ·Durant 는 뺐다(방이 내 값 근처에 산다).
AD 는 올해 $54 를 안 낼 수 있다 → 예산이 안 준다.</div>

<h2>6 · 추첨 직후 10초 — 순번이 태우기를 정한다</h2>
<code>내 순번 p → 최단 간격 = min(29−2p, 2p−1)   (스네이크 · 매 라운드 반전 · 총 9회)</code>
{gap_tbl}
<div class=n><b>간격 1~5</b>(순번 {', '.join(tight)}) → <b>짧은 간격에 몰아라.</b>
방이 값을 재조정할 틈 없이 예산이 두 번 빠진다.<br>
<b>간격 7+</b>(순번 {', '.join(wide)}) → 몰 자리가 없다 · <b>분산</b>(초반 2 · 중반 3).</div>
<div class=r><b>#1 에서도 태운다 — 최상위 이름만.</b> 태우기는 남이 <b>안 붙을 때</b> 실패하고,
#1 은 전원이 $200 을 든 순간이라 붙을 확률이 가장 높다. 한계 대상은 뒤로.<br>
<b>후반 연속 쌍에서는 태우기를 멈춘다</b> — 예산이 얇아 안 붙고 자동 $1 로 두 명을 떠안는다.
그 자리는 내 칸을 채우는 자리다.<br>
위 표는 <b>28지명까지 정확</b>하다(9명 채운 팀이 로테이션에서 빠진다).</div>

<h2>7 · 그 자리에서</h2>
<div class=n>
· <b>못 사는 값이 나왔다</b> → 대체로 내려간다. 대체도 상한 위면 <b>그 칸을 버린다.</b><br>
· <b>계획에 없는 선수가 싸다</b> → 산다. 단 <b>남은 칸의 포지션 자격</b>을 먼저 본다.<br>
· <b>자동 $1 입찰이 있다</b> — 태우기는 남이 100% 붙을 선수만.<br>
· 내 차례는 반드시 온다 — <b>급하게 지명하지 않는다.</b><br>
· 2026-27 야후 <b>포지션 자격</b>은 1순위 전원 확인됐다. 대체 사슬을 쓰게 되면 그 자리에서 화면을 본다.
</div>

</div>
"""


if __name__ == "__main__":
    io.open(OUT, "w", encoding="utf-8").write(build())
    n = len(io.open(OUT, encoding="utf-8").read())
    print("생성: tool/draft-sheet-print.html (%d바이트)" % n)
    print("브라우저로 열고 Cmd+P → A4 · 배율 100% · 배경 그래픽 끔")
