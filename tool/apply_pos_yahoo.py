#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`pos_yahoo` — 야후 **실제 포지션 자격**을 players.json 에 신설한다 (40차).

왜 필요한가 🔴
  기존 `pos` 는 `G` / `F` / `C` 3분 추상이고, 평가 경로는 이를
  `G→PG,SG` · `F→SF,PF` · `C→C` 로 펼쳐 슬롯 자격을 판정해 왔다.
  사용자가 야후에서 19명의 실자격을 확인해 대조한 결과 **11명이 불일치했고,
  11건 전부 「자격을 잃는」 방향**이다. 추상화의 계통 편향이다.

      Amen Thompson   G/F → PG,SG   (SF·PF 상실)   Okongwu  F/C → C     (SF·PF 상실)
      Şengün·Towns·Mobley·Sabonis  F/C → PF,C      (전부 SF 상실)
      Randle F → PF · Bane/Knueppel G/F → SG,SF · DeRozan G/F → SF,PF · Hart G/F → SF,SG

  그 결과 불변식 30개가 **SF 충원 0명인 c3**, **PF 충원 0명인 c2** 를 통과시켰다.

기존 필드를 왜 안 고치는가
  `pos` · `team` · `name` 은 **건드리지 않는다.** `nba_score` 세션이 같은 파일을
  읽고 있고, 그 필드가 바뀌면 그쪽 계수가 낡는다. 새 필드를 얹고 소비자가
  「있으면 그것, 없으면 pos」로 고르게 한다(validate.py `elig()`).

미확인 선수
  `pos_yahoo: null`. 남은 추정 10명(Jokić·SGA·White·Trae·Lillard·Daniels·
  Vučević·Quickley·Gillespie·McDaniels)은 전부 G 계열 또는 C 전용이라
  SF 병목에 영향이 없다 — 확인 우선순위가 낮다는 뜻이지 확인됐다는 뜻이 아니다.
"""
import json, io, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PP = BASE + "/data/players.json"

SOURCE = "사용자 야후 화면 확인 2026-08-27"

# 확정 19명. ⚠️ 순서·표기를 손으로 고치지 말 것 — 화면에서 옮겨적은 원본이다.
YAHOO = {
    "Amen Thompson":      ["PG", "SG"],
    "Tyrese Haliburton":  ["PG", "SG"],
    "VJ Edgecombe":       ["PG", "SG"],
    "Desmond Bane":       ["SG", "SF"],
    "Kon Knueppel":       ["SG", "SF"],
    "Josh Hart":          ["SF", "SG"],
    "DeMar DeRozan":      ["SF", "PF"],
    "Julius Randle":      ["PF"],
    "Alperen Şengün":     ["PF", "C"],
    "Karl-Anthony Towns": ["PF", "C"],
    "Evan Mobley":        ["PF", "C"],
    "Domantas Sabonis":   ["PF", "C"],
    "Onyeka Okongwu":     ["C"],
    "Moussa Diabaté":     ["C"],
    "Donovan Clingan":    ["C"],
    "Rudy Gobert":        ["C"],
    "Jalen Duren":        ["C"],
    "Deandre Ayton":      ["C"],
    "Ivica Zubac":        ["C"],
}

EXPAND = {"G": ["PG", "SG"], "F": ["SF", "PF"], "C": ["C"]}


def expand(pos):
    out = []
    for t in (pos or "").split("/"):
        out += EXPAND.get(t, [])
    return out


def main():
    pl = json.load(io.open(PP, encoding="utf-8"))
    names = {p["name"] for p in pl}
    missing = [n for n in YAHOO if n not in names]
    if missing:
        raise SystemExit("🔴 DB에 없는 이름: " + ", ".join(missing))

    diff = 0
    out = []
    for p in pl:
        y = YAHOO.get(p["name"])
        new = collections.OrderedDict()
        for k, v in p.items():
            new[k] = v
            if k == "pos":                      # pos 바로 뒤에 끼운다 (사람이 읽는 순서)
                new["pos_yahoo"] = y
                if y:
                    new["pos_yahoo_source"] = SOURCE
        if "pos_yahoo" not in new:              # pos 가 없는 엔트리 방어
            new["pos_yahoo"] = y
        if y and set(y) != set(expand(p.get("pos"))):
            diff += 1
            print("  %-24s %-6s → %-10s  잃음: %s" % (
                p["name"], p.get("pos"), ",".join(y),
                ",".join(sorted(set(expand(p.get("pos"))) - set(y))) or "-"))
        out.append(new)

    json.dump(out, io.open(PP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("pos_yahoo 기록: 확정 %d명 / 전체 %d명 · 기존 pos 와 불일치 **%d명**"
          % (len(YAHOO), len(out), diff))


if __name__ == "__main__":
    main()
