#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""작년 옥션 실측 12팀 로스터를 **실제 상대**로 복원한다 (38차).

## 왜 필요한가 — 목적함수가 순환이었다

`data/matchup_sim.json`을 보면 **7코어 전부 `min_win_rate_vs = ["value_max"]`** 다.
maximin의 최소값이 항상 `value_max` 하나에서 나오고, 그 상대는 **우리 z모델을
최대화해 조립한 팀**이다. 즉 코어 순위 전체가 "우리 모델의 자기 최적해에 대한 성적"으로
정해진다 — 순환이다. `docs/05` 2b-3에 "가치최대는 우리 모델 안에서의 상한이고 현실적
상대가 아니다"라고 경고가 있는데, **그 상대가 목적함수를 단독 지배한다**는 사실은
어디에도 기록돼 있지 않았다.

저장소 안에 진짜 상대가 있다: `data/prior_auction_2025_26/results.json` —
이 리그 사람들이 실제로 짠 12개 로스터다. 합성 상대보다 정보량이 압도적이다.

## ⚠️ 이 상대가 무엇인지 — 오독 금지

**"작년 그 팀이 올해 얼마나 강한가"가 아니다.**
**"이 리그 사람들이 짜는 로스터 유형을 상대로 우리가 얼마나 이기는가"** 다.

작년 낙찰 조합을 **현재 스탯(2시즌 혼합)으로** 평가한다. 그래서:
- 선수 구성은 작년 사람들의 선택이고 (= 이 리그의 드래프트 성향)
- 능력치는 올해 예측치다 (= 우리 코어와 같은 기준)
가격·예산 제약은 작년 것(12팀·로스터10·슬롯당 $20.0)이고 올해는 14팀·로스터9·$22.2라
**같은 사람들이 올해 짜면 다른 팀이 된다.** 성향의 대리 표본으로만 읽어야 한다.

## 보충 규칙
낙찰자 120명 중 상당수가 174명 DB 밖이다. `tool/build_measured.line()`을 **그대로 불러**
BBRef 2시즌 GP 가중 혼합(최근 ×1.5)으로 보충한다 — 규칙을 두 번 구현하면 갈라진다
(27차 M5·M6 이중 구현 사고).

로스터 10명 중 **앞 9명**만 쓴다(올해 로스터 9인). 9명 미만으로 복원된 팀은 버린다.

실행: python3 tool/real_opponents.py     # 복원 현황만 출력. 파일을 쓰지 않는다.
"""
import io, json, os, re, sys, unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE + "/tool")
import cat_model as CM        # noqa: E402
import build_measured as BM   # noqa: E402  — line() 재사용. import 시 파일을 쓰지 않는다.

ROSTER_N = 9    # 올해 로스터. 작년 10명 중 앞 9명만 쓴다


def key(s):
    """이름 정규화. 분음부호·구두점·접미사를 털어낸다.

    ⚠️ results.json의 `name_en`은 분음부호가 없다(Sengun · Doncic · Jokic · Porzingis ·
    Vucevic). 정규화 없이 매칭하면 유니코드가 다른 선수들이 통째로 누락된다.
    `build_measured.nm()`과 같은 규칙을 쓴다.
    """
    return BM.nm(s)


def load_teams():
    r = json.load(io.open(BASE + "/data/prior_auction_2025_26/results.json", encoding="utf-8"))
    return r["teams"], r["meta"]


def build(verbose=False):
    """(rosters, report) — rosters는 {manager: [이름 9개]}.

    이름은 **CM.F 에서 조회 가능한 키**로 돌려준다. DB 밖 선수는 CM.F 에 in-memory로
    주입한다(파일은 쓰지 않는다 — 30·32차 원칙).
    """
    teams, meta = load_teams()
    by_key = {key(n): n for n in CM.F}          # DB 174명(실측 171)
    added, missing, rosters, dropped = {}, [], {}, []

    for t in teams:
        names = []
        for e in t["players"]:
            en = e.get("name_en")
            if not en:
                continue
            k = key(en)
            if k in by_key:                      # DB 안
                names.append(by_key[k]); continue
            if en in added:                      # 이미 보충됨
                names.append(en); continue
            row = BM.line(en)                    # BBRef 보충 — build_measured와 같은 규칙
            if row is None:
                missing.append(en); continue
            added[en] = row
            by_key[k] = en
            names.append(en)
        if len(names) < ROSTER_N:
            dropped.append((t["manager"], len(names)))
            continue
        rosters[t["manager"]] = names[:ROSTER_N]

    CM.F.update(added)                            # in-memory 주입 (파일 무변경)
    report = {
        "teams_total": len(teams),
        "teams_used": len(rosters),
        "teams_dropped": dropped,
        "picks_total": sum(len(t["players"]) for t in teams),
        "matched_in_db": sum(1 for t in teams for e in t["players"]
                             if key(e.get("name_en") or "") in
                             {key(n) for n in json.load(io.open(
                                 BASE + "/data/stats_2025_26/measured_full.json",
                                 encoding="utf-8"))["players"]}),
        "supplemented": len(added),
        "unmatched": sorted(set(missing)),
        "roster_n": ROSTER_N,
    }
    return rosters, report


if __name__ == "__main__":
    R, rep = build()
    print("작년 옥션 12팀 → 실제 상대 복원")
    print("  낙찰 %d건 · DB 매칭 %d명 · BBRef 보충 %d명 · 미매칭 %d명"
          % (rep["picks_total"], rep["matched_in_db"], rep["supplemented"],
             len(rep["unmatched"])))
    print("  사용 팀 %d/%d (로스터 앞 %d명)"
          % (rep["teams_used"], rep["teams_total"], rep["roster_n"]))
    if rep["teams_dropped"]:
        print("  버린 팀: " + ", ".join("%s(%d명)" % d for d in rep["teams_dropped"]))
    if rep["unmatched"]:
        print("  미매칭: " + ", ".join(rep["unmatched"]))
    print()
    for mgr, names in R.items():
        print("  %-6s %s" % (mgr, ", ".join(names)))
