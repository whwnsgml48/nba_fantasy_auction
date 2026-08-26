# 코어 7종 + 과열 피벗 + 판단 순서

> ⚠️ **실전 확정안이 아니라 가설 묶음입니다.** `노리는 캣`은 겨냥하는 캣 목록이며 승리 확률이나
> 14팀 내 순위를 뜻하지 않습니다(`05-limitations.md` 2번). 계획가는 **제 추정 시장가** 기반입니다.

**모든 수치는 `data/cores.json`에서 생성됩니다.** 검증: `python3 validate.py`

## 판단 순서 (조건부 우선순위)

> **정상 시장: 코어 6 기본 → Hali 할인 시 코어 1 → SGA 할인 시 코어 3 → 앵커 실패 시 코어 4. 저가 센터 2명 이상 과열: 즉시 코어 7. Jokić·Sabonis는 조건 충족 시에만 별도 진입.**

| 우선 | 조건 | 선택 | 근거 |
|---|---|---|---|
| **0** | 저가 센터 계층 과열 2명 이상 | **C7** — 반센터 인플레 (센터 붕괴 시 최우선) | ⚠ 코어 6·4의 과열 피벗보다 먼저 코어 7로 전환. 센터 시장이 붕괴하면 피벗으로는 부족하다. 판정은 low_cost_center 계층의 overheat_at(실측 기대치 기반)으로만 한다 — 네임밸류 빅(Şengün·Mobley·Zubac)이 $30~60에 팔리는 것은 정상가이므로 세지 않는다. |
| **1** | 센터 정상가 + KAT ≤ $50 + Hali ≤ $48 | **C1** — KAT 앵커 + Haliburton | Hali가 정말 할인되면 코어 1의 천장이 가장 높다. 임계 $48은 내 최대가 $50보다 낮게 잡은 '선택 기준'이다 — $48~50은 살 수는 있으나 코어 1을 우선할 근거는 아니다. |
| **2** | 센터 정상가 + Hali 불확실/비쌈 | **C6** — A/T 분산 조달 (정상 시장 기본값) | 정상 시장의 기본값. Hali가 기대만큼 안 싸거나 아킬레스 복귀 리스크를 피하고 싶으면 여기. |
| **3** | 센터가 조금 비싸지만 SGA ≤ $72 | **C3** — SGA + 저가 빅 4인 | 빅맨 예산 $77(39%)로 7개 코어 중 최저 — 센터가 약간 비싸지는 정도라면 코어 4보다 먼저. |
| **4** | 앵커를 못 잡았지만 센터는 정상가 | **C4** — 무앵커 분산 (상한 $31) | 앵커 실패 시의 안전망. 센터 과열 대응책이 아니다 — 센터가 깨졌으면 코어 7. |
| **조건부** | Jokić ≤ $88 | **C2** — Jokić 압축 | 스타 집중형. 예산이 Jokić·D.White에 잠기므로 조건 충족 시에만 진입. |
| **격리** | Sabonis 건강 확인 + ≤ $26 | **C5** — Sabonis 부상 할인 (조건부 베팅) | 별도 베팅안. 정상 복귀를 기본값으로 두지 않는다. |
### 판단의 요점

- **센터 시장 붕괴면 코어 7이 무조건 1순위입니다.** 코어 6·4의 *과열 피벗보다 먼저* 전환합니다 —
  피벗은 센터 하나가 비싸질 때의 대응이고, 두 명 이상이면 전제 자체가 깨진 것입니다.
- 정상 시장에서 **Hali가 정말 할인되면 코어 1의 천장이 가장 높습니다.** 임계 `≤ $48`은
  내 최대가 $50보다 낮게 잡은 **선택 기준**입니다 — $48~50은 살 수는 있으나 코어 1을
  우선할 근거는 아닙니다.
- Hali가 기대만큼 안 싸거나 아킬레스 복귀 리스크를 피하고 싶으면 **코어 6이 기본값**입니다.
- 센터가 **약간** 비싸지는 정도라면 빅맨 예산이 $77(39%)로 최저인 **코어 3이 코어 4보다 먼저**입니다.
- **코어 4는 앵커 실패 시의 안전망이고, 센터 과열 대응책이 아닙니다.**

툴 우측 `판단 순서` 카드가 이 표를 행별로 **충족 / 불가 / 미정 / 기본값**으로 실시간 판정하고
현재 권장 코어를 강조합니다. 카드 하단에 **과열 임계값 2계층**(계층별 철수가·기대치·과열선)이
함께 표시되고, `그 외 센터 (저가 계층)` 계층에서 2명 이상 과열 시 피벗 카드에 `피벗 대신 코어 7` 경고가 뜹니다.

## 장기 부상 제외 규칙

> 개막 후 4주 이상 결장 예상 또는 복귀 일정 불확실 → 코어·대체후보·피벗에서 전면 제외. IL+ 슬롯이 있어도 코어 자산으로 계산하지 않는다. 드래프트 직전 복귀 일정이 명확히 앞당겨질 경우에만 수동 해제.

| 선수 | 사유 |
|---|---|
| **Jimmy Butler III** (GSW) | 🚑 장기 부상 제외 — ACL 파열, 복귀 12월 이후 불확실. 드래프트 직전 일정이 앞당겨지면 수동 해제 |

## 코어 7 발동 조건 (저가 센터 전제 붕괴)

| 조건 | 판정 |
|---|---|
| **그 외 센터 (저가 계층)** 계층 6명 중 **2명 이상**이 `overheat_at` 초과 | 툴 `판단 순서` 우선 0 자동 발동 |
| 저가 빅맨 **3명 이상**이 계획가 대비 **25% 이상** 상승 | 툴 `시장가 보정` 계수 ×1.25 이상 |
| `big_budget_cap` 지키며 C 자격 2명 + 유효 7캣 빌드 불가 | `빅맨 예산 초과` + `노리는 캣 미달` 동시 |

판정 대상: Donovan Clingan · Rudy Gobert · Jalen Duren · Mitchell Robinson · Deandre Ayton · Mark Williams

