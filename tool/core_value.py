#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""코어별 **마지막 칸 판단표** — 캣 승률 곡선 기울기 가중 (42차 신설).

🔴🔴 **이것은 가격표가 아니다. 42차에 가격표로 만들려다 실패했고 그 기록을 남긴다.**
   달러 열(`my_max_core`·`surplus_core`·`obtainable_core`)은 **제거됐다.** 이유는
   아래 「달러로 만들려다 실패한 기록」 절에 전부 적혀 있다. 다시 만들지 마라.

## 🔴 왜 필요한가 — 목적함수와 가격표가 다른 이론 위에 있었다

`my_max` 는 **13캣 균등 가중 일반 가치**다. `tool/value_model.py` 자신이 그렇게 적어 뒀다:
*"동일 가중: 12캣을 같은 비중으로 본다. 실제로는 코어가 포기하는 캣이 있어 코어별 가치가
다르다(이 모델은 코어 무관 '일반 가치')."*

그런데 전략은 **3~5캣을 포기하는 코어 7종 중 하나를 짓는 것**이고,
`bid_ceiling = min(my_max, 단일상한, 철수가)` 이므로 **일반 가치가 모든 코어의 모든 입찰에
하드 상한**이다. 드래프트 당일 화면에 뜨는 숫자가 플랜과 다른 이론 위에 있었다.

그리고 2026-09-07 커미셔너 확인으로 **매치업 = 주간 캣 다수결**(13캣 중 7캣 이상)이
확정됐다. 목적함수는 `P(≥7/13)` 이고, **이 포맷은 펀트를 보상한다.**

## 가중 함수 — 사전에 고정한다. 결과에 맞춰 튜닝하지 않는다 (24차 원칙)

목적은 `P(≥7/13)` 이다. 캣 c 의 마진을 조금 늘렸을 때의 이득을 쪼개면:

    ∂P(≥7)/∂margin_c  =  P(나머지 12캣 중 정확히 6승)  ×  ∂P(캣 c 승)/∂margin_c
                          └─ 캣에 거의 무관한 공통항 ─┘   └─ 캣 c 의 마진 분포 밀도 ─┘

앞 항은 **모든 캣에 공통**이므로 상대 가중에서 약분된다. 남는 것은 **마진 분포의
0 지점 밀도**다. 마진 분포를 로지스틱(척도 s)으로 근사하면 `p = σ(μ/s)` 이고

    dp/dμ = p(1−p)/s

이므로 **상대 가중 ∝ p(1−p)** 다. 최대점(p=0.5)에서 1이 되도록 4를 곱한다:

    🔴  w_c = 4 · p_c · (1 − p_c)        ← 이 형태를 **먼저 고정했다**

    p=0.50 → 1.00   p=0.65 → 0.91   p=0.80 → 0.64   p=0.90 → 0.36   p=0.98 → 0.08

읽는 법: 이미 98% 이기는 캣에 마진을 더 쌓아도 **7이라는 선을 넘는 데 기여하지 않는다.**
승률 50% 근처 캣에 쓴 돈이 그 선을 직접 움직인다.

### 고려했고 버린 형태 (기록 — 나중에 "왜 이걸 골랐나"가 다시 안 나오게)
- **포기 캣 가중 0 / 나머지 1** (이진) — 미분 불가능하고 「포기」의 컷을 사람이 정해야 한다.
  그리고 승률 98% 캣과 65% 캣을 같게 본다 — 잠금 캣에 쓴 초과분을 못 잡는다.
- **|p − 0.5| 선형** — 목적함수에서 유도되지 않는다. 꼬리에서 밀도를 과대평가한다.
- **로짓 도함수의 이차 항까지** — s 를 캣별로 추정해야 하고, 그 추정이 곧 실측 튜닝이다.

### ⚠️ 순환을 1회로 끊는다
캣 승률로 가중을 만들고 그 가중으로 로스터를 고치면 승률이 다시 바뀐다.
**가중은 현행 로스터의 승률에서 고정하고 재귀하지 않는다.** 이유:
① 수렴 보장이 없다. ② 반복할수록 「이미 이기는 캣을 더 버리는」 방향으로 폭주해
   `docs/05 §2b-7`(후견 편향 23%p ≫ 신호 3.5%p)이 금지하는 잡음 추적이 된다.
