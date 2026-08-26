# 선수 가치 평가 · 방법론과 결과

선수 174명. 전원 `measured_2025_26` 필드 보유(루키 3명은 '실적 없음' 명시).
전체 데이터: `data/players.json` / `data/players.csv`

## 평가 사슬

각 선수는 세 단계로 평가되며 툴에서 이 순서로 표시됩니다.

```
실측 25-26   →   팀 변화(2026 오프시즌)   →   13캣 판정 → 내 최대가
```

**검증 기준**: 2025-26 리그 리더보드 9종(BLK · STL · OREB · 3PT% · FT% · A/T ×2 · PTS · DD)
대조 + 개별 시즌 스탯 34명 조회.

📂 **원본 데이터 전체: `data/stats_2025_26/`** — 리더보드 211행, 개별 스탯 34명, 커버리지 표.
아래 모든 수치를 여기서 역추적할 수 있습니다. 출처 URL은 `SOURCES.md`.

⚠️ 리더보드는 **상위 25위까지만** 확보됐습니다. 26위 이하는 "top-25 밖"이라는 사실만 알고
정확한 값은 모릅니다 — `05-limitations.md` 2b번.

## 파생 지표

### 잉여 = 내 최대가 − 시장 중간값
플러스면 시장보다 내 평가가 높은 구간 = 실제 승부처. **122명이 잉여 플러스.**

### 획득 가능성 = 내 최대가 ≥ 시장 하단
최대가가 시장 하단보다 낮으면 낙찰 자체가 불가능 → 계획에서 제외. **35명 획득 불가.**

### 실측 근거 (14차부터 전체 스탯)
`data/stats_2025_26/measured_full.json` — Basketball Reference 리그 전체 per-game,
DB 174명 중 **171명 매칭**(2시즌 GP 가중 혼합 · 최근 시즌 ×1.5).
미매칭 3명은 NBA 무경력 루키(Dybantsa·Boozer·Peterson)입니다.
13캣 중 12캣 커버(DD만 공백). 시도량(`FGA`·`FTA`·`3PA`)이 있어 비율 캣도 레버리지 계산 가능.
**가중치 자격 기준 `GP >= 40`** — 자격자 150명. 미달 24명은 `weights_data_verified: false`.

### 볼륨 레버리지 (비율 캣 전용)
비율 캣은 팀 합계 기준이므로 rate가 아니라 **시도량 지분**만큼만 기여합니다.

```
레버리지(pp) = (내 주간 시도 / 팀 주간 시도) × (내 rate − 리그평균)
변동성(pp)   = sqrt(p(1-p)/n),  n = 주간 시도수
가정: 선발 7명 · 주간 3.5경기 · 팀 주간 3PA 135 · 리그평균 3PT% 36.0%
```

이 계산이 저볼륨 특화 선수 평가를 뒤집었습니다:

<!-- GEN:leverage — tool/gen_docs03.py 가 생성. 직접 수정하지 마라 -->
| 선수 | 3PA/G | 주간시도 | 지분 | 3PT% | 레버리지 | 변동성 |
|---|---|---|---|---|---|---|
| Kon Knueppel | 7.9 | 28 | 20.5% | 42.5% | **+1.25pp** | ±9.4pp |
| Jamal Murray | 6.9 | 24 | 17.9% | 41.9% | **+0.99pp** | ±10.0pp |
| AJ Green | 6.3 | 22 | 16.3% | 42.2% | **+0.95pp** | ±10.5pp |
| Luke Kennard | 3.4 | 12 | 8.9% | 46.2% | **+0.87pp** | ±14.4pp |
| Cameron Johnson | 5.7 | 20 | 14.9% | 41.3% | **+0.74pp** | ±11.0pp |
| **Josh Hart** | 3.5 | 12 | 9.1% | 37.8% | +0.13pp (최하) | ±13.8pp |

기준선 3PT% 36.4%(`cat_baselines`) · 주간 3.5경기 · 팀 주간 3PA 135 가정. 변동성은 이항 SD √(p(1−p)/주간시도). 대상 19명 중 상위 5 + 최하 1.
<!-- /GEN:leverage -->

→ **rate 리그 1위인 Kennard의 레버리지는 그룹 8위, 변동성은 1위.** 주간 11시도로는
한 경기 0/4에 그 주 비율이 무너지고 볼륨으로 상쇄할 수도 없음. 같은 논리를 FT%에도 적용.