> ⚠️ **네임밸류 빅(Evan Mobley · Ivica Zubac · Alperen Şengün)은 판정에 넣지 않습니다.**
> 이 리그에서 그들의 $30~60은 과열이 아니라 정상가입니다 — `docs/08` 2절 ③.

## 과열 임계값 · 2계층 (단일 소스)

**2026-08-20 분리.** 한 필드에 섞여 있던 두 개념을 나눴습니다:

| 필드 | 의미 | 쓰임 |
|---|---|---|
| `threshold` / `walk_away` | **철수 가격** — 이 값 위로는 안 산다 | 해당 코어의 과열 피벗 트리거 |
| `overheat_at` | **시장 과열 신호** — 실측 기대치 대비 이상 | 코어 7 전환 판정 |

분리 전에는 Gobert `> $18`(실측 $8)이 영원히 안 터지고 Zubac `> $16`(실측 $35)이
항상 터졌습니다. 둘 다 철수 가격인데 과열 신호로 쓰였기 때문입니다.

### 네임밸류 빅 — 코어 7 **무관**

> 이 계층에서 $30~60은 과열이 아니라 정상가다. 코어 7은 '저가 센터 시장 붕괴' 대응책이므로 이 계층의 가격 상승은 전환 근거가 아니다.
>
> 실측 근거: 작년 실측 11명(Wemby·Jokić·Giannis·KAT·Sabonis·Şengün·AD·Mobley·Zubac·Holmgren·Adebayo) 합 $626 = 리그 센터 지출의 77% · 평균 $56.9 · 범위 $29-87
> · 과열선 = 기대치 × 1.25

| 선수 | 철수 가격 | 실측 기대치 | 과열선 | 내 최대가 | 근거 |
|---|---|---|---|---|---|
| Evan Mobley | `> $30` | $48 | `> $60` | $36 | 작년 실측 $43 × 1.117 = $48 |
| Ivica Zubac | `> $16` | $39 | `> $49` | $18 | 작년 실측 $35 × 1.117 = $39 |
| Alperen Şengün | `> $34` | $67 | `> $84` | $46 | 작년 실측 $60 × 1.117 = $67 · 네임밸류 빅 11명 평균 $56.9 |

### 그 외 센터 (저가 계층) — 코어 7 판정 대상

> 코어 7의 전제는 '이름값 없는 생산형 센터를 $10 안쪽에 쓸어담는다'다. 그 경로가 막히는 것이 곧 전환 조건이므로 코어 7 조건은 이 계층에서만 센다.
>
> 실측 근거: 작년 실측 23명 합 $188 · 평균 $8.2 · 중앙값 $6 · 87%(20/23)가 $15 이하
> · 과열선 = 기대치 × 1.4 (최소 +$3)

| 선수 | 철수 가격 | 실측 기대치 | 과열선 | 내 최대가 | 근거 |
|---|---|---|---|---|---|
| Donovan Clingan | `> $22` | $14 | `> $20` | $34 | 작년 미지명 · 비교군 Kessler $15 · M.Williams $14 · Duren $11 기준 추정 |
| Rudy Gobert | `> $18` | $9 | `> $13` | $26 | 작년 실측 $8 × 1.117 = $9 |
| Jalen Duren | `> $34` | $11 | `> $15` | $46 | 작년 실측 $10 × 1.117 = $11 |
| Mitchell Robinson | `> $16` | $6 | `> $9` | $24 | 작년 미지명 · 비교군 Poeltl $4 · Claxton $3 · Okongwu $7 기준 추정 |
| Deandre Ayton | `> $14` | $5 | `> $8` | $18 | 작년 실측 $5 × 1.117 = $5 |
| Mark Williams | `> $14` | $14 | `> $20` | $18 | 작년 실측 $13 × 1.117 = $14 |

### 앵커 (센터 아님) — 코어 7 **무관**

> 이 두 명은 '시장이 뜨거운가'가 아니라 '앵커를 확보할 수 있는가'를 판정한다. overheat_at 개념 비적용(null).
>
> 실측 근거: Jalen Johnson(F) · Tyrese Haliburton(G) — 센터가 아니므로 센터 시장 온도와 무관

| 선수 | 철수 가격 | 실측 기대치 | 과열선 | 내 최대가 | 근거 |
|---|---|---|---|---|---|
| Jalen Johnson | `> $58` | — | — (개념 비적용) | $56 | 포워드. 코어 7 앵커 확보 가능성 판정용 — 센터 시장 온도와 무관 |
| Tyrese Haliburton | `> $50` | — | — (개념 비적용) | $50 | 가드. 코어 1·5 앵커 확보 가능성 판정용 — 센터 시장 온도와 무관 |

### 작년 실측 대입 백테스트

| 방식 | 발동 인원 | 코어 7 |
|---|---|---|
| 분리 전 (철수가 · 계층 무시) | **3명** (Şengün $60 · Mobley $43 · Zubac $35) | **즉시 발동** |
| 분리 후 (`overheat_at` · 저가 계층만) | **0명** | 미발동 |

저가 계층 실측: Gobert $8(과열선 $13) · Ayton $5($8) · Duren $10($15) · M.Williams $13($20)
— 전부 미달. Clingan·M.Robinson은 작년 미지명.

→ **코어 7이 상시 발동에서 진짜 예외로 돌아왔습니다.**

## 앵커 여유 정책 (단일 소스)

**2026-08-20 신설.** 이전에는 "앵커는 대체후보 면제 · 실패 시 코어 전환"이 서술로만
있어 검증되지 않았습니다. 그 결과 두 가지가 방치돼 있었습니다.

| 정의 | 내용 |
|---|---|
| `bid_ceiling` | my_max. 이 값 위로는 어떤 경우에도 부르지 않는다 |
| `nominal_margin` | my_max − 계획가 |
| `effective_headroom` | min(my_max, 계획가 + 코어 예산여유) − 계획가. 예산 여유가 없으면 명목 여유는 허구다 |
| `constraint` | none = 여력 있음 · budget = 예산이 병목 · my_max = 평가가 병목(예산으로 해결 불가) |
| `dual_world_ok` | 현 시장추정과 재적합(실측 기반) 양쪽에서 my_max ≥ 시장하단 |

