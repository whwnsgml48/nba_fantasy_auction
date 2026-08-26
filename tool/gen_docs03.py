#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs/03의 표를 players.json에서 생성한다. 산문은 손대지 않는다.

왜 생성으로 바꾸는가 (26차)
  docs/03은 손으로 유지되던 탓에 두 가지가 동시에 낡았다:
    (1) 시세·my_max — Luka가 "$72-80 $52"로 적혀 있는데 실제는 $83-91, Giannis는
        "$50-58 $30"인데 실제 $61-69 · $25 였다.
    (2) 사유 문구 — Curry "3PT% 엘리트 아님"(14차 폐기) · A.Davis·Kessler
        "블록 top-25 밖 (검증)"(가중치 w3) 등 8건.
  표의 열은 전부 players.json에 있고, 사유 열조차 flag·verdict 필드에 있으며
  **validate.py의 M4가 상시 검사**한다. 즉 생성으로 바꾸면 사유 열이 M4 보호 아래
  들어가고, 위 8건은 애초에 생길 수 없다.

경계
  분석 산문(평가 사슬·파생 지표 설명·캣 가중치 표기)은 **수기 유지**다.
  이 스크립트는 마커 사이만 교체한다:
      <!-- GEN:<key> -->  ... 생성 구간 ...  <!-- /GEN:<key> -->
  마커가 없으면 해당 섹션의 첫 표를 찾아 마커로 감싼 뒤 교체한다(최초 1회).
