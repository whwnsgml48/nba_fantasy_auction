# 코어 7종 + 과열 피벗 + 판단 순서

> ⚠️ **실전 확정안이 아니라 가설 묶음입니다.** `노리는 캣`은 겨냥하는 캣 목록이며,
> 승리 확률은 별도 지표(`data/matchup_sim.json`의 주간 승률)로 봅니다. 두 개념을 섞지 마십시오.

**이 문서는 `tool/gen_docs06.py`가 `data/cores.json`에서 전량 생성합니다.**
손으로 고치면 다음 생성에 날아갑니다 — 숫자를 바꾸려면 데이터를 바꾸십시오.
검증: `python3 validate.py`

## 판단 순서 (조건부 우선순위)

> **정상 시장: 코어 6 기본 → Hali 할인 시 코어 1 → SGA 할인 시 코어 3 → 앵커 실패 시 코어 4. 저가 센터 2명 이상 과열: 즉시 코어 7. 🔴 **Jokić를 $97 이하로 잡으면 즉시 코어 2 — 실측 88.9%로 전 코어 1위이고 게이트가 열리면 다른 모든 행보다 우선한다.** Sabonis는 조건 충족 시에만 별도 진입.**

| 우선 | 조건 | 선택 | 근거 |
|---|---|---|---|
| **0** | 저가 센터 계층 과열 2명 이상 | **C7** — 중가 센터 전환 (센터 인플레 대응) | ⚠ 코어 6·4의 과열 피벗보다 **먼저** 코어 7로 전환. 센터 시장이 붕괴하면 피벗으로는 부족하다. 판정은 `low_cost_center` 계층의 `overheat_at`(실측 기대치 기반)으로만 한다 — 네임밸류 빅(Şengün·Mobley·Zubac)이 $30~60에 팔리는 것은 정상가이므로 세지 않는다. |
| **1** | 센터 정상가 + KAT ≤ $50 + Hali ≤ $56 | **C1** — KAT 앵커 + Haliburton | Hali가 정말 할인되면 코어 1의 천장이 가장 높다. 임계 $56은 철수가와 같은 값이고, 실측 시장이 $54-66이라 **중간값 아래에서 잡아야** 성립한다 — 할인이 없으면 이 행은 발동하지 않고 기본값 c6로 간다. **실행 조건: Tyrese Haliburton 실낙찰가 <= $56 (철수가)** (실패 시 → c6 (기본값)) |
| **2** | 센터 정상가 + Hali 불확실/비쌈 | **C6** — A/T 분산 조달 (정상 시장 기본값) | 정상 시장의 기본값. Hali가 기대만큼 안 싸거나 아킬레스 복귀 리스크를 피하고 싶으면 여기. |
| **3** | 센터가 조금 비싸지만 SGA ≤ $85 | **C3** — SGA + 저가 빅 4인 | 빅맨 예산 $77(39%)로 7개 코어 중 최저 — 센터가 약간 비싸지는 정도라면 코어 4보다 먼저. |
| **4** | 앵커를 못 잡았지만 센터는 정상가 | **C4** — 무앵커 분산 (상한 $31) | 앵커 실패 시의 안전망. **센터 과열 대응책이 아니다** — 센터가 깨졌으면 코어 7. |
| **조건부 ★** | Jokić ≤ $97 낙찰 → 즉시 코어 2 | **C2** — Jokić 압축 | 🔴 **게이트가 열리면 이 표의 다른 모든 행보다 우선한다** — 실측 88.9% / 최저 74.1% 로 전 코어 1위다(c6 87.5% / 71.6%). 우선순위 표는 '무엇이 강한가'가 아니라 '무엇을 살 수 있는가' 순이라 c2는 조건부에 남지만, **조건이 충족되면 최강이다.** ⏱ **Jokić는 최상위 선수라 드래프트 초반에 지명된다 — 즉 이 게이트의 개폐를 초반에 알게 된다.** 그 시점에 $97 이하로 잡았다면 기본값 c6로 가지 말고 c2로 전환하라. |
| **격리** | Sabonis 프리시즌 정상 복귀 확인 (가격 게이트 없음) | **C5** — Sabonis 부상 할인 (조건부 베팅) | 별도 베팅안. 정상 복귀를 기본값으로 두지 않는다. |

### 판단의 요점

- **센터 시장 붕괴면 코어 7이 무조건 1순위입니다.** 코어 6·4의 *과열 피벗보다 먼저* 전환합니다 —
  피벗은 센터 하나가 비싸질 때의 대응이고, 두 명 이상이면 전제 자체가 깨진 것입니다.
- 34차에 **실행 가능성 제약**(저가 센터 6명을 `overheat_at` 이상으로 강제 매수) 하에서
  재계산한 결과, 그 세계에서 조립 가능한 채택 코어는 **c7 하나뿐**입니다
  (c1 $203 · c6 $209로 예산 초과). 33차의 "우선 0을 c6로" 제안은 이 근거로 철회됐습니다.
- **"승률이 높다"와 "그 로스터를 살 수 있다"는 다른 질문입니다.** 아래 승률표를 읽을 때
  발동 조건이 참인 세계의 가격으로 강제 매수시킨 뒤 총액을 확인하십시오.

툴 우측 `판단 순서` 카드가 이 표를 행별로 **충족 / 불가 / 미정 / 기본값**으로 실시간
판정하고 현재 권장 코어를 강조합니다.

## 장기 부상 제외 규칙

> 개막 후 4주 이상 결장 예상 또는 복귀 일정 불확실 → 코어·대체후보·피벗에서 전면 제외. IL+ 슬롯이 있어도 코어 자산으로 계산하지 않는다. 드래프트 직전 복귀 일정이 명확히 앞당겨질 경우에만 수동 해제.

| 선수 | 사유 |
|---|---|
| **Jimmy Butler III** (GSW) | 🚑 장기 부상 제외 — ACL 파열, 복귀 12월 이후 불확실. 드래프트 직전 일정이 앞당겨지면 수동 해제 |
| **Russell Westbrook** (—) | 🚫 은퇴 — 2026 오프시즌 은퇴. 킹스·위저즈 제안을 거절하고 19번째 시즌을 뛰지 않는다. 드래프트 대상이 아니다 |

## 코어 7 발동 조건 (저가 센터 전제 붕괴)

| 조건 | 판정 |
|---|---|
| **그 외 센터 (저가 계층)** 계층 6명 중 **2명 이상**이 `overheat_at` 초과 | 툴 `판단 순서` 우선 0 자동 발동 |
| 저가 빅맨 **3명 이상**이 계획가 대비 **25% 이상** 상승 | 툴 `시장가 보정` 계수 ×1.25 이상 |
| `big_budget_cap` 지키며 C 자격 2명 + 유효 7캣 빌드 불가 | `빅맨 예산 초과` + `노리는 캣 미달` 동시 |

판정 대상: Donovan Clingan · Rudy Gobert · Jalen Duren · Mitchell Robinson · Deandre Ayton · Mark Williams

> ⚠️ **네임밸류 빅 계층은 판정에 넣지 않습니다.** 이 계층에서 $30~60은 과열이 아니라 정상가다. 코어 7은 '저가 센터 시장 붕괴' 대응책이므로 이 계층의 가격 상승은 전환 근거가 아니다.