### 핵심: 명목 여유는 예산 여유가 없으면 허구다

`my_max`가 계획가보다 높아도 코어에 남는 돈이 없으면 더 부를 수 없습니다.
발견 당시 명목 여유 합이 실효 여력 합보다 **$28 컸습니다**
(예: 코어 1의 KAT는 명목 $12인데 예산 여유가 $1이라 실효 $1).

**조치**: 비앵커 계획가를 재적합(실측 기반)이 더 싸게 보는 만큼 트림해 예산 여유를 확보.
코어 1 $199→$187($13 여유) · 코어 5 $194→$192($8) · 코어 6 $194→$185($15) · 코어 7 $195→$188($12).
**예산 제약 병목은 전부 해소됐습니다** — 남은 `constraint: my_max`는 평가 한계이므로 예산으로 풀 수 없습니다.

### 앵커 14개 현황

| 코어 | 슬롯 | 앵커 | 계획 | 상한 | 명목 | 실효 | 제약 | 실패 시 | 실측곡선 |
|---|---|---|---|---|---|---|---|---|---|
| C1 | C | Karl-Anthony Towns | $50 | $62 | $12 | **$12** | `none` | 치환 → Jalen Duren | 획득 가능 |
| C1 | PG | Tyrese Haliburton | $50 | $50 | $0 | **$0** | `my_max` | 치환 → Josh Giddey | **획득 불가** |
| C2 | C | Nikola Jokić | $88 | $88 | $0 | **$0** | `my_max` | **코어 전환 → C6** | **획득 불가** |
| C2 | SG | Derrick White | $44 | $44 | $0 | **$0** | `my_max` | 치환 → De'Aaron Fox | 획득 가능 |
| C3 | SG | Shai Gilgeous-Alexander | $72 | $72 | $0 | **$0** | `my_max` | **코어 전환 → C4** | **획득 불가** |
| C5 | PG | Tyrese Haliburton | $50 | $50 | $0 | **$0** | `my_max` | 치환 → Josh Giddey | **획득 불가** |
| C5 | PF | Domantas Sabonis | $26 | $34 | $8 | **$8** | `none` | **코어 전환 → C6** | 획득 가능 |
| C6 | C | Karl-Anthony Towns | $50 | $62 | $12 | **$12** | `none` | 치환 → Jalen Duren | 획득 가능 |
| C6 | SG | DeMar DeRozan | $16 | $16 | $0 | **$0** | `my_max` | 치환 → Dennis Schröder | 획득 가능 |
| C6 | PG | T.J. McConnell | $4 | $14 | $10 | **$10** | `none` | 치환 → Andrew Nembhard | 획득 가능 |
| C7 | PF | Jalen Johnson | $56 | $56 | $0 | **$0** | `my_max` | **과열 피벗 실행** | **획득 불가** |
| C7 | PG | De'Aaron Fox | $28 | $28 | $0 | **$0** | `my_max` | 치환 → Dennis Schröder | 획득 가능 |
| C7 | UTIL | DeMar DeRozan | $16 | $16 | $0 | **$0** | `my_max` | 치환 → Dennis Schröder | 획득 가능 |
| C7 | BN | T.J. McConnell | $4 | $14 | $10 | **$10** | `none` | 치환 → Andrew Nembhard | 획득 가능 |

### 규칙 (`validate.py`가 검사)

1. 모든 앵커는 on_fail을 선언한다 — substitute(코어 내 치환) 또는 switch_core(코어 전환)
2. on_fail=substitute는 이중세계 유효 대체후보가 1명 이상일 때만 허용
3. on_fail=switch_core의 목적지는 존재하는 다른 코어이며 같은 앵커에 의존하지 않아야 한다
4. 재적합에서 획득 불가 + 대체 0명인 앵커를 가진 코어는 conditional_on_discount를 선언한다
5. 피벗·백업 로스터도 이중세계 유효해야 하며, 아니면 이중세계 유효 대체후보를 갖는다

### 조건부 베팅 (시장 할인 없이는 확보 불가)

| 코어 | 앵커 | 사유 | 실패 시 |
|---|---|---|---|
| **C2** | Nikola Jokić | my_max $88 < 재적합 시장하단 $93 — 시장 할인 없이는 확보 불가 | 코어 전환 → **C6** |
| **C3** | Shai Gilgeous-Alexander | my_max $72 < 재적합 시장하단 $81 — 시장 할인 없이는 확보 불가 | 코어 전환 → **C4** |

이 둘은 대체후보가 **설계상 없습니다** — 앵커가 곧 코어의 전제입니다.
실측 곡선에서는 확보 불가이므로 **시장이 우리 최대가 이하로 내려올 때만 진입**합니다.

### 재적합(실측 곡선) 적용 시 생존 검증

| | 앵커 정책 이전 | 이후 |
|---|---|---|
| `validate.py` 위반 | **22건** | **4건** |
| 실패 코어 | c1·c2·c3·c5·c7 (5개) | c2·c3 (2개, 조건부 선언됨) |
| 정상 실행 | c4·c6 | c1·c4·c5·c6·**c7** |

판단표 **기본값 c6**과 **우선 0 c7**이 모두 실측 곡선에서 실행됩니다.
남은 4건은 c2(Jokić `my_max $88` < 실측 $93)·c3(SGA `$72` < `$81`)로,
`my_max`를 근거 없이 올리지 않는 한 줄일 수 없는 값입니다.

## 요약표

