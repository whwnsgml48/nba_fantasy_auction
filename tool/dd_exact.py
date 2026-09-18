#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DD 를 **추정하지 않고 게임로그에서 센다** — 두 시즌을 measured_full 과 같은 가중으로 혼합 (46차).

## 왜 그냥 2025-26 실계수를 쓰면 안 되는가 🔴
조율 세션이 `nba_score/dd_exact_2026.json`(2025-26 95명)을 만들어 줬고 숫자는
**독립 재계산으로 전부 일치**한다(TD ⊆ DD 도 성립). 그런데 그대로 넣으면 안 된다:

  **DD 만 단일 시즌이 되고 나머지 12캣은 두 시즌 혼합으로 남는다.**

그러면 한 캣에서만 혼합의 정규화가 사라진다. 실제로 보고된 「추정기 오차」의 절반 이상이
**추정기 탓이 아니라 시즌 차이**였다:
```
Clingan  혼합스탯 추정 0.318 → 25-26 실계수 0.480   (+11.4 DD/시즌 「오차」로 보고됨)
         그런데 **25-26 스탯**으로 추정하면 0.492 — 실계수와 사실상 같다
Trae     혼합스탯 추정 0.624 → 25-26 실계수 0.200   (−29.7 DD)
         **25-26 스탯** 추정 0.278 — 역시 실계수에 가깝다
같은 시즌끼리 MAE 2.08 DD/시즌 · 혼합↔단일 비교는 3.19 — 차이 1.11 이 시즌 불일치다
```
→ **두 시즌을 다 세서 `build_measured` 와 같은 가중으로 혼합한다.** 그러면 DD 가
   다른 캣과 같은 축 위에 선다.

## 가중 (build_measured.blend 와 동일 · 값을 두 곳에 두지 않으려 상수만 참조)
```
w25 = GP(2025-26) × RECENCY(1.5)      w24 = GP(2024-25)
dd_per_game = (dd25/gp25·w25 + dd24/gp24·w24) / (w25+w24)
```
⚠️ **출장 판정은 게임로그 기준**이다 — `MP` 가 있거나 PTS·REB·AST·FGA 중 하나라도 양수.
   BBRef 시즌표의 GP 와 1~2 경기 다를 수 있다(DNP 표기 차이). 여기서는 **로그 기준으로
   일관되게** 세고, 그 사실을 `gp_gamelog` 로 같이 낸다.
🔴 **덮지 않는다.** `DD_exact` · `dd_source` 를 **신설**하고 `DD` 는 그대로 둔다.
   채택은 7코어 두 세계 측정 뒤에 한 번에 한다(42차 패턴 · `docs/05 §20`).

실행:  python3 tool/dd_exact.py
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_measured as BM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.expanduser("~/personal_work/nba_score/raw/gamelog2")
PEER = os.path.expanduser("~/personal_work/nba_score/dd_exact_2026.json")
SEASON_FILE = {"2025-26": "2026", "2024-25": "2025"}


def count(bbref_id, tag):
    """한 시즌의 (출장수, DD, TD). 로그가 없으면 None."""
    p = "%s/%s_%s.json" % (LOGS, bbref_id, tag)
    if not os.path.exists(p):
        return None
    gp = dd = td = 0
    for g in json.load(io.open(p, encoding="utf-8"))["games"]:
        if not ((g.get("MP") is not None)
                or any((g.get(k) or 0) > 0 for k in ("PTS", "REB", "AST", "FGA"))):
            continue
        gp += 1
        c = sum(1 for k in ("PTS", "REB", "AST") if (g.get(k) or 0) >= 10)
        if c >= 2:
            dd += 1
        if c >= 3:
            td += 1
    return gp, dd, td


def resolve_ids():
    """🔴 **id 를 추측하지 않는다.** 저장소 자체 해석기(`gamelog.player_ids()` +
    `load.norm_name`)를 쓴다 — 조율 세션이 `성5+이름2+01` 로 추측했다가 86명을 놓쳤다
    (접미사가 02·04~07 도 있다). 조율 세션 파일은 **대조용**으로만 쓴다.
    ⚠️ 46차에 상대 로스터 37명을 추가로 받으면서 이 함수가 필요해졌다 — 그들은
       조율 세션 파일에 없어서 거기서 id 를 가져올 수 없다."""
    sys.path.insert(0, os.path.expanduser("~/personal_work/nba_score"))
    import gamelog as G, load
    ids = G.player_ids()
    return {n: ids.get(load.norm_name(n)) for n in ids} , ids, load