> 📌 33차: 목적지 c7은 이제 A1(중가 센터 전환)이다. 기존 c7(반센터)은 c7_old에 보존.

## 과열 임계값 · 2계층 (단일 소스)

과열 임계값의 2계층. 'threshold/walk_away'는 철수 가격(피벗 트리거), 'overheat_at'은 시장 과열 신호(코어 7 전환). 두 개념을 한 필드에 섞어 쓰던 것을 2026-08-20에 분리했다.

### 네임밸류 빅 — 코어 7 **무관**

> 실측 근거: 작년 실측 11명(Wemby·Jokić·Giannis·KAT·Sabonis·Şengün·AD·Mobley·Zubac·Holmgren·Adebayo) 합 $626 = 리그 센터 지출의 77% · 평균 $56.9 · 범위 $29-87

이 계층에서 $30~60은 과열이 아니라 정상가다. 코어 7은 '저가 센터 시장 붕괴' 대응책이므로 이 계층의 가격 상승은 전환 근거가 아니다.

| 선수 | 철수가 | 기대치 | 과열선 | my_max | 근거 |
|---|---|---|---|---|---|
| Alperen Şengün | `> $34` | $26 | `> $32` | $52 | 우리 시장 중간값 $26 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Evan Mobley | `> $30` | $23 | `> $29` | $36 | 우리 시장 중간값 $23 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Ivica Zubac | `> $16` | $11 | `> $14` | $18 | 우리 시장 중간값 $11 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |

### 그 외 센터 (저가 계층) — 판정 대상

> 실측 근거: 작년 실측 23명 합 $188 · 평균 $8.2 · 중앙값 $6 · 87%(20/23)가 $15 이하

코어 7의 전제는 '이름값 없는 생산형 센터를 $10 안쪽에 쓸어담는다'다. 그 경로가 막히는 것이 곧 전환 조건이므로 코어 7 조건은 이 계층에서만 센다.

| 선수 | 철수가 | 기대치 | 과열선 | my_max | 근거 |
|---|---|---|---|---|---|
| Jalen Duren | `> $34` | $27 | `> $34` | $52 | 우리 시장 중간값 $27 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Donovan Clingan | `> $22` | $12 | `> $15` | $38 | 우리 시장 중간값 $12 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Rudy Gobert | `> $18` | $8 | `> $10` | $30 | 우리 시장 중간값 $8 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Mitchell Robinson | `> $16` | $5 | `> $6` | $12 | 우리 시장 중간값 $5 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Deandre Ayton | `> $14` | $5 | `> $6` | $18 | 우리 시장 중간값 $5 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Mark Williams | `> $14` | $7 | `> $9` | $18 | 우리 시장 중간값 $7 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |

### 앵커 (센터 아님) — 코어 7 **무관**

> 실측 근거: Jalen Johnson(F) · Tyrese Haliburton(G) — 센터가 아니므로 센터 시장 온도와 무관

이 두 명은 '시장이 뜨거운가'가 아니라 '앵커를 확보할 수 있는가'를 판정한다. overheat_at 개념 비적용(null).

| 선수 | 철수가 | 기대치 | 과열선 | my_max | 근거 |
|---|---|---|---|---|---|
| Jalen Johnson | `> $58` | $67 | — (앵커) | $56 | 우리 시장 중간값 $67 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Tyrese Haliburton | `> $56` | $60 | — (앵커) | $56 | 우리 시장 중간값 $60 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Karl-Anthony Towns | `> $55` | $45 | — (앵커) | $71 | 우리 시장 중간값 $45 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |
| Derrick White | `> $44` | $39 | — (앵커) | $52 | 우리 시장 중간값 $39 (39차 ③안). **작년 실낙찰가 × 1.117을 쓰지 않는다** — 작년 가격은 프리시즌 기대치라 개별 선수 가격 판정에 쓰면 '기대 vs 결과'를 재게 된다(docs/08 §0). 계층 판정(docs/08 ③ 이봉분포)에는 여전히 유효하다. |

## 앵커 여유 정책 (단일 소스)

앵커 여유 정책 (2026-08-20 신설). 이전에는 '앵커는 대체후보 면제 · 실패 시 코어 전환'이 서술로만 있어 검증되지 않았다.

| 정의 | 내용 |
|---|---|
| `bid_ceiling` | my_max. 이 값 위로는 어떤 경우에도 부르지 않는다 |
| `nominal_margin` | my_max − 계획가 |
| `effective_headroom` | min(my_max, 계획가 + 코어 예산여유) − 계획가. 예산 여유가 없으면 명목 여유는 허구다 |
| `constraint` | none = 여력 있음 · budget = 예산이 병목 · my_max = 평가가 병목(예산으로 해결 불가) |
| `dual_world_ok` | 현 시장추정과 재적합(실측 기반) 양쪽에서 my_max ≥ 시장하단 |

### 핵심: 명목 여유는 예산 여유가 없으면 허구다

`my_max`가 계획가보다 높아도 코어에 남는 돈이 없으면 더 부를 수 없습니다.
그래서 **명목 여유가 아니라 실효 여유(`effective_headroom`)로 판정**합니다.

### 앵커 12개 현황

| 코어 | 슬롯 | 앵커 | 계획 | 상한 | 명목 | 실효 | 제약 | 실패 시 | 실측곡선 |
|---|---|---|---|---|---|---|---|---|---|
| C1 | C | Karl-Anthony Towns | $45 | $71 | $26 | **$12** | `budget` | 치환 → Jalen Duren | 획득 가능 |
| C1 | PG | Tyrese Haliburton | $56 | $56 | $0 | **$0** | `my_max` | 치환 → Josh Giddey | 획득 가능 |
| C2 | C | Nikola Jokić | $97 | $97 | $0 | **$0** | `my_max` | **코어 전환 → C6** | 획득 가능 |
| C2 | SG | Derrick White | $39 | $52 | $13 | **$8** | `budget` | 치환 → Trey Murphy III | 획득 가능 |
| C3 | SG | Shai Gilgeous-Alexander | $85 | $85 | $0 | **$0** | `my_max` | **코어 전환 → C4** | 획득 가능 |
| C5 | PG | Tyrese Haliburton | $56 | $56 | $0 | **$0** | `my_max` | 치환 → Josh Giddey | 획득 가능 |
| C5 | PF | Domantas Sabonis | $19 | $34 | $15 | **$14** | `budget` | **코어 전환 → C6** | 획득 가능 |
| C6 | C | Karl-Anthony Towns | $45 | $71 | $26 | **$9** | `budget` | 치환 → Jalen Duren | 획득 가능 |
| C6 | SG | DeMar DeRozan | $8 | $16 | $8 | **$8** | `none` | 치환 → Dennis Schröder | 획득 가능 |
| C6 | PG | Derrick White | $39 | $52 | $13 | **$9** | `budget` | 치환 → T.J. McConnell | 획득 가능 |
| C7 | C | Karl-Anthony Towns | $45 | $71 | $26 | **$16** | `budget` | 치환 → Jalen Duren | 획득 가능 |
| C7 | PG | Derrick White | $39 | $52 | $13 | **$13** | `none` | 치환 → Josh Giddey | 획득 가능 |

### 규칙 (`validate.py`가 검사)

