#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README 의 승률 표 2종을 **산출물에서** 다시 쓴다 (46차 · 도구로 승격).

## 왜 도구인가
44차에 승격(c6 BN)으로, 46차에 DD 실계수 채택으로 **두 번** 이 표를 손으로 고쳤다.
승률이 바뀔 때마다 낡는 표이고, 손으로 숫자를 옮기면 그때마다 틀릴 기회가 생긴다
— 이 저장소는 그 실패를 여러 번 겪었다(낡은 「21명 실측 1위」·「상위 5개와 동급」).
**표는 `data/matchup_sim.json` 에서 생성한다. 손으로 고치지 않는다.**

⚠️ 표 밖 **서술 문장**은 자동으로 못 고친다. 이 스크립트는 바뀐 숫자를 찍어 주므로
   그 목록을 들고 서술을 직접 확인할 것.

실행:  python3 tool/gen_readme_tables.py
"""
import io, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = json.load(io.open(f"{BASE}/data/matchup_sim.json", encoding="utf-8"))
ST = {r["core"]: r for r in SIM["assumption_stress"]["rows"]}
CO = SIM["cores"]
LBL = {"c1": "KAT + Haliburton", "c2": "Jokić 앵커", "c3": "SGA 앵커",
       "c4": "무앵커 분산 (상한 $31)", "c5": "Sabonis 부상 할인",
       "c6": "전방위 윙 · **정상 시장 기본값**", "c7": "중가 센터 전환"}
NOTE = {"c1": "KAT ≤ $50 · Hali ≤ $56 · ⚠ Hali 73경기 가정",
        "c2": "Jokić ≤ $97", "c3": "SGA ≤ $85 · 🔴 **Lillard 투영 GP**",
        "c4": "앵커 실패", "c5": "🔴 가정 셋 — 참고 열 참조",
        "c6": "없음", "c7": "저가 센터 2명+ 과열"}


def who(cid):
    a = ST[cid]["assumptions"]
    return " + ".join(x["player"].split()[-1] for x in a) if a else "**없음 — 1순위 전원 실측**"


def main():
    p = BASE + "/README.md"
    s = io.open(p, encoding="utf-8").read()
    old = s

    # ── 표 1: 가정 취약성 ──
    t1 = []
    for cid in sorted(ST, key=lambda c: (-ST[c]["delta"], -CO[c]["real_mean_win_rate"])):
        r = ST[cid]
        d = 100 * r["delta"]
        t1.append("| %s | %.1f%% | **%.1f%%** | %s | %s |" % (
            ("**%s**" % cid) if d == 0 else cid, 100 * r["base"], 100 * r["stressed"],
            "**±0**" if d == 0 else ("**%.1f%%p**" % d if d <= -5 else "%.1f%%p" % d), who(cid)))
    m1 = re.search(r"(?m)^\| \*{0,2}c\d\*{0,2} \| \d[\d.]*% \|(?:.*\n)+?(?=\n)", s)
    assert m1, "표1 을 못 찾았다 — README 구조가 바뀌었다"
    s = s[:m1.start()] + "\n".join(t1) + "\n" + s[m1.end():]

    # ── 표 2: 판단표 요약 ──
    order = sorted(CO, key=lambda c: -CO[c]["real_mean_win_rate"])
    t2 = []
    for cid in order:
        d = 100 * ST[cid]["delta"]
        tier = "**1위**" if cid == order[0] else ("아래" if cid in ("c5", "c4") else "동급")
        t2.append("| %s | %s | %s | %.1f%% | %.1f%% | %s | %s |" % (
            tier, cid, LBL[cid], 100 * CO[cid]["real_mean_win_rate"],
            100 * CO[cid]["real_min_win_rate"],
            "**±0 🟢**" if d == 0 else "%.1f%%p" % d, NOTE[cid]))
    m2 = re.search(r"(?m)^\| (?:\*\*1위\*\*|동급|아래) \| c\d \|(?:.*\n)+?(?=\n)", s)
    assert m2, "표2 를 못 찾았다"
    s = s[:m2.start()] + "\n".join(t2) + "\n" + s[m2.end():]

    io.open(p, "w", encoding="utf-8").write(s)
    print("README 표 2종 재생성 · 변경 %s" % ("있음" if s != old else "없음"))
    print("\n현재 값 (서술 문장은 **직접** 확인할 것)")
    for cid in order:
        print("  %-3s 평균 %.2f%% · 최저 %.2f%% · 취약성 %+.2f%%p"
              % (cid, 100 * CO[cid]["real_mean_win_rate"],
                 100 * CO[cid]["real_min_win_rate"], 100 * ST[cid]["delta"]))
    g = 100 * (CO[order[0]]["real_mean_win_rate"] - CO[order[1]]["real_mean_win_rate"])
    print("  1-2위 격차 %.2f%%p · 대응 SE %.2f%%p (배수 %.1f)"
          % (g, 100 * SIM["standard_error"]["paired_se_median"],
             g / (100 * SIM["standard_error"]["paired_se_median"])))


if __name__ == "__main__":
    main()
