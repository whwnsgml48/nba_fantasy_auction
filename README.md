# NBA Fantasy 2026-27 · 13캣 옥션 드래프트 준비

Yahoo Fantasy Basketball 사설 리그의 옥션 드래프트 준비 산출물. 리그 세팅 분석 →
선수 가치 평가 → 코어(로스터 구성안) 5종 → 실시간 입찰 보조 툴까지.

작성: 2026-08-19 · 대상 시즌 개막 2026-10-20

---

## 이어서 작업하려면

**`HANDOFF.md`를 먼저 읽으세요** — 콜드 스타트 오리엔테이션, 남은 작업 우선순위,
데이터 모델 불변식, 작업 시 함정(문자열 치환의 조용한 실패 등), 드래프트 당일 런북.

## 현재 상태

⚠️ **코어 플랜은 실전 확정안이 아니라 가설 묶음입니다.** 외부 평가를 받아 6건을 수정했습니다:
계획가가 자체 최대가를 넘던 위반 5건, 대체안 없는 슬롯 25개, `잠금 N캣` 명칭,
툴의 포지션 자격 미강제, 시장가 보정 수단 부재, 문서 숫자 불일치.
상세: `docs/04-audit-log.md` 최하단.

~~가장 큰 미해결 병목은 시장 예상가가 전부 추정치~~ → **2026-08-20 부분 해소.**
작년 옥션 실측(`data/prior_auction_2025_26/`, 120건 전원 식별)을 확보해 곡선을 검증했습니다.

결과 3줄:
- 세팅이 작년 12팀·로스터10 → 올해 **14팀·로스터9**. 돈 +16.7%인데 낙찰 인원 +5%뿐 →
  **상단 가격을 $11~16 싸게 봤음** (1위 재적합 $97 vs 추정 $84)
- 반대로 중하단은 비싸게 봤음 — 실측은 낙찰 인원의 1/4을 $5 이하로 채우는데 우리 모델은 9명뿐
- **센터 시장이 이봉분포**(네임밸류 빅 11명 평균 $56.9 / 그 외 23명 평균 $8.2)로
  코어 7의 전제는 확정. 그런데 **과열 임계값이 두 계층을 섞어놔서 코어 7이 상시 발동**함

상세: `docs/08-prior-auction-calibration.md`. `players.json`에는 **미적용** —
적용하면 코어 5종이 깨집니다(c1·c2·c3·c5·c7). 기본 경로인 **코어 6과 코어 4는 무사**.

## 평가자에게

이 산출물은 **한 번에 만들어진 게 아니라 사용자 지적으로 6차례 크게 뒤집혔습니다.**
평가 시 가장 중요한 문서는 `docs/04-audit-log.md`입니다 — 어떤 오류가 왜 발생했고
어떻게 잡혔는지가 전부 기록돼 있습니다.

**중점적으로 검증해주면 좋은 것:**

0. **`data/stats_2025_26/`가 원본 근거 전체입니다.** `my_max` 값을 여기서 역추적해
   재검증할 수 있습니다. 같은 폴더 `README.md`에 데이터 공백 4종이 정리돼 있습니다.
1. **`docs/05-limitations.md`에 적힌 한계가 정직한지, 더 있는지.**
   ~~시장 예상가는 전부 저자 추정~~ → **2026-08-20 실측 기반으로 교체됨**
   (작년 리그 옥션 120건 재적합 · `docs/08`). 남은 한계는 곡선 *형태*만 실측이고
   선수별 순위는 여전히 우리 평가라는 점입니다.
2. **13캣 구조 분석(`docs/01`)의 논리.** 특히 "TOV와 A/T는 서로 반대 방향 캣이라
   둘 중 하나는 거의 자동으로 내준다"는 핵심 주장.
3. **`노리는 캣` 지표.** 팀 가중치 합 ≥ 6을 "확보"로 정의했는데 이건 임의 기준이고
   "정말 이긴다"는 보장이 아닙니다. 더 나은 모델 제안 환영.
   ⚠️ **13차 감사에서 이 규칙이 실제로 깨져 있음을 확인했습니다** — 7개 코어 전부 선언과
   불일치하고, c1·c4·c5·c6은 PTS를 포기 선언했는데 규칙상 확보(합 9~13)입니다.
   원인은 PTS 엘리트(w3)가 174명 중 41명(24%)이라 규칙이 PTS에서 무의미해진 것입니다.
