#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""**로스터 전용 해시** — 「계획이 바뀌었나」와 「파일이 바뀌었나」를 가른다 (2026-09-01 신설).

🔴 왜 — 같은 혼동이 하루에 두 번 났다
```
조율 세션  「Duren 을 반영하면 c3 피벗이 바뀐다」  → 안 바뀌었다. 근거 문구만 달았다
05 세션    cores.json 파일 해시로 재측정 필요를 판정 → 주석만 바뀌어도 해시가 달라진다
```
**파일 해시는 「파일이 바뀌었다」를 잡지 「계획이 바뀌었다」를 못 잡는다.** 이 저장소는
근거 문구를 아주 많이 쓰므로 파일 해시는 거의 항상 달라진다 — 그러면 **매번 재측정하거나,
매번 무시하게 된다.** 둘 다 나쁘다.

무엇을 해싱하나 — **승률에 영향을 주는 것만**
```
포함   base 1순위 9명 · 피벗 final_roster 9명 · 각 칸의 대체 **순서** · 계획가 · 상한
제외   note·why·premise·근거 문구 전부 · 측정 기록 · 감사 주석
```
⚠️ 대체 **순서**를 넣는 이유: 순서가 바뀌면 「1순위를 놓쳤을 때 누구로 가는가」가 바뀐다.
   이름 집합만 해싱하면 승격이 안 잡힌다.
⚠️ 계획가·상한을 넣는 이유: 로스터가 같아도 가격이 바뀌면 조달 판정이 바뀐다.

쓰는 법
    python3 tool/roster_hash.py            # 두 해시를 나란히 찍는다
    from roster_hash import roster_hash    # 다른 도구가 스탬프에 넣는다
"""
import hashlib
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CP = BASE + "/data/cores.json"


def _plan(cj):
    """승률·조달에 영향을 주는 것만 추린 정규 구조."""
    out = []
    for co in sorted(cj["cores"], key=lambda c: c["id"]):
        slots = []
        for s in co["slots"]:
            slots.append([s["slot"],
                          [[c["name"], c.get("plan_price"), c.get("bid_ceiling")]
                           for c in s["candidates"]]])
        piv = []
        for e in ((co.get("pivot_plan") or {}).get("final_roster") or []):
            piv.append([e.get("slot"), e["name"], e.get("plan_price"), e.get("bid_ceiling"),
                        [[a["name"], a.get("plan_price"), a.get("bid_ceiling")]
                         for a in (e.get("alternates") or [])]])
        out.append([co["id"], slots, piv])
    return out


def roster_hash(cj=None):
    cj = cj or json.load(io.open(CP, encoding="utf-8"))
    blob = json.dumps(_plan(cj), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def file_hash():
    return hashlib.sha256(io.open(CP, "rb").read()).hexdigest()[:12]


def stamp():
    """측정 산출물에 붙일 4줄. 두 해시를 **나란히** 찍는 것이 요점이다."""
    return ("── 데이터 스탬프 ──\n"
            "  로스터 해시 %s   ← **이게 바뀌면 재측정한다**\n"
            "  파일 해시   %s   ← 근거 문구만 바뀌어도 달라진다. 재측정 판정에 쓰지 말 것\n"
            "  (cores.json · 로스터 = 1순위·대체 순서·계획가·상한)"
            % (roster_hash(), file_hash()))


if __name__ == "__main__":
    print(stamp())
    if len(sys.argv) > 1:
        prev = sys.argv[1]
        cur = roster_hash()
        print("\n비교 대상 %s → %s : %s"
              % (prev, cur, "🟢 계획 동일 — 재측정 불필요" if prev == cur
                 else "🔴 계획이 바뀌었다 — 재측정 필요"))
