# 2025-26 실측 스탯 데이터

선수 가치 평가의 **모든 근거**가 여기 있습니다. 평가자는 이 파일들로 `data/players.json`의
`my_max` 값을 역추적·재검증할 수 있습니다.

## 파일

| 파일 | 내용 |
|---|---|
| `leaderboards.json` / `.csv` | 리더보드 9종 · 211행 |
| `player_lines.json` / `.csv` | 개별 풀 스탯 라인 34명 (15개 필드) |
| `coverage.csv` | 캣별 리더보드 → 선수 DB 매칭률 + 미수록 선수 |
| `unevaluated_leaderboard_players.csv` | 리더보드에 있으나 DB에서 평가 안 된 12명 |

## 리더보드 9종

| 키 | 캣 | 행 | 특기사항 |
|---|---|---|---|
| `blocks_per_game` | BLK | 25 | — |
| `steals_per_game` | STL | 25 | ⚠️ Cason Wallace가 조회 2회에서 2.0/1.9로 다르게 반환 |
| `offensive_rebounds_per_game` | OREB | 25 | 팀 표기는 2025-26 기준 (오프시즌 이적 미반영) |
| `three_point_pct` | 3PT% | 25 | **3PM·3PA 동반** → 볼륨 레버리지 계산의 유일한 근거 |
| `free_throw_pct` | FT% | 25 | **FTA 미제공** → FT% 레버리지는 계산 불가 |
| `assist_turnover_ratio` | A/T | 25 | 4+ APG 자격자가 리그에 25명뿐 |
| `assist_turnover_supplementary` | A/T | 11 | 개별 조회 보충 (저볼륨 A/T 상위자 포함) |
| `points_per_game` | PTS | 25 | ⚠️ SGA 31.1 vs 27.6 출처 불일치 미해소 |
| `double_doubles` | DD | 25 | **경기수 동반** → 출장 리스크 판단 근거 |

전부 리그 상위 25행만. **26위 이하는 출처가 제공하지 않아 확보하지 못했습니다.**

## 캣별 커버리지

| 캣 | 매칭률 | 비고 |
|---|---|---|
| BLK · STL · PTS · DD | 100% | 리더보드 25명 전원 DB에 있음 |
| OREB | 96% | |
| FT% | 88% | |
| 3PT% | 84% | |
| A/T | 80% | 미수록 5명 |

## ⚠️ 알려진 데이터 공백

### 1. 26위 이하 데이터 없음
리더보드가 상위 25행만이라, **26위권 이하 선수의 캣 수치는 "top-25 밖"이라는 사실만 알고
정확한 값은 모릅니다.** 이 때문에 `players.json`에서 다수 선수의 캣 가중치가 실측값이 아니라
"top-25 진입/미진입"의 이진 판정에 근거합니다.

예: Walker Kessler의 BLK를 `1`로 내린 근거는 "블록 top-25 밖"이며, 실제 수치(1.0? 0.7?)는 모릅니다.

### 2. FTA·FGA 미확보
비율 캣 중 **3PT%만 볼륨 레버리지를 계산했습니다.** FT%와 FG%는 시도량 데이터가 없어
정성 판단에 머물렀습니다 (`docs/05-limitations.md` 5번).

### 3. 리더보드 미평가 12명 → **해소 완료**
`unevaluated_leaderboard_players.csv`에 처리 결과가 있습니다. 전원 2026-27 소속을 조사해
선수 DB에 추가했습니다(총 174명).

- **DeMar DeRozan → GSW** ($16, 매수 타겟). `A/T 3.42` 4+APG 그룹 3위 + FT% 86.8%.
  이 포맷에서 A/T와 TOV를 동시에 주는 드문 유형
- 소속 미확인 잔존 2명: Svi Mykhailiuk · Russell Westbrook (DB에는 `—` 표기로 추가)

**파생 발견**: 조사 중 **Damian Lillard(POR, 3년 $42M 복귀)** 가 DB에 없는 것을 확인.
2025-26 전체 결장(아킬레스)이라 리더보드에 없어 정규화 대조로도 색출되지 않았습니다.
같은 이유로 **결장 시즌 선수는 이 방법으로 검출 불가**라는 한계가 있습니다.

### 4. 출처 간 불일치 2건 (미해소)
- **SGA 득점**: StatMuse 31.1 / Yahoo 티어 기사 27.6
- **Cason Wallace 스틸**: 조회 2회에서 2.0 / 1.9

## 재검증 방법

```bash
# 캣별로 가격과 실측이 역행하는 구간 찾기
python3 -c "
import json,csv
pl=json.load(open('../players.json'))
lb=json.load(open('leaderboards.json'))
blk={r[0]:r[2] for r in lb['blocks_per_game']['rows']}
for p in sorted(pl,key=lambda x:-x['my_max']):
    if p['cat_weights'].get('BLK',0)>=2:
        print(p['my_max'], p['name'], blk.get(p['name'],'top-25 밖'))
"
```