4. **비율 캣 볼륨 레버리지 계산.** 3PT%는 `docs/03` 하단(가정: 선발 7명·주간 3.5경기·팀 3PA 135),
   A/T는 `docs/07`(가정: 나머지 6명 20.0 AST / 10.0 TOV). 두 가정이 타당한지.
   FG%·FT%는 시도량 데이터가 없어 같은 계산을 못 했습니다.
5. **남은 오류.** 아래 "알려진 오류 패턴 3종"과 같은 유형이 데이터에 더 있을 가능성이 높습니다.

**알려진 오류 패턴 3종** (모두 사용자가 발견, 저자가 아님):
- ①평판을 캣 기여로 착각 — 계약규모·수비상·이름값을 실측 없이 엘리트 가중치로 부여 (22건)
- ②출처 한 줄에 근거한 가격 — 기사의 "타겟 $22~28"을 검증 없이 채택 (Reed Sheppard)
- ③rate만 보고 볼륨 무시 — 비율 캣은 시도량 지분만큼만 레버리지 (17건)

---

## 파일 구조

```
docs/
  01-league-and-format.md   리그 세팅 · 13캣 구조 분석 · 포지션 제약
  02-auction-strategy.md    옥션 수학 · 지명권 룰 악용 · 시장 곡선 추정
  03-player-valuations.md   가치 평가 방법론 · 잉여 상위 · 태우기 명단 (실측 곡선 반영)
  04-audit-log.md           오류 발견·수정 이력 (평가 핵심 문서)
  05-limitations.md         검증 안 된 것 · 알려진 약점
  06-cores.md               코어 7종 + 과열 피벗 + 장기부상 제외 규칙 (전부 데이터 생성)
  07-at-marginal-lift.md    A/T 한계기여 모델 (비율 캣 평가 방법)
  08-prior-auction-calibration.md  ★ 작년 옥션 실측 보정 (곡선 검증·센터 이봉분포·임계값 백테스트)
data/
  players.json              선수 174명 (기계 판독용)
  players.csv               같은 데이터 표 형식
  cores.json                코어 7종 + 피벗 + 판단표 + 과열 임계값 + 앵커정책
  league_settings.json      리그 규칙 · 캣 목록
  stats_2025_26/            ★ 평가의 모든 원본 근거
    README.md               커버리지 · 데이터 공백 4종
    leaderboards.json/.csv  리더보드 9종 · 211행
    player_lines.json/.csv  개별 풀 스탯 34명
    coverage.csv            캣별 매칭률
    unevaluated_...csv      리더보드에 있으나 미평가 12명
tool/
  auction-console.html      실시간 입찰 보조 툴 (오프라인 단일 파일)
  fetch_bbref.py            BBRef 리그 전체 per-game 수집 (2025-26 · 2024-25)
  build_measured.py         BBRef → DB 174명 매칭 · 2시즌 GP 가중 혼합 → measured_full.json
  cat_model.py              캣 평가 단일 소스 (기준선 2종 · 선수/팀 한계기여)
  unify_cat_weights.py      12캣 cat_weights 등급 + cat_baselines **단일 작성자**
  value_model.py            z-score 평가 참고선 (my_max 대조용 · 순위 비교 전용)
  recompute_cores.py        cores.json 파생 필드 전체 재계산
  sync_tool.py              auction-console.html 임베드 상수 7종 재생성
  snapshot_data.py          data/ 스냅샷 + 구조적 diff (커밋 전 필드 단위 요약)
  gen_docs03.py             docs/03 표를 players.json에서 생성 (26차 전환)
  gen_docs06.py             docs/06을 cores.json에서 **전량** 생성 (36차 — 그전엔 생성기가 없었다)
  plant_value_reference.py  value_reference 재산정 (M5·M6 판정 근거)
  divergence_rules.py       M5·M6 판정 규칙 + core_hits 단일 소스
  close_unused_ceilings.py  미사용 천장 기계 종결 (조건 대조로 자동 무효화)
  matchup_sim.py            주간 맞대결 몬테카를로 → data/matchup_sim.json
                            (상대 6종 · 5캣 동시붕괴 P · 최소 승률 maximin)
  track_divergence.py       임계 진입/이탈 비교용 상태 스냅샷
validate.py                 기본 코어 + 피벗 통합 검증기 (불변식 I1~I23 · M1~M6)
HANDOFF.md                  다음 작업자용 인수인계 (여기서 시작)
SOURCES.md                  출처 전체
.gitignore                  __pycache__ · .venv · .DS_Store · data-snapshots
```

## 드래프트 중 판단 순서

