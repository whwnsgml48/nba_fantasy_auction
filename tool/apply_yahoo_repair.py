#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""야후 실자격 반영 수리 (40차) — 1순위 교체 · 슬롯 라벨 재배정 · 대체후보 재선정.

배경
  `pos_yahoo` 가 들어오면서 불변식 30개가 통과시켰던 것들이 드러났다.
  ⚠️ **「조립 불가」가 아니다.** 야후는 포지션 커버리지를 강제하지 않고, 선발 7칸 × 7일
  = 49 슬롯-일이 주간 29.7 선수-경기를 크게 웃돈다. 문제는 **그 칸이 매일 비는 것**이고,
  실측 손실은 c2 3.16% · c3 1.57% · 나머지 0.2~0.6% 다(`tool/lineup_feasibility.py`).

무엇을 고치는가
  ① 1순위 교체 3건
     c2  Ivica Zubac $11 → DeMar DeRozan $8   (PF 자격 확보 + 예비비 $5→$11)
     c3  Sam Merrill $2  → Josh Hart $4       (SF 자격 확보)
     c3  Ivica Zubac $11 → Nic Claxton $4     (Hart 로 늘어난 총액을 되돌린다)
  ② 슬롯 라벨 재배정 — 매칭은 성립하는데 **화면이 틀린 자리를 지시**하던 것
     `SF=Amen Thompson`(실제 PG/SG) 4개 코어 · `SG=DeRozan`(실제 SF/PF) 1개 코어
  ③ 대체후보 자격 수리 — 부적격 5건이 **전부 SF 칸**이었다

측정 근거 (실제 12팀 · 자격 보정 후 · 6000시행 · seed 20261020)
  c2 Okongwu→DeRozan 86.8% 예비비 $5 ↔ **Zubac→DeRozan 86.7% 예비비 $11**
     → 강도는 무승부(0.1%p). c2 의 **5번째 센터는 캣 기여가 사실상 $0** 이다
       (4개 변형이 전부 86.5~86.8 안). 그래서 선택은 예산이 정했다.
  c3 Hart 단독 88.7% / 예비비 $2 ← **I22 위반**(<$4)
     c3 Hart + Zubac→Claxton **87.6% / 예비비 $9**  ← 채택
  🔴 버리는 1.1%p 는 **이 시뮬의 SE(±0.8%p) 안이라 강도 차이로 주장할 수 없다.**
     상대 표본이 n=12 라 시행수를 10000으로 올려도 SE 가 0.77%p 아래로 안 내려간다.
     **있는지 모르는 1.1%p 와 확실히 있는 예비비 $7 의 교환**이므로 방향이 명확하다.

🔴 왜 F·F/C 를 SF 대체후보로 쓰지 않는가
  확인된 19명에서 **DB `pos` 별 SF 보유율**이 이렇게 갈렸다:
      G/F  4/5      F  0/1      F/C  0/5      C  0/6      G  0/2
  즉 야후 SF 자격은 사실상 **`G/F` 표기에서만** 나온다. 추상 `pos="F"`(Camara·McDaniels)를
  SF 자리에 넣는 것은 방금 11건을 틀리게 만든 그 낙관 편향을 그대로 반복하는 것이다.
  → SF 대체후보는 **확정 SF 이거나 `G/F`** 인 선수로만 고른다.

가격은 여기서 쓰지 않는다
  `recompute_cores.py` 가 `bid_ceiling = min(my_max, 단일상한, 철수가)` ·
  `expected_cost = clamp(시장중간)` 으로 다시 쓴다. 이 스크립트는 **이름과 라벨만** 바꾼다.
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pos_elig as PE

CP = BASE + "/data/cores.json"
PP = BASE + "/data/players.json"

# ── 1순위 교체: (코어, 나가는 선수) → (들어오는 선수, 새 라벨 or None, 새 role)
REPLACE = [
    ("c2", "Ivica Zubac", "DeMar DeRozan", "PF",
     "PF 자격 확정 — 이 코어의 유일 PF · A/T +0.152 · TOV 1.2 · FT% 86.8%"),
    ("c3", "Sam Merrill", "Josh Hart", "SF",
     "SF 자격 확정 — 이 코어의 유일 SF · 12.7P 8.4R 5.3A"),
    ("c3", "Ivica Zubac", "Nic Claxton", "BN",
     "저가 센터 — BLK · FG% · 예비비 $9 확보용(Hart 편입분 상쇄)"),
]