③ 이 표의 용도는 **로스터 재설계가 아니라 「경매장에 올라온 이 선수를 이 코어에서
   얼마까지 부를까」** 다. 그 판단에는 현행 로스터의 승률이 정확히 맞는 입력이다.

## 두 개의 산출값 — 섞지 말 것

| 필드 | 무엇 | 쓸모 |
|---|---|---|
| `dollar_core` | 코어 가중 z 를 $2,674 에 비례 배분 (`value_model.values()` 와 **같은 레시피**) | `value_reference.dollar_naive` 와 **직접 비교** 가능 |
| `my_max_core` | 기존 `my_max` 사다리를 **코어 순위로 재배치** | `bid_ceiling_core` 의 입력 |

`my_max_core` 를 왜 순위 재배치로 하는가:
- `my_max` 는 손으로 유지되며 실측 시장가에 대조돼 **달러 눈금이 교정**돼 있다.
  `dollar_naive` 는 z 합산이 상단을 압축해 **절대액을 신뢰하지 않는다**고 적혀 있다
  (`HANDOFF` 데이터 모델 절). 새 달러 눈금을 발명하는 대신 **교정된 눈금을 유지**하고
  **누가 어느 칸에 서는지만** 바꾼다.
- 부수 효과로 `Σ my_max_core == Σ my_max` 가 정확히 성립한다 — 예산 노출 총량이 안 바뀐다.
- ⚠️ **한계**: 사다리 모양이 고정이므로 「이 코어는 상위 20명이 다 비슷하다」 같은
  **압축**을 표현하지 못한다. 코어별 차이는 **순서**로만 나타난다.

## 이 표가 하지 않는 것
- 로스터를 바꾸지 않는다. 어긋남을 **드러낼** 뿐이다(작업 2-5 · `conflicts`).
- `my_max`(일반)를 덮지 않는다. 불변식 1·23 은 그대로 일반 값 위에서 돈다.

## 🔴 달러로 만들려다 실패한 기록 — **다시 만들지 마라**

42차 1차 시도는 이 가중으로 z 를 재합산해 순위를 내고, **기존 `my_max` 사다리를 그
순위로 재배치**해 `my_max_core` 를 만들었다(Σ 보존이 성립해서 안전해 보였다).
그리고 `bid_ceiling = min(my_max_core, 단일상한, 철수가)` 로 체인에 넣었다.
**시뮬로 검증하니 기각됐다.**

같은 실행·같은 시드(20261020)·이름 정렬·4000시행·실제 12팀 · `WEEK_MODEL=standard`:

| 검증 | 표의 주장 | 실측 | 판정 |
|---|---|---|---|
| c1 C  KAT $45 → Duren ($18 절감)      | KAT 코어상한 $30 (일반 $71) = $15 과지출 | **−2.19%p** (SE 0.56 · 3.9σ) | 🔴 기각 |
| c7 C  KAT $45 → Duren ($18 절감)      | KAT 코어상한 $26 = $19 과지출            | **−2.37%p** (SE 0.46 · 5.1σ) | 🔴 기각 |
| c6 PF Şengün $26 → Mobley ($3 절감)   | Şengün 코어상한 $10 = $16 과지출         | **−1.16%p** (SE 0.25 · 4.6σ) | 🔴 기각 |
| c6 PF Şengün $26 → LeBron ($12 절감)  | 같음                                      | **−0.70%p** (SE 0.32 · 2.2σ) | 🔴 기각 |
| c6 SG Amen $26 → Knueppel ($4 절감)   | Amen 코어상한 $16 · Knueppel $60         | −0.16%p (SE 0.26 · 0.6σ)     | ⚪ 잡음 |

**4/5 기각 · 1건 판정 불가.** 반대편도 깨졌다 — c6 에서 시장 $1-3 선수의 코어 상한이
$26~40 이 되어 `surplus_core` 상위 8 중 **5명이 $1-3 선수**였다. 그 화면을 보고 부르면
$2 다트 넷에 $100 을 쓴다. 그리고 `docs/01` 의 실측(Bane 슬롯 21명 전수 시뮬 —
「상위가 전방위 윙 · **$2 3PT 스페셜리스트는 아래였다**」)이 정확히 그 원형을 하위로
판정해 뒀다. **측정이 모형을 이긴다**(29·33·40차 전례).

