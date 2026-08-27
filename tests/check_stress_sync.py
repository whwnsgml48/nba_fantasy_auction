#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""툴의 `const STRESS` ↔ data/matchup_sim.json.assumption_stress 대조.

왜 별도 파일인가 (40차 · 2026-08-27):
  `STRESS` 는 sync_tool 이 **가공 없이 통과**시키는 상수라 tool_embed 에 빌더가 없고,
  그래서 `validate.py` 의 동기화 대조 목록에도 아직 없다(A 세션에 편입 요청 중).
  검사 없는 임베드 데이터를 화면에 두지 않기 위해 그때까지 이 파일이 대신 본다.

  🔴 validate.py 에 편입되면 **이 파일을 지울 것.** 두 곳에서 같은 것을 검사하면
     이 저장소가 반복해 당한 「규칙 이중 구현」이 된다.

실행:  python3 tests/check_stress_sync.py     (종료코드 0 = 일치)
"""
import io, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ts = io.open(f"{BASE}/tool/auction-console.html", encoding="utf-8").read()
m = re.search(r"const STRESS=(\{.*?\});\n", ts, re.S)
if not m:
    sys.exit("✗ 툴에 const STRESS 가 없다")
tool = json.loads(m.group(1))
sim = json.load(io.open(f"{BASE}/data/matchup_sim.json", encoding="utf-8")).get("assumption_stress") or {}

if tool != sim:
    print("✗ const STRESS ≠ matchup_sim.json.assumption_stress — sync_tool.py 를 돌리십시오")
    tk, sk = set(tool), set(sim)
    if tk - sk: print("   툴에만:", sorted(tk - sk))
    if sk - tk: print("   데이터에만:", sorted(sk - tk))
    for k in sorted(tk & sk):
        if tool[k] != sim[k]: print(f"   다름: {k}")
    sys.exit(1)

rows = tool.get("rows") or []
print(f"✅ const STRESS 일치 — 코어 {len(rows)}행 · 배율 {tool.get('gp_factor')} · {tool.get('iterations')}시행")
for r in sorted(rows, key=lambda x: x.get("delta", 0)):
    who = " · ".join(a["player"] for a in (r.get("assumptions") or [])) or "없음"
    print(f"   {r['core']}  {r['base']*100:5.1f} → {r['stressed']*100:5.1f}  ({r.get('delta',0)*100:+5.1f}%p)  {who}")