## 잉여 상위 20 (실제 승부처)

<!-- GEN:surplus — tool/gen_docs03.py 가 생성. 직접 수정하지 마라 -->
| 잉여 | 시장중간 | 최대가 | 포지션 | 선수 | 실측(BBRef) |
|---|---|---|---|---|---|
| +$22 | $12 | $34 | C | **Donovan Clingan** | 10P 10.2R 1.7A 0.6S 1.7B 1.2TO · OREB 4 · FG 52.7% (7.5FGA) · 3P 32.1% (2.3×) 0.8×3PM · FT 64.9% (2.2FTA) · 혼합 GP 73.3 · 24.5MPG · 25-26 63% |
| +$20 | $26 | $46 | F/C | **Alperen Şengün** | 19.9P 9.5R 5.7A 1.2S 1B 3TO · OREB 3.2 · FG 50.9% (15.4FGA) · 3P 27.5% (1.6×) 0.5×3PM · FT 69.1% (5.4FTA) · 혼합 GP 73.7 · 32.6MPG · 25-26 58% |
| +$19 | $27 | $46 | C | **Jalen Duren** | 16.2P 10.4R 2.3A 0.8S 0.9B 1.8TO · OREB 3.7 · FG 66.8% (9.6FGA) · 3P — (0×) 0×3PM · FT 71.4% (4.8FTA) · 혼합 GP 73.4 · 27.3MPG · 25-26 57% |
| +$19 | $5 | $12 | C | **Mitchell Robinson** | 5.6P 8.3R 0.9A 0.9S 1.2B 0.7TO · OREB 4 · FG 71.3% (3.4FGA) · 3P — (0×) 0×3PM · FT 45.2% (1.6FTA) · 혼합 GP 53.2 · 19.2MPG · 25-26 84% |
| +$18 | $8 | $26 | C | **Rudy Gobert** | 11.3P 11.3R 1.7A 0.8S 1.5B 1.3TO · OREB 3.8 · FG 67.7% (6.7FGA) · 3P 0.0% (0.1×) 0×3PM · FT 58.3% (3.9FTA) · 혼합 GP 74.5 · 32MPG · 25-26 61% |
| +$17 | $45 | $62 | F/C | **Karl-Anthony Towns** | 21.8P 12.3R 3A 0.9S 0.6B 2.6TO · OREB 3 · FG 51.1% (15FGA) · 3P 38.8% (4.3×) 1.7×3PM · FT 84.7% (5.6FTA) · 혼합 GP 73.8 · 32.6MPG · 25-26 61% |
| +$16 | $26 | $42 | G/F | **Amen Thompson** | 16.8P 7.9R 4.7A 1.5S 0.9B 2.3TO · OREB 2.9 · FG 54.2% (12.1FGA) · 3P 23.8% (1.4×) 0.3×3PM · FT 74.4% (4.4FTA) · 혼합 GP 75.3 · 35.5MPG · 25-26 63% |
| +$15 | $19 | $34 | F/C | **Domantas Sabonis** | 18.1P 13.2R 5.5A 0.8S 0.3B 2.8TO · OREB 3.7 · FG 57.6% (12.5FGA) · 3P 35.0% (2×) 0.7×3PM · FT 74.6% (4.1FTA) · 혼합 GP 55.2 · 33.3MPG · 25-26 28% |
| +$13 | $23 | $36 | F/C | **Evan Mobley** | 18.3P 9.1R 3.4A 0.8S 1.7B 1.9TO · OREB 2.4 · FG 55.1% (13FGA) · 3P 32.8% (3.2×) 1.1×3PM · FT 65.6% (4.5FTA) · 혼합 GP 67.5 · 31.3MPG · 25-26 57% |
| +$13 | $5 | $18 | C | **Deandre Ayton** | 13P 8.6R 1A 0.7S 1B 1.3TO · OREB 2.7 · FG 64.3% (9.2FGA) · 3P 18.8% (0.2×) 0.1×3PM · FT 65.1% (1.9FTA) · 혼합 GP 63.4 · 28MPG · 25-26 73% |
| +$12 | $2 | $14 | G | **T.J. McConnell** | 9.3P 2.3R 4.8A 1S 0.2B 1.2TO · OREB 0.5 · FG 52.9% (8FGA) · 3P 31.3% (0.8×) 0.3×3PM · FT 80.3% (0.7FTA) · 혼합 GP 67.1 · 17.5MPG · 25-26 51% |
| +$11 | $7 | $18 | C | **Mark Williams** | 12.9P 8.7R 1.5A 0.8S 1B 1.3TO · OREB 3.1 · FG 63.1% (8.3FGA) · 3P 67.2% (0×) 0×3PM · FT 78.2% (3.2FTA) · 혼합 GP 54.7 · 24.6MPG · 25-26 67% |
| +$11 | $2 | $8 | G | **Sam Merrill** | 10.1P 2.4R 2A 0.6S 0.1B 0.7TO · OREB 0.5 · FG 43.5% (7.7FGA) · 3P 39.8% (6.2×) 2.5×3PM · FT 90.8% (0.9FTA) · 혼합 GP 61.1 · 23.3MPG · 25-26 52% |
| +$9 | $2 | $11 | F/C | **Bobby Portis** | 13.8P 7.1R 1.8A 0.6S 0.3B 1.1TO · OREB 1.5 · FG 48.1% (11.5FGA) · 3P 42.6% (4.1×) 1.8×3PM · FT 74.9% (1.2FTA) · 혼합 GP 61.1 · 24.6MPG · 25-26 67% |
| +$9 | $2 | $11 | G | **AJ Green** | 9.2P 2.6R 1.7A 0.5S 0.1B 0.8TO · OREB 0.3 · FG 42.6% (7.1FGA) · 3P 42.2% (6.3×) 2.7×3PM · FT 84.0% (0.6FTA) · 혼합 GP 76.1 · 26.6MPG · 25-26 61% |
| +$8 | $12 | $20 | G | **Dyson Daniels** | 12.8P 6.4R 5.3A 2.4S 0.5B 1.9TO · OREB 2.1 · FG 50.7% (11FGA) · 3P 24.9% (2.1×) 0.6×3PM · FT 60.6% (1.7FTA) · 혼합 GP 76 · 33.4MPG · 25-26 60% |
| +$8 | $4 | $12 | C | **Nic Claxton** | 11.1P 7.1R 3.1A 0.8S 1.2B 1.3TO · OREB 2.3 · FG 56.8% (8.3FGA) · 3P 19.0% (0.3×) 0×3PM · FT 57.4% (2.9FTA) · 혼합 GP 69.4 · 27.4MPG · 25-26 59% |
| +$8 | $2 | $10 | G | **Isaiah Joe** | 10.7P 2.5R 1.4A 0.7S 0.2B 0.6TO · OREB 0.5 · FG 44.9% (7.7FGA) · 3P 41.8% (6.1×) 2.5×3PM · FT 86.4% (1.3FTA) · 혼합 GP 72.2 · 21.4MPG · 25-26 59% |
| +$8 | $2 | $10 | G/F | **Tim Hardaway Jr.** | 12.5P 2.5R 1.5A 0.5S 0.1B 0.5TO · OREB 0.2 · FG 43.1% (9.3FGA) · 3P 39.2% (6.5×) 2.6×3PM · FT 82.8% (2.3FTA) · 혼합 GP 78.8 · 27.1MPG · 25-26 60% |
| +$8 | $2 | $10 | G | **Collin Sexton** | 16.5P 2.5R 3.6A 0.9S 0.1B 2.3TO · OREB 0.8 · FG 48.3% (12FGA) · 3P 40.3% (4.2×) 1.6×3PM · FT 85.9% (3.9FTA) · 혼합 GP 66.1 · 25.3MPG · 25-26 61% |
<!-- /GEN:surplus -->

