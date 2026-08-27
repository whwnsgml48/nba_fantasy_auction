#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""측정 오차를 시뮬 산출물에 저장한다 (40차 신설).

왜 데이터로 내리는가
  판단표가 상위 코어들을 **「동급 묶음」**으로 묶는데, 그 컷 폭이 화면에 상수로 박히면
  상대 집합을 바꾸는 순간(13팀으로 늘리거나 다른 리그 실측으로 교체하면) **조용히 틀린다.**
  이 저장소가 반복한 형태 그대로다. 컷은 측정에서 나와야 한다.

🔴 두 오차를 구분한다 — 섞으면 4배 틀린다
  **비대응(unpaired) SE** = 상대별 승률의 표본SD ÷ √n.  **≈ 2.5%p**
    "이 코어의 평균 승률이 얼마인가"의 오차다. 상대 12팀이 서로 크게 다르기 때문에
    (상대 간 SD 7.5~9.7%p) 이 값은 클 수밖에 없다.

  **대응(paired) SE** = 두 코어의 **상대별 차이** 벡터의 SD ÷ √n.  **≈ 0.6%p**
    "코어 A 가 코어 B 보다 나은가"의 오차다. 모든 코어를 **같은 12팀**에 붙이므로
    상대의 강약이 양쪽에 똑같이 들어가 **상쇄된다.**

  코어를 **비교**할 때 쓸 값은 대응 SE 다. 비대응 SE(2.5%p)로 컷을 잡으면 c4 만 빼고
  전부 한 덩어리가 돼 **없는 불확실성을 만든다.**

⚠️ 시행수로는 거의 안 줄어든다
  병목은 몬테카를로가 아니라 **n=12** 다. 2500 → 10000 시행에서 0.87 → 0.77%p 로
  0.1%p 줄었을 뿐이다. 정밀도를 올리려면 상대 표본을 늘려야 한다.

⚠️ 쌍마다 다르다
  c1-c6 은 0.25%p, c2-c3 은 0.80%p 다. 선수를 많이 공유하는 코어끼리는 차이가
  더 정밀하게 측정된다. 단일 컷은 근사이므로 **쌍별 행렬도 함께 저장**한다.
"""
import json, io, os, statistics as st, itertools

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = BASE + "/data/matchup_sim.json"


def main():
    sim = json.load(io.open(SP, encoding="utf-8"))
    C = sim["cores"]
    mgrs = list(next(iter(C.values()))["real"])
    n = len(mgrs)
    V = {c: [C[c]["real"][m]["weekly_win_rate"] for m in mgrs] for c in C}

    unpaired = {}
    for c, v in V.items():
        se = st.stdev(v) / n ** 0.5
        unpaired[c] = round(se, 4)
        C[c]["real_mean_se_unpaired"] = round(se, 4)

    pairs = {}
    for a, b in itertools.combinations(sorted(C), 2):
        d = [x - y for x, y in zip(V[a], V[b])]
        pairs["%s-%s" % (a, b)] = {"mean_diff": round(st.mean(d), 4),
                                   "se": round(st.stdev(d) / n ** 0.5, 4)}
    med = round(st.median(p["se"] for p in pairs.values()), 4)

    sim["standard_error"] = {
        "n_opponents": n,
        "paired_se_median": med,
        "paired_se_by_pair": pairs,
        "unpaired_se_by_core": unpaired,
        "which_to_use": ("코어끼리 **비교**할 때는 paired 를 쓴다. unpaired 는 '이 코어의 절대 승률이 "
                         "얼마인가'의 오차이고, 모든 코어를 같은 12팀에 붙이므로 비교에서는 "
                         "상대의 강약이 상쇄된다. 섞으면 4배 크게 잡는다."),
        "definition": ("paired: 두 코어의 상대별 승률 **차이** 벡터의 표본SD ÷ √n. "
                       "unpaired: 한 코어의 상대별 승률 벡터의 표본SD ÷ √n."),
        "not_monte_carlo": ("🔴 몬테카를로 오차가 아니다 — 시행수를 늘려도 거의 안 줄어든다"
                            "(2500 ±0.87%p → 10000 ±0.77%p). 병목은 n=12 다."),
        "use": ("판단표 「동급 묶음」 컷에 쓴다. **컷 폭을 화면에 상수로 박지 말 것** — "
                "상대 집합이 바뀌면 이 값이 바뀌는데 화면 상수는 그대로 남아 조용히 틀린다."),
        "suggested_cut": round(1.25 * med, 4),
        "caveat": ("단일 컷은 근사다. 쌍마다 SE 가 다르다(c1-c6 0.25%p ↔ c2-c3 0.80%p) — "
                   "선수를 많이 공유하는 코어끼리는 차이가 더 정밀하게 측정된다."),
    }
    json.dump(sim, io.open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cut = 1.25 * med
    print("대응 SE 중앙값 %.2f%%p · 컷 제안 %.2f%%p (비대응 %.2f%%p 는 비교용이 아니다)"
          % (100 * med, 100 * cut, 100 * st.median(unpaired.values())))
    o = sorted(C, key=lambda c: -C[c]["real_mean_win_rate"])
    grp = [[o[0]]]
    for a, b in zip(o, o[1:]):
        if C[a]["real_mean_win_rate"] - C[b]["real_mean_win_rate"] > cut:
            grp.append([b])
        else:
            grp[-1].append(b)
    print("동급 묶음: " + "  |  ".join(
        " ".join("%s %.1f" % (c, 100 * C[c]["real_mean_win_rate"]) for c in g) for g in grp))


if __name__ == "__main__":
    main()
