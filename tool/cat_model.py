#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""캣 평가 모델 (21차 정정판) — 단일 소스.

## 왜 정정했나 🔴
16~20차는 **선발 7명만 집계**한다고 가정했습니다. **틀렸습니다.**
야후 판타지는 라인업을 **매일** 세팅하고, NBA 팀들은 서로 다른 날에 경기합니다.
월요일에 선발이던 선수가 화요일엔 벤치이고, 벤치 선수가 그날 선발로 올라갑니다.

  로스터 9명 × 주 3.4경기 = 30.8 선수-경기   (GAMES_PER_STANDARD_WEEK = 3.417 · 42차)
  선발 슬롯 7개 × 7일      = 49 슬롯-일   → 용량이 남는다

즉 **9명 전원의 스탯이 집계됩니다.** 같은 날 8명 이상이 겹칠 때만 손실이 생기고,
그건 이 모델에서 미반영(보수적으로 무시)입니다.
`slot`/`BN` 표기는 명목 스케치이고 실제 캣 기여와 무관합니다.

## 출장 경기 수 가중
주간 기여 ∝ 경기당 스탯 × 그 주 출장 경기수. 시즌 가용률 = GP/82.
82경기 선수는 50경기 선수의 1.64배 기여합니다. 결장한 선수의 슬롯-일은 다른 선수가
채우지만 **그 선수의 경기는 이미 계산돼 있으므로 보상되지 않습니다** — 그냥 잃습니다.
따라서 계수형 캣은 `per-game × GP/82`, 비율형 캣은 시도량도 같은 가중을 적용합니다.

