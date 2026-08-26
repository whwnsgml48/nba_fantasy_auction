#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M6 위반 중 **미사용 천장**을 기계로 종결한다. 사람이 사유를 쓰지 않는다.

닫는 조건 (둘 중 하나)
  코어 등장 0회  — 슬롯·후보·피벗·판단표 어디에도 없다. 그 천장으로 입찰할 기회가 없다.
  획득 불가       — my_max < 시장 하단. 그 천장에 도달하기 전에 남이 데려간다.

왜 기계로 닫는가 (28차)
  41건에 사람이 사유를 한 줄씩 쓰는 것은 정렬이 틀린 작업이다. 위 두 조건에 걸린 건은
  **천장이 입찰에 쓰이지 않으므로** 값이 틀렸다는 사실 자체가 무해하다.

자동 무효화가 이 필드의 유일한 가치다
  생성 당시의 core_hits·obtainable을 conditions에 함께 적는다.
  divergence_rules.has_any_basis()가 현재값과 대조해서, 등장이 1회 이상으로 바뀌거나
  획득 가능으로 바뀌면 **이 basis를 무효로 보고 다시 위반으로 띄운다.**
  사람이 쓴 basis(auto 없음)는 그런 검사를 받지 않는다.
"""
import json, io, os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import divergence_rules as DR

FP = f"{BASE}/data/players.json"
pl = json.load(io.open(FP, encoding="utf-8"))
cj = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))

core_hits = DR.hits_fn_for(cj)   # 30차: 상대 로스터 제외 · 단일 구현

pool = DR.pool_names(pl)
closed, skipped, kept = [], [], []

def close(p, rule, field):
    """미사용 천장이면 auto basis를 심는다. **수기 basis는 절대 덮지 않는다.**"""
    hits = core_hits(p["name"])
    reason = DR.unused_ceiling(p, hits)
    if reason is None:
        skipped.append((DR.exposure(p), p["name"], hits, rule)); return False
    existing = p.get(field)
    is_auto = bool((p.get("my_max_basis") or {}).get("auto")) if field == "my_max_basis" \
              else bool(p.get("tag_basis_auto"))
    if existing and not is_auto:
        kept.append((p["name"], rule, field)); return False      # 수기 근거 보존
    meta = {"auto": True, "rule": rule + "/unused_ceiling",
            "generated_by": "tool/close_unused_ceilings.py",
            "conditions": {"core_hits": hits, "obtainable": p["my_max"] >= p["market_low"]},
            "invalidation": ("conditions가 현재값과 달라지면 이 basis는 무효가 되어 다시 위반으로 뜬다 "
                             "(divergence_rules.has_any_basis / has_tag_basis)"),
            "div": DR.div_of(p), "exposure": DR.exposure(p)}
    if field == "my_max_basis":
        p["my_max_basis"] = dict(meta, why=reason)
    else:
        # tag_basis는 문자열 필드다. 조건은 tag_basis_auto에 따로 둔다.
        # ⚠️ 자동 문구는 div를 **인용하지 않는다** — div는 드리프트하는데 M5b가 ±2로
        #    대조하므로, 인용하면 자동 생성물이 스스로 위반을 만든다. M5b는 auto를 건너뛴다.
        p["tag_basis"] = reason + " (자동 생성 — 조건 대조로 무효화됨)"
        p["tag_basis_auto"] = meta
    closed.append((DR.exposure(p), p["name"], DR.div_of(p), hits,
                   p["my_max"] >= p["market_low"], rule))
    return True

for p in DR.m6_violations(pl, pool, core_hits):
    close(p, "M6", "my_max_basis")
# 30차: M5에도 같은 경로. M6에만 있어서 등장 0회인 건에 사람이 tag_basis를 썼다.
for p in DR.m5_violations(pl, core_hits):
    close(p, "M5", "tag_basis")

json.dump(pl, io.open(FP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("기계 종결 %d건 (노출 내림차순):" % len(closed))
for e, n, d, h, ob, rule in sorted(closed, reverse=True):
    print("  [%s] 노출 $%-4d %-24s div %+5d · 등장 %2d회 · %s" % (
        rule, e, n, d, h, "획득가능" if ob else "획득불가"))
print("\n수기 근거 보존(덮지 않음) %d건:" % len(kept))
for n, rule, field in kept: print("  [%s] %-24s %s 유지" % (rule, n, field))
print("\n사람 판단 필요 %d건 (등장>=1 & 획득가능):" % len(skipped))
for e, n, h, rule in sorted(skipped, reverse=True):
    print("  [%s] 노출 $%-4d %-24s 등장 %2d회" % (rule, e, n, h))