1. 모든 앵커는 on_fail을 선언한다 — substitute(코어 내 치환) 또는 switch_core(코어 전환)
2. on_fail=substitute는 이중세계 유효 대체후보가 1명 이상일 때만 허용
3. on_fail=switch_core의 목적지는 존재하는 다른 코어이며 같은 앵커에 의존하지 않아야 한다
4. 재적합에서 획득 불가 + 대체 0명인 앵커를 가진 코어는 conditional_on_discount를 선언한다
5. 피벗·백업 로스터도 이중세계 유효해야 하며, 아니면 이중세계 유효 대체후보를 갖는다

## 요약표

35차에 `plan_price` 한 필드가 세 가지 뜻(입찰 상한 · 기대 지출 · 입찰 목표)을
겸하던 것을 쪼갰습니다. 이 문서의 **계획가는 `expected_cost`(기대 낙찰가)** 이고,
경매장에서 **부를 수 있는 최대치는 `bid_ceiling`** 입니다 — 두 숫자는 다릅니다.

| 필드 | 계산 | 뜻 |
|---|---|---|
| `bid_ceiling` | `min(my_max, 단일상한, 철수가)` | **부를 최대치** |
| `expected_cost` | `clamp(시장중간, ·, bid_ceiling)` | **예산 계산용 기대 낙찰가** |
| `plan_price` | `expected_cost` 별칭 | 툴·기존 검사 하위 호환 |

예비비 = `$200 − 계획총액`. 앵커 한 명이 시장 상단까지 올라가면 예산이 넘으므로
**남겨두는 돈**입니다(34차 · 불변식 I22). 목표 ≥$12 · 경고 <$8 · 위반 <$4 ·
$25 초과는 "과소 편성"(로스터가 예산을 못 씀) 경고입니다.

| | 코어 | 계획 | 예비비 | 빅맨/상한 | C자격 | 노리는 캣 | 포기 | 승리 캣 | 피벗 총액 |
|---|---|---|---|---|---|---|---|---|---|
| c1 | KAT 앵커 + Haliburton | $188 | $12 | $93/$115 | 5 | 10개 | 3PM, FT%, TOV | **10**/13 | $180 |
| c2 | Jokić 압축 | $192 | $8 | $127/$153 | 5 | 13개 | — | **13**/13 | $183 |
| c3 | SGA + 저가 빅 4인 | $196 | $4 | $57/$85 | 4 | 9개 | 3P%, 3PM, FT%, TOV | **9**/13 | $183 |
| c4 | 무앵커 분산 (상한 $31) | $186 | $14 | $84/$107 | 4 | 8개 | 3P%, 3PM, A/T, FT%, TOV | **8**/13 | $193 |
| c5 | Sabonis 부상 할인 (조건부 베팅) | $186 | $14 | $70/$96 | 5 | 9개 | 3PM, FT%, PTS, TOV | **9**/13 | $184 |
| c6 | A/T 분산 조달 (정상 시장 기본값) | $191 | $9 | $79/$113 | 3 | 9개 | 3P%, 3PM, FT%, TOV | **9**/13 | $188 |
| c7 | 중가 센터 전환 (센터 인플레 대응) | $184 | $16 | $107/$130 | 5 | 9개 | 3P%, A/T, FT%, TOV | **9**/13 | $185 |

## 주간 승률 (몬테카를로)

상대 6종에 대해 주 단위 표본을 뽑아 낸 **주간 승률**입니다(30·32차 · `tool/matchup_sim.py`).
목적함수는 **maximin** — 상대 6종 중 **최저** 승률, 동률이면 빅5 동시붕괴 확률이 낮은 쪽.

⚠️ `data/matchup_sim.json`의 `objective.note`: **"값만 산출한다. 이 지표로 코어를 고르지 않는다(32차)."**
같은 3% 마진이 캣에 따라 승률 52~66%라 "이기는 캣 수"만으로는 강약을 못 가립니다.
반대로 승률만 보고 고르면 34차처럼 **조립 불가능한 로스터**를 1등으로 뽑습니다.

시행 6000회 · seed 20261020 · 승리선 7캣

| 코어 | 무작위 | 가치최대 | 빅스택 | 가드스택 | 기준선 | 벤치마크 | **최소** | 최소 상대 | 빅5붕괴 |
|---|---|---|---|---|---|---|---|---|---|
| c1 | 92.3% | 38.7% | 46.9% | 56.2% | 90.7% | 52.9% | **38.7%** | 가치최대 | 41.0% |
| c2 | 93.5% | 38.0% | 44.6% | 62.1% | 92.8% | 47.5% | **38.0%** | 가치최대 | 64.5% |
| c6 | 93.7% | 36.7% | 45.6% | 58.2% | 93.0% | 45.2% | **36.7%** | 가치최대 | 61.3% |
| c7 | 92.2% | 34.7% | 43.7% | 55.8% | 90.2% | 53.1% | **34.7%** | 가치최대 | 38.5% |
| c5 | 90.8% | 31.5% | 40.2% | 53.1% | 87.8% | 44.2% | **31.5%** | 가치최대 | 39.6% |
| c3 | 89.8% | 30.4% | 43.2% | 58.9% | 88.9% | 44.4% | **30.4%** | 가치최대 | 48.2% |
| c4 | 91.2% | 29.9% | 37.2% | 54.8% | 88.7% | 44.6% | **29.9%** | 가치최대 | 44.8% |

빅5 = REB · OREB · BLK · FG% · DD (동시에 지면 빅맨 전략 자체가 무너지는 묶음). p_big5_collapse는 캣별 승률의 곱이 아니다 — 같은 시행에서 REB·OREB·BLK·FG%·DD 5캣이 **동시에** 패한 횟수를 직접 셌다. 무승부는 패로 세지 않는다.

---

## 코어 1 · KAT 앵커 + Haliburton

**우선 1** — 센터 정상가 + KAT ≤ $50 + Hali ≤ $56

> 잉여가 $50 이상 구간에서 시장을 앞서는 선수는 KAT 하나뿐(+$16). A/T는 Haliburton 단독(한계기여 +0.517, 리그 1위)으로 조달. 아킬레스 복귀 리스크를 감수하는 조건부 플랜이며, 회피하려면 코어 6.

**계획 $188** · 예비비 **$12** · 빅맨 $93/$115 (C자격 5명) · 노리는 캣 10개 `3P% A/T AST BLK DD FG% OREB PTS REB STL` · 포기 `3PM FT% TOV`

**주간 승률** 최소 **38.7%** (vs 가치최대) · 빅5 동시붕괴 41.0% · 기대 승리 캣 8.95

> **채택 근거** — 33차: B-c1-2 채택 — BN McConnell $2 → VJ Edgecombe $5. 최소 승률 31.9% → 39.2% · 보수 57.5% → 61.7% · 빅5붕괴 49.1% → 42.8%. ⚠️ **조건부**: 이 수치는 Haliburton(시장 $54-66 · my_max $50)을 $50 이하에 잡는 세계에서만 존재한다. 이전 후보: ['T.J. McConnell', 'Andrew Nembhard', 'Davion Mitchell']

> **예비비 구성** — 34차: 예비비 제약(>=$12)을 **재가격만으로** 달성. 전 슬롯을 min(시장중간, my_max)로 재가격 → 총액 $190 → $182 · 예비비 $10 → $18. 로스터 교체 없음. 앵커 Haliburton은 mid $60 > my_max $50이므로 $50 유지(조건부 상태 그대로).