→ **잉여 상위 20 중 C 자격이 12명입니다.** 실측 곡선 적용 후 이 편중이 더 커졌습니다 —
이 리그가 네임밸류 빅에 센터 예산의 77%를 쓰고 그 외 센터를 평균 $8.2에 방치하기 때문입니다
(`docs/08` 2절 ③). 시장 상단($50+)에서 잉여가 있는 선수는 없습니다입니다.
**결론이 뒤집혔습니다**: 추정 곡선에서는 "$8~31 구간이 승부처"였지만, 실측 곡선에서는
**이름값 없는 센터가 가장 큰 승부처**입니다. 코어 7(반센터)은 그 경로가 막혔을 때의 보험이고,
기본 경로는 센터를 싸게 쓸어담는 코어 6·1입니다.

## 획득 불가 35명 (시장 상단 대부분)

내 최대가 < 시장 하단 → 낙찰 불가. **전수 검증의 결론은 '시장 상단에 참전하지 않는다'입니다.**

<!-- GEN:unobtainable — tool/gen_docs03.py 가 생성. 직접 수정하지 마라 -->
| 시장 | 내 최대가 | 선수 | 사유 |
|---|---|---|---|
| $90-102 | $70 | Victor Wembanyama | 64경기(55선발) · 같은 값이면 Jokić 우선 |
| $93-101 | $88 | Nikola Jokić | 65경기 · TOV 3.7은 포기 |
| $83-91 | $52 | Luka Dončić | 64경기 · 남이 $80 쓰게 하라 |
| $81-89 | $72 | Shai Gilgeous-Alexander | ⚠ 득점·FT% 출처 충돌 미해소(기준값 채택) · OKC 로드 매니지먼트 · TOV 실측 미확보 |
| $80-86 | $60 | Cade Cunningham | 64경기 · 시장가 그대로라 이득 없음 |
| $72-80 | $40 | Anthony Edwards | 3~4캣 선수 |
| $66-74 | $44 | Tyrese Maxey | Brown·LeBron 합류로 사용률 하락 |
| $65-71 | $48 | Jayson Tatum | 시장가가 13캣 실질보다 높음 |
| $64-70 | $56 | Jalen Johnson | 3PT%·FT%·TOV 미확인 |
| $64-70 | $44 | Scottie Barnes | $44 이하면 매수 · 3PT%/FT% 확인 권장 |
| $61-69 | $25 | Giannis Antetokounmpo | 36경기 · FT% 65% |
| $54-66 | $50 | Tyrese Haliburton | 2025-26 전체 결장(아킬레스) · Nembhard 헤지 필수 · ⚠ 가중치 근거가 2024-25(73경기) — 2025-26 전체 결장 |
| $54-60 | $48 | Donovan Mitchell | 득점·3점·스틸. 클리블랜드 4년 $273M 연장. |
| $52-58 | $46 | Jamal Murray | 빅맨 캣(OREB·BLK·DD) 기여 없음 |
| $49-55 | $40 | Chet Holmgren | 69경기 · AST/OREB 빈약 |
| $45-51 | $26 | Kevin Durant | A/T 최하위권 · 빅맨 캣 전무 |
| $44-50 | $34 | Cooper Flagg | 캣별 임팩트 미확정 |
| $41-47 | $32 | Austin Reaves | 레이커스 4년 $180M 연장. |
| $38-46 | $22 | Kawhi Leonard | GP 리스크 최상급 |
| $35-43 | $34 | Bam Adebayo | Giannis 합류로 사용률 하락 우려 |
| $37-43 | $32 | Jalen Brunson | OREB·DD·BLK 기여 0 |
| $36-42 | $30 | LaMelo Ball | TOV 높음 · GP 리스크 |
| $34-40 | $26 | Stephen Curry | 43경기 · A/T 1.68 하위권 · 빅맨 캣 전무 |
| $34-40 | $24 | Deni Avdija | 포틀랜드에 Morant·Lillard·Holiday 동시 합류 — 사용률 대폭 하락 위험 |
| $32-40 | $17 | Ja Morant | GP 리스크 상습 · FG%·3PT% 약점 |
| $31-39 | $30 | James Harden | TOV 높고 A/T 평범 · 나이 · Donovan Mitchell과 볼 공유 |
| $31-37 | $22 | Jaren Jackson Jr. | 48경기 · 무릎 수술 · OREB/DD 기여 0 |
| $26-32 | $24 | Devin Booker | 빅맨 캣 기여 0 |
| $20-26 | $16 | Jalen Williams | 33경기 · 3PT% 29.9% 악재 |
| $19-25 | $10 | Anthony Davis | 2025-26 20경기(2024-25 51경기 사용) · GP 리스크 · Ayton과 겹침 |
| $12-18 | $10 | Kyrie Irving | 2025-26 전체 결장(ACL) — 가중치 근거는 2024-25 50경기 · 복귀 시점 불확실 |
| $11-17 | $16 | LeBron James | 나이 |
| $5-11 | $2 | Gary Trent Jr. | 매수 대상 아님 — 코어 후보에서 제외됨 |