### 🔴 기전 — **음수 z 벌점 면제** (2차 철회의 근거)

`w` 를 **풀 평균 기준 z** 에 곱하기 때문에, 잠긴 캣에서 z 가 **음수**인 선수는 벌점이
면제되고 **양수**인 선수는 신용이 압수된다. c6 에서 `(w−1)·z` 를 분해하면:

```
Cam Spencer     Σ +4.01   REB +1.09(z −1.4) · OREB +0.79(z −0.9) = +1.88  (47%)
Duncan Robinson Σ +3.69   OREB +0.96(z −1.1) · REB +0.87(z −1.2) = +1.83  (49%)
Luke Kennard    Σ +3.67   REB +0.92(z −1.2) · OREB +0.82(z −0.9) = +1.74  (47%)

Rudy Gobert     Σ −5.48   OREB −2.57(z +2.8) · REB −1.98(z +2.6) = −4.55  (83%)
Alperen Şengün  Σ −5.28   OREB −1.87(z +2.1) · REB −1.36(z +1.8) = −3.23  (61%)
Amen Thompson   Σ −4.20   OREB −1.69(z +1.9) · REB −0.92(z +1.2) = −2.61  (62%)
```

**Cam Spencer 의 최대 상승 항목은 3P% 가 아니라 REB 다.** 표는 "3점을 잘 쏘니 올린다"가
아니라 **"리바운드를 못하니 봐준다"** 를 실행하고 있었다. 상승분의 47~50% · 하락분의
61~83% 가 이 채널이므로 **달러만이 아니라 순위도 오염돼 있다.**
→ 2차 철회에서 `rank_core`·`rank_shift`·`z_total_core` 까지 산출에서 내렸다.

### 왜 틀렸나 — 셋

**① 국소 한계 가중으로 총 가치를 매겼다.** `w ∝ p(1−p)` 는 「여덟 명이 정해졌고 한 칸이
남았다」에만 유효하다. 유도식의 공통항 `P(나머지 12캣 중 정확히 6승)` 이 약분된다는 것도
**한 선수를 바꿔도 나머지 캣 승률이 안 변한다**는 전제 위에 있고, 앵커를 바꾸면 깨진다.
KAT 를 빼면 3PM 이 39%→23% 로 무너진다 — 그의 가치는 잠긴 캣에만 있지 않았다.

**② 순환을 끊은 게 아니라 얼렸다.** c6 의 OREB 가 98% 인 것은 c6 가 Gobert·Clingan 을
**샀기 때문**이다. 잠겼다는 이유로 OREB 가중을 0.10 으로 내리고 그 결과 Gobert 를 $11 로
깎으면, 그를 안 사게 되고 OREB 는 98% 가 아니다. 「1회로 끊는다」는 반복 횟수의 문제가
아니라 **일관되지 않은 지점에 고정**하는 것이었다.

**③ 사다리 재배치가 인공물을 만들었다.** `my_max` 사다리 모양은 **일반 가치 분포에 맞춰**
교정된 것이다. 순위를 50계단 올리면 그 선수가 **자기와 무관한 눈금**을 물려받는다.
`Σmy_max_core == Σmy_max` 는 총액 보존일 뿐 개별 값의 타당성과 무관하다.

### 🔴 그래서 원래 결함은 **해결되지 않았다**
「드래프트 당일 화면의 `my_max` 가 13캣 균등 일반 가치이고 플랜과 다른 이론 위에 있다」는
그대로 남아 있다. 42차가 밝힌 것은 **「z 재가중으로는 못 고친다」** 이다.
실제 해법은 **측정**이다 — 후보를 슬롯에 넣고 ΔP(≥7) 을 직접 재는 것
(`tool/pivot_delta.py` · `tool/alt_promote.py` 가 이미 그 일을 한다). 전수는 불가능하므로
**슬롯별 숏리스트 범위에서만** 가능하고, 그 밖은 **판정하지 않는다**고 적어야 한다.