### 기본 플랜

| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|---|
| **C** `앵커` | $45 | $55 | **$12** (실패→치환 Jalen Duren) | 앵커 · DD 56 리그 1위 | **Karl-Anthony Towns** `C` | Jalen Duren $27 | Alperen Şengün $26 |
| **PG** `앵커` | $56 | $56 | **$0** (실패→치환 Josh Giddey) | A/T +0.517 리그 1위 · TOV 동시 | **Tyrese Haliburton** | Josh Giddey $41 | De'Aaron Fox $24 |
| **PF** | $26 | $34 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** `C` | Evan Mobley $23 | — |
| **SF** | $22 | $33 | — | 3PT% 레버리지 2위 · 3PM 3.4 | **Kon Knueppel** | Desmond Bane $22 | Toumani Camara $11 |
| **SG** | $12 | $20 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $3 | Cason Wallace $3 |
| **UTIL** | $12 | $22 | — | OREB 4.5 리그 1위 · 77G | **Donovan Clingan** `C` | Rudy Gobert $8 | Mitchell Robinson $5 |
| **UTIL** | $8 | $18 | — | OREB+BLK+DD 빅 | **Rudy Gobert** `C` | Ivica Zubac $11 | Mark Williams $7 |
| **BN** | $5 | $9 | — | B-c1-2 채택 — 저가 다트 교체 (McConnell 대체) | **VJ Edgecombe** | T.J. McConnell $2 | Andrew Nembhard $2 |
| **BN** | $2 | $6 | — | OREB 3.7 다트 | **Moussa Diabaté** `C` | Andre Drummond $2 | Day'Ron Sharpe $2 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Rudy Gobert > $18`

> 저가 OREB 경로가 막히면 OREB 완전 장악을 포기하고 REB·DD만 지킨다. 빅맨을 5명→4명($78)으로 줄이고 절감분을 3P%·FT% 윙으로 옮긴다. 두 명 이상 과열이면 코어 7로 전환.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| UTIL | Donovan Clingan → **Nikola Vučević** | $2 | -10 |
| UTIL | Rudy Gobert → **Onyeka Okongwu** | $5 | -3 |
| BN | Moussa Diabaté → **Cameron Johnson** | $7 | +5 |
| SF | Kon Knueppel → **Desmond Bane** | $22 | +0 |
| C | Karl-Anthony Towns → **Karl-Anthony Towns** | $49 | +4 |

**피벗 최종 9인** — 총액 $180 · 예비비 $20 · 빅맨 $78 (C자격 4명) · 노리는 캣 `3P% 3PM A/T AST BLK DD FG% FT% OREB PTS REB STL` · 포기 `TOV`

| 슬롯 | 선수 | 계획가 | 상한 |
|---|---|---|---|
| C | Karl-Anthony Towns `C` | $45 | $55 |
| PG | Tyrese Haliburton | $56 | $56 |
| PF | Alperen Şengün `C` | $26 | $34 |
| SF | Desmond Bane | $22 | $31 |
| SG | Dyson Daniels | $12 | $20 |
| UTIL | Nikola Vučević `C` | $2 | $8 |
| UTIL | Onyeka Okongwu `C` | $5 | $10 |
| BN | VJ Edgecombe | $5 | $9 |
| BN | Cameron Johnson | $7 | $10 |

---

## 코어 2 · Jokić 압축

**우선 조건부 ★** — Jokić ≤ $97 낙찰 → 즉시 코어 2

> Jokić 한 칸이 빅맨 캣(REB 12.8 · OREB 3.0 · DD)과 가드 캣(AST 10.5 · A/T +0.241)을 동시에 주므로, 나머지 8칸을 **전부 시장 저평가 구간**에서 채운다. $39 Derrick White 하나만 중가이고 $22 Bane 아래로는 전원 $12 이하다.

🔴 **39차에 base를 전면 교체했다.** 구 c2(Şengün·Gobert·THJ·Nembhard·Merrill)는 실측 79.2%로 7코어 최하위였다. 실제 12팀 목적함수로 재탐색해 **89.3% / 최저 75.0%** 안을 얻었고 평가 세션이 독립 재현(3시드 전부 c6 초과)으로 승인했다. **공식 시뮬 재실행(6000시행 · seed 20261020) 결과 88.9% / 최저 74.1% 로 전 코어 1위다** — c6 87.5% / 71.6%. 다만 조건부이므로 기본값은 여전히 c6다.

이 코어는 **KAT를 쓰지 않는다** — KAT가 과열되는 세계에서 쓸 수 있는 두 번째 갈래다.

**계획 $192** · 예비비 **$8** · 빅맨 $127/$153 (C자격 5명) · 노리는 캣 13개 `3P% 3PM A/T AST BLK DD FG% FT% OREB PTS REB STL TOV` · 포기 `—`

**주간 승률** 최소 **38.0%** (vs 가치최대) · 빅5 동시붕괴 64.5% · 기대 승리 캣 9.30

> **예비비 구성** — 34차: 예비비 제약(>=$12) 적용. 전 슬롯을 min(시장중간, my_max)로 재가격($199→$181)하고 BN Andre Drummond $2 → DeMar DeRozan $8로 교체($187 · 예비 $13). 최소 승률 16.0% → 25.7% · 보수 혼합 41.5% → 50.6%. 앵커 Jokić는 my_max $88 < 시장 하단 $93이라 **조건부 코어 상태는 그대로**다 — 이 수치는 Jokić 할인 세계의 값이다.

### 기본 플랜

| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|---|
| **C** `앵커` | $97 | $97 | **$0** (실패→C6) | 앵커 · REB 12.8 · AST 10.5 · A/T +0.241 · 빅맨/가드 캣 동시 보유 | **Nikola Jokić** `C` | — | — |
| **SG** `앵커` | $39 | $44 | **$8** (실패→치환 Trey Murphy III) | 3PM 3.0 (3PA 8.6) · BLK 1.2 · A/T w3 | **Derrick White** | Trey Murphy III $32 | Nickeil Alexander-Walker $22 |
| **SF** | $22 | $31 | — | FT% 90.3% w3 · 7캣 폭 · PTS 19.8 — 3PT 스페셜리스트가 아니다 | **Desmond Bane** | DeMar DeRozan $8 | OG Anunoby $14 |
| **PF** | $5 | $10 | — | $5 빅 · BLK 1.0 · OREB 2.3 · FG% 51.5% | **Onyeka Okongwu** `C` | Jaden McDaniels $5 | Royce O'Neale $2 |
| **PG** | $2 | $4 | — | $2 가드 · 3P% 40.8% w3 · A/T w2 | **Collin Gillespie** | Cason Wallace $3 | Jordan Goodwin $2 |
| **UTIL** | $12 | $22 | — | 저가 센터 · OREB 4.0 · BLK 1.7 · REB 10.2 | **Donovan Clingan** `C` | Myles Turner $14 | Brook Lopez $2 |
| **UTIL** | $11 | $16 | — | 저가 센터 · FG% 61.4% w3 · REB 11.7 · OREB 3.6 | **Ivica Zubac** `C` | Kel'el Ware $2 | Rui Hachimura $2 |
| **BN** | $2 | $8 | — | $2 빅 · REB 9.1 · 3PM 1.7 보유 센터 | **Nikola Vučević** `C` | Brook Lopez $2 | Andrew Wiggins $2 |
| **BN** | $2 | $5 | — | $2 가드 · A/T w3 · 3PM 2.5 | **Immanuel Quickley** | Cason Wallace $3 | Royce O'Neale $2 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Ivica Zubac > $16`