| | 코어 | 계획 | 빅맨/상한 | C자격 | 노리는 캣 | 포기 | A/T 조달 | 피벗 총액 |
|---|---|---|---|---|---|---|---|---|
| c1 | KAT 앵커 + Haliburton | $187 | $95/$115 | 5 | 11개 | PTS | Haliburton +0.517 | $195 |
| c2 | Jokić 압축 | $199 | $145/$153 | 5 | 11개 | TOV, STL | Jokić +0.241 + D.White +0.171 | $197 |
| c3 | SGA + 저가 빅 4인 | $199 | $77/$85 | 5 | 10개 | TOV, A/T | 포기 | $200 |
| c4 | 무앵커 분산 (상한 $31) | $194 | $105/$107 | 4 | 10개 | PTS, TOV | McConnell +0.261 | $195 |
| c5 | Sabonis 부상 할인 (조건부 베팅) | $192 | $86/$96 | 5 | 11개 | FT%, PTS | Haliburton +0.517 (Sabonis −0.102 상쇄) | $192 |
| c6 | A/T 분산 조달 (정상 시장 기본값) | $185 | $96/$113 | 4 | 12개 | PTS | McConnell +0.261 + DeRozan +0.152 = +0.413 | $193 |
| c7 | 반센터 인플레 (센터 붕괴 시 최우선) | $188 | $25/$36 | 2 | 8개 | OREB, DD, BLK, FG% | Fox +0.130 + DeRozan +0.152 + McConnell +0.261 = +0.543 | $189 |

---

## 코어 1 · KAT 앵커 + Haliburton

**우선 1** — 센터 정상가 + KAT ≤ $50 + Hali ≤ $48

> 잉여가 $50 이상 구간에서 시장을 앞서는 선수는 KAT 하나뿐(+$16). A/T는 Haliburton 단독(한계기여 +0.517, 리그 1위)으로 조달. 아킬레스 복귀 리스크를 감수하는 조건부 플랜이며, 회피하려면 코어 6.

**계획 $187** · 빅맨 $95/$115 (C자격 5명) · 예산여유 **$13** · 노리는 캣 11개 `FG% REB OREB DD BLK AST A/T TOV STL 3PM FT%` · 포기 `PTS`

### 기본 플랜

| 슬롯 | 계획가 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|
| **C** `앵커` | $50 | **$12** (상한 $62 · 실패→치환 Duren) | 앵커 · DD 56 리그 1위 | **Karl-Anthony Towns** | Jalen Duren $34 | Alperen Şengün $32 |
| **PG** `앵커` | $50 | **0** (상한 $50 · 실패→치환 Giddey) | A/T +0.517 리그 1위 · TOV 동시 | **Tyrese Haliburton** | Josh Giddey $42 | De'Aaron Fox $28 |
| **PF** | $26 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** | Evan Mobley $27 | Paolo Banchero $30 |
| **SF** | $25 | — | 3PT% 레버리지 2위 · 3PM 3.4 | **Kon Knueppel** | Desmond Bane $26 | Toumani Camara $13 |
| **SG** | $15 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $6 | Cason Wallace $6 |
| **UTIL** | $9 | — | OREB 4.5 리그 1위 · 77G | **Donovan Clingan** | Rudy Gobert $12 | Mitchell Robinson $8 |
| **UTIL** | $8 | — | OREB+BLK+DD 빅 | **Rudy Gobert** | Ivica Zubac $13 | Mark Williams $9 |
| **BN** | $2 | — | A/T +0.261 리그 2위 | **T.J. McConnell** | Andrew Nembhard $2 | Davion Mitchell $2 |
| **BN** | $2 | — | OREB 3.7 다트 | **Moussa Diabaté** | Andre Drummond $2 | Day'Ron Sharpe $2 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Rudy Gobert > $18`

> 저가 OREB 경로가 막히면 OREB 완전 장악을 포기하고 REB·DD만 지킨다. 빅맨을 5명→4명($96)으로 줄이고 절감분을 3P%·FT% 윙으로 옮긴다. 두 명 이상 과열이면 코어 7로 전환.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| UTIL | Donovan Clingan → **Mitchell Robinson** | $8 | -6 |
| UTIL | Rudy Gobert → **Mark Williams** | $9 | -3 |
| BN | Moussa Diabaté → **Sam Merrill** | $6 | +4 |
| SF | Kon Knueppel → **Desmond Bane** | $26 | +1 |

**피벗 최종 9인** — 총액 $195 · 빅맨 $96 (C자격 4명) · 노리는 캣 `FG% REB OREB DD BLK AST A/T TOV STL 3PM FT%` · 포기 `PTS`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| C | Karl-Anthony Towns `C` | $50 |
| PG | Tyrese Haliburton | $50 |
| PF | Alperen Şengün `C` | $29 |
| SF | Desmond Bane | $26 |
| SG | Dyson Daniels | $15 |
| UTIL | Mitchell Robinson `C` | $8 |
| UTIL | Mark Williams `C` | $9 |
| BN | T.J. McConnell | $2 |
| BN | Sam Merrill | $6 |

---

## 코어 2 · Jokić 압축

**우선 조건부** — Jokić ≤ $88

> Jokić가 AST·A/T(+0.241)를 공급하므로 PG를 최저가로 때우고 Derrick White(A/T +0.171 · FT% 90.2% · BLK 1.3)를 붙인다. 잉여가 +$4뿐이라 시장가를 지불하는 플랜 — 앵커를 시장가 이하로 잡았을 때만 발동하는 조건부.

**계획 $199** · 빅맨 $145/$153 (C자격 5명) · 예산여유 **$1** · 노리는 캣 11개 `PTS FG% REB OREB AST A/T DD BLK 3PM FT% 3P%` · 포기 `TOV STL`

### 기본 플랜