def main():
    peer = json.load(io.open(PEER, encoding="utf-8"))["players"]
    sys.path.insert(0, os.path.expanduser("~/personal_work/nba_score"))
    import gamelog as G, load
    IDS = G.player_ids()
    # 🔴 **상대 전용 선수까지 덮어야 한다.** `real_opponents.build()` 가 DB 밖 선수를
    #    `cat_model.F` 에 in-memory 로 주입한다(171 → 199). measured_full 만 돌면
    #    상대 28명이 추정으로 남고, 추정기가 DD 를 과소평가하므로 **우리만 올라간다** —
    #    46차 1차 측정에서 7코어가 전부 오른 것이 그 인공물이었다(우리 95% ↔ 상대 66%).
    import cat_model as CM
    import real_opponents as RO
    RO.build()
    rows = CM.F                    # {이름: 행} · 주입 후 199명
    ours = set(json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",
                                 encoding="utf-8"))["players"])

    out, n_both, n_one, mismatch = {}, 0, 0, []
    for nm in rows:
        bid = (peer.get(nm) or {}).get("bbref_id") or IDS.get(load.norm_name(nm))
        if not bid:
            continue
        a = count(bid, SEASON_FILE["2025-26"])
        b = count(bid, SEASON_FILE["2024-25"])
        if not a and not b:
            continue
        w25 = (a[0] * BM.RECENCY) if a else 0.0
        w24 = b[0] if b else 0.0
        if w25 + w24 == 0:
            continue
        pg = ((a[1] / a[0] * w25 if a and a[0] else 0.0)
              + (b[1] / b[0] * w24 if b and b[0] else 0.0)) / (w25 + w24)
        n_both += bool(a and b)
        n_one += bool(bool(a) ^ bool(b))
        e = {"DD_exact": round(pg, 4), "dd_source": "gamelog_blend",
             "seasons": {"2025-26": ({"gp_gamelog": a[0], "dd": a[1], "td": a[2],
                                      "weight": round(w25, 1)} if a else None),
                         "2024-25": ({"gp_gamelog": b[0], "dd": b[1], "td": b[2],
                                      "weight": round(w24, 1)} if b else None)},
             "blend_share_2025_26": round(w25 / (w25 + w24), 3)}
        if a and nm in peer and peer[nm]["dd_season_2025_26"] != a[1]:
            mismatch.append((nm, a[1], peer[nm]["dd_season_2025_26"]))
        out[nm] = e

    # 🔴 남의 산출물을 검산 없이 쓰지 않는다 — 2025-26 카운트를 대조한다
    print("조율 세션 파일 대조 (2025-26 DD 카운트): 불일치 **%d건**" % len(mismatch))
    for m in mismatch[:5]:
        print("   🔴 %s 내 %d ↔ 상대 %d" % m)
    # TD ⊆ DD
    bad = [n for n, e in out.items()
           for s in e["seasons"].values() if s and s["td"] > s["dd"]]
    print("TD ⊆ DD 불변식: %s" % ("✅" if not bad else "🔴 %s" % bad[:3]))

    covered = len(out)
    miss_ours = [n for n in rows if n in ours and n not in out]
    miss_opp = [n for n in rows if n not in ours and n not in out]
    print("\n커버리지 %d / %d 명 (두 시즌 %d · 한 시즌 %d)" % (covered, len(rows), n_both, n_one))
    print("  우리 풀   %d/%d 커버 · 결측 %d명" % (len(ours) - len(miss_ours), len(ours), len(miss_ours)))
    print("  상대 전용 %d/%d 커버 · 결측 %d명 %s"
          % (len(rows) - len(ours) - len(miss_opp), len(rows) - len(ours), len(miss_opp), miss_opp))
    print("  🔴 **양쪽 커버리지가 비슷해야 비교가 유효하다** — 한쪽만 올라가면 그건 실력이 "
          "아니라 커버리지다(46차에 실제로 겪었다).")

    json.dump({"generated_by": "tool/dd_exact.py",
               "what": ("게임로그에서 DD 를 세어 measured_full 과 **같은 가중**으로 두 시즌 혼합. "
                        "추정기(cat_model.dd_game_prob)를 대체할 후보값이다."),
               "recency": BM.RECENCY,
               "why_blend": ("2025-26 실계수만 쓰면 DD 만 단일 시즌이 되어 나머지 12캣과 축이 "
                             "달라진다. 보고된 「추정기 오차」의 절반 이상이 시즌 차이였다 "
                             "(같은 시즌 MAE 2.08 DD/시즌 ↔ 혼합↔단일 3.19)."),
               "does_not": ["DD 를 덮지 않는다 — DD_exact 를 병기한다",
                            "커버리지 밖 선수를 추정하지 않는다 — dd_source 로 구분한다"],
               "source": "nba_score/raw/gamelog2 (BBRef) · id 는 조율 세션 해석기 결과",
               "peer_crosscheck": {"file": PEER, "mismatches": mismatch},
               "coverage": {"n": covered, "of": len(rows),
                            "both_seasons": n_both, "one_season": n_one,
                            "missing_ours": miss_ours, "missing_opponent_only": miss_opp,
                            "why_symmetry_matters": ("추정기가 DD 를 +1.2/시즌 과소평가하므로 "
                                "실계수 전환은 커버된 쪽을 올린다. 우리 95% ↔ 상대 66% 상태로 "
                                "재면 7코어가 전부 오르는데 그건 실력이 아니라 인공물이다.")},
               "players": out},
              io.open(f"{BASE}/data/dd_exact.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("data/dd_exact.json 기록")


if __name__ == "__main__":
    main()