> 🔴 **빠진 예산을 채우는 것이 아니라 그 슬롯에서 최선을 다시 고른다**(39차 원칙). base의 유일한 얇은 캣이 STL(+0.100)이고, 저가 센터 두 칸이 과열되면 REB·OREB·BLK는 Jokić·Okongwu·Vučević로 이미 과잉이다. 그래서 한 칸을 **STL 실측 1위 Dyson Daniels(2.4)** 로 돌려 얇은 캣을 두껍게 하고, 다른 칸은 같은 기능의 최저가 센터 **Kel'el Ware $2**(OREB 2.4 · BLK 1.1 · FG% 53.9%)로 대체한다. $2~5 잡부로 때우지 않는다.

실측(4000시행 · 실제 12팀): **87.9% / maximin 40.0%** · 총액 $183 · 예비비 $17. 구 c2 피벗은 56.3%(최저 36.9%)로 14개 플랜 중 유일한 30%대였다. 차선 Gobert·DeRozan은 maximin 41.5%로 더 높지만 평균 87.3%로 낮아, 1차 지표(실제 12팀 평균)에 따라 Daniels·Ware를 채택했다.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| UTIL | Donovan Clingan → **Dyson Daniels** | $12 | +0 |
| UTIL | Ivica Zubac → **Kel'el Ware** | $2 | -9 |

**피벗 최종 9인** — 총액 $183 · 예비비 $17 · 빅맨 $106 (C자격 4명) · 노리는 캣 `3P% 3PM A/T AST BLK DD FG% FT% OREB PTS REB STL TOV` · 포기 `—`

| 슬롯 | 선수 | 계획가 | 상한 |
|---|---|---|---|
| C | Nikola Jokić `C` | $97 | $97 |
| SG | Derrick White | $39 | $44 |
| SF | Desmond Bane | $22 | $31 |
| PF | Onyeka Okongwu `C` | $5 | $10 |
| PG | Collin Gillespie | $2 | $4 |
| UTIL | Dyson Daniels | $12 | $20 |
| UTIL | Kel'el Ware `C` | $2 | $4 |
| BN | Nikola Vučević `C` | $2 | $8 |
| BN | Immanuel Quickley | $2 | $5 |

---

## 코어 3 · SGA + 저가 빅 4인

**우선 3** — 센터가 조금 비싸지만 SGA ≤ $85

> 가드가 FG% 55.1% + FT% 87.9%. 빅맨 예산 $77(계획 총액의 39%)로 6개 코어 중 최저 — 빅맨 시장 과열에 가장 강하다. ⚠️ 'SGA의 FT%가 빅맨 FT% 붕괴를 상쇄한다'는 주장은 FTA 볼륨 데이터가 없어 검증되지 않았습니다. SGA 득점은 출처 충돌(StatMuse 31.1 / Yahoo 27.6)이 있어 리더보드값을 채택했습니다.

**계획 $196** · 예비비 **$4** · 빅맨 $57/$85 (C자격 4명) · 노리는 캣 9개 `A/T AST BLK DD FG% OREB PTS REB STL` · 포기 `3P% 3PM FT% TOV`

**주간 승률** 최소 **30.4%** (vs 가치최대) · 빅5 동시붕괴 48.2% · 기대 승리 캣 8.71

> **예비비 구성** — 34차: 예비비 제약(>=$12) 적용. 재가격만으로는 $176이 되어 **하한 $180 미달**이었다. BN Mark Williams $7 → Damian Lillard $14로 교체($183 · 예비 $17). 최소 승률 21.0% → 32.7% · 보수 혼합 53.1% → 59.5%. ⚠️ Lillard의 가중치 근거는 **2024-25 폴백**이고 아킬레스 복귀다(docs/05 1.7). 차선: Sam Merrill → LeBron James(최소 29.7% · 보수 60.3% · 예비 $12) · Sam Merrill → DeMar DeRozan(최소 29.0% · 예비 $18 · 특별 리스크 플래그 없음). 앵커 SGA는 my_max $72 < 시장 하단 $81이라 조건부 코어 상태 그대로다.

### 기본 플랜

| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|---|
| **SG** `앵커` | $85 | $85 | **$0** (실패→C4) | 앵커 (실패 시 코어 전환) | **Shai Gilgeous-Alexander** | — | — |
| **PF** | $26 | $34 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** `C` | Evan Mobley $23 | — |
| **SF** | $26 | $49 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $11 | Jaden McDaniels $5 |
| **PG** | $12 | $20 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $3 | Cason Wallace $3 |
| **C** | $12 | $22 | — | OREB 4.5 리그 1위 · 77G | **Donovan Clingan** `C` | Jalen Duren $27 | Rudy Gobert $8 |
| **UTIL** | $11 | $16 | — | DD 24 · 롤맨 빅 | **Ivica Zubac** `C` | Mitchell Robinson $5 | Deandre Ayton $5 |
| **UTIL** | $8 | $18 | — | OREB 3.9 · BLK 1.6 · 76G | **Rudy Gobert** `C` | Mark Williams $7 | Nic Claxton $4 |
| **BN** | $14 | $14 | — | 3PM·FT%·AST 3종 엘리트 — ⚠ 아킬레스 복귀 · 가중치 근거는 2024-25 · 대체는 저가 센터라 이 3종을 잃고 OREB·FG%로 바뀐다 | **Damian Lillard** | Deandre Ayton $5 | Neemias Queta $2 |
| **BN** | $2 | $8 | — | 3PT% 레버리지 3위 | **Sam Merrill** | AJ Green $2 | Isaiah Joe $2 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Rudy Gobert > $18` · `Ivica Zubac > $16`

> 저가 센터 3명(Clingan·Gobert·Zubac)이 전부 과열되면 '저가 빅 4인' 전제가 무너진다. 센터 자리를 **최저가 3명**(Vučević $2 · Myles Turner $14 · Jay Huff $2)으로 갈아타 REB·BLK·FG%의 바닥만 지키고, 남는 돈은 SGA 앵커($79)를 지키는 데 쓴다. ⚠️ 이전 피벗은 **트리거 선수인 Zubac을 $11에 그대로 사고 있었다** — 트리거가 걸린 세계에 존재하지 않는 가격이다. 함께 총액도 $196(예비 $4)이라 앵커가 흔들리면 대응 여력이 없었다. 재탐색(실행 가능 조합 1,577,375개 중 프리필터 상위 30개 시뮬 · 6000시행 재대조) 결과 최소 승률 32.1% → **34.9%** · 빅5 동시붕괴 68.1% → **66.0%** · 예비비 $4 → 밴드 내로 개선됐다.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| C | Donovan Clingan → **Nikola Vučević** | $2 | -10 |
| UTIL | Ivica Zubac → **Myles Turner** | $14 | +3 |
| UTIL | Rudy Gobert → **Jay Huff** | $2 | -6 |
| BN | Sam Merrill → **Isaiah Joe** | $2 | +0 |

**피벗 최종 9인** — 총액 $183 · 예비비 $17 · 빅맨 $44 (C자격 4명) · 노리는 캣 `3P% 3PM A/T AST BLK DD FG% FT% OREB PTS REB STL TOV` · 포기 `—`

| 슬롯 | 선수 | 계획가 | 상한 |
|---|---|---|---|
| SG | Shai Gilgeous-Alexander | $85 | $85 |
| PF | Alperen Şengün `C` | $26 | $34 |
| SF | Amen Thompson | $26 | $49 |
| PG | Dyson Daniels | $12 | $20 |
| C | Nikola Vučević `C` | $2 | $8 |
| UTIL | Myles Turner `C` | $14 | $18 |
| UTIL | Jay Huff `C` | $2 | $4 |
| BN | Damian Lillard | $14 | $14 |
| BN | Isaiah Joe | $2 | $10 |

---

## 코어 4 · 무앵커 분산 (상한 $31)

**우선 4** — 앵커를 못 잡았지만 센터는 정상가

> 잉여가 $8~31 구간에 몰려 있으므로 그 구간만으로 9칸을 채운다. 최고가 $31로 결장 리스크가 분산되고 앵커 실패에 면역 — 앵커를 못 잡았을 때의 안전망이다. ⚠️ PTS·TOV 포기가 실제로 나머지 7캣 승리로 이어지는지는 검증되지 않았다.

**계획 $186** · 예비비 **$14** · 빅맨 $84/$107 (C자격 4명) · 노리는 캣 8개 `AST BLK DD FG% OREB PTS REB STL` · 포기 `3P% 3PM A/T FT% TOV`

**주간 승률** 최소 **29.9%** (vs 가치최대) · 빅5 동시붕괴 44.8% · 기대 승리 캣 8.53

> **예비비 구성** — 34차: 예비비 제약(>=$12). 재가격만으로는 $158(하한 미달)이라 업그레이드가 필수였다. BN T.J. McConnell → **Trae Young** · 총액 $186 · 예비 $14. 최소 승률 20.9% → 30.1% · 보수 혼합 56.5% · 빅5붕괴 44.6%.
⚠️ 900시행 탐색 1위는 Julius Randle → Derrick White(28.0%)였으나 **6000시행 재측정에서 26.7%로 3위**가 됐다. Trae Young안은 900시행 26.6% → 6000시행 30.1%. c6에서 배운 승자의 저주를 이번엔 사전에 걸러냈다.

### 기본 플랜

| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|---|
| **C** | $27 | $31 | — | OREB 3.8 · DD 41 · 70G | **Jalen Duren** `C` | Donovan Clingan $12 | Ivica Zubac $11 |
| **PF** | $26 | $31 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** `C` | Evan Mobley $23 | — |
| **SF** | $26 | $31 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $11 | Jaden McDaniels $5 |
| **UTIL** | $23 | $30 | — | OREB+BLK+DD | **Evan Mobley** `C` | Walker Kessler $16 | — |
| **SG** | $22 | $31 | — | 3PT% 레버리지 2위 · 3PM 3.4 | **Kon Knueppel** | Desmond Bane $22 | Sam Merrill $2 |
| **UTIL** | $12 | $20 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $3 | Cason Wallace $3 |
| **BN** | $8 | $18 | — | OREB 3.9 · 76G | **Rudy Gobert** `C` | Mark Williams $7 | Mitchell Robinson $5 |
| **BN** | $12 | $18 | — | PTS+REB+DD 포워드 | **Julius Randle** | Paul George $8 | Josh Hart $4 |
| **PG** | $30 | $30 | — | AST 10.8 · A/T +0.169 · FT% 엘리트 PG — 대체(Schröder·Nembhard)는 FT%가 w1로 내려간다 | **Trae Young** | Dennis Schröder $5 | Andrew Nembhard $2 |

### 과열 피벗

**트리거**: `Evan Mobley > $30` · `Rudy Gobert > $18`

> 상한 $31을 유지한 채 UTIL 한 칸을 빅맨에서 윙(Bane)으로 전환. Duren이 $34를 넘으면 피벗이 아니라 코어 전환(→ 코어 7).

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| UTIL | Evan Mobley → **Walker Kessler** | $16 | -9 |
| UTIL | Rudy Gobert → **Desmond Bane** | $22 | +10 |

**피벗 최종 9인** — 총액 $193 · 예비비 $7 · 빅맨 $69 (C자격 3명) · 노리는 캣 `AST BLK DD FG% OREB PTS REB STL` · 포기 `3P% 3PM A/T FT% TOV`

| 슬롯 | 선수 | 계획가 | 상한 |
|---|---|---|---|
| C | Jalen Duren `C` | $27 | $31 |
| PF | Alperen Şengün `C` | $26 | $31 |
| SF | Amen Thompson | $26 | $31 |
| UTIL | Walker Kessler `C` | $16 | $19 |
| SG | Kon Knueppel | $22 | $31 |
| UTIL | Dyson Daniels | $12 | $20 |
| BN | Desmond Bane | $22 | $31 |
| BN | Julius Randle | $12 | $18 |
| PG | Trae Young | $30 | $30 |

---

## 코어 5 · Sabonis 부상 할인 (조건부 베팅)

**우선 격리** — Sabonis 프리시즌 정상 복귀 확인 (가격 게이트 없음)

> ⚠️ 격리된 별도 베팅안. Sabonis 건강이 프리시즌에 확인될 때만 발동. 실출장 ~20경기이고 A/T 한계기여는 −0.102로 마이너스 — 정상 복귀를 기본값으로 두면 위험합니다. 헤지 빅 2명을 필수로 붙입니다.

**계획 $186** · 예비비 **$14** · 빅맨 $70/$96 (C자격 5명) · 노리는 캣 9개 `3P% A/T AST BLK DD FG% OREB REB STL` · 포기 `3PM FT% PTS TOV`

**주간 승률** 최소 **31.5%** (vs 가치최대) · 빅5 동시붕괴 39.6% · 기대 승리 캣 8.70

> **예비비 구성** — 34차: 예비비 제약(>=$12). 재가격만으로는 $170(하한 미달). BN T.J. McConnell → **Dyson Daniels** · 총액 $180 · 예비 $20. 최소 승률 23.2% → 31.1% · 보수 혼합 57.2% · 빅5붕괴 41.3%(후보 중 최저). 900·6000시행 순위가 일치했다(31.2% → 31.1%).

### 기본 플랜

| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|---|
| **PG** `앵커` | $56 | $56 | **$0** (실패→치환 Josh Giddey) | A/T +0.517 리그 1위 | **Tyrese Haliburton** | Josh Giddey $41 | De'Aaron Fox $24 |
| **SF** | $26 | $49 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $11 | Jaden McDaniels $5 |
| **UTIL** | $23 | $30 | — | Sabonis 헤지 빅 ① | **Evan Mobley** `C` | Walker Kessler $16 | — |
| **SG** | $22 | $33 | — | 3PT% 레버리지 2위 | **Kon Knueppel** | Desmond Bane $22 | Sam Merrill $2 |
| **PF** `앵커` | $19 | $34 | **$14** (실패→C6) | 앵커 (부상 할인 · 실패 시 코어 전환) | **Domantas Sabonis** `C` | — | — |
| **C** | $12 | $22 | — | Sabonis 헤지 빅 ② (필수) | **Donovan Clingan** `C` | Jalen Duren $27 | Rudy Gobert $8 |
| **UTIL** | $11 | $16 | — | DD 24 · Hali 픽앤롤 시너지 | **Ivica Zubac** `C` | Mitchell Robinson $5 | Mark Williams $7 |
| **BN** | $5 | $14 | — | OREB 2.6 · DD 22 | **Deandre Ayton** `C` | Nic Claxton $4 | Neemias Queta $2 |
| **BN** | $12 | $20 | — | STL 2.0 리그 공동 1위 · 가드 OREB 2.1 | **Dyson Daniels** | Andrew Nembhard $2 | Davion Mitchell $2 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Ivica Zubac > $16`

