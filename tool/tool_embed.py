#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""툴 임베드 상수의 **단일 소스** (39차 신설).

왜 만드는가
  `sync_tool.py`(생성)와 `validate.py`(대조)가 **같은 구조를 각자 재구현**하고 있었다.
  이 저장소가 반복해 당한 「같은 값을 두 곳에 두면 반드시 갈라진다」 그대로이고,
  실제로 갈라졌다 — A가 `overheat_thresholds`에 `binding` 필드를 실어 툴에 노출하려 하자
  `sync_tool` 쪽만 바뀌고 `validate` 쪽은 그대로라 **즉시 `✗ 툴 OVERHEAT 불일치`**가 났다.
  필드 하나를 추가하려면 두 파일을 같이 고쳐야 했고, 그 사실을 아무도 모르고 있었다.

  이제 양쪽이 여기를 import 한다. **필드를 늘리려면 이 파일만 고치면 된다.**

경계
  · 순수 함수만 둔다. 파일을 읽지도 쓰지도 않는다(`sync_tool`은 import 시점에 HTML을
    다시 쓰므로, `validate`가 그걸 import 하면 검증이 파일을 변형시킨다).
  · `cores.json` dict 하나만 받는다.

앵커 결손 처리
  `build_cores`는 `(구조, 문제목록)`을 돌려준다. 33차에 `recompute_cores`가 앵커 2개에
  `anchor_plan`을 만들지 않아 `sync_tool`이 `KeyError`로 죽었고, 38차에는 같은 결손이
  `validate`를 중단시켜 뒤쪽 검사(I20·I11·I10)가 통째로 실행되지 않았다.
  → 여기서는 **죽지 않고 문제를 보고**한다. 소비자가 등급을 정한다:
    `sync_tool`은 생성을 중단해야 하고(깨진 상수를 쓰면 안 된다),
    `validate`는 위반으로 세고 나머지 검사를 계속한다.
"""


def build_overheat(cj):
    """툴 `OVERHEAT` 상수. 필드를 늘리려면 **여기만** 고친다."""
    out = []
    for t in cj["overheat_thresholds"]:
        e = {"n": t["player"], "tier": t["tier"], "walk": t["threshold"],
             "exp": t["expected_2026_27"], "oh": t["overheat_at"]}
        # 39차: 어떤 모델에서도 발동하지 않는 임계값은 툴에서 그렇게 보여야 한다.
        # "철수가 $18"을 보고 보호받는다고 믿는 것이 드래프트 당일 가장 나쁘다(I26 참조).
        if t.get("binding") is False:
            e["binding"] = False
        return_note = t.get("binding_note")
        if return_note:
            e["bnote"] = return_note
        out.append(e)
    return out


def build_decision(cj, sim=None):
    """판단표 상수. `sim`(data/matchup_sim.json)을 주면 각 행에 **강도**를 얹는다.

    39차 갈래 1: 판단표는 **도달 가능성 순**이지 강도 순이 아니다. 그 사실이 화면에
    없어서 우선순위가 강도로 오독됐다. 각 행에 실제 12팀 평균/최저 승률을 실어
    **방 안에서 사람이 거래를 보고 고르게** 한다.

    ⚠️ 강도는 `cores.json`에 넣지 않는다 — 32차 원칙(시뮬 산출물을 계획 파일에 쓰지
    말 것). 여기서 **툴 상수를 만들 때만** 합친다. `validate`도 같은 함수를 쓰면
    이중 구현이 안 생긴다.
    """
    out = []
    for d in cj["decision_table"]:
        e = dict(d)
        c = (sim or {}).get("cores", {}).get(d["core"]) if sim else None
        if c and c.get("real_mean_win_rate") is not None:
            e["str"] = {"mean": c["real_mean_win_rate"], "min": c.get("real_min_win_rate"),
                        "n": (sim or {}).get("iterations")}
        note = (cj.get("decision_strength_notes") or {}).get(d["core"])
        if note:
            e["snote"] = note
        out.append(e)
    return out


def build_tiers(cj):
    """툴 `OTIERS` 상수."""
    return {k: {"label": v["label"], "c7": v["counts_toward_core7"], "why": v["why"]}
            for k, v in (cj.get("overheat_tiers") or {}).items() if not k.startswith("_")}


def build_pivots(cj):
    """툴 `PIVOTS` 상수."""
    return {x["id"]: x["pivot_plan"] for x in cj["cores"]}


def build_cores(cj):
    """툴 `CORES` 상수. 반환 `(list, problems)` — problems 는 앵커 결손 설명 문자열."""
    problems = []
    out = [{"id": "c0", "n": "— 코어 미선택 —"}]
    for co in cj["cores"]:
        plan = []
        for sl in co["slots"]:
            row = [sl["slot"], sl.get("role") or "",
                   [[x["name"], x["plan_price"]] for x in sl["candidates"]]]
            if sl.get("is_anchor"):
                ap = sl.get("anchor_plan")
                of = (ap or {}).get("on_fail")
                if not ap or not of:
                    problems.append("%s/%s 앵커 %s에 anchor_plan%s 없음" % (
                        co["id"], sl["slot"], sl["candidates"][0]["name"],
                        "" if not ap else ".on_fail"))
                    row.append(True)
                    plan.append(row)
                    continue
                row.append(True)
                row.append({"ceil": ap["bid_ceiling"], "nom": ap["nominal_margin"],
                            "eff": ap["effective_headroom"], "con": ap["constraint"],
                            "act": of["action"], "tgt": of["target"],
                            "dual": ap["dual_world_ok"]})
            plan.append(row)
        e = {"id": co["id"], "n": co["name"], "prem": co.get("premise") or "",
             "target": co.get("targeted_cats") or [], "punt": co.get("punted_cats") or [],
             "cap": co.get("single_player_cap"), "bigCap": co["big_budget_cap"],
             "slack": co["budget_slack"], "plan": plan}
        if co.get("conditional_on_discount"):
            e["condDiscount"] = co["conditional_on_discount"]
        out.append(e)
    return out, problems
