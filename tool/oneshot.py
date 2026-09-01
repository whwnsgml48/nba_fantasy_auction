#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1회성 이행 스크립트의 **재실행 가드** — 클래스 차원의 처방 (2026-09-01 신설).

🔴 왜 있는가 — 두 번 물렸다
```
잠재  tool/fix_preseason_gates.py  본문이 옛 날짜(09-05) 위에 있어, 돌면 cores.json
                                  정정본을 40차 문안으로 덮는다
실제  tool/guard_tilt_search.py    재실행이 손으로 쓴 `verdict`·`first_run_discarded`
                                  (4차 탐색을 닫은 판정)를 **날렸다**
```
**`validate.py` 는 이걸 못 잡는다.** 덮어쓴 문장도 문법이 멀쩡하고 불변식을 안 건드린다.
사람이 읽어야만 「이건 옛날 문안이다」를 안다 — 그래서 검사로는 안 되고 **차단**이어야 한다.

⚠️ 이 저장소의 1회성 스크립트는 **문안을 하드코딩**한다. 그 문안은 쓰인 회차의
   사실 위에 있다. 회차가 지나면 스크립트는 **자산이 아니라 지뢰**다 —
   지워도 되지만 「무엇을 왜 바꿨나」의 기록이라 남긴다. 남기려면 **막아야 한다.**

## 쓰는 법

    import oneshot
    oneshot.spent(
        __file__,
        did="40차 후속 4건 — 실행 불가 대체안 · Hart 최대가 · DeRozan 감시",
        breaks="재실행하면 data/cores.json·matchup_sim.json 을 40차 문안으로 덮는다 (샌드박스 측정 확인)",
        instead="지금 문안을 고치려면 해당 파일을 직접 고치고 validate.py 를 돌려라",
    )

🔴 **`did`/`breaks`/`instead` 를 전부 채워라.** 「1회성이다」만 적혀 있으면 다음 사람이
   가드를 지우고 돌린다 — 왜 막혔는지와 그래도 하려면 무엇을 하는지가 있어야 멈춘다.

## 그래도 돌려야 한다면

    ONESHOT_FORCE=apply_40_followups python3 tool/apply_40_followups.py

일부러 이름을 적게 했다. `--force` 였으면 반사적으로 붙인다.
"""
import os
import sys

ENV = "ONESHOT_FORCE"


def spent(script_file, did, breaks, instead):
    """이 스크립트는 **소진된 1회성 이행 스크립트**다. 강제하지 않으면 여기서 멈춘다.

    did      무엇을 한 스크립트인가 (어느 회차의 무슨 이행인가)
    breaks   재실행하면 **무엇이 덮이는가** — 추측 말고 측정한 것을 적어라
    instead  그 일을 지금 하려면 **대신 무엇을 하는가**
    """
    name = os.path.basename(script_file).rsplit(".", 1)[0]
    if os.environ.get(ENV) == name:
        sys.stderr.write("⚠️ %s=%s — 가드를 넘어 실행한다. %s\n" % (ENV, name, breaks))
        return
    raise SystemExit(
        "🔴 tool/%s.py 는 **소진된 1회성 이행 스크립트**다 — 실행하지 않았다.\n"
        "\n"
        "   한 일     %s\n"
        "   재실행하면 %s\n"
        "   대신      %s\n"
        "\n"
        "   ⚠️ validate.py 는 이 사고를 못 잡는다 — 덮어쓴 문장도 문법과 불변식이 멀쩡하다.\n"
        "   정말 돌려야 하면:  %s=%s python3 tool/%s.py\n"
        % (name, did, breaks, instead, ENV, name, name))