| 슬롯 | 계획가 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|
| **C** `앵커` | $88 | **0** (상한 $88 · 실패→코어전환 C6) | 앵커 (실패 시 코어 전환) | **Nikola Jokić** | — | — |
| **SG** `앵커` | $44 | **0** (상한 $44 · 실패→치환 Fox) | A/T +0.171 · FT% 90.2% · BLK 1.3 | **Derrick White** | De'Aaron Fox $28 | Dennis Schröder $12 |
| **PF** | $29 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** | Evan Mobley $27 | Paolo Banchero $30 |
| **UTIL** | $14 | — | OREB 4.5 리그 1위 | **Donovan Clingan** | Rudy Gobert $12 | Mitchell Robinson $8 |
| **UTIL** | $12 | — | OREB+BLK+DD 빅 | **Rudy Gobert** | Ivica Zubac $13 | Mark Williams $9 |
| **BN** | $6 | — | 3PT% 레버리지 3위 · 3PM 3.0 | **Sam Merrill** | AJ Green $4 | Miles McBride $4 |
| **SF** | $2 | — | 3PM 고볼륨 저가 | **Tim Hardaway Jr.** | Duncan Robinson $4 | Royce O'Neale $2 |
| **PG** | $2 | — | A/T 다트 | **Andrew Nembhard** | Cam Spencer $2 | Davion Mitchell $2 |
| **BN** | $2 | — | OREB 다트 | **Andre Drummond** | Moussa Diabaté $2 | Ryan Kalkbrenner $2 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Rudy Gobert > $18`

> Jokić가 REB·OREB·DD를 혼자 상당 부분 커버하므로 빅맨 수를 줄이는 여지가 가장 크다. UTIL 한 칸을 3P% 윙(AJ Green)으로 전환.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| UTIL | Donovan Clingan → **Mitchell Robinson** | $8 | -6 |
| UTIL | Rudy Gobert → **AJ Green** | $4 | -8 |
| PF | Alperen Şengün 지불 상향 | $32 | +3 |
| SF | Tim Hardaway Jr. → **Duncan Robinson** | $4 | +2 |
| BN | Andre Drummond → **Mark Williams** | $9 | +7 |

**피벗 최종 9인** — 총액 $197 · 빅맨 $137 (C자격 4명) · 노리는 캣 `PTS FG% REB OREB AST A/T DD BLK 3PM FT% 3P%` · 포기 `TOV STL`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| C | Nikola Jokić `C` | $88 |
| SG | Derrick White | $44 |
| PF | Alperen Şengün `C` | $32 |
| UTIL | Mitchell Robinson `C` | $8 |
| UTIL | AJ Green | $4 |
| BN | Sam Merrill | $6 |
| SF | Duncan Robinson | $4 |
| PG | Andrew Nembhard | $2 |
| BN | Mark Williams `C` | $9 |

---

## 코어 3 · SGA + 저가 빅 4인

**우선 3** — 센터가 조금 비싸지만 SGA ≤ $72

> 가드가 FG% 55.1% + FT% 87.9%. 빅맨 예산 $77(계획 총액의 39%)로 6개 코어 중 최저 — 빅맨 시장 과열에 가장 강하다. ⚠️ 'SGA의 FT%가 빅맨 FT% 붕괴를 상쇄한다'는 주장은 FTA 볼륨 데이터가 없어 검증되지 않았습니다. SGA 득점은 출처 충돌(StatMuse 31.1 / Yahoo 27.6)이 있어 리더보드값을 채택했습니다.

**계획 $199** · 빅맨 $77/$85 (C자격 5명) · 예산여유 **$1** · 노리는 캣 10개 `PTS FG% FT% REB OREB BLK DD AST STL 3P%` · 포기 `TOV A/T`

### 기본 플랜

| 슬롯 | 계획가 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|
| **SG** `앵커` | $72 | **0** (상한 $72 · 실패→코어전환 C4) | 앵커 (실패 시 코어 전환) | **Shai Gilgeous-Alexander** | — | — |
| **PF** | $29 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** | Evan Mobley $27 | Paolo Banchero $30 |
| **SF** | $29 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $13 | Jaden McDaniels $9 |
| **PG** | $15 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $6 | Cason Wallace $6 |
| **C** | $14 | — | OREB 4.5 리그 1위 · 77G | **Donovan Clingan** | Jalen Duren $31 | Rudy Gobert $12 |
| **UTIL** | $13 | — | DD 24 · 롤맨 빅 | **Ivica Zubac** | Mitchell Robinson $8 | Deandre Ayton $8 |
| **UTIL** | $12 | — | OREB 3.9 · BLK 1.6 · 76G | **Rudy Gobert** | Mark Williams $9 | Nic Claxton $6 |
| **BN** | $9 | — | OREB 3.1 주전 C | **Mark Williams** | Deandre Ayton $8 | Neemias Queta $2 |
| **BN** | $6 | — | 3PT% 레버리지 3위 | **Sam Merrill** | AJ Green $4 | Isaiah Joe $4 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Rudy Gobert > $18` · `Ivica Zubac > $16`

> 이미 빅맨 예산 최저($77)인 코어. 최저가 빅맨으로 내리고 절감분 전부를 3PM·3P% 고볼륨(Knueppel)으로.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| C | Donovan Clingan → **Nic Claxton** | $6 | -8 |
| UTIL | Rudy Gobert → **Neemias Queta** | $2 | -10 |
| BN | Sam Merrill → **Kon Knueppel** | $25 | +19 |

**피벗 최종 9인** — 총액 $200 · 빅맨 $59 (C자격 5명) · 노리는 캣 `PTS FG% FT% REB OREB BLK DD AST STL 3P%` · 포기 `TOV A/T`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| SG | Shai Gilgeous-Alexander | $72 |
| PF | Alperen Şengün `C` | $29 |
| SF | Amen Thompson | $29 |
| PG | Dyson Daniels | $15 |
| C | Nic Claxton `C` | $6 |
| UTIL | Ivica Zubac `C` | $13 |
| UTIL | Neemias Queta `C` | $2 |
| BN | Mark Williams `C` | $9 |
| BN | Kon Knueppel | $25 |

---

## 코어 4 · 무앵커 분산 (상한 $31)

**우선 4** — 앵커를 못 잡았지만 센터는 정상가

> 잉여가 $8~31 구간에 몰려 있으므로 그 구간만으로 9칸을 채운다. 최고가 $31로 결장 리스크가 분산되고 앵커 실패에 면역 — 가장 현실적인 기본 플랜. ⚠️ PTS·TOV 포기가 실제로 나머지 7캣 승리로 이어지는지는 검증되지 않았습니다.

**계획 $194** · 빅맨 $105/$107 (C자격 4명) · 예산여유 **$6** · 노리는 캣 10개 `FG% REB OREB BLK DD AST STL 3PM 3P% FT%` · 포기 `PTS TOV` · 단일 상한 $31

### 기본 플랜