총 33명 (`obtainable=false` — 내 최대가 < 시장 하단).
<!-- /GEN:unobtainable -->

## 태우기 지명 명단 (tag=burn)

이름값 대비 13캣 가치가 낮아, 남이 시장가에 사가면 그쪽이 손해인 선수.

<!-- GEN:burn — tool/gen_docs03.py 가 생성. 직접 수정하지 마라 -->
| 시장 | 최대가 | div | 선수 | 실측 |
|---|---|---|---|---|
| $83-91 | $52 | -8 | Luka Dončić | 31.7P 7.9R 8.1A 1.7S 0.5B 3.9TO · OREB 0.7 · FG 46.7% (22FGA) · 3P 36.7% (10.4×) 3.8×3PM · FT 78.1% (9.3FTA) · 혼합 GP 59.2 · 35.7MPG · 25-26 65% |
| $72-80 | $40 | -12 | Anthony Edwards | 28.2P 5.3R 4.1A 1.3S 0.7B 3TO · OREB 0.7 · FG 46.9% (20.3FGA) · 3P 39.7% (9.3×) 3.7×3PM · FT 81.5% (6.8FTA) · 혼합 GP 69.3 · 35.6MPG · 25-26 53% |
| $61-69 | $25 | -16 | Giannis Antetokounmpo | 29.2P 11R 6A 0.9S 1B 3.1TO · OREB 2.4 · FG 61.1% (18.3FGA) · 3P 27.2% (1.1×) 0.3×3PM · FT 63.2% (10.3FTA) · 혼합 GP 53.2 · 31.8MPG · 25-26 44% |
| $45-51 | $26 | +17 | Kevin Durant | 26.2P 5.7R 4.6A 0.8S 1B 3.2TO · OREB 0.5 · FG 52.2% (17.8FGA) · 3P 41.9% (5.9×) 2.5×3PM · FT 86.2% (5.9FTA) · 혼합 GP 72.5 · 36.4MPG · 25-26 65% |
| $38-46 | $22 | +18 | Kawhi Leonard | 26.1P 6.3R 3.5A 1.8S 0.4B 2TO · OREB 1 · FG 50.3% (18.7FGA) · 3P 39.4% (6.3×) 2.5×3PM · FT 86.9% (5.5FTA) · 혼합 GP 57.3 · 32MPG · 25-26 72% |
| $31-37 | $22 | -47 | Jaren Jackson Jr. | 20.8P 5.6R 2A 1.2S 1.5B 2.1TO · OREB 1.1 · FG 48.2% (15.7FGA) · 3P 36.6% (5.1×) 1.9×3PM · FT 79.2% (4.8FTA) · 혼합 GP 61.2 · 30MPG · 25-26 49% |
| $19-25 | $10 | +6 | Anthony Davis | 23.1P 11.4R 3.2A 1.2S 2B 2.2TO · OREB 2.8 · FG 51.2% (17.4FGA) · 3P 27.8% (2.2×) 0.6×3PM · FT 75.8% (6.1FTA) · 혼합 GP 39.5 · 32.7MPG · 25-26 37% |
| $11-17 | $18 | -4 | Myles Turner | 13.4P 5.8R 1.5A 0.7S 1.8B 1.4TO · OREB 1.2 · FG 45.7% (10FGA) · 3P 38.8% (5.4×) 2.1×3PM · FT 75.3% (2.8FTA) · 혼합 GP 71.4 · 28.2MPG · 25-26 59% |
| $5-11 | $2 | +14 | Gary Trent Jr. | 9.4P 1.6R 1.2A 0.7S 0B 0.6TO · OREB 0.2 · FG 40.6% (8FGA) · 3P 38.4% (5.6×) 2.1×3PM · FT 80.3% (1FTA) · 혼합 GP 68.9 · 23.1MPG · 25-26 56% |
| $4-10 | $4 | +28 | Luguentz Dort | 9P 3.8R 1.4A 1S 0.4B 0.8TO · OREB 1 · FG 40.5% (7.9FGA) · 3P 37.2% (5.6×) 2.1×3PM · FT 74.2% (0.7FTA) · 혼합 GP 69.8 · 27.8MPG · 25-26 59% |

