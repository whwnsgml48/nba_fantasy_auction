#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""탐색기의 **후보 풀 생성** — 두 축 혼합을 강제한다 (40차 신설).

🔴 왜 이 파일이 있는가 — 40차에 **네 번 중 네 번** 같은 실패를 했다

```
1차 rate_core_search   프리필터가 캣 마진을 원값으로 합산 → FG% 가 지배 → 「FG% 최대화」를 탐색
2차 guard_stack 참고값  matchup_sim.z() 가 정규화 없이 합산 → 슈팅과 무관한 이름이 든 로스터
3차 shooting_core       후보를 **달러당**으로만 정렬 → 전부 $2 → 총액 $24 짜리 퇴화 해
4차 guard_tilt          가드는 **절대값**만·빅은 **달러당**만 → $35~97 과 $2 → 조합 0개
```

**증상**  탐색 첫 실행이 항상 깨진다 — 하이재킹 · 퇴화 해 · 조합 0개
**원인**  후보를 **한 축으로만** 정렬한다
          절대값만 → 비싼 쪽에 몰려 **예산 초과**
          달러당만 → $2 에 몰려 **예산 미소진**
**빈도**  40차에서 **4/4 · 예외 없음**

⚠️ **「다음엔 조심하겠다」로는 안 된다.** 네 번 조심했고 네 번 다 밟았다.
   그래서 이 파일은 조언이 아니라 **강제**다 — `mix_axes()` 를 쓰고, 섞이지 않았으면
   `assert` 로 죽는다. 탐색기를 새로 쓸 때 후보 풀은 **여기를 거쳐야 한다.**
"""


def mix_axes(rows, k, score=lambda r: r[2], price=lambda r: r[1], name=lambda r: r[0],
             min_span=3.0, label=""):
    """절대 점수 상위 k 와 **달러당** 상위 k 를 합쳐 후보 이름 목록을 만든다.

    rows      (name, price, score, ...) 튜플들. 접근자는 인자로 바꿀 수 있다.
    min_span  섞인 결과의 **가격 범위**(최대/최소)가 이 배수 이상이어야 한다.
              한 가격대에 몰리면 예산 구간을 못 만든다 — 그게 4/4 실패의 형태다.

    🔴 두 축을 섞었는데도 가격대가 몰려 있으면 **AssertionError 로 죽는다.**
       조용히 나쁜 후보를 내놓느니 멈추는 편이 낫다 — 40차에 조용히 통과한 결과가
       「사전 등록 기준에 맞는 쓰레기」였다.
    """
    if not rows:
        raise AssertionError("mix_axes(%s): 입력이 비었다" % label)
    by_abs = sorted(rows, key=lambda r: -score(r))[:k]
    by_eff = sorted(rows, key=lambda r: -score(r) / max(1, price(r)))[:k]
    out = list(dict.fromkeys([name(r) for r in by_abs] + [name(r) for r in by_eff]))
    idx = {name(r): price(r) for r in rows}
    ps = [idx[n] for n in out]
    lo, hi = max(1, min(ps)), max(ps)
    span = hi / lo
    if span < min_span:
        raise AssertionError(
            "mix_axes(%s): 후보 가격대가 %.1f배로 좁다 ($%d~$%d · %d명). "
            "한 가격대에 몰리면 예산 구간을 못 만든다 — 40차에 4/4 로 겪은 형태다. "
            "점수식이나 k 를 고쳐서 비싼 쪽과 싼 쪽이 **둘 다** 들어오게 하라."
            % (label or "?", span, lo, hi, len(out)))
    return out


def assert_spend_band(total, lo, hi, label=""):
    """조립 결과의 총액이 의도한 구간 안인지. 퇴화 해(총액 $24)를 막는다."""
    if not (lo <= total <= hi):
        raise AssertionError(
            "%s: 총액 $%d 가 의도 구간 $%d~$%d 밖이다. "
            "예산을 안 쓰면 남긴 돈은 0점이다(docs/12 §1)." % (label or "조립", total, lo, hi))
    return total