> Sabonis 자체가 부상 할인 자산이라 빅맨 과열 영향이 가장 작다. 헤지 빅을 최저가로 내리고 절감분을 3PM·FT%·STL 윙(Murphy)으로.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| C | Donovan Clingan → **Mark Williams** | $7 | -5 |
| UTIL | Ivica Zubac → **Nic Claxton** | $4 | -7 |
| SG | Kon Knueppel → **Trey Murphy III** | $32 | +7 |
| SF | Amen Thompson → **Amen Thompson** | $26 | +3 |

**피벗 최종 9인** — 총액 $184 · 예비비 $16 · 빅맨 $58 (C자격 5명) · 노리는 캣 `A/T AST BLK DD FG% OREB REB STL TOV` · 포기 `3P% 3PM FT% PTS`

| 슬롯 | 선수 | 계획가 | 상한 |
|---|---|---|---|
| PG | Tyrese Haliburton | $56 | $56 |
| SF | Amen Thompson | $26 | $49 |
| UTIL | Evan Mobley `C` | $23 | $30 |
| SG | Trey Murphy III | $32 | $32 |
| PF | Domantas Sabonis `C` | $19 | $34 |
| C | Mark Williams `C` | $7 | $14 |
| UTIL | Nic Claxton `C` | $4 | $12 |
| BN | Deandre Ayton `C` | $5 | $14 |
| BN | Dyson Daniels | $12 | $20 |

---

## 코어 6 · A/T 분산 조달 (정상 시장 기본값)

**우선 2** — 센터 정상가 + Hali 불확실/비쌈

> A/T 한계기여를 Derrick White(+0.171) + DeRozan(+0.152) = +0.323으로 분산 조달한다 — Haliburton 단독(+0.517)의 62%를 조달하면서 아킬레스 복귀 리스크를 지지 않고, 절감분으로 KAT 앵커를 붙인다.
🔄 **센터 헤비가 아니다.** Clingan $12 → Bane $22로 C자격이 4 → 3이 되고 빅맨 예산이 $79/$113($34 여유)로 줄었다. 저가 센터를 쓸어담는 축이 아니라 **전방위 윙으로 슬롯 효율을 사는 축**이다 — 과열 판정 시 이 점을 전제로 대응할 것. 그 대신 3P%가 −80.5 → 개선되고 실제 12팀 평균이 84.5% → **87.5%(전 코어 1위)** 가 됐다.

**계획 $191** · 예비비 **$9** · 빅맨 $79/$113 (C자격 3명) · 노리는 캣 9개 `A/T AST BLK DD FG% OREB PTS REB STL` · 포기 `3P% 3PM FT% TOV`

**주간 승률** 최소 **36.7%** (vs 가치최대) · 빅5 동시붕괴 61.3% · 기대 승리 캣 8.90

> **예비비 구성** — 34차 최종: 예비비 제약(>=$12)을 **Knueppel $22 → VJ Edgecombe $5**로 달성. 총액 $181 · 예비비 $19. D.White $39 유지.
⚠️ 자기 정정: 처음에는 Şengün → LeBron James를 적용했다. 900시행 탐색이 그 안을 maximin 38.9%로 1위로 냈으나 **6000시행 같은 스트림 직접 대조에서 뒤집혔다**:
  LeBron        예비 $14 · 최소 35.1% · 보수 60.5% · 빅5붕괴 54.0%
  Şengün(33차)  예비  $2 · 최소 37.3% · 보수 61.6% · 빅5붕괴 42.6%
  Edgecombe     예비 $19 · 최소 36.9% · 보수 60.9% · 빅5붕괴 39.5%  ← 채택
Edgecombe안이 LeBron안을 **모든 축에서** 지배하고, Şengün안과 maximin 차이(0.4%p)는 노이즈 범위인데 예비비가 $2 → $19다. 900시행 순위는 1~2%p 수준에서 신뢰할 수 없다 (승자의 저주).

### 기본 플랜

| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|---|
| **C** `앵커` | $45 | $55 | **$9** (실패→치환 Jalen Duren) | 앵커 · DD 56 리그 1위 | **Karl-Anthony Towns** `C` | Jalen Duren $27 | Alperen Şengün $26 |
| **PF** | $26 | $34 | — | OREB 3.0 · DD · 빅맨 최상급 AST | **Alperen Şengün** `C` | Evan Mobley $23 | LeBron James $14 |
| **SF** | $26 | $49 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $11 | Jaden McDaniels $5 |
| **UTIL** | $5 | $9 | — | STL 보조 $5 다트 — 예비비 확보용 | **VJ Edgecombe** | Kon Knueppel $22 | Desmond Bane $22 |
| **UTIL** | $12 | $20 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $3 | Cason Wallace $3 |
| **BN** | $22 | $31 | — | 전방위 저가 윙 — FT% 엘리트 · 후보 21명 실측 1위 | **Desmond Bane** | Josh Hart $4 | Nikola Vučević $2 |
| **SG** `앵커` | $8 | $16 | **$8** (실패→치환 Dennis Schröder) | A/T +0.152 · TOV 1.2 · FT% 86.8% | **DeMar DeRozan** | Dennis Schröder $5 | D'Angelo Russell $2 |
| **BN** | $8 | $18 | — | OREB+BLK+DD 빅 | **Rudy Gobert** `C` | Ivica Zubac $11 | Mark Williams $7 |
| **PG** `앵커` | $39 | $44 | **$9** (실패→치환 T.J. McConnell) | A/T +0.171 · FT% 90.2% · 3PM3 · BLK 1.3 (가드가 BLK) | **Derrick White** | T.J. McConnell $2 | Andrew Nembhard $2 |

### 과열 피벗

**트리거**: `Rudy Gobert > $18`

> 정상 시장 기본값 코어의 생존 분기. 저가 센터가 과열되면 **Gobert $8 → Okongwu $5** 하나만 바꿔 빅맨을 $76로 낮추고 나머지 8칸은 그대로 둔다 — 이 코어는 저가 센터를 쓸어담는 축이 아니라 전방위 윙으로 슬롯 효율을 사는 축이라 센터 과열에 노출이 작다. 저가 빅 3명 이상이 과열되면 피벗이 아니라 코어 7로 전환한다.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| BN | Rudy Gobert → **Onyeka Okongwu** | $5 | -3 |

**피벗 최종 9인** — 총액 $188 · 예비비 $12 · 빅맨 $76 (C자격 3명) · 노리는 캣 `A/T AST BLK DD FG% FT% OREB PTS REB STL` · 포기 `3P% 3PM TOV`