## 이 표의 유효 범위 — 좁게 쓸 것

✅ **유효**: 캣 승률·밴드·**가중치**. 「이 코어에서 다음 1달러는 어느 캣에 쓰면 되는가」.
   c6 예: 잠금 OREB 98%(w0.10)·REB 96%(w0.25) → 여기 더 쌓아도 7이라는 선을 못 넘는다.
   최고 가중은 3P% 41%(w1.41)·FT% 37%(w1.36)·**3PM 32%(w1.27)·TOV 32%(w1.27)** 다.
   🔴 즉 **「포기 캣이 낭비」가 아니라 「잠긴 캣이 낭비」다.** 32% 캣은 18점만 뒤집으면
   되고, 98% 캣은 선을 48점 지나 있어 더 기여할 수 없다. 42차 이전 진단은 반대로 봤다.

🔴 **선수 순위·달러는 산출하지 않는다.** 「마지막 칸에서는 벌점 면제가 오히려 맞다」는
   반론이 가능하지만(여덟이 OREB 를 잠갔으면 아홉 번째의 부진은 실제로 공짜),
   **그 좁은 범위에서도 우리가 가진 유일한 지상진실과 어긋난다** —
   `docs/01` 의 **Bane 슬롯 21명 실측**(같은 슬롯에 21명을 넣고 ΔP 를 잰 것)에서
   상위는 전방위 윙이고 **$2 3PT 스페셜리스트는 하위**였다. 이 표는 그 하위 원형을
   상위로 올린다. 측정이 모형을 이긴다.

   선형 근사가 왜 그 실측을 못 맞히는지 — **가설이다. 재지 않았다**:
   ① 잠금 캣의 σ 가 크다(OREB 18% · DD 62%) — 한 선수의 결손이 98% 를 실제로 흔든다.
      `p(1−p)` 는 그 분산을 모른다.
   ② 비율캣 볼륨 레버리지가 z 에 이미 섞여 있어 재가중이 **이중계산**이 된다.
   ③ `p(1−p)` 는 0.5 대칭이라 **32% 캣을 50% 캣과 거의 같게** 본다(c6 TOV·3PM w1.27).
      「포기」의 반대 신호를 낸다.

⚠️ **부분적으로는 저장소의 다른 실측과 방향이 맞는다** — 숨기지 않는다.
   「빅은 세 자리쯤에서 포화한다」(`docs/01`: c6 Clingan→Bane +3.1%p · c2 자격 보정
   −2.4%p = 네 번째 센터 기여 ≈ 0)와 이 표의 빅 강등은 같은 방향이다.
   기각된 것은 **방향이 아니라 크기와 적용 범위**다 — 앵커·1순위에 쓰면 틀린다
   (KAT −2.19/−2.37%p · Şengün −1.16%p).