> **정상 시장: 코어 6 기본 → Hali 할인 시 코어 1 → SGA 할인 시 코어 3 → 앵커 실패 시 코어 4. 저가 센터 2명 이상 과열: 즉시 코어 7. Jokić·Sabonis는 조건 충족 시에만 별도 진입.**

상세 표와 실시간 판정: `docs/06-cores.md` · 툴 우측 `판단 순서` 카드

## 버전 관리 — git + 스냅샷 2층 (2026-08-26 전환)

저장소: **https://github.com/whwnsgml48/nba_fantasy_auction** (`main`)

2026-08-26에 git 저장소로 전환했습니다. **그 전까지는 저장소가 아니었고
`snapshot_data.py`가 유일한 되돌리기 수단이었습니다.** 이제 역할이 나뉩니다 —
스냅샷 규칙은 폐지된 게 아니라 **적용 구간이 좁아졌습니다.**

| 층 | 수단 | 역할 |
|---|---|---|
| 영구 이력 | `git` | 커밋 단위 되돌리기 · 원격 백업 · 차수 간 비교 |
| 작업 중 | `tool/snapshot_data.py` | **필드 단위 변경 요약** · 커밋 전 셀프 리뷰 |

`players.json`(743KB·174명)과 `cores.json`은 스크립트로 대량 재기록되므로,
커밋하기 전에 **무엇이 바뀌었는지 필드 단위로 확인**해야 합니다.
`data/` 를 건드리기 **전에** 스냅샷을 만들고, 끝나면 diff 요약을 냅니다.

```bash
export SNAPSHOT_ROOT=<scratchpad>/data-snapshots
python3 tool/snapshot_data.py snap "작업명"   # 수정 전
#  ... 작업 ...
python3 tool/snapshot_data.py diff            # 수정 후 요약
python3 tool/snapshot_data.py list            # 스냅샷 목록
```

**`git diff`가 이 스크립트를 대체하지 못하는 이유** (`diff -r`을 쓰지 않았던 이유와 같습니다):
indent=1 JSON은 한 필드가 바뀌어도 텍스트 diff가 수백 줄을 뱉고, 배열 재정렬을 전부
변경으로 잡습니다. 이 스크립트는 경로 단위로 평탄화해 `[*].my_max  10건 (변경 10)` 처럼
**필드별로 묶어** 냅니다. `players.json`은 배열 인덱스가 아니라 선수 이름으로 키를 잡아
재정렬에 면역입니다.

⚠️ scratchpad는 세션 전용입니다 — 스냅샷은 **세션 내** 되돌리기이고, 영구 이력은 이제
git이 담당합니다. **작업이 끝나면 커밋하십시오.** 커밋하지 않고 세션을 닫으면
그 세션의 되돌리기 수단이 함께 사라집니다.

추적 정책: `data/stats_2025_26/bbref/`의 원본 HTML 4.5MB는 **의도적으로 추적합니다** —
`build_measured.py`의 입력이자 평가 사슬의 재현 근거이므로 제외하지 않습니다.

## 재계산 파이프라인

**순서가 중요합니다.** `unify_cat_weights.py`가 `cat_baselines`를 다시 쓰고
`recompute_cores.py`가 그 값을 읽어 팀 한계기여를 내므로, 거꾸로 돌리면
stale 판정이 그대로 통과합니다.

```bash
python3 tool/snapshot_data.py snap "작업명"   # ← 항상 먼저
python3 tool/build_measured.py      # 실측 갱신 (BBRef 원본이 바뀔 때만)
python3 tool/unify_cat_weights.py   # cat_weights 등급 + cat_baselines
python3 tool/recompute_cores.py     # cores.json 파생 필드
python3 tool/sync_tool.py           # 툴 임베드 상수
python3 tool/plant_value_reference.py   # my_max 참고선 (M5·M5b가 이 값을 검사)
python3 tool/gen_docs03.py          # docs/03 표 생성 (산문은 수기 유지)
python3 tool/gen_docs06.py          # docs/06 전량 생성 (코어·피벗·판단표·임계값)
python3 tool/matchup_sim.py 20261020 4000   # 승률 판정 → data/matchup_sim.json
python3 validate.py                 # 위반 0건 확인
python3 tool/track_divergence.py    # M5·M6 진입/이탈 기준선 갱신 (검증기는 읽기만)
python3 tool/snapshot_data.py diff  # 변경 요약
git status                          # 내가 만들지 않은 변경이 있는지 먼저 확인
git add <바뀐 파일들> && git commit  # ← 마지막. 검증 통과 후에만 · **-A/-a 금지**
```