| 슬롯 | 계획가 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|
| **C** | $31 | — | OREB 3.8 · DD 41 · 70G | **Jalen Duren** | Donovan Clingan $14 | Ivica Zubac $13 |
| **PF** | $31 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** | Evan Mobley $27 | Paolo Banchero $30 |
| **SF** | $29 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $13 | Jaden McDaniels $9 |
| **UTIL** | $27 | — | OREB+BLK+DD | **Evan Mobley** | Paolo Banchero $30 | Walker Kessler $18 |
| **SG** | $25 | — | 3PT% 레버리지 2위 · 3PM 3.4 | **Kon Knueppel** | Desmond Bane $26 | Sam Merrill $6 |
| **PG** | $18 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $6 | Cason Wallace $6 |
| **UTIL** | $16 | — | OREB 3.9 · 76G | **Rudy Gobert** | Mark Williams $9 | Mitchell Robinson $8 |
| **BN** | $15 | — | PTS+REB+DD 포워드 | **Julius Randle** | Paul George $13 | Josh Hart $5 |
| **BN** | $2 | — | A/T +0.261 리그 2위 | **T.J. McConnell** | Dennis Schröder $7 | Andrew Nembhard $2 |

### 과열 피벗

**트리거**: `Evan Mobley > $30` · `Rudy Gobert > $18`

> 상한 $31을 유지한 채 UTIL 한 칸을 빅맨에서 윙(Bane)으로 전환. Duren이 $34를 넘으면 피벗이 아니라 코어 전환(→ 코어 7).

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| UTIL | Evan Mobley → **Walker Kessler** | $18 | -9 |
| UTIL | Rudy Gobert → **Desmond Bane** | $26 | +10 |

**피벗 최종 9인** — 총액 $195 · 빅맨 $80 (C자격 3명) · 노리는 캣 `FG% REB OREB BLK DD AST STL 3PM 3P% FT%` · 포기 `PTS TOV`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| C | Jalen Duren `C` | $31 |
| PF | Alperen Şengün `C` | $31 |
| SF | Amen Thompson | $29 |
| UTIL | Walker Kessler `C` | $18 |
| SG | Kon Knueppel | $25 |
| PG | Dyson Daniels | $18 |
| UTIL | Desmond Bane | $26 |
| BN | Julius Randle | $15 |
| BN | T.J. McConnell | $2 |

---

## 코어 5 · Sabonis 부상 할인 (조건부 베팅)

**우선 격리** — Sabonis 건강 확인 + ≤ $26

> ⚠️ 격리된 별도 베팅안. Sabonis 건강이 프리시즌에 확인될 때만 발동. 실출장 ~20경기이고 A/T 한계기여는 −0.102로 마이너스 — 정상 복귀를 기본값으로 두면 위험합니다. 헤지 빅 2명을 필수로 붙입니다.

**계획 $192** · 빅맨 $86/$96 (C자격 5명) · 예산여유 **$8** · 노리는 캣 11개 `FG% REB OREB DD BLK AST A/T TOV 3PM 3P% STL` · 포기 `FT% PTS`

### 기본 플랜