실행:  python3 tool/core_value.py        → data/core_value_tables.json
"""
import json, io, os, sys, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import value_model as VM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = {p["name"]: p for p in json.load(io.open(f"{BASE}/data/players.json", encoding="utf-8"))}
CJ = json.load(io.open(f"{BASE}/data/cores.json", encoding="utf-8"))

# 승률 출처 — 우선순위. 🔴 값이 **어느 세계에서 나왔는지**를 기록에 남긴다.
GPW = f"{BASE}/data/gpw_dual.json"
SIM = f"{BASE}/data/matchup_sim.json"

# 잠금/경합 구간 — 서술·화면용 라벨. **가중 계산에는 쓰지 않는다**(연속 함수다).
BANDS = [(0.85, "잠금"), (0.60, "우세"), (0.35, "경합"), (0.0, "포기")]


def band(p):
    for lo, lbl in BANDS:
        if p >= lo:
            return lbl
    return "포기"


def cat_win_probs():
    """코어별 13캣 승률. 실제 12팀 평균(1차 지표)을 쓴다.

    출처는 `data/gpw_dual.json` 의 **primary world**(신 기본값 세계)를 1순위로 본다 —
    42차에 주 길이 모형이 바뀌었으므로 `matchup_sim.json` 저장값은 옛 세계다.
    없으면 `matchup_sim.json` 으로 내려가고, **그 사실을 기록한다.**
    """
    if os.path.exists(GPW):
        g = json.load(io.open(GPW, encoding="utf-8"))
        pw = g["primary_world"]
        seed = g["seeds"][0]
        C = g["worlds"][pw]["by_seed"][str(seed)]["cores"]
        return ({cid: C[cid]["cat_win_probs_real_mean"] for cid in C},
                {"file": "data/gpw_dual.json", "world": pw, "seed": seed,
                 "metric": "real 12팀 평균 캣 승률",
                 "week_model": g["worlds"][pw]["config"],
                 "iterations": g["iterations"]})
    s = json.load(io.open(SIM, encoding="utf-8"))
    C = s["cores"]
    mgrs = list(next(iter(C.values()))["real"])
    out = {}
    for cid in C:
        out[cid] = {c: round(st.mean(C[cid]["real"][m]["cat_win_probs"][c] for m in mgrs), 4)
                    for c in C[cid]["real"][mgrs[0]]["cat_win_probs"]}
    return out, {"file": "data/matchup_sim.json", "world": "(42차 이전 세계 — 옛 주 길이 모형)",
                 "seed": s.get("seed"), "metric": "real 12팀 평균 캣 승률",
                 "iterations": s.get("iterations"),
                 "warning": "gpw_dual.json 이 없어 옛 세계 저장값으로 내려갔다"}


def weights(p_by_cat, cats):
    """🔴 w_c = 4 p(1−p), 합이 캣 수가 되도록 정규화. 사전 고정 형태다."""
    raw = {c: 4.0 * p_by_cat[c] * (1.0 - p_by_cat[c]) for c in cats}
    tot = sum(raw.values())
    if tot <= 0:
        raise ValueError("가중 합이 0 — 모든 캣이 0% 또는 100%다. 승률 입력을 확인할 것")
    k = len(cats) / tot
    return {c: round(raw[c] * k, 4) for c in cats}


TOP_N = 40


def conflicts(co, tbl, players, top_n=TOP_N):
    """🔴 **폐기 (42차)**. 호출하지 마라. 남겨둔 이유는 왜 없앴는지를 남기기 위해서다.

    이 함수는 「플랜 × 코어별 가격표의 어긋남」 세 목록을 냈고 `recompute_cores.py` 가
    그것을 `cores.json` 에 썼다. **두 가지가 동시에 틀렸다:**

    ① **내용** — 「과지출」 목록은 달러 열 위에 있었고 그 달러가 시뮬 검증에서 기각됐다
       (파일 상단 표). 「코어 상위40 미편입」 목록은 그 칸을 채울 수 없는 가드로 채워졌다
       — 이 표는 **포지션 자격을 모른다.** c6 PF 칸을 비우라면서 대안으로 Lillard(PG)를
       올리는 식이었다.
    ② **자리** — 선수 이름을 `cores.json` 에 넣자 `divergence_rules.core_hits()` 가
       그것을 **등장 횟수로 셌고**, `my_max_basis.auto` 가 무효화되어 M6 위반이 떴다
       (Luke Kennard). 32차에 시뮬 산출물을 `cores.json` 에서 **파일 분리**한 것과
       똑같은 사고를 다시 낸 것이다. 진단 산출은 이 파일(`core_value_tables.json`)에 둔다.

    → 진단이 필요하면 `data/core_value_tables.json` 의 `cores[cid].players[*].rank_shift`
      를 직접 읽어라. **`cores.json` 에 선수 이름을 새로 넣지 마라.**
    """
    raise NotImplementedError(
        "42차에 폐기됨 — 위 docstring 참조. cores.json 에 선수 이름을 넣으면 "
        "core_hits 가 오염된다(32차 전례). 진단은 core_value_tables.json 에서 읽을 것.")


def main():
    Z, _stats = VM.zscores()
    pool = [p["name"] for p in VM.pool()]
    CATS = VM.CATS
    probs, prov = cat_win_probs()

    scored = [n for n in Z if n in PL]
    out_cores = {}
    for co in CJ["cores"]:
        cid = co["id"]
        if cid not in probs:
            continue
        p = probs[cid]
        w = weights(p, CATS)
        # 🔴 **선수 순위·달러를 산출하지 않는다** (42차 2차 철회 · 파일 상단 「기전」).
        #    `Σ w·z` 는 잠긴 캣에서 음수 z 의 벌점을 면제하고 양수 z 의 신용을 압수한다.
        #    상승분의 절반이 그 채널이라 **순위 자체가 오염**된다. 다시 만들지 마라.
        #
        #    남기는 것: 그 코어 **자기 선발 9명**에 대한 `(w−1)·z` 분해를
        #    **잠금 밴드(p≥85%)를 뺀 캣에서만** 낸다. 오염 채널이 잠금 캣에 전부 있으므로
        #    그 캣을 빼면 구조적으로 섞이지 않는다.
        #    ⚠️ 이것도 **가설 생성용**이다. 「이 선수가 이 코어의 경합 캣을 깎는다」는
        #       관찰이고, 교체 판단은 ΔP(≥7) 측정으로 해야 한다(tool/pivot_delta.py).
        roster = [s2["candidates"][0]["name"] for s2 in
                  next(x for x in CJ["cores"] if x["id"] == cid)["slots"]]
        contested = [c for c in CATS if band(p[c]) != "잠금"]
        diag = {}
        for n in roster:
            if n not in Z:
                continue
            zz = Z[n]["z"]
            terms = {c: round((w[c] - 1.0) * zz.get(c, 0.0), 3) for c in contested}
            worst = sorted(contested, key=lambda c: terms[c])[:3]
            best = sorted(contested, key=lambda c: -terms[c])[:2]
            diag[n] = {"drags": [{"cat": c, "term": terms[c], "z": zz.get(c),
                                  "w": w[c], "p": p[c]} for c in worst if terms[c] < 0],
                       "helps": [{"cat": c, "term": terms[c], "z": zz.get(c),
                                  "w": w[c], "p": p[c]} for c in best if terms[c] > 0]}
        out_cores[cid] = {
            "cat_win_probs": p,
            "cat_bands": {c: band(p[c]) for c in CATS},
            "cat_weights": w,
            "weight_note": ("w = 4p(1−p) 를 합이 13이 되도록 정규화. p 는 그 코어의 "
                            "실제 12팀 평균 캣 승률. **사전 고정 형태 · 결과에 맞춰 "
                            "튜닝하지 않았다**(24차 원칙)."),
            "contested_cats": contested,
            "roster_cat_diagnostic": diag,
            "roster_cat_diagnostic_note": (
                "그 코어 선발 9명의 (w−1)·z 를 **잠금 밴드를 뺀 캣에서만** 분해한 것. "
                "잠금 캣을 뺀 이유는 42차에 확인된 오염 채널(음수 z 벌점 면제)이 전부 "
                "거기 있기 때문이다. 🔴 **가설 생성용이다** — 「이 선수가 이 코어의 경합 캣을 "
                "깎는다」는 관찰이고, 교체 판단은 ΔP(≥7) 측정으로 할 것."),
        }

    out = {
        "generated_by": "tool/core_value.py",
        "objective": "P(≥7/13) — 주간 캣 다수결 (2026-09-07 커미셔너 확인)",
        "weight_function": "w_c = 4·p_c·(1−p_c) / 정규화(합=13)",
        "weight_derivation": ("∂P(≥7)/∂margin_c = P(나머지 12캣 중 정확히 6승) × "
                              "∂P(캣c승)/∂margin_c. 앞 항은 캣에 공통이라 상대 가중에서 "
                              "약분되고, 뒤 항은 마진 분포의 0 지점 밀도다. 로지스틱 근사에서 "
                              "dp/dμ = p(1−p)/s 이므로 상대 가중 ∝ p(1−p)."),
        "weight_rejected": ["포기 캣 가중 0 (이진) — 미분 불가 · 컷을 사람이 정해야 함 · "
                            "98% 캣과 65% 캣을 같게 본다",
                            "|p−0.5| 선형 — 목적함수에서 유도되지 않음 · 꼬리 과대평가",
                            "로짓 도함수 2차항 — s 를 캣별로 추정해야 하고 그 추정이 곧 실측 튜닝"],
        "iteration_policy": ("🔴 **1회로 끊는다.** 가중은 현행 로스터의 승률에서 고정하고 "
                             "재귀하지 않는다. ① 수렴 보장 없음 ② 반복하면 「이미 이기는 캣을 "
                             "더 버리는」 방향으로 폭주해 docs/05 §2b-7 이 금지하는 잡음 추적이 "
                             "된다 ③ 이 표의 용도는 로스터 재설계가 아니라 「경매장에 올라온 이 "
                             "선수를 이 코어에서 얼마까지 부를까」다."),
        "scope": {
            "valid": ["캣 승률·밴드·가중치 — 「이 코어에서 다음 1달러는 어느 캣에 쓰는가」",
                      "선발 9명의 경합 캣 분해 — 가설 생성용"],
            "forbidden": ["선수 순위(rank_core)·달러(my_max_core) — **산출하지 않는다**",
                          "계획 슬롯의 앵커·1순위 가격 판단 (시뮬 검증 4/5 기각)",
                          "잉여 정렬 ($1-3 다트를 상단에 올린다)"],
            "why": ("w ∝ p(1−p) 는 국소 한계 가중이다. 총 가치를 매기면 자기 전제를 먹고, "
                    "잠긴 캣에서 **음수 z 의 벌점을 면제**해 순위까지 오염시킨다."),
        },
        "dollar_columns_removed_42": {
            "what": "my_max_core · surplus_core · obtainable_core · dollar_core 를 제거했다",
            "why": "시뮬 검증에서 달러 주장 4/5 기각 (KAT −2.19/−2.37%p · Şengün −1.16/−0.70%p). "
                   "반대편에서는 시장 $1-3 선수의 코어 상한이 $26~40 이 되어 surplus 상위 8 중 "
                   "5명이 $1-3 선수였다.",
            "measurement": "같은 실행·시드 20261020·이름 정렬·4000시행·실제 12팀·WEEK_MODEL=standard",
            "unresolved": "원래 결함(화면 my_max 가 13캣 균등 일반 가치)은 **해결되지 않았다**. "
                          "42차가 밝힌 것은 「z 재가중으로는 못 고친다」이고, 실제 해법은 "
                          "슬롯별 숏리스트에 대한 ΔP(≥7) **측정**이다(tool/pivot_delta.py).",
        },
        "does_not": ["로스터를 바꾸지 않는다",
                     "my_max(일반)를 덮지 않는다 — bid_ceiling 체인은 일반 값 위에서 돈다"],
        "provenance": prov,
        "cats": CATS,
        "n_players": len(_ := [n for n in Z if n in PL]),
        "cores": out_cores,
    }
    json.dump(out, io.open(f"{BASE}/data/core_value_tables.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ── 보고
    print("코어별 가격표 — 승률 출처: %s / %s (%s)"
          % (prov["file"], prov.get("world"), prov.get("metric")))
    if prov.get("warning"):
        print("  ⚠️ " + prov["warning"])
    print("가중: w = 4p(1−p) · 합 13 정규화 · **사전 고정**\n")
    for cid in sorted(out_cores):
        d = out_cores[cid]
        w, p = d["cat_weights"], d["cat_win_probs"]
        print("── %s ─────────────────────────────────" % cid)
        for lo, lbl in BANDS:
            g = sorted([c for c in CATS if band(p[c]) == lbl], key=lambda c: -p[c])
            if g:
                print("  %-4s %s" % (lbl, " · ".join("%s %.0f%%(w%.2f)"
                                                     % (c, 100 * p[c], w[c]) for c in g)))
        dg = d["roster_cat_diagnostic"]
        rows = sorted(((n, t) for n in dg for t in dg[n]["drags"]),
                      key=lambda x: x[1]["term"])[:3]
        if rows:
            print("  경합 캣을 가장 많이 깎는 선발: " + " · ".join(
                "%s %s %.2f(p%.0f%%)" % (n.split()[-1], t["cat"], t["term"], 100 * t["p"])
                for n, t in rows))
    print("\n🔴 선수 순위·달러는 산출하지 않는다 (42차 2차 철회 — 음수 z 벌점 면제)")
    print("data/core_value_tables.json 기록 (코어 %d종 · 캣 가중·밴드 + 선발 캣 진단)"
          % len(out_cores))


if __name__ == "__main__":
    main()