⚠️ **가격 두 필드를 섞지 마십시오** (35차 분리):

| 필드 | 계산 | 용도 |
|---|---|---|
| `bid_ceiling` | `min(my_max, 단일상한, 철수가)` | **부를 최대치** — 불변식 1 · 앵커 여유도 |
| `expected_cost` | `clamp(시장중간, ·, bid_ceiling)` | **예산 계산** — 총액 · 예비비 · 빅맨 상한 |
| `plan_price` | `expected_cost` 별칭 | 툴·기존 검사 하위 호환 |

경매에서 '부르는 값'과 '내는 값'은 다른 숫자입니다. 한 필드로 겸하면 슬롯마다 해석이
갈리고, 총액 하한을 맞추려 **시장 $1-3 선수에게 $8**을 붙이는 일이 생깁니다.
인바리언트 **I23**이 세 관계를 상시 검사합니다(361개 엔트리).

하한 규칙: `예비비 < $4` 위반 · `> $25` 경고(과소 편성) · 초과 $200만 하드 위반.

⚠️ **기준선 3종을 섞지 마십시오** (23차에 실제로 코어가 붕괴했습니다):

| 필드 | 계산 | 용도 |
|---|---|---|
| `baseline` | `cat_model.baselines()` · GP 가중 | **팀** 한계기여 (캣 승패 판정) |
| `baseline_per_game` | `cat_model.baselines_per_game()` · 경기당·비가중 | **선수** 가중치 등급 · M1/M2 · `value_model` |
| ~~MPG≥25 풀 평균~~ | unify의 옛 자체 레시피 | **폐기** (21차에 근거 상실) |

인바리언트 19가 이 값들을 `cat_model` 계산과 직접 대조합니다.

## 검증

```bash
python3 validate.py     # 기본 코어 7종 + 피벗 7종 = 14개 플랜 검증. 위반 0건이면 exit 0
```
검사 항목: 계획가 범위(`market_low ≤ plan_price ≤ my_max`) · 9슬롯 완성 · 포지션 자격 ·
총액 ≤$200 · 빅맨 예산 상한 · 비앵커 대체안 2명 · 선수 중복 · **장기 부상 제외 준수** ·
피벗의 노리는 캣/포기 캣 명시 · 피벗 트리거의 임계값 소스 일치.
**기본 코어 7종 + 과열 피벗 7종 = 14개 플랜, 대체 후보까지 전부 검사합니다.**
백업 로스터는 33차에 c7을 전면 교체하면서 사라졌습니다(구 c7의 백업 · `cores.json.c7_old`에 함께 보존).

## 툴 실행

⚠️ **사용자가 실제로 쓰는 것은 발행된 아티팩트입니다.**
https://claude.ai/code/artifact/e75e441d-63ce-4c8c-a504-9f0ced805dca

`tool/auction-console.html`을 고치는 것만으로는 그 화면이 바뀌지 않습니다.
`sync_tool.py`가 P 배열을 갱신하므로 **데이터만 바뀐 경우에도 재발행이 필요합니다.**
재발행은 Artifact 도구에 위 URL을 `url` 인자로 넘깁니다(같은 URL 유지).
파일은 이미 아티팩트 형식입니다 — `<title>`로 시작하고 doctype/html/head/body 래퍼가 없습니다.

로컬에서 열어볼 때:


```
open tool/auction-console.html
```
외부 의존 없음. 브라우저 localStorage에 로스터 저장. 배포판:
https://claude.ai/code/artifact/e75e441d-63ce-4c8c-a504-9f0ced805dca

## 핵심 수치

| | |
|---|---|
| 리그 | 14팀 · $200 · 로스터 9(선발 7·벤치 2·IL+ 1) · H2H 13캣 |
| 캣 | PTS FG% 3PTM 3PT% FT% REB OREB AST STL BLK DD A/T TOV |
| 리그 전체 지명 | 126명 (14×9) |
| 선수 DB | **174명** · 실측/명시 174명 · 루키 3명(검증 불가) |
| 획득 가능 | **141명** (내 최대가 ≥ 시장 하단) |
| 획득 불가 | **35명** — Wemby·Luka·Cade·Giannis·Tatum·Lillard 등 시장 상단 대부분 |
| 잉여(내 최대가>시장 중간값) | **122명** · 상위 20 중 **12명이 C 자격** |
| 코어 | **7종** · 계획액 $180~187 · 예비비 $13~20 · 각 코어에 구조화 과열 피벗 |
