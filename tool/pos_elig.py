#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""슬롯 자격 판정의 **단일 소스** (40차 신설).

왜 여기 모으는가
  `validate.py` 는 `NEED={"PG":"G",...}` + `k in p["pos"]` 라는 **문자열 포함 검사**로
  자격을 봐 왔다. 그 규칙이 `pos="G/F"` 를 SF 로도 PF 로도 통과시켰고, 그래서
  불변식 30개가 **SF 충원 0명인 c3** 를 통과시켰다. 규칙 자체는 틀리지 않았다 —
  입력이 3분 추상(G/F/C)이라 실제 자격보다 **넓었을 뿐**이다.

  이제 `pos_yahoo`(실자격)가 생겼으므로 판정이 두 갈래다. 그 갈래를 여러 파일이
  각자 구현하면 이 저장소가 반복해 당한 「같은 값을 두 곳에 두면 갈라진다」가 다시
  일어난다(39차 `tool_embed.py` 와 같은 이유). **여기 하나만 둔다.**

규칙
  · `pos_yahoo` 가 있으면 **그것이 전부다.** 추상 `pos` 로 보강하지 않는다 —
    보강하면 확인한 사실을 추정으로 되돌리는 셈이다.
  · 없으면 `pos` 를 펼친다: G→PG,SG · F→SF,PF · C→C.
  · UTIL·BN 은 무제한.

⚠️ 넓은 쪽이 안전한 게 아니다
  확인된 19명 중 **11명이 불일치했고 11건 전부 자격을 잃는 방향**이었다.
  추상 `pos` 는 계통적으로 **낙관 편향**이다. 미확인 선수를 쓸 때 그 사실을 기억할 것.
"""

EXPAND = {"G": ["PG", "SG"], "F": ["SF", "PF"], "C": ["C"]}
NAMED = ("PG", "SG", "SF", "PF", "C")
# 로스터 9칸. 선발 7 / 벤치 2 (docs/01).
ROSTER_SLOTS = ["PG", "SG", "SF", "PF", "C", "UTIL", "UTIL", "BN", "BN"]
START_SLOTS  = ["PG", "SG", "SF", "PF", "C", "UTIL", "UTIL"]


def elig(p):
    """선수 dict → 채울 수 있는 **명명 슬롯** 집합. UTIL·BN 은 포함하지 않는다."""
    y = p.get("pos_yahoo")
    if y:
        return set(y)
    out = set()
    for t in (p.get("pos") or "").split("/"):
        out |= set(EXPAND.get(t, []))
    return out


def confirmed(p):
    """자격이 **확인된** 선수인가. 미확인이면 판정이 낙관 편향임을 뜻한다."""
    return bool(p.get("pos_yahoo"))


def can(p, slot):
    return slot in ("UTIL", "BN") or slot in elig(p)


def match(players, slots=None):
    """이분매칭. players: [선수dict]. 전원 배정되면 {슬롯인덱스: 선수인덱스}, 아니면 None.

    슬롯이 9칸이고 선수도 9명이므로 완전매칭 여부가 곧 조립 가능 여부다.
    ⚠️ '조립 가능'은 합법성 판정이 아니다 — 야후는 커버리지를 강제하지 않는다.
      매칭이 깨진다는 것은 **그 칸이 매일 비어 선수-경기를 버린다**는 뜻이고,
      실제 손실률은 `tool/lineup_feasibility.py` 가 잰다(0.2~3.2%p).
    """
    slots = list(slots if slots is not None else ROSTER_SLOTS)
    adj = [[j for j in range(len(slots)) if can(p, slots[j])] for p in players]
    mt = [-1] * len(slots)

    def aug(i, seen):
        for j in adj[i]:
            if j in seen:
                continue
            seen.add(j)
            if mt[j] < 0 or aug(mt[j], set(seen)):
                mt[j] = i
                return True
        return False

    for i in range(len(players)):
        if not aug(i, set()):
            return None
    return {j: mt[j] for j in range(len(slots)) if mt[j] >= 0}


def max_match_size(players, slots):
    """전원 배정이 안 될 때 **몇 명까지** 들어가는가 (일일 라인업용)."""
    adj = [[j for j in range(len(slots)) if can(p, slots[j])] for p in players]
    mt = [-1] * len(slots)

    def aug(i, seen):
        for j in adj[i]:
            if j in seen:
                continue
            seen.add(j)
            if mt[j] < 0 or aug(mt[j], set(seen)):
                mt[j] = i
                return True
        return False

    return sum(1 for i in range(len(players)) if aug(i, set()))


def label_errors(roster, players_by_name):
    """선언된 슬롯 라벨이 그 선수에게 유효한가. roster: [(slot, name)].

    매칭이 성립해도 **라벨이 틀릴 수 있다** — 화면이 잘못된 자리를 지시한다.
    10초 시계 아래서 그 자리에 넣으려다 막히는 것은 실전 비용이다.
    """
    bad = []
    for slot, name in roster:
        p = players_by_name.get(name)
        if p is None or can(p, slot):
            continue
        bad.append((slot, name, sorted(elig(p))))
    return bad