"""
import json, io, os, re, math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC  = f"{BASE}/docs/03-player-valuations.md"
PL   = json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))
CB   = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))["opponent_baseline"]["cat_baselines"]
F    = json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json", encoding="utf-8"))["players"]

WEEK_GAMES = 3.5      # 주간 경기수 가정
TEAM_3PA   = 135      # 팀 주간 3점 시도 가정 (선발 7명)

def mid(p):  return (p["market_low"] + p["market_high"]) / 2
def mkt(p):  return f"${p['market_low']}-{p['market_high']}"
def reason(p):
    """사유 열 — flag 우선, 없으면 verdict. 둘 다 M4가 검사하는 필드다."""
    t = (p.get("flag") or "").strip() or (p.get("verdict") or "").strip() or "—"
    return t.replace("|", "·").replace("\n", " ")[:150]
def line(p):
    lf = (p.get("measured_line_full") or {}).get("line")
    if lf: return lf.replace("|", "·")[:150]
    return (p.get("measured_2025_26") or "—").replace("|", "·")[:150]

def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)

# ── 1) 볼륨 레버리지 (비율 캣 전용)
def gen_leverage():
    base = CB["3P%"]["baseline_per_game"]
    rows = []
    for p in PL:
        if not p.get("volume_leverage"): continue
        r = F.get(p["name"])
        if not r or not r.get("3PA") or r.get("3P%") is None: continue
        wk  = r["3PA"] * WEEK_GAMES
        shr = wk / TEAM_3PA
        lev = (r["3P%"] - base) * shr * 100
        sd  = math.sqrt(max(r["3P%"] * (1 - r["3P%"]) / wk, 0.0)) * 100
        rows.append((lev, p["name"], r["3PA"], wk, shr, r["3P%"], sd))
    rows.sort(key=lambda x: -x[0])
    keep = rows[:5] + ([rows[-1]] if len(rows) > 6 else [])
    body = []
    for i, (lev, n, pa, wk, shr, pct, sd) in enumerate(keep):
        last = (i == len(keep) - 1 and len(rows) > 6)
        nm = f"**{n}**" if last else n
        body.append([nm, f"{pa:.1f}", f"{wk:.0f}", f"{shr*100:.1f}%", f"{pct*100:.1f}%",
                     ("**%+.2fpp**" % lev) if not last else ("%+.2fpp (최하)" % lev),
                     f"±{sd:.1f}pp"])
    return (table(["선수", "3PA/G", "주간시도", "지분", "3PT%", "레버리지", "변동성"], body)
            + f"\n\n기준선 3PT% {base*100:.1f}%(`cat_baselines`) · 주간 {WEEK_GAMES}경기 · 팀 주간 3PA {TEAM_3PA} 가정."
            + f" 변동성은 이항 SD √(p(1−p)/주간시도). 대상 {len(rows)}명 중 상위 5 + 최하 1.")

# ── 2) 잉여 상위 20
def gen_surplus():
    rows = sorted([p for p in PL if p.get("surplus") is not None],
                  key=lambda p: -p["surplus"])[:20]
    return table(["잉여", "시장중간", "최대가", "포지션", "선수", "실측(BBRef)"],
                 [[f"+${p['surplus']}" if p['surplus'] >= 0 else f"-${abs(p['surplus'])}",
                   f"${mid(p):.0f}", f"${p['my_max']}", p["pos"], f"**{p['name']}**", line(p)]
                  for p in rows])

# ── 3) 획득 불가
def gen_unobtainable():
    rows = sorted([p for p in PL if p.get("obtainable") is False],
                  key=lambda p: -p["market_high"])
    return table(["시장", "내 최대가", "선수", "사유"],
                 [[mkt(p), f"${p['my_max']}", p["name"], reason(p)] for p in rows]) \
           + f"\n\n총 {len(rows)}명 (`obtainable=false` — 내 최대가 < 시장 하단)."

# ── 4) 태우기 지명 명단
def gen_burn():
    rows = sorted([p for p in PL if p.get("tag") == "burn"], key=lambda p: -p["market_high"])
    return table(["시장", "최대가", "div", "선수", "실측"],
                 [[mkt(p), f"${p['my_max']}",
                   "%+d" % ((p.get("value_reference") or {}).get("rank_divergence") or 0),
                   p["name"], line(p)] for p in rows]) \
           + (f"\n\n총 {len(rows)}명. `div`는 `value_reference.rank_divergence` — "
              "양수면 my_max가 가치보다 인색하다는 뜻이고, `validate.py`의 M5가 "
              "|div| >= 20 인 burn을 위반으로 잡는다.")

# ── 5) 특화 다트
def gen_darts():
    rows = sorted([p for p in PL if p.get("tag") == "dart" and (p.get("surplus") or 0) > 0],
                  key=lambda p: (-(p.get("surplus") or 0), p["market_low"]))[:30]
    return table(["최대가", "시장", "선수", "캣", "실측"],
                 [[f"${p['my_max']}", mkt(p), p["name"], p["cats"], line(p)] for p in rows]) \
           + f"\n\n잉여 플러스 다트 상위 30 (전체 {sum(1 for p in PL if p.get('tag')=='dart' and (p.get('surplus') or 0)>0)}명)."

# ⚠️ 26차: 제목을 **행 앵커 정규식**으로 잡는다. 처음엔 doc.find("획득 불가")를 썼는데
# 산문("### 획득 가능성 …" 아래 설명문)에 같은 문구가 있어 그쪽을 먼저 잡았고,
# 그 뒤 첫 표가 이미 삽입된 leverage 블록이라 **마커가 중첩**됐다 —
# 진짜 획득불가 표는 손도 안 댄 채 leverage 표가 덮였다. 제목행만 매칭한다.
SECTIONS = [
    ("leverage",     r"^#{2,3}\s*볼륨 레버리지",  gen_leverage),
    ("surplus",      r"^#{2,3}\s*잉여 상위",       gen_surplus),
    ("unobtainable", r"^#{2,3}\s*획득 불가",       gen_unobtainable),
    ("burn",         r"^#{2,3}\s*태우기 지명",     gen_burn),
    ("darts",        r"^#{2,3}.*특화 다트",         gen_darts),
]

def main():
    doc = io.open(DOC, encoding="utf-8").read()
    for key, heading, fn in SECTIONS:   # heading은 정규식(행 앵커)
        body = fn()
        block = f"<!-- GEN:{key} — tool/gen_docs03.py 가 생성. 직접 수정하지 마라 -->\n{body}\n<!-- /GEN:{key} -->"
        pat = re.compile(r"<!-- GEN:%s.*?-->.*?<!-- /GEN:%s -->" % (key, key), re.S)
        if pat.search(doc):
            doc = pat.sub(lambda m: block, doc, count=1)
            print(f"  {key:<13} 교체")
            continue
        # 최초 1회: 해당 제목행 뒤 첫 표를 찾아 감싼다
        hm = re.search(heading, doc, re.M)
        if not hm:
            print(f"  {key:<13} ⚠️ 제목 '{heading}' 없음 — 건너뜀"); continue
        hi = hm.end()
        m = re.search(r"^\|.*?(?:\n\|.*)+", doc[hi:], re.M)
        if not m:
            print(f"  {key:<13} ⚠️ 표를 못 찾음 — 건너뜀"); continue
        a, b = hi + m.start(), hi + m.end()
        if "<!-- GEN:" in doc[hi:a]:
            print(f"  {key:<13} ⚠️ 다음 표가 이미 생성 블록 안 — 중첩 방지로 건너뜀"); continue
        doc = doc[:a] + block + doc[b:]
        print(f"  {key:<13} 마커 삽입 + 교체")
    io.open(DOC, "w", encoding="utf-8").write(doc)
    print("docs/03 표 생성 완료 (산문 미변경)")

if __name__ == "__main__":
    main()