| 슬롯 | 계획가 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|
| **PG** `앵커` | $50 | **0** (상한 $50 · 실패→치환 Giddey) | A/T +0.517 리그 1위 | **Tyrese Haliburton** | Josh Giddey $42 | De'Aaron Fox $28 |
| **SF** | $29 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $13 | Jaden McDaniels $9 |
| **UTIL** | $27 | — | Sabonis 헤지 빅 ① | **Evan Mobley** | Paolo Banchero $30 | Walker Kessler $18 |
| **SG** | $25 | — | 3PT% 레버리지 2위 | **Kon Knueppel** | Desmond Bane $26 | Sam Merrill $6 |
| **PF** `앵커` | $26 | **$8** (상한 $34 · 실패→코어전환 C6) | 앵커 (부상 할인 · 실패 시 코어 전환) | **Domantas Sabonis** | — | — |
| **C** | $12 | — | Sabonis 헤지 빅 ② (필수) | **Donovan Clingan** | Jalen Duren $31 | Rudy Gobert $12 |
| **UTIL** | $13 | — | DD 24 · Hali 픽앤롤 시너지 | **Ivica Zubac** | Mitchell Robinson $8 | Mark Williams $9 |
| **BN** | $8 | — | OREB 2.6 · DD 22 | **Deandre Ayton** | Nic Claxton $6 | Neemias Queta $2 |
| **BN** | $2 | — | A/T 다트 | **T.J. McConnell** | Andrew Nembhard $2 | Davion Mitchell $2 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Ivica Zubac > $16`

> Sabonis 자체가 부상 할인 자산이라 빅맨 과열 영향이 가장 작다. 헤지 빅을 최저가로 내리고 절감분을 3PM·FT%·STL 윙(Murphy)으로.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| C | Donovan Clingan → **Mark Williams** | $9 | -5 |
| UTIL | Ivica Zubac → **Nic Claxton** | $6 | -7 |
| SG | Kon Knueppel → **Trey Murphy III** | $32 | +7 |
| SF | Amen Thompson 지불 상향 | $32 | +3 |

**피벗 최종 9인** — 총액 $192 · 빅맨 $76 (C자격 5명) · 노리는 캣 `FG% REB OREB DD BLK AST A/T TOV 3PM 3P% STL` · 포기 `FT% PTS`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| PG | Tyrese Haliburton | $50 |
| SF | Amen Thompson | $32 |
| UTIL | Evan Mobley `C` | $27 |
| SG | Trey Murphy III | $32 |
| PF | Domantas Sabonis `C` | $26 |
| C | Mark Williams `C` | $9 |
| UTIL | Nic Claxton `C` | $6 |
| BN | Deandre Ayton `C` | $8 |
| BN | T.J. McConnell | $2 |

---

## 코어 6 · A/T 분산 조달 (정상 시장 기본값)

**우선 2** — 센터 정상가 + Hali 불확실/비쌈

> A/T 한계기여를 McConnell(+0.261) + DeRozan(+0.152) = +0.413($21)으로 분산 조달. Haliburton 단독(+0.517, $50)의 80%를 42% 가격에 확보하고 절감분으로 KAT 앵커까지 붙인다. ⚠️ 아킬레스 리스크는 없지만 A/T 리스크가 없는 것은 아니다 — McConnell은 Hali·Nembhard 뒤 3번째 가드이고, DeRozan 대체안(Schröder +0.110 / D.Russell +0.017)은 A/T 질이 크게 떨어진다. McConnell을 $6 이내에 못 잡으면 노리는 캣 12개 표기를 즉시 낮춰 읽어야 한다. 빅맨 총액 $113 상한도 생존 조건.

**계획 $185** · 빅맨 $96/$113 (C자격 4명) · 예산여유 **$15** · 노리는 캣 12개 `FG% REB OREB DD BLK AST A/T TOV STL 3PM 3P% FT%` · 포기 `PTS`

### 기본 플랜

| 슬롯 | 계획가 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|
| **C** `앵커` | $50 | **$12** (상한 $62 · 실패→치환 Duren) | 앵커 · DD 56 리그 1위 | **Karl-Anthony Towns** | Jalen Duren $34 | Alperen Şengün $32 |
| **PF** | $29 | — | OREB 3.0 · DD 34 · AST | **Alperen Şengün** | Evan Mobley $27 | Paolo Banchero $30 |
| **SF** | $29 | — | 가드형 OREB 3.0 · 79G | **Amen Thompson** | Toumani Camara $13 | Jaden McDaniels $9 |
| **BN** | $25 | — | 3PT% 레버리지 2위 · 3PM 3.4 | **Kon Knueppel** | Desmond Bane $26 | Sam Merrill $6 |
| **BN** | $15 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $6 | Cason Wallace $6 |
| **UTIL** | $9 | — | OREB 4.5 리그 1위 · 77G | **Donovan Clingan** | Rudy Gobert $12 | Mitchell Robinson $8 |
| **SG** `앵커` | $16 | **0** (상한 $16 · 실패→치환 Schröder) | A/T +0.152 · TOV 1.2 · FT% 86.8% | **DeMar DeRozan** | Dennis Schröder $10 | D'Angelo Russell $8 |
| **UTIL** | $8 | — | OREB+BLK+DD 빅 | **Rudy Gobert** | Ivica Zubac $13 | Mark Williams $9 |
| **PG** `앵커` | $4 | **$10** (상한 $14 · 실패→치환 Nembhard) | A/T +0.261 리그 2위 · TOV 1.1 | **T.J. McConnell** | Andrew Nembhard $4 | Davion Mitchell $3 |

### 과열 피벗

**트리거**: `Donovan Clingan > $22` · `Rudy Gobert > $18`

> ⚠ 정상 시장 기본값 코어의 생존 분기. 빅맨을 4명→3명($96)으로 줄이고 앵커 KAT 지불을 $56까지 올린다(최대 $62). 벤치 두 칸은 Daniels→Ausar Thompson(STL 2.0 동일, $9 절감) / Knueppel→Trey Murphy III(3PM+FT% 88.6+STL 1.5). 저가 빅 3명 이상이 과열되면 피벗이 아니라 코어 7로 전환.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| C | Karl-Anthony Towns 지불 상향 | $56 | +6 |
| UTIL | Donovan Clingan → **Mitchell Robinson** | $8 | -6 |
| UTIL | Rudy Gobert → **Sam Merrill** | $6 | -6 |
| BN | Dyson Daniels → **Ausar Thompson** | $6 | -9 |
| BN | Kon Knueppel → **Trey Murphy III** | $32 | +7 |
| PG | T.J. McConnell 지불 상향 | $8 | +4 |
| PF | Alperen Şengün 지불 상향 | $32 | +3 |

**피벗 최종 9인** — 총액 $193 · 빅맨 $96 (C자격 3명) · 노리는 캣 `FG% REB OREB DD BLK AST A/T TOV STL 3PM 3P% FT%` · 포기 `PTS`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| C | Karl-Anthony Towns `C` | $56 |
| PF | Alperen Şengün `C` | $32 |
| SF | Amen Thompson | $29 |
| BN | Trey Murphy III | $32 |
| BN | Ausar Thompson | $6 |
| UTIL | Mitchell Robinson `C` | $8 |
| SG | DeMar DeRozan | $16 |
| UTIL | Sam Merrill | $6 |
| PG | T.J. McConnell | $8 |

---

## 코어 7 · 반센터 인플레 (센터 붕괴 시 최우선)

**우선 0** — 저가 센터 계층 과열 2명 이상

> 저가 센터 시장이 붕괴했을 때의 독립 플랜. C 자격을 최소 2명(Turner·Naz Reid, 합 $28)만 확보하고 저가 OREB 전문 센터를 전제로 쓰지 않는다 — Clingan·Gobert·M.Robinson·Zubac·Ayton·Diabaté 누구도 필요하지 않다. OREB·DD·BLK·FG%를 의도적으로 포기하고 PTS·3PM·3P%·FT%·AST·A-T·STL·TOV 8캣으로 승부한다. REB는 Jalen Johnson(10.3)이 포워드로 커버해 완전 포기를 면한다.

**계획 $188** · 빅맨 $25/$36 (C자격 2명) · 예산여유 **$12** · 노리는 캣 8개 `PTS 3PM 3P% FT% AST A/T STL TOV` · 포기 `OREB DD BLK FG%`

### 기본 플랜

| 슬롯 | 계획가 | 여력 | 역할 | 1순위 | 대체 ① | 대체 ② |
|---|---|---|---|---|---|---|
| **PF** `앵커` | $56 | **0** (상한 $56 · 실패→피벗) | 앵커 · 22.5P 10.3R 7.9A · DD 49 | **Jalen Johnson** | Toumani Camara $13 | Jaden McDaniels $9 |
| **PG** `앵커` | $28 | **0** (상한 $28 · 실패→치환 Schröder) | A/T +0.130 · AST 6.2 · STL | **De'Aaron Fox** | Dennis Schröder $10 | D'Angelo Russell $8 |
| **SG** | $22 | — | 3PT% 42.5 on 7.9시도 · 3PM 3.4 | **Kon Knueppel** | Desmond Bane $26 | Sam Merrill $6 |
| **SF** | $22 | — | FT% 90.2 리그 4위 · STL 1.3 | **Nickeil Alexander-Walker** | Trey Murphy III $32 | Toumani Camara $13 |
| **C** | $17 | — | BLK 1.6 + 3PM — OREB형 아님 | **Myles Turner** | Kristaps Porziņģis $12 | John Collins $11 |
| **UTIL** `앵커` | $16 | **0** (상한 $16 · 실패→치환 Schröder) | A/T +0.152 · TOV 1.2 · FT% | **DeMar DeRozan** | Dennis Schröder $10 | D'Angelo Russell $8 |
| **UTIL** | $15 | — | STL 2.0 리그 공동 1위 | **Dyson Daniels** | Ausar Thompson $6 | Cason Wallace $6 |
| **BN** | $8 | — | 3PM 2.1 + BLK 1.0 · 77G | **Naz Reid** | Brook Lopez $4 | Onyeka Okongwu $10 |
| **BN** `앵커` | $4 | **$10** (상한 $14 · 실패→치환 Nembhard) | A/T +0.261 리그 2위 · TOV 1.1 | **T.J. McConnell** | Andrew Nembhard $4 | Davion Mitchell $3 |

### 과열 피벗

**트리거**: `Jalen Johnson > $58`

> 코어 7의 유일한 고가 자산(Jalen Johnson)이 막히면 그 예산을 A/T 최상위(Haliburton +0.517)와 3PM·FT% 윙(Murphy)으로 재배치한다. 빅맨은 여전히 2명($30)만 유지 — 센터 시장과 무관하게 성립하는 것이 이 코어의 존재 이유.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| PF | Jalen Johnson → **Toumani Camara** | $13 | -43 |
| PG | De'Aaron Fox → **Tyrese Haliburton** | $50 | +22 |
| SF | Nickeil Alexander-Walker → **Trey Murphy III** | $32 | +10 |
| UTIL | Dyson Daniels 지불 상향 | $18 | +3 |
| C | Myles Turner 지불 상향 | $18 | +1 |
| BN | Naz Reid 지불 상향 | $12 | +1 |

**피벗 최종 9인** — 총액 $189 · 빅맨 $30 (C자격 2명) · 노리는 캣 `PTS 3PM 3P% FT% AST A/T STL TOV` · 포기 `OREB DD BLK FG%`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| PF | Toumani Camara | $13 |
| PG | Tyrese Haliburton | $50 |
| SG | Kon Knueppel | $26 |
| SF | Trey Murphy III | $32 |
| C | Myles Turner `C` | $18 |
| UTIL | DeMar DeRozan | $16 |
| UTIL | Dyson Daniels | $18 |
| BN | Naz Reid `C` | $12 |
| BN | T.J. McConnell | $4 |

#### 백업 규칙 (1차 피벗 실행 불가 시)

**발동 조건** (`AND`): `Jalen Johnson > $58` **그리고** `Tyrese Haliburton > $50`

> Hali까지 막히면 코어 7 기본안의 저가 대체(Camara $13 · McDaniels $9)로 내려가는 대신, 절감분을 고득점 가드·윙(Donovan Mitchell $48 · Trey Murphy III $32)과 F 전용 포워드(Julius Randle $15)로 재배치한다. 빅맨은 여전히 2명($28)만 유지 — 센터 시장과 무관하다는 코어 7의 전제를 지킨다. 대가로 STL이 2.0→1.5급으로 약화되어 포기 캣에 들어간다.

| 슬롯 | 변경 | 계획가 | 증감 |
|---|---|---|---|
| PF | Jalen Johnson → **Julius Randle** | $15 | -41 |
| SF | Nickeil Alexander-Walker → **Trey Murphy III** | $32 | +10 |
| UTIL | Dyson Daniels → **Donovan Mitchell** | $48 | +33 |

**백업 최종 9인** — 총액 $197 · 빅맨 $28 (C자격 2명) · 노리는 캣 `PTS 3PM 3P% FT% AST A/T TOV` · 포기 `OREB DD BLK FG% STL`

| 슬롯 | 선수 | 계획가 |
|---|---|---|
| PF | Julius Randle | $15 |
| PG | De'Aaron Fox | $28 |
| SG | Kon Knueppel | $26 |
| SF | Trey Murphy III | $32 |
| C | Myles Turner `C` | $17 |
| UTIL | DeMar DeRozan | $16 |
| UTIL | Donovan Mitchell | $48 |
| BN | Naz Reid `C` | $11 |
| BN | T.J. McConnell | $4 |

---

## 자동 검증 (`python3 validate.py`)

| 규칙 | 적용 대상 | 상태 |
|---|---|---|
| 9개 슬롯 완성 | 기본 7 + 피벗 7 + 백업 1 | ✅ |
| `market_low ≤ plan_price ≤ my_max` | 1순위 + 대체 후보 전부 | ✅ |
| PG/SG→G · SF/PF→F · C→C 자격 | 1순위 + 대체 후보 전부 | ✅ |
| 총액 ≤ $200 | 전 15개 플랜 | ✅ |
| 빅맨 예산 ≤ `big_budget_cap` | 전 15개 플랜 | ✅ |
| 장기 부상 제외 준수 | 1순위 + 대체 + 피벗 + 백업 | ✅ |
| 노리는 캣/포기 캣 명시 | 피벗 7 + 백업 1 | ✅ |
| 트리거·백업 조건이 임계값 단일 소스와 일치 | 피벗 7 + 백업 1 | ✅ |
| 선수 중복 없음 | 전 15개 플랜 | ✅ |
| 판단표가 7개 코어 전부 포함 · 우선 0 = 코어 7 | 판단표 | ✅ |
| 판단표 임계값 ≤ `my_max` | 판단표 | ✅ |

**총 15개 플랜(기본 7 + 피벗 7 + 백업 1) · 위반 0건**

## 드래프트 직전 필수 확인

| 항목 | 이유 |
|---|---|
| **야후 실제 포지션 자격** | 데이터는 G/F/C 수준만 저장 |
| **T.J. McConnell 출장 역할** | 코어 6 A/T의 63% 담당 · 인디애나 3번째 가드 |
| **지명 시 자동 $1 입찰 여부** | 태우기 지명 전략의 전제 |
| **초반 5~10명 실낙찰가** | 툴 `시장가 보정` 입력 → `보정 적용` 토글 |