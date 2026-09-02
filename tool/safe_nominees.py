#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""후반 지명용 **「$1에 받아도 손해 아닌 선수」** 후보 풀 (2026-09-02 신설 · 측정만).

왜 필요한가
  지명 규칙이 **순번 로테이션**으로 바뀌면서 **내 차례가 무조건 옵니다**(총 9회).
  거기에 **지명 시 자동 $1 입찰**이 겹치면, 예산이 얇거나 남은 슬롯이 예약돼 있을 때
  차례가 오면 **아무도 안 붙는 선수를 $1에 떠안고 그 슬롯을 잃습니다.**

  `docs/02 §3②` · `docs/12 §7③` · `README` 셋 다 **「미리 3~4명 정해 두라」**고
  지시하는데 **목록이 어디에도 없었습니다.** `tag=dart` 59명은 목록이 아닙니다 —
  당일에 59명 중에서 고르는 것은 안 정해 둔 것과 같습니다.

기준 (사전 등록)
```
시장 상단 ≤ $4        아무도 안 붙을 가격대여야 「$1에 떠안는」 상황이 성립한다
my_max ≥ 시장 상단    떠안아도 우리 평가로 손해가 아니다
획득 가능             injury_exclude 아님
투영 GP ≥ 60          출장이 얇으면 슬롯을 잃는 것과 같다
```

🔴 **후보 산출이지 결정이 아닙니다.** 3~4명 확정은 사람이 합니다 — 기준은 **자격 폭**이고,
   후반에 어느 칸이 비어 있을지 모르므로 한 포지션에 몰리면 안 됩니다.
⚠️ 아무것도 쓰지 않습니다.
"""
import io, json, os, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pos_elig as PE  # noqa: E402

MAX_MARKET, MIN_GP = 4, 60


def main():
    pl = json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))
    rows = []
    for p in pl:
        if p.get("injury_exclude"):
            continue
        if p["market_high"] > MAX_MARKET or p["my_max"] < p["market_high"]:
            continue
        gp = (p.get("measured_source") or {}).get("GP") or 0
        if gp < MIN_GP:
            continue
        rows.append((p["name"], p["market_low"], p["market_high"], p["my_max"],
                     gp, sorted(PE.elig(p))))
    rows.sort(key=lambda r: -r[3])
    print("후반 지명용 「$1에 받아도 손해 아닌 선수」 후보 풀\n")
    print("  기준: 시장 상단 ≤$%d · my_max ≥ 시장 상단 · 획득 가능 · 투영 GP ≥%d"
          % (MAX_MARKET, MIN_GP))
    print("  🔴 분모: 전체 %d명 중 **%d명**\n" % (len(pl), len(rows)))
    cnt = Counter()
    for r in rows:
        for e in r[5]:
            cnt[e] += 1
    print("  포지션 커버: " + " · ".join("%s %d" % (k, cnt[k]) for k in ["PG", "SG", "SF", "PF", "C"]))
    thin = [k for k in ["PG", "SG", "SF", "PF", "C"] if cnt[k] < 10]
    if thin:
        print("  🔴 얇은 포지션: %s — 여기가 후반에 비면 고를 것이 적다" % ", ".join(thin))
    print("\n  %-24s %8s %6s %5s  %s" % ("선수", "시장", "상한", "GP", "자격"))
    for n, lo, hi, mx, gp, e in rows:
        wide = " ◀ 4포지션" if len(e) >= 4 else ""
        print("  %-24s %8s %6d %5.0f  %s%s"
              % (n[:24], "$%d-%d" % (lo, hi), mx, gp, "/".join(e), wide))
    print("\n⚠️ **후보 산출이지 결정이 아니다.** 3~4명 확정은 사람이 한다 —")
    print("   기준은 **자격 폭**이고, 한 포지션에 몰리면 정작 필요한 칸을 못 채운다.")


if __name__ == "__main__":
    main()