# ── 라벨만 재배정: (코어, 1순위 이름) → 새 라벨
RELABEL = [
    ("c2", "Onyeka Okongwu",          "UTIL"),
    ("c3", "Shai Gilgeous-Alexander", "PG"),
    ("c3", "Amen Thompson",           "SG"),
    ("c3", "Dyson Daniels",           "UTIL"),
    ("c3", "Rudy Gobert",             "BN"),
    ("c3", "Damian Lillard",          "UTIL"),
    ("c4", "Amen Thompson",           "SG"),
    ("c4", "Kon Knueppel",            "SF"),
    ("c5", "Amen Thompson",           "SG"),
    ("c5", "Kon Knueppel",            "SF"),
    ("c6", "Amen Thompson",           "SG"),
    ("c6", "DeMar DeRozan",           "SF"),
]

# ── 대체후보 재선정: (코어, 1순위 이름) → [대체 이름]
#    선정 = `tool/pick_alternates.py` (후보를 그 자리에 넣고 cat_model 로 로스터 재판정,
#    승리 캣 수 → 상대마진 합 순). SF 칸은 위 사유로 확정SF·G/F 만 후보에 넣었다.
ALTS = {
    ("c2", "DeMar DeRozan"):  ["Jaden McDaniels", "John Collins"],
    # Bane 을 잃으면 c2 에 SF 가 없다. 기존 대체 2명이 둘 다 못 쓰게 됐다 —
    # DeRozan 은 이제 이 코어의 PF 1순위(같은 사람을 두 칸에 쓸 수 없다),
    # OG Anunoby 는 `pos="F"` 라 위 0/1 사례(Randle)대로 PF 전용일 공산이 크다.
    ("c2", "Desmond Bane"):   ["Josh Hart", "Kon Knueppel"],
    ("c3", "Josh Hart"):      ["DeMar DeRozan", "Andrew Wiggins"],
    ("c3", "Amen Thompson"):  ["Kon Knueppel", "Isaiah Joe"],
    ("c3", "Rudy Gobert"):    ["Mark Williams", "Neemias Queta"],
    ("c4", "Amen Thompson"):  ["Josh Hart", "Immanuel Quickley"],
    ("c4", "Kon Knueppel"):   ["Desmond Bane", "Ausar Thompson"],
    ("c5", "Amen Thompson"):  ["VJ Edgecombe", "Nickeil Alexander-Walker"],
    ("c5", "Kon Knueppel"):   ["Josh Hart", "Desmond Bane"],
    ("c6", "Amen Thompson"):  ["Kon Knueppel", "Duncan Robinson"],
    ("c6", "DeMar DeRozan"):  ["Josh Hart", "Andrew Wiggins"],
    ("c7", "Kon Knueppel"):   ["Desmond Bane", "Andrew Wiggins"],
}

# 재배정으로 뜻이 달라지는 role 문장. 라벨만 바꾸고 문장을 두면 화면이 또 어긋난다.
ROLE = {
    ("c3", "Amen Thompson"): "SG 자격 확정(SF 아님) — 가드형 OREB 3.0 · 79G",
    ("c4", "Amen Thompson"): "SG 자격 확정(SF 아님) — 가드형 OREB 3.0 · 79G",
    ("c5", "Amen Thompson"): "SG 자격 확정(SF 아님) — 가드형 OREB 3.0 · 79G",
    ("c6", "Amen Thompson"): "SG 자격 확정(SF 아님) — 가드형 OREB 3.0 · 79G",
    ("c4", "Kon Knueppel"):  "SF 자격 확정 — 이 코어의 유일 SF · 3PT% 레버리지 2위 · 3PM 3.4",
    ("c5", "Kon Knueppel"):  "SF 자격 확정 — 이 코어의 유일 SF · 3PT% 레버리지 2위",
    ("c6", "DeMar DeRozan"): "SF 자격 확정 — A/T +0.152 · TOV 1.2 · FT% 86.8%",
    ("c3", "Rudy Gobert"):   "OREB 3.9 · BLK 1.6 · 76G",
}


