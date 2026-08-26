#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5·M6 임계값 진입/이탈 비교용 상태 스냅샷을 갱신한다. 파이프라인 마지막 단계.

왜 검증기가 아니라 별도 스크립트인가 (27차)
  validate.py가 data/를 쓰면 snapshot diff가 검증 실행마다 오염된다.
  검증기는 이 파일을 **읽기만** 하고, 갱신은 파이프라인 마지막에 여기서 한 번 한다.

왜 상태가 필요한가
  John Collins가 -20 → -19 로 밀려 위반 목록에서 **조용히 사라졌다.**
  해소가 아니라 드리프트다 — 다른 선수의 my_max가 바뀌면 순위가 밀린다.
  (그리고 27차에 my_max 2건을 내리자 -19 → -20 으로 되돌아왔다.)
  이 파일이 있으면 다음 실행에서 "진입/이탈"로 드러난다.
"""
import json, io, os, sys, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))
OUT = f"{BASE}/data/divergence_state.json"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import divergence_rules as DR   # 규칙 단일 소스 (27차)

div = {p["name"]: DR.div_of(p) for p in PL if p.get("value_reference")}
core_hits = DR.hits_fn_for(CJ)   # 30차: 상대 로스터 제외 · 단일 구현

# ⚠️ 30차: 여기서 hits_fn을 안 넘겨서 auto basis 27건이 이 스크립트에서만 무조건 유효했다.
flagged = DR.flagged_names(PL, core_hits)

# 날짜는 인자로 받는다 — 스크립트가 시간을 스스로 읽으면 재현이 깨진다.
at = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
json.dump({"at": at, "m5_threshold": DR.M5_TH, "m6_threshold": DR.M6_TH,
           "flagged": flagged, "div": div,
           "note": "validate.py가 읽어 진입/이탈을 표시한다. 갱신은 이 스크립트만 한다."},
          io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"divergence_state.json 갱신 · {at} · 위반 대상 {len(flagged)}명 · div 기록 {len(div)}명")