총 10명. `div`는 `value_reference.rank_divergence` — 양수면 my_max가 가치보다 인색하다는 뜻이고, `validate.py`의 M5가 |div| >= 20 인 burn을 위반으로 잡는다.
<!-- /GEN:burn -->

## $1~8 특화 다트 (tag=dart, 잉여 플러스만)

<!-- GEN:darts — tool/gen_docs03.py 가 생성. 직접 수정하지 마라 -->
| 최대가 | 시장 | 선수 | 캣 | 실측 |
|---|---|---|---|---|
| $14 | $1-3 | T.J. McConnell | A/T3 TOV1 AST1 FG%2 STL1 FT%1 | 9.3P 2.3R 4.8A 1S 0.2B 1.2TO · OREB 0.5 · FG 52.9% (8FGA) · 3P 31.3% (0.8×) 0.3×3PM · FT 80.3% (0.7FTA) · 혼합 GP 67.1 · 17.5MPG · 25-26 51% |
| $10 | $1-3 | Collin Sexton | FT%2 3P%2 | 16.5P 2.5R 3.6A 0.9S 0.1B 2.3TO · OREB 0.8 · FG 48.3% (12FGA) · 3P 40.3% (4.2×) 1.6×3PM · FT 85.9% (3.9FTA) · 혼합 GP 66.1 · 25.3MPG · 25-26 61% |
| $10 | $1-3 | Jerami Grant | 3PM2 3P%1 FT%1 BLK1 TOV1 | 17.1P 3.5R 2.1A 0.8S 0.7B 1.9TO · OREB 0.9 · FG 42.5% (12.6FGA) · 3P 38.1% (6.2×) 2.4×3PM · FT 82.6% (4.9FTA) · 혼합 GP 53.5 · 30.7MPG · 25-26 64% |
| $9 | $1-3 | Duncan Robinson | 3P%3 3PM2 TOV2 A/T1 FT%1 | 11.7P 2.5R 2.2A 0.6S 0.2B 0.9TO · OREB 0.3 · FG 44.9% (9.1FGA) · 3P 40.3% (6.8×) 2.8×3PM · FT 80.6% (1.1FTA) · 혼합 GP 75.8 · 26.1MPG · 25-26 60% |
| $9 | $1-3 | Miles McBride | 3P%2 3PM1 TOV3 A/T2 FT%1 | 10.7P 2.5R 2.8A 1S 0.3B 0.7TO · OREB 0.7 · FG 41.4% (9.2FGA) · 3P 39.1% (5.7×) 2.2×3PM · FT 80.0% (1FTA) · 혼합 GP 52.7 · 25.6MPG · 25-26 49% |
| $12 | $2-8 | Dennis Schröder | AST2 A/T2 FT%1 TOV1 | 11.8P 2.7R 5.1A 0.8S 0.2B 1.8TO · OREB 0.5 · FG 40.5% (9.8FGA) · 3P 33.4% (4×) 1.4×3PM · FT 83.6% (2.9FTA) · 혼합 GP 72.1 · 25.8MPG · 25-26 58% |
| $8 | $1-3 | Nikola Vučević | DD1 REB3 FT%1 TOV1 OREB2 3P%1 FG%2 A/T1 3PM1 | 16.6P 9.1R 3.4A 0.7S 0.6B 1.4TO · OREB 2.2 · FG 50.9% (13.2FGA) · 3P 38.3% (4.3×) 1.7×3PM · FT 81.8% (1.7FTA) · 혼합 GP 67.9 · 29.6MPG · 25-26 56% |
| $8 | $1-3 | Andre Drummond | OREB3 REB2 TOV2 BLK1 | 6.7P 8.2R 1.2A 0.7S 0.7B 1.1TO · OREB 3.1 · FG 48.0% (5.5FGA) · 3P 29.5% (1.1×) 0.4×3PM · FT 62.8% (1.6FTA) · 혼합 GP 56.2 · 19.3MPG · 25-26 70% |
| $8 | $1-3 | Yves Missi | OREB3 BLK3 TOV2 FG%2 REB2 | 7.1P 6.8R 1.3A 0.4S 1.4B 0.9TO · OREB 3.1 · FG 54.5% (5.4FGA) · 3P 0.0% (0×) 0×3PM · FT 58.6% (2.1FTA) · 혼합 GP 69 · 22.7MPG · 25-26 57% |
| $8 | $1-3 | Ryan Kalkbrenner | OREB2 BLK3 FG%3 TOV2 | 7.6P 5.5R 0.8A 0.5S 1.5B 0.9TO · OREB 2.4 · FG 75.3% (4.2FGA) · 3P 0.0% (0.1×) 0×3PM · FT 71.6% (1.7FTA) · 혼합 GP 69 · 21.4MPG · 25-26 100% |
| $8 | $1-3 | Isaiah Stewart | BLK3 OREB1 TOV2 FG%2 | 8.2P 5.2R 1.4A 0.3S 1.5B 1.1TO · OREB 1.7 · FG 55.4% (5.8FGA) · 3P 32.8% (1.5×) 0.5×3PM · FT 75.7% (1.8FTA) · 혼합 GP 64.3 · 21.4MPG · 25-26 54% |
| $8 | $1-3 | Royce O'Neale | 3P%3 3PM2 TOV2 A/T1 | 9.5P 4.8R 2.5A 1S 0.4B 1.1TO · OREB 0.8 · FG 42.2% (7.8FGA) · 3P 40.7% (6.4×) 2.6×3PM · FT 71.9% (0.4FTA) · 혼합 GP 76.8 · 26.9MPG · 25-26 60% |
| $8 | $1-5 | Ausar Thompson | STL3 OREB2 TOV1 BLK1 FG%2 | 10P 5.5R 2.8A 1.9S 0.8B 1.5TO · OREB 2 · FG 52.8% (7.9FGA) · 3P 24.1% (0.5×) 0.1×3PM · FT 59.6% (2.5FTA) · 혼합 GP 68.1 · 24.8MPG · 25-26 65% |
| $8 | $1-5 | Cason Wallace | STL3 TOV2 FT%1 A/T2 | 8.5P 3.2R 2.6A 1.9S 0.4B 0.9TO · OREB 0.9 · FG 44.8% (7.5FGA) · 3P 35.3% (3.5×) 1.2×3PM · FT 81.0% (0.8FTA) · 혼합 GP 73.7 · 27MPG · 25-26 62% |
| $7 | $1-3 | Anthony Black | STL2 TOV1 | 12.5P 3.4R 3.4A 1.3S 0.7B 2TO · OREB 0.7 · FG 43.6% (10.2FGA) · 3P 32.6% (3.7×) 1.2×3PM · FT 74.5% (3.1FTA) · 혼합 GP 70.3 · 27.3MPG · 25-26 55% |
| $10 | $2-8 | Matas Buzelis | BLK3 TOV1 3PM1 | 13.1P 4.9R 1.6A 0.6S 1.3B 1.6TO · OREB 0.9 · FG 45.9% (10.2FGA) · 3P 35.4% (5.1×) 1.8×3PM · FT 79.8% (2.4FTA) · 혼합 GP 78.2 · 25MPG · 25-26 59% |
| $6 | $1-3 | Moussa Diabaté | OREB3 REB2 FG%2 TOV2 BLK2 | 7P 7.7R 1.5A 0.7S 0.8B 1TO · OREB 3.3 · FG 61.7% (4.6FGA) · 3P 30.3% (0×) 0×3PM · FT 63.4% (2.1FTA) · 혼합 GP 72.2 · 22.7MPG · 25-26 60% |
| $6 | $1-3 | Andrew Nembhard | A/T3 AST3 FT%1 | 13.9P 3R 6.5A 1S 0.1B 2.1TO · OREB 0.4 · FG 44.9% (11.1FGA) · 3P 33.1% (4.1×) 1.4×3PM · FT 81.2% (3.2FTA) · 혼합 GP 60.5 · 30.3MPG · 25-26 56% |
| $6 | $1-3 | Neemias Queta | OREB2 REB2 FG%3 BLK2 TOV2 | 8.4P 6.8R 1.3A 0.6S 1.1B 0.9TO · OREB 2.4 · FG 65.2% (5.4FGA) · 3P 8.1% (0.1×) 0×3PM · FT 72.1% (1.8FTA) · 혼합 GP 71.1 · 21.3MPG · 25-26 64% |
| $6 | $1-3 | Tyus Jones | A/T3 TOV3 FT%1 | 6.2P 1.7R 3.7A 0.7S 0B 0.7TO · OREB 0.3 · FG 39.3% (5.6FGA) · 3P 34.6% (3.3×) 1.2×3PM · FT 83.0% (0.4FTA) · 혼합 GP 73.2 · 20MPG · 25-26 55% |
| $6 | $1-3 | Marcus Smart | STL2 TOV1 FT%1 | 9.2P 2.6R 3.1A 1.3S 0.4B 1.5TO · OREB 0.6 · FG 39.5% (7.7FGA) · 3P 33.6% (4.5×) 1.5×3PM · FT 80.6% (2.1FTA) · 혼합 GP 54.5 · 26.2MPG · 25-26 73% |
| $6 | $1-3 | Cam Spencer | 3P%3 FT%2 A/T3 TOV2 AST1 3PM1 | 9.8P 2.3R 4.8A 0.6S 0.2B 1.1TO · OREB 0.6 · FG 46.2% (6.9FGA) · 3P 43.3% (4×) 1.8×3PM · FT 95.1% (1.7FTA) · 혼합 GP 63.2 · 21.2MPG · 25-26 81% |
| $6 | $1-3 | Andrew Wiggins | 3P%2 BLK2 TOV1 OREB1 3PM1 STL1 | 16.4P 4.7R 2.7A 1.1S 0.9B 1.6TO · OREB 1.6 · FG 46.5% (12.8FGA) · 3P 39.9% (5.2×) 2.1×3PM · FT 77.6% (3.1FTA) · 혼합 GP 65 · 30.4MPG · 25-26 63% |
| $6 | $1-3 | Brook Lopez | BLK3 TOV2 3P%1 | 10.4P 4.2R 1.5A 0.6S 1.5B 0.9TO · OREB 0.9 · FG 46.2% (8.2FGA) · 3P 36.5% (4.4×) 1.6×3PM · FT 78.6% (1.3FTA) · 혼합 GP 77.1 · 26MPG · 25-26 58% |
| $9 | $2-8 | Ryan Rollins | 3P%2 STL2 3PM1 A/T1 AST1 | 13.6P 3.7R 4.4A 1.3S 0.4B 2.1TO · OREB 0.6 · FG 47.7% (10.8FGA) · 3P 40.7% (4.8×) 2×3PM · FT 79.7% (1.7FTA) · 혼합 GP 68 · 26.2MPG · 25-26 66% |
| $5 | $1-3 | Day'Ron Sharpe | OREB3 REB1 FG%2 TOV1 | 8.4P 6.7R 2.1A 1S 0.5B 1.6TO · OREB 2.9 · FG 57.3% (5.9FGA) · 3P 23.5% (0.7×) 0.1×3PM · FT 70.6% (2.2FTA) · 혼합 GP 57.8 · 18.5MPG · 25-26 65% |
| $5 | $1-3 | Immanuel Quickley | A/T3 STL1 3PM2 FT%1 TOV1 AST2 3P%1 | 16.6P 3.9R 5.9A 1.2S 0.1B 1.6TO · OREB 0.5 · FG 43.8% (13FGA) · 3P 37.5% (6.8×) 2.5×3PM · FT 83.2% (3.2FTA) · 혼합 GP 61.2 · 30.9MPG · 25-26 76% |
| $5 | $1-3 | Kris Dunn | STL3 TOV1 A/T2 | 7P 3.3R 3.3A 1.6S 0.3B 1.2TO · OREB 0.7 · FG 46.2% (5.8FGA) · 3P 35.9% (2.8×) 1×3PM · FT 73.4% (0.7FTA) · 혼합 GP 79 · 26MPG · 25-26 62% |
| $5 | $1-3 | Moritz Wagner | FG%2 PTS2 OREB1 | 9P 3.8R 1A 0.5S 0.2B 0.9TO · OREB 1 · FG 47.5% (6.4FGA) · 3P 33.0% (2.1×) 0.7×3PM · FT 78.3% (2.6FTA) · 혼합 GP 33.9 · 14.4MPG · 25-26 64% |
| $5 | $1-3 | Santi Aldama | REB1 TOV1 OREB1 A/T1 3PM1 | 13.2P 6.5R 2.9A 0.8S 0.5B 1.2TO · OREB 1.5 · FG 48.1% (10.5FGA) · 3P 35.9% (4.9×) 1.7×3PM · FT 67.9% (2FTA) · 혼합 GP 54 · 26.7MPG · 25-26 49% |

잉여 플러스 다트 상위 30 (전체 55명).
<!-- /GEN:darts -->

## 캣 가중치 표기

`OREB3 DD3 BLK2` = OREB 엘리트(3) · DD 엘리트(3) · BLK 플러스(2).
`TOV`는 양수 = 턴오버가 적어 해당 캣에 유리. ⚠️ 가중치는 순서 척도이고 실측 단위가 아님 —
`05-limitations.md` 참조.