def core(cj, cid):
    return next(c for c in cj["cores"] if c["id"] == cid)


def slot_of(co, name):
    for s in co["slots"]:
        if s["candidates"][0]["name"] == name:
            return s
    raise SystemExit("🔴 %s 에 1순위 %s 가 없다" % (co["id"], name))


def main():
    cj = json.load(io.open(CP, encoding="utf-8"))
    pl = {p["name"]: p for p in json.load(io.open(PP, encoding="utf-8"))}

    for cid, out, inn, label, role in REPLACE:
        co = core(cj, cid)
        s = slot_of(co, out)
        if inn not in pl:
            raise SystemExit("🔴 DB에 없는 선수 " + inn)
        s["candidates"][0] = {"name": inn}
        if label:
            s["slot"] = label
        s["role"] = role
        print("  교체 %-3s %-5s %-22s → %-22s" % (cid, s["slot"], out, inn))

    for cid, name, label in RELABEL:
        co = core(cj, cid)
        s = slot_of(co, name)
        print("  라벨 %-3s %-22s %-5s → %-5s" % (cid, name, s["slot"], label))
        s["slot"] = label

    for (cid, name), alts in ALTS.items():
        co = core(cj, cid)
        s = slot_of(co, name)
        cur = [c["name"] for c in s["candidates"][1:]]
        if cur != alts:
            print("  대체 %-3s %-5s %-22s %s → %s" % (cid, s["slot"], name,
                                                    ", ".join(cur) or "-", ", ".join(alts)))
        s["candidates"] = [s["candidates"][0]] + [{"name": a} for a in alts]

    for (cid, name), role in ROLE.items():
        slot_of(core(cj, cid), name)["role"] = role

    # ── 자기검사: 라벨 구성 · 자격 · 중복 ────────────────────────────────
    bad = 0
    for co in cj["cores"]:
        labels = sorted(s["slot"] for s in co["slots"])
        if labels != sorted(PE.ROSTER_SLOTS):
            print("  ✗ %s 슬롯 구성 %s" % (co["id"], labels)); bad += 1
        firsts = [s["candidates"][0]["name"] for s in co["slots"]]
        if len(set(firsts)) != 9:
            print("  ✗ %s 1순위 중복" % co["id"]); bad += 1
        for s in co["slots"]:
            for i, cd in enumerate(s["candidates"]):
                n = cd["name"]
                if n not in pl:
                    print("  ✗ %s %s 없는 선수 %s" % (co["id"], s["slot"], n)); bad += 1; continue
                if not PE.can(pl[n], s["slot"]):
                    print("  ✗ %s %s %s%s 자격 %s" % (co["id"], s["slot"], n,
                          "" if i == 0 else "(대체)", "/".join(sorted(PE.elig(pl[n]))))); bad += 1
                if i and n in firsts:
                    # 경고에 그친다. 이 저장소는 **슬라이드**를 의도적으로 쓴다 —
                    # c1 C 대체가 Şengün(같은 코어 PF)인 것은 "Towns 를 놓치면 Şengün 을
                    # C 로 내리고 PF 를 다시 채운다"는 뜻이다. 40차 이전부터 7건 있었고
                    # 위반으로 세면 멀쩡한 설계를 깨뜨린다.
                    print("  △ %s %s 대체 %s 는 이 코어 로스터에 있다 (슬라이드 전제)"
                          % (co["id"], s["slot"], n))
            if len(s["candidates"]) < 2 and not s.get("is_anchor"):
                print("  ✗ %s %s 비앵커인데 대체안 없음" % (co["id"], s["slot"])); bad += 1
        if PE.match([pl[n] for n in firsts]) is None:
            print("  ✗ %s 이분매칭 불성립" % co["id"]); bad += 1
    if bad:
        raise SystemExit("🔴 자기검사 %d건 실패 — 기록하지 않는다" % bad)

    json.dump(cj, io.open(CP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("자기검사 통과 · data/cores.json 기록")
    print("→ 이어서: rebuild_pivots(낡은 swap 정리) → recompute_cores → matchup_sim → validate")


if __name__ == "__main__":
    main()