## 기준선
상대도 9명을 지명 풀(시장가 상위 126명)에서 뽑습니다. 따라서 슬롯당 기준선은
**지명 풀 전체 평균**(MPG 필터 없음 — 9칸 전부 집계되므로)에 같은 GP 가중을 적용한 값입니다.
"""
import json, io, os, statistics, math
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# build_measured.py가 이 모듈의 DD 추정 함수를 쓰는데, 그 스크립트가 만드는 파일이
# measured_full.json이다. import 시점에 파일이 없어도 죽지 않아야 순환이 끊긴다
# (DD 수식은 데이터 의존이 없는 순수 함수다).
try:
    F=json.load(io.open(f"{BASE}/data/stats_2025_26/measured_full.json",encoding="utf-8"))["players"]
except FileNotFoundError:
    F={}
PL={p["name"]:p for p in json.load(io.open(f"{BASE}/data/players.json",encoding="utf-8"))}
RATE={"3P%":"3PA","FT%":"FTA","FG%":"FGA"}
# 24차: DD 편입. 이전에는 evaluate()가 dd_target 플래그만 보고 **측정 없이 +1캣**을
# 줬다 — 코어 7개 중 6개가 그 공짜 캣에 승리선을 의존했다. 이제 DD도 다른 캣과 똑같이
# 경기당 값(더블더블 확률)으로 들어와 marginal()로 판정된다. 아래 dd_game_prob 참조.
COUNT=["PTS","REB","OREB","AST","STL","BLK","TOV","3PM","DD"]
LOWER={"TOV"}
CATS=COUNT+list(RATE)+["A/T"]
POOL_N=126

# ── 주간 경기수 — 단일 소스 (42차 전면 재작성) ────────────────────────────
#
# ## 확정 사실 — 사용자가 야후 스케줄 탭에서 22주 전체를 읽어 왔다 (2026-09-07)
#     W1  10-19~10-25 (7)   W8  12-14~12-20 (7)   W15 02-01~02-07 (7)
#     W2  10-26~11-01 (7)   W9  12-21~12-27 (7)   W16 02-08~02-14 (7)
#     W3  11-02~11-08 (7)   W10 12-28~01-03 (7)   W17 02-15~02-28 (**14** · 올스타 브레이크)
#     W4  11-09~11-15 (7)   W11 01-04~01-10 (7)   W18 03-01~03-07 (7)
#     W5  11-16~11-22 (7)   W12 01-11~01-17 (7)   W19 03-08~03-14 (7)
#     W6  11-23~11-29 (7)   W13 01-18~01-24 (7)   W20~W22 03-15~04-04 (7·7·7) **플옵**
#     W7  11-30~12-13 (**14** · 브레이크 없음)     W14 01-25~01-31 (7)
#   검산: 20×7 + 2×14 = 168일 = 24 캘린더 주 · **22 매치업 주**. 연속성·길이 전부 확인.
#   NBA 시즌 = 2026-10-20 ~ 2027-04-11 = 174일 → 말미 7일(04-05~04-11)은 **판타지 밖**.
#   플옵 = 상위 8팀 / 14팀 · 3주 단판 (커미셔너 확인).
#
# ## 🔴🔴 종전 3.299 는 **3.6% 저평가**였다. 원인은 브레이크를 퍼뜨린 것이다
#   종전 값은 82경기를 시즌 174일에 **균일하게** 퍼뜨렸다(82/174 × 7 = 3.30).
#   그런데 올스타 브레이크 무경기일은 **W17 이라는 2주 매치업 안에 격리**돼 있다.
#   그러면 나머지 19개 표준 주는 그만큼 빽빽하다:
#
#       밀도 = 82 / (174 − 브레이크일)  = 82/168 = 0.4881 경기/일   (브레이크 6일)
#       표준 주(활동 7일) = 7 × 0.4881 = **3.417**       ← 종전 3.299 대비 +3.6%
#
#   브레이크 길이에 거의 무관하다 — 창 안 총량 78.6 이 고정이기 때문이다:
#       브레이크 5일 → 표준 3.396 · 6일 → 3.417 · 7일 → 3.437     (**3.42 ± 0.02**)
#   ⚠️ 그래서 브레이크 정확한 일수는 **어떤 결론도 바꾸지 않는다.** 6일로 둔다.
#
# ## 🔴 「긴 주 = 2 × 표준」은 **틀렸다.** 긴 주 둘의 성격이 정반대다
#       W7  14일 · 전부 활동  → 6.83 = 2.00 × 표준   ← 최저분산 주
#       W17 14일 · 6일 무경기 → 3.90 = 1.14 × 표준   ← 정규시즌에서 코인플립에 가장 가까운 주
#   보존해야 하는 항등식은 「긴 주 = 2×표준」이 **아니라 「창 안 총량 78.58」** 이다.
#   전자를 가드로 박으면 표준 주가 3.279 로 끌려 내려간다 — 조용히 틀린 값이 되는
#   정확히 그 형태다. 아래 가드는 **총량 기준**이다.
#
# ## 🔴🔴 코어 비교·우승 확률은 **표준 주(3.417)** 로 잰다. 3.577 은 서술용이다
#       긴 주 2개(W7·W17)는 **전부 정규시즌 안**에 있다.
#       플옵 W20~W22 = 03-15~04-04 = 21일 = **전부 표준 주**.
#   14팀 중 8팀이 진출하므로 정규시즌 성적은 사실상 공짜다 — 우승은 플옵 **3주 연속
#   승리**(`p³`)이고 그 3주는 전부 표준 주다.
#   → `WEEK_MODEL` 기본값은 **`standard`**. 22주 평균(`mixed` · 3.572)은 시즌 서술·시딩용이고
#     **어디에도 헤드라인으로 쓰지 않는다** — 그 값은 W7 하나가 만든 것이다.
#
# ## 24차 원칙에 걸리지 않는다 — 이건 튜닝이 아니라 **확정 일정의 반영**이다
#   38차 주석은 지지집합 확장을 *"근거가 n=1주 관측이고 24차 원칙(사전 고정 계수를
#   실측에 맞춰 튜닝하지 않는다)에 걸린다"* 며 미적용으로 뒀다. **그 근거가 바뀌었다.**
#   위 주 목록은 관측 표본이 아니라 **사용자가 야후 화면에서 읽은 일정**이다.
#   표본에 맞춰 계수를 움직이는 것과 규정을 반영하는 것은 다르다.
#
# ## 🟡 남은 한계
#   · 브레이크 **정확한 일수**를 모른다(5~7 가정). 표준 주를 ±0.02 움직일 뿐이다.
#   · 주 안의 **일별 분포**는 균일로 둔다. 실제로는 팀별로 2~5경기까지 퍼진다 —
#     그 변동은 선수별 추첨(2단)이 담당한다.
#   · 3월 말은 이미 탱킹 구간이다. 「우승 3주」의 상대는 로스터 관리가 개입된 세계다
#     — 관측으로만 적고 수치를 만들지 않는다(`docs/05 §12`).
SEASON_DAYS   = 174               # 2026-10-20 ~ 2027-04-11
BREAK_DAYS    = 6                 # 올스타 브레이크 무경기일 (W17 안에 격리 · 5~7 구간)
GAMES_PER_DAY = 82.0 / (SEASON_DAYS - BREAK_DAYS)          # 0.4881

# 주 유형 = (라벨, 창 안 **활동일수**, 주 수). 일정이 확정이므로 추첨할 이유가 없다 —
# 주 하나하나에 평균을 박는다. 확률 혼합은 「무작위 한 주」를 뽑을 때만 쓴다(P = 주수/22).
WEEK_TYPES = (
    ("standard", 7,  19),   # W2~W6 · W8~W16 · W18~W19 · W20~W22(플옵)
    ("W1",       6,   1),   # 주 시작 10-19, 시즌 개막 10-20 → 실질 6일
    ("W7",      14,   1),   # 14일 · 전부 활동
    ("W17",      8,   1),   # 14일 중 6일 무경기(브레이크)
)
MATCHUP_WEEKS  = sum(k for _, _, k in WEEK_TYPES)          # 22
CALENDAR_WEEKS = 24
GAMES_IN_WINDOW = round(sum(k * d * GAMES_PER_DAY for _, d, k in WEEK_TYPES), 3)   # 78.583

# 🔴 이 둘은 **확정 일정에서 유도된 값**이다. 환경변수로 덮지 않는다 — 덮으면
#   「어느 날짜에서 나온 값인가」를 잃는다. 감도 검증용 주입구는 아래에 따로 있다.
#   **단일 소스는 이 블록 하나다.** 다른 파일은 `CM.<상수>` 를 참조할 것 —
#   복제하면 38차에 모아놓은 사고가 재발한다. (실제로 재발했다: `lineup_feasibility.py`
#   가 40차에 3.299 를 다시 하드코딩했고, 그 때문에 이 상수를 바꿔도 **사용률 표가
#   따라오지 않았다.** 42차에 참조로 교체 · `validate.py [I39]` 가 상시 검사한다.)
GAMES_PER_STANDARD_WEEK = round(7 * GAMES_PER_DAY, 3)                       # 3.417
GAMES_PER_MATCHUP_WEEK  = round(GAMES_IN_WINDOW / MATCHUP_WEEKS, 3)         # 3.572
# (구) 이름 — 「82를 24 캘린더 주에 균일 분산」. 🔴 **브레이크를 퍼뜨린 값이라 쓰지 말 것.**
#   3.279 로 남겨두는 이유는 42차 이전 문서·저장값이 그 세계에서 만들어졌기 때문이다.
GAMES_PER_CALENDAR_WEEK = round(GAMES_IN_WINDOW / CALENDAR_WEEKS, 3)        # 3.274

# ── 주 길이 모형 ──────────────────────────────────────────────────────────
#   standard  모든 주가 표준 주(3.417).  **기본값** — 코어 비교·플옵/우승 확률의 세계.
#             플옵 3주가 실제로 전부 표준 주이므로 이건 근사가 아니라 **정확**하다.
#   mixed     22주 전체(표준 19 + W1 + W7 + W17 · 평균 3.572). 시즌 서술·시딩용.
#             🔴 코어 선택 근거로 쓰지 말 것 — 평균을 만드는 것은 W7 하나다.
#   legacy    환경변수로 준 값을 **평평하게** 적용. 종전 3.299 재현·비교 전용.
WEEK_MODEL = os.environ.get("WEEK_MODEL") or "standard"
if WEEK_MODEL not in ("standard", "mixed", "legacy"):
    raise ValueError("WEEK_MODEL=%r — 'standard' | 'mixed' | 'legacy'" % WEEK_MODEL)

# ── 감도 검증용 주입구 (기본값은 위 유도값) ───────────────────────────────
#   STANDARD_WEEK_GAMES  표준 주 평균. 브레이크 구간 3.396~3.437 검증에 쓴다.
#   LEGACY_WEEK_GAMES    legacy 모형의 평평한 값. 종전 3.299 재현에 쓴다.
#                        (하위호환: 옛 이름 `GAMES_PER_WEEK` 도 받는다)
_env_std = os.environ.get("STANDARD_WEEK_GAMES")
_env_leg = os.environ.get("LEGACY_WEEK_GAMES") or os.environ.get("GAMES_PER_WEEK")

STD_WEEK_GAMES = float(_env_std) if _env_std else GAMES_PER_STANDARD_WEEK


def _support(mu):
    """평균 mu 를 {floor, floor+1} 두 점으로 표현한다. (base, P(base+1))"""
    b = int(math.floor(mu))
    return b, round(mu - b, 4)


if WEEK_MODEL == "legacy":
    _flat = float(_env_leg) if _env_leg else GAMES_PER_MATCHUP_WEEK
    STD_WEEK_GAMES = _flat
    WEEK_MIX = [(_flat, 1.0)]
elif WEEK_MODEL == "standard":
    WEEK_MIX = [(STD_WEEK_GAMES, 1.0)]
else:
    # 활동일수 → 평균. 표준 주만 주입값에 맞춰 스케일한다(감도 검증 시 전 주가 함께 움직인다).
    _scale = STD_WEEK_GAMES / GAMES_PER_STANDARD_WEEK
    WEEK_MIX = [(round(d * GAMES_PER_DAY * _scale, 4), k / MATCHUP_WEEKS)
                for _, d, k in WEEK_TYPES]

# 누적 확률 + 지지집합을 미리 굳혀 둔다 — 추첨은 시뮬 내부 루프다
_WEEK_DRAW = []
_acc = 0.0
for _mu, _pr in WEEK_MIX:
    _acc += _pr
    _b, _p = _support(_mu)
    _WEEK_DRAW.append((_acc, _b, _p))
_WEEK_DRAW[-1] = (1.0, _WEEK_DRAW[-1][1], _WEEK_DRAW[-1][2])

STD_BASE, STD_P = _support(STD_WEEK_GAMES)
# 이 모형의 매치업 주당 실효 평균 — 보고에 쓰는 값
EFFECTIVE_MEAN = round(sum(_mu * _pr for _mu, _pr in WEEK_MIX), 4)

# ── 가드 3종. ⚠️ 지우지 말 것 ────────────────────────────────────────────
# (1) 지지집합 — `_support` 의 두 점 근사가 성립하는 범위인가.
#     이 저장소의 대표 실패 형태(빠뜨려도 조용히 통과)를 막는다.
for _mu, _pr in WEEK_MIX:
    if not (1.0 <= _mu <= 9.0):
        raise ValueError("주 평균 %.3f — 팀당 주간 경기수 범위(1~9) 밖이다. "
                         "_support 의 두 점 근사가 성립하는지 먼저 확인할 것." % _mu)
# (2) 확률 합
if abs(sum(_pr for _, _pr in WEEK_MIX) - 1.0) > 1e-9:
    raise ValueError("주 유형 확률 합 %.6f ≠ 1" % sum(_pr for _, _pr in WEEK_MIX))
# (3) 🔴 **총량** 검산 — 「긴 주 = 2×표준」이 아니라 이것이 보존해야 하는 항등식이다.
#     mixed 모형에서만 의미가 있다(standard/legacy 는 정의상 평평하다).
if WEEK_MODEL == "mixed" and not _env_std:
    if abs(EFFECTIVE_MEAN * MATCHUP_WEEKS - GAMES_IN_WINDOW) > 0.05:
        raise ValueError("22주 총량 %.3f ≠ 창 안 경기 %.3f — 유도가 깨졌다"
                         % (EFFECTIVE_MEAN * MATCHUP_WEEKS, GAMES_IN_WINDOW))

# 하위호환 별칭. 🔴 **새 코드에서 쓰지 말 것** — 「어느 주인가」가 모호해서
# 40차에 lineup_feasibility 가 이 이름으로 잘못된 상수를 복제했다.
GAMES_PER_WEEK = GAMES_PER_STANDARD_WEEK
WEEK_GAMES_P4 = STD_P          # (구) 이름. 표준 주의 P(base+1)


def configure(model=None, standard_week_games=None, flat=None):
    """주 길이 모형을 **런타임에** 바꾼다. `tool/gpw_dual.py` 가 한 프로세스 안에서
    여러 세계를 잴 때 쓴다.

    ⚠️ 환경변수 경로와 같은 유도를 쓴다 — 두 곳에 규칙을 두면 갈라진다.
    ⚠️ 바꾼 뒤에는 `matchup_sim._URATE`·`_RND_RATE` 캐시를 **비워야** 한다.
       사용률은 주당 경기수의 함수이므로 캐시가 남으면 조용히 옛 값을 쓴다.
    """
    global WEEK_MODEL, STD_WEEK_GAMES, WEEK_MIX, _WEEK_DRAW, STD_BASE, STD_P, EFFECTIVE_MEAN
    if model is not None:
        if model not in ("standard", "mixed", "legacy"):
            raise ValueError("model=%r — 'standard' | 'mixed' | 'legacy'" % model)
        WEEK_MODEL = model
    if WEEK_MODEL == "legacy":
        STD_WEEK_GAMES = float(flat) if flat is not None else GAMES_PER_MATCHUP_WEEK
        WEEK_MIX = [(STD_WEEK_GAMES, 1.0)]
    else:
        STD_WEEK_GAMES = (float(standard_week_games) if standard_week_games is not None
                          else GAMES_PER_STANDARD_WEEK)
        if WEEK_MODEL == "standard":
            WEEK_MIX = [(STD_WEEK_GAMES, 1.0)]
        else:
            sc = STD_WEEK_GAMES / GAMES_PER_STANDARD_WEEK
            WEEK_MIX = [(round(d * GAMES_PER_DAY * sc, 4), k / MATCHUP_WEEKS)
                        for _, d, k in WEEK_TYPES]
    _WEEK_DRAW = []
    acc = 0.0
    for mu, pr in WEEK_MIX:
        acc += pr
        b, pp = _support(mu)
        _WEEK_DRAW.append((acc, b, pp))
    _WEEK_DRAW[-1] = (1.0, _WEEK_DRAW[-1][1], _WEEK_DRAW[-1][2])
    STD_BASE, STD_P = _support(STD_WEEK_GAMES)
    EFFECTIVE_MEAN = round(sum(mu * pr for mu, pr in WEEK_MIX), 4)
    # 가드는 여기서도 돈다 — 주입 경로가 검사를 건너뛰면 조용히 틀린다
    for mu, _ in WEEK_MIX:
        if not (1.0 <= mu <= 9.0):
            raise ValueError("주 평균 %.3f — 팀당 주간 경기수 범위(1~9) 밖이다." % mu)
    if abs(sum(pr for _, pr in WEEK_MIX) - 1.0) > 1e-9:
        raise ValueError("주 유형 확률 합이 1이 아니다")
    return {"model": WEEK_MODEL, "standard": STD_WEEK_GAMES,
            "effective_mean": EFFECTIVE_MEAN, "mix": list(WEEK_MIX)}


def week_games_drawer(rng):
    """🔴 **매치업당 한 번** 호출한다. 주 유형을 뽑아 선수별 추첨 클로저를 돌려준다.

    2단 구조다 — 둘 중 하나만 하면 양쪽으로 틀린다:
      1단  **주 유형**을 매치업당 한 번 뽑아 **양 팀이 공유**한다.
           NBA 캘린더는 리그가 공유한다 — 우리는 W7(6.83경기), 상대는 W17(3.90경기)인
           매치업은 존재하지 않는다. `simulate()` 가 클로저 하나를 양쪽에 넘긴다.
      2단  그 유형의 평균을 중심으로 **선수마다** 경기수를 뽑는다(돌려준 클로저).
           팀별 주간 경기수는 캘린더 안에서 흩어진다(관측: 한 주 30팀이
           2G 4 · 3G 13 · 4G 12 · 5G 1). 이 변동을 0으로 만들면 팀 총합 분산이
           급감해 **강한 쪽 승률이 부풀어 오른다.**"""
    if len(_WEEK_DRAW) == 1:
        _, b, p = _WEEK_DRAW[0]
    else:
        x = rng.random()
        for cum, b, p in _WEEK_DRAW:
            if x < cum: break
    return lambda r: (b + 1) if r.random() < p else b


def draw_week_games(rng):
    """(구) 선수별 추첨 — **주 유형을 모르는** 경로. 표준 주로 뽑는다.

    ⚠️ 혼합 모형에서 이 함수만 쓰면 긴 주가 통째로 사라진다. 매치업 단위 코드는
    `week_games_drawer` 를 쓸 것. 남겨둔 이유는 주 유형이 의미 없는 호출자
    (단일 선수 주간 기여 근사)가 있기 때문이다."""
    return (STD_BASE + 1) if rng.random() < STD_P else STD_BASE


def avail(r): return (r.get("GP") or 0)/82.0

def baselines_per_game():
    """선수 가중치용 기준선 — 경기당·비가중.
    가중치는 '그 선수가 뛸 때 무엇을 주는가'(실력)를 재는 값이므로 출장률을 섞지 않는다.
    출장 리스크는 GP·gp_qualified·flag가 따로 담당한다."""
    top=sorted([p for p in PL.values() if p["name"] in F],
               key=lambda p:-(p["market_low"]+p["market_high"])/2)[:POOL_N]
    B={}
    for cat in COUNT:
        v=[F[p["name"]][cat] for p in top if F[p["name"]].get(cat) is not None]
        B[cat]=round(statistics.mean(v),4)
    for cat,at in RATE.items():
        v=[F[p["name"]] for p in top if F[p["name"]].get(cat) is not None and F[p["name"]].get(at) is not None]
        B[cat]=round(sum(r[cat]*r[at] for r in v)/sum(r[at] for r in v),5)
    B["A/T"]=round(B["AST"]/B["TOV"],4)
    return B

def player_lift(name, cat, Bpg):
    """선수 한계기여 — 경기당 기준. 가중치 부여·검증에 쓴다."""
    r=F.get(name)
    if not r: return None
    b=Bpg[cat]
    if cat=="A/T": return r.get("at_marginal_lift")
    if cat in RATE:
        v,a=r.get(cat),r.get(RATE[cat])
        return None if (v is None or a is None) else round((v-b)*a*100,2)
    v=r.get(cat)
    if v is None: return None
    return round(b-v,3) if cat in LOWER else round(v-b,3)

def baselines():
    """지명 풀 상위 126명 · GP 가중 · 슬롯당 기대치."""
    top=sorted([p for p in PL.values() if p["name"] in F],
               key=lambda p:-(p["market_low"]+p["market_high"])/2)[:POOL_N]
    B={}
    for cat in COUNT:
        v=[F[p["name"]] for p in top if F[p["name"]].get(cat) is not None and F[p["name"]].get("GP")]
        B[cat]=round(statistics.mean(r[cat]*avail(r) for r in v),4)
    for cat,at in RATE.items():
        v=[F[p["name"]] for p in top if F[p["name"]].get(cat) is not None
           and F[p["name"]].get(at) is not None and F[p["name"]].get("GP")]
        num=sum(r[cat]*r[at]*avail(r) for r in v); den=sum(r[at]*avail(r) for r in v)
        B[cat]=round(num/den,5)
    B["A/T"]=round(B["AST"]/B["TOV"],4)
    return B

def marginal(names, cat, B):
    """팀 한계기여. 양수 = 그 캣을 이긴다. names는 로스터 9명 전원."""
    b=B[cat]
    if cat=="A/T":
        rr=[F[n] for n in names if n in F and F[n].get("AST") is not None
            and F[n].get("TOV") is not None and F[n].get("GP")]
        if not rr: return None
        a=sum(r["AST"]*avail(r) for r in rr); t=sum(r["TOV"]*avail(r) for r in rr)
        return round(a/t-b,3)
    if cat in RATE:
        at=RATE[cat]
        rr=[F[n] for n in names if n in F and F[n].get(cat) is not None
            and F[n].get(at) is not None and F[n].get("GP")]
        if not rr: return None
        num=sum(r[cat]*r[at]*avail(r) for r in rr); den=sum(r[at]*avail(r) for r in rr)
        return round((num/den-b)*den*100,1)
    rr=[F[n] for n in names if n in F and F[n].get(cat) is not None and F[n].get("GP")]
    if not rr: return None
    t=sum(r[cat]*avail(r) for r in rr); base=b*len(rr)
    return round((base-t) if cat in LOWER else (t-base),1)

def evaluate(names, B=None):
    """로스터 9명의 13캣 판정. 승리 캣 수는 **전부 실측/추정 기반**이다.

    ⚠️ 24차 정정: 이전 시그니처는 evaluate(names, B, dd_target=True)였고,
    dd_target이 참이면 **측정 없이 +1캣**을 더했다. DD 실측 소스가 25명뿐이라
    그렇게 뒀던 것인데, 코어 7개 중 6개가 그 공짜 캣으로 승리선(7캣)을 넘고 있었다 —
    가정 하나가 판정 전체를 떠받치는 구조였다. 지금은 DD도 dd_game_prob으로 추정해
    다른 12캣과 똑같이 marginal()로 판정한다."""
    B=B or baselines()
    cm={c:marginal(names,c,B) for c in CATS}
    win=[c for c,v in cm.items() if v is not None and v>0]
    lose=[c for c,v in cm.items() if v is not None and v<=0]
    return cm, len(win), win, lose

def rel_margin(cat, v, B, names=None):
    """상대 마진(%) — 캣 간 비교용. 기준선 대비.

    ⚠️ 29차 정정 — **비율캣 분모가 틀렸다.**
    marginal()의 비율캣 반환값은 v = (rate − b) × 시도량 × 100 이다(볼륨 레버리지).
    이전 구현은 이것을 계수캣과 같은 분모(b×9)로 나눴다:

        (구) v/100/(b*9)*100 = (rate−b)·att/(9b)·100

    여기서 att/9 가 남는다. 팀 시도량은 캣마다 전혀 다르므로 **캣별로 다른 배율**로
    부풀었다 — c6 기준 FG% **10.5배** · FT% 3.3배 · 3P% 2.4배. 계수캣과 같은 자가 아니고,
    비율캣끼리도 같은 자가 아니다. "7캣 전부 N% 이상 마진" 같은 **캣 간 비교가 무의미**했다.

        (신) (rate − b)/b × 100          시도량을 빼고 순수 비율 개선

    비율캣은 시도량 합(den)이 필요하므로 names를 받는다. names 없이 비율캣을 부르면
    계산할 수 없으므로 None을 돌려준다 — 조용히 틀린 값을 내는 것보다 낫다.
    (볼륨 레버리지 자체는 marginal()의 절대값에 그대로 남아 있다. 여기서 빼는 것은
     '캣 간 비교용 무차원 척도'에서다.)"""
    if v is None: return None
    b=B[cat]
    if cat in RATE:
        if not names: return None
        at=RATE[cat]
        rr=[F[n] for n in names if n in F and F[n].get(cat) is not None
            and F[n].get(at) is not None and F[n].get("GP")]
        den=sum(r[at]*avail(r) for r in rr)
        if not den: return None
        num=sum(r[cat]*r[at]*avail(r) for r in rr)
        return (num/den - b)/b*100
    if cat=="A/T":  return v/b*100
    return v/(b*9)*100

# ── DD (더블더블) 추정 ──────────────────────────────────────────────────
# 23차까지 evaluate()는 dd_target이면 **측정 없이 +1캣**을 줬다. 코어 7개 전부가
# 그 공짜 1캣에 승리선(7캣)을 의존하고 있었으므로, 가정 하나가 판정을 떠받치고 있었다.
# BBRef가 DD를 집계하지 않아 실측이 25명(리더보드)뿐이라 그렇게 뒀던 것인데,
# per-game PTS·REB·AST가 있으면 추정은 가능하다.
#
# 모델: 한 경기에서 PTS·REB·AST 중 **2개 이상이 10 이상**일 확률 × 출장경기수.
#   각 스탯을 정규분포 N(μ, σ²)로 근사하고 연속성 보정(10 이상 → 9.5 초과)을 쓴다.
#   σ는 과분산 포아송 형태 σ = c·√μ 로 잡는다. c는 실측 DD를 보지 않고 미리 정한다
#   (검증 집합에 맞춰 c를 튜닝하면 검증이 무의미해진다):
#     PTS c=1.50  — 25득점 선수의 경기간 SD ≈ 7.5
#     REB c=1.10  — 10리바운드 선수의 SD ≈ 3.5
#     AST c=1.05  — 8어시스트 선수의 SD ≈ 3.0
#
# ⚠️ 알려진 편향 두 가지 — 결과를 읽을 때 반드시 같이 본다:
#   (1) **독립 가정**. PTS·REB는 출장시간·사용률이 같이 밀어올리므로 양의 상관이 있다.
#       독립으로 곱하면 P(둘 다 ≥10)이 **과소**추정된다 → 빅맨에서 저추정 경향.
#   (2) **트리플더블 경로 무시 아님**: 2개 이상이므로 TD도 포함된다. 다만 STL·BLK가
#       10을 넘는 경우(사실상 0)는 무시한다.
_DD_C = {"PTS": 1.50, "REB": 1.10, "AST": 1.05}
_DD_THRESHOLD = 10
_DD_CONT = 0.5          # 연속성 보정

def _norm_sf(z):
    """P(Z > z). math.erfc 기반 — 외부 의존 없이."""
    return 0.5*math.erfc(z/math.sqrt(2.0))

def dd_game_prob(pts, reb, ast):
    """한 경기에서 더블더블이 날 확률. 세 스탯의 경기당 평균을 받는다."""
    ps=[]
    for cat, mu in (("PTS",pts),("REB",reb),("AST",ast)):
        mu = mu or 0.0
        if mu <= 0: ps.append(0.0); continue
        sd = _DD_C[cat]*math.sqrt(mu)
        ps.append(_norm_sf(((_DD_THRESHOLD-_DD_CONT)-mu)/sd))
    p1,p2,p3 = ps
    # P(2개 이상) = Σ 쌍곱 − 2·삼중곱
    return p1*p2 + p1*p3 + p2*p3 - 2*p1*p2*p3

def dd_estimate(pts, reb, ast, gp):
    """시즌 DD 추정 = 경기당 확률 × 출장경기수."""
    if not gp: return None
    return dd_game_prob(pts, reb, ast)*gp

def dd_from_row(r):
    """measured_full.json 한 행에서 DD를 추정한다."""
    if not r: return None
    return dd_estimate(r.get("PTS"), r.get("REB"), r.get("AST"), r.get("GP"))