| 슬롯 | 선수 | 계획가 | 상한 |
|---|---|---|---|
| C | Karl-Anthony Towns `C` | $45 | $55 |
| PF | Alperen Şengün `C` | $26 | $34 |
| SF | Amen Thompson | $26 | $49 |
| UTIL | VJ Edgecombe | $5 | $9 |
| UTIL | Dyson Daniels | $12 | $20 |
| BN | Desmond Bane | $22 | $31 |
| SG | DeMar DeRozan | $8 | $16 |
| BN | Onyeka Okongwu `C` | $5 | $10 |
| PG | Derrick White | $39 | $44 |

---

## 코어 7 — 중가 센터 전환 (센터 인플레 대응)

**우선 0** — 저가 센터 계층 과열 2명 이상

> 센터 인플레의 답은 센터를 버리는 것이 아니라 **중가 센터로 갈아타는 것**이다 — 저가 센터(Clingan·Gobert 계층)가 과열되면 Mobley $23 · Okongwu $5 로 옮겨 OREB·BLK·FG%의 바닥을 지키고 KAT·D.White 축은 그대로 둔다. 저가 센터 노출이 Gobert 한 명뿐이라 **과열 세계에서도 예산 안에 조립된다** (강제 매수 시 $189 · 예비비 $11) — 그것이 이 코어가 우선 0인 이유다.

**계획 $184** · 예비비 **$16** · 빅맨 $107/$130 (C자격 5명) · 노리는 캣 9개 `3PM AST BLK DD FG% OREB PTS REB STL` · 포기 `3P% A/T FT% TOV`

**주간 승률** 최소 **34.7%** (vs 가치최대) · 빅5 동시붕괴 38.5% · 기대 승리 캣 8.90

### 기본 플랜

| 슬롯 | 계획가 | 상한 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|---|
| **C** `앵커` | $45 | $55 | **$16** (실패→치환 Jalen Duren) | 앵커 · DD 56 리그 1위 · OREB 3.1 | **Karl-Anthony Towns** `C` | Jalen Duren $27 | Domantas Sabonis $19 |
| **PF** | $26 | $34 | — | OREB 3.0 · DD 34 · 빅맨 최상급 AST | **Alperen Şengün** `C` | Domantas Sabonis $19 | Pascal Siakam $25 |
| **SF** | $22 | $33 | — | 3PT% 레버리지 2위 · 3PM 3.4 | **Kon Knueppel** | Desmond Bane $22 | Amen Thompson $26 |
| **SG** | $12 | $20 | — | STL 2.0 리그 공동 1위 · OREB 2.4 | **Dyson Daniels** | Ausar Thompson $3 | Cason Wallace $3 |
| **PG** `앵커` | $39 | $44 | **$13** (실패→치환 Josh Giddey) | 앵커 · A/T +0.171 · FT% 90.2% · 가드 BLK 1.3 | **Derrick White** | Josh Giddey $41 | Nickeil Alexander-Walker $22 |
| **UTIL** | $23 | $30 | — | 중가 센터 — OREB 2.4 · BLK 1.7 · DD 27 | **Evan Mobley** `C` | Ivica Zubac $11 | Mark Williams $7 |
| **UTIL** | $8 | $18 | — | OREB 3.9 · BLK 1.6 · DD 33 · 76G | **Rudy Gobert** `C` | Mitchell Robinson $5 | Deandre Ayton $5 |
| **BN** | $4 | $5 | — | 다재다능 저가 — 12.7P 8.4R 5.3A | **Josh Hart** | Neemias Queta $2 | Moussa Diabaté $2 |
| **BN** | $5 | $10 | — | 중가 센터 저가 — OREB+BLK+DD | **Onyeka Okongwu** `C` | Nikola Vučević $2 | Kel'el Ware $2 |

### 과열 피벗

**트리거**: `Rudy Gobert > $18` · `Donovan Clingan > $22`

> UTIL 센터 2자리(Gobert·Okongwu)를 저가 가드로 바꾸고 절감분을 SG(Daniels 12→15)·SF(Knueppel 22→25) 상향에 쓴다. 중가 센터 축(KAT·Şengün·Mobley)은 유지한다 — 그 축을 버리는 것이 기존 c7의 오류였다.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| UTIL | Rudy Gobert → **Nikola Vučević** | $2 | -6 |
| BN | Onyeka Okongwu → **DeMar DeRozan** | $8 | +3 |
| C | Karl-Anthony Towns → **Karl-Anthony Towns** | $49 | +4 |

**피벗 최종 9인** — 총액 $185 · 예비비 $15 · 빅맨 $100 (C자격 4명) · 노리는 캣 `3P% 3PM A/T AST BLK DD FG% OREB PTS REB STL` · 포기 `FT% TOV`

| 슬롯 | 선수 | 계획가 | 상한 |
|---|---|---|---|
| C | Karl-Anthony Towns `C` | $49 | $55 |
| PF | Alperen Şengün `C` | $26 | $34 |
| SF | Kon Knueppel | $22 | $33 |
| SG | Dyson Daniels | $12 | $20 |
| PG | Derrick White | $39 | $44 |
| UTIL | Evan Mobley `C` | $23 | $30 |
| UTIL | Nikola Vučević `C` | $2 | $8 |
| BN | Josh Hart | $4 | $5 |
| BN | DeMar DeRozan | $8 | $16 |

---

## 자동 검증 (`python3 validate.py`)

`validate.py`가 기본 코어와 피벗 로스터 전부에 대해 상시 검사합니다.
불변식 전문은 `HANDOFF.md`의 「반드시 지켜야 하는 불변식」을 보십시오.

| 규칙 | 적용 대상 |
|---|---|
| 9개 슬롯 완성 · 포지션 자격 | 기본 7 + 피벗 7 |
| `market_low ≤ plan_price ≤ my_max` | 1순위 + 대체 후보 전부 |
| 가격 3필드 정합 (I23) | `bid_ceiling` ≤ my_max · `expected_cost` ≤ `bid_ceiling` ≤ 시장 상단 |
| 예비비 (I22) | 목표 ≥$12 · 경고 <$8 · 위반 <$4 · >$25 과소 편성 |
| 총액 ≤ $200 · 빅맨 예산 ≤ `big_budget_cap` | 전 플랜 |
| 장기 부상 제외 준수 · 선수 중복 없음 | 전 플랜 |
| 캣 선언 = 실측 팀 한계기여 | 전 플랜 |
| 트리거·백업 조건이 임계값 단일 소스와 일치 | 피벗 |
| 툴 임베드 상수 · P 배열 동기화 (I20) | `tool/auction-console.html` |

**총 14개 플랜(기본 7 + 피벗 7 · 백업 없음)**

> 📌 백업 로스터는 33차에 c7을 A1으로 전면 교체하면서 사라졌습니다(구 c7의 백업이었고 `cores.json.c7_old`에 함께 보존). "15개 플랜"이라는 옛 표기를 보면 그 문서가 33차 이전입니다.

## 드래프트 직전 필수 확인

| 항목 | 이유 |
|---|---|
| **야후 실제 포지션 자격** | 데이터는 G/F/C 수준만 저장 — 슬롯 배치가 유효하려면 실자격 확인 필요 |
| **지명 시 자동 $1 입찰 여부** | 태우기 지명 전략의 전제 |
| **Sabonis · Haliburton 프리시즌 상태** | c5는 Sabonis 건강 확인이 발동 조건 · c1/c5는 Hali 할인이 전제 |
| **소속 미확인 선수** | `team: "—"` 로 남은 선수 갱신 |
