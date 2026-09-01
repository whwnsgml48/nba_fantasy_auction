#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""프리시즌·캠프 관측 갱신 **절차** — 2026-09-01 날짜 정정으로 생긴 창구.

왜 생겼나
  사용자가 드래프트를 **2026-09-05 → 2026-10-05** 로 정정했다. 그 결과
  전 구단 훈련캠프(09-29)와 프리시즌 경기 개시(10-03)가 **드래프트 앞**으로 왔다.
  이 저장소가 「확인할 방법이 없다」고 닫아 둔 항목들이 다시 열렸다 — `docs/05 §6f`.

🔴 이 스크립트가 **하지 않는** 것
  · 값을 추정해서 채우지 않는다. 사람이 넣지 않은 칸은 **빈칸으로 남는다.**
  · 투영 GP·`value_model`·계획가·상한을 건드리지 않는다. 1~2경기로 174명 모델을
    흔드는 것이 정확히 `docs/11` 이 막는 일이다.
  · `injury_exclude` 를 건드리지 않는다 — 취득 제외는 다른 축이다.

⚠️ 잴 수 있는 것은 **「뛰는가」라는 이항 하나**다.
   GP 73 과 54 를 가르는 것은 정도이고, 캠프 6일 + 실경기 ≤2일로는 **못 잰다.**
   코어를 5.4%p 움직이는 것은 그 정도 쪽이다 — 이항이 확인돼도 그건 미해소로 남는다.

⚠️ **프리시즌 개막일은 팀마다 다르다.** 리그 개시일(10-03)로 판정하면 틀린다 —
   확인된 반례: **POR 는 10-07 개막으로 드래프트 뒤**이고, 하필 Lillard 의 팀이다.
   그래서 아래 표의 첫 칸이 「그 선수의 팀 개막일」이다.
"""
import io, json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = BASE + "/data/preseason_observations.json"

DRAFT = "2026-10-05"
CAMP_ALL = "2026-09-29"          # 전 구단 훈련캠프 개시 · 드래프트 −6일
CAMP_INTL = "2026-09-22"         # 해외 경기팀 · 드래프트 −13일
PRESEASON_OPEN = "2026-10-03"    # 리그 최초 경기 · 드래프트 −2일 (팀별로 다름)

# 관측 대상 — 투영 GP 가정을 지고 있는 선수들. 팀 개막일은 **확인된 것만** 적는다.
WATCH = [
    # (선수, 팀, 팀 프리시즌 개막일 or None, 어느 코어가 이 가정 위에 있나)
    ("Damian Lillard",    "POR", "2026-10-07", "c3 — 87.7%가 이 가정 위. 실측 비중 0.0%"),
    ("Tyrese Haliburton", "IND", None,         "c1·c5 — GP 73→54 면 c1 이 5.4%p 빠진다"),
    ("Domantas Sabonis",  "SAC", None,         "c5 — 발동 조건 자체"),
    ("Trae Young",        "WAS", None,         "c4 — 실측 비중 22.8% · 워싱턴 역할 데이터 없음"),
    ("Nikola Jokić",      "DEN", None,         "c2 — 게이트가 열리면 최우선. GP 민감도 기록 있음"),
]

# 사전 등록 판정 기준 — **관측 전에 박아 둔다.** 보고 나서 고치면 사후 합리화다(docs/11 ⑧).
CRITERION = {
    "이항 확인": "캠프 **풀 연습 참가** 보도 + (팀이 드래프트 전 경기를 했다면) **출전**",
    "결장":      "구단·보도가 드래프트 시점 결장/제한을 명시하거나 야후 OUT·IL 지정",
    "미확인":    "위 둘 중 어느 쪽도 아님 — 제한 참가 · 미보도 · 팀이 경기를 안 함",
}
# 🔴 「미확인」은 「결장」이 아니다. 섞으면 안 뛴다는 근거 없이 코어를 내리게 된다.


def load():
    if os.path.exists(LEDGER):
        return json.load(io.open(LEDGER, encoding="utf-8"))
    return {"draft_date": DRAFT, "observations": {}, "yahoo_eligibility_2026_27": {
        "published_before_draft": None,       # ⬜ 야후가 10-05 전에 공시하는가 — 미확인
        "checked_at": None,
        "note": "개막(10-20) 전에 공시되는 것만 안다. 드래프트 전인지는 확인되지 않았다.",
    }}


def main():
    led = load()
    obs = led["observations"]

    print("프리시즌 관측 원장 — 드래프트 %s\n" % DRAFT)
    print("  캠프 개시  %s (해외 경기팀) · %s (전 구단 · 드래프트 −6일)" % (CAMP_INTL, CAMP_ALL))
    print("  프리시즌   %s 개시 (~10-16) · 드래프트 −2일  ⚠️ 팀별 개막일이 다르다\n" % PRESEASON_OPEN)

    print("  %-19s %-4s %-12s %-9s %s" % ("선수", "팀", "팀 개막", "판정", "실경기 채널"))
    print("  " + "-" * 74)
    blanks = 0
    for name, team, opens, why in WATCH:
        rec = obs.get(name) or {}
        verdict = rec.get("verdict") or "⬜ 미기입"
        if opens is None:
            ch, od = "⬜ 팀 일정 미확인", "⬜ 미확인"
            blanks += 1
        elif opens > DRAFT:
            ch, od = "🔴 없다 (드래프트 뒤)", opens
        else:
            ch, od = "있다", opens
        if not rec.get("verdict"):
            blanks += 1
        print("  %-19s %-4s %-12s %-9s %s" % (name.split()[-1], team, od, verdict, ch))
        print("       └ %s" % why)

    print("\n  사전 등록 판정 기준")
    for k, v in CRITERION.items():
        print("    %-8s %s" % (k, v))
    print("    🔴 「미확인」은 「결장」이 아니다 — 섞으면 근거 없이 코어를 내리게 된다.")

    ye = led["yahoo_eligibility_2026_27"]
    print("\n  야후 2026-27 자격 공시가 드래프트(%s) 전인가: %s"
          % (DRAFT, "⬜ 미확인" if ye["published_before_draft"] is None else ye["published_before_draft"]))
    print("    현재 19명 손확인 · 11명 불일치(전부 낙관 방향) · 73명 미확인")
    print("    공시돼 있으면 pos_yahoo 를 채우고 validate.py [I31] 재실행.")
    print("    ⚠️ 편향이 낙관 방향이므로 **자격이 좁아지는 쪽**으로 움직일 것을 예상할 것.")

    print("\n  빈칸 %d개 — 값은 %s 이후에 사람이 채운다. **추정으로 채우지 말 것.**" % (blanks, CAMP_ALL))
    print("  절차 전문: docs/05 §6f · 드래프트 전 체크리스트: docs/12 §9b-C")

    if not os.path.exists(LEDGER):
        json.dump(led, io.open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n  %s 생성 (전부 빈칸)" % os.path.relpath(LEDGER, BASE))


if __name__ == "__main__":
    main()
