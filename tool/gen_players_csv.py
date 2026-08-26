#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/players.csv 를 players.json + measured_full + cat_model 에서 **전량 생성**한다.

왜 만드는가 (38차)
  `README`는 `players.csv`를 *"같은 데이터 표 형식"* 이라고 적어놨지만 **생성기가 없었고
  손으로 유지되는 미러**였습니다. 이 저장소가 반복해서 당한 「같은 값을 두 곳에 두면
  반드시 갈라진다」 형태 그대로이고, 실제로 갈라져 있었습니다.

  발견 당시 Jokić 한 행에서만:
    cats       CSV `FT%3 … STL3`      ↔ JSON `FT%1 … STL3 BLK1 3P%2 3PM1`  (13차 재산정 미반영)
    PTS        CSV 27.7               ↔ 혼합 실측 28.494                    (20차 2시즌 혼합 미반영)
    season     CSV `2025-26`          ↔ `blend`
    pts_lift   CSV 9.02               ↔ cat_model 11.365
    tov_lift   CSV -2.033             ↔ -1.529
    at_lift    CSV 0.241              ↔ 0.253
  38차의 DeRozan 소속 정정도 두 파일을 **각각** 고쳐야 했습니다.

열별 출처 (단일 소스)
  name team pos market_low market_high my_max surplus obtainable
  injury_exclude tag cats measured_2025_26 flag      ← data/players.json
  GP season gp_qualified                             ← players.json.measured_source
  MPG PTS REB OREB AST STL BLK TOV FG% FGA
  3PM 3PA 3P% FT% FTA A/T DD                         ← measured_full.json
  pts_lift tov_lift at_lift dd_lift                  ← cat_model.player_lift (경기당 한계기여)

⚠️ 열 순서는 종전 35열을 **그대로 보존**하고 `DD`·`dd_lift` 2열만 뒤에 붙였습니다.
   DD는 13캣 중 하나이고 커버리지 100%인데 표에서 빠져 있었습니다(전량 추정이라
   `docs/05` 2b-2의 한계가 함께 적용됩니다).

실행: python3 tool/gen_players_csv.py        → data/players.csv 재작성
검사: validate.py 의 I25 가 디스크 파일과 이 생성 결과를 대조합니다.
"""
import csv, io, json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE + "/tool")
import cat_model as CM   # noqa: E402

CSV_PATH = BASE + "/data/players.csv"

# 종전 35열 + DD·dd_lift
COLS = ["name", "team", "pos", "market_low", "market_high", "my_max", "surplus",
        "obtainable", "injury_exclude", "tag", "cats",
        "GP", "MPG", "season", "gp_qualified",
        "PTS", "pts_lift", "REB", "OREB", "AST", "STL", "BLK", "TOV", "tov_lift",
        "FG%", "FGA", "3PM", "3PA", "3P%", "FT%", "FTA", "A/T", "at_lift",
        "measured_2025_26", "flag",
        "DD", "dd_lift"]

# 소수 자리 — 종전 CSV의 표기 관례를 따른다(원값을 그대로 흘리면 17자리가 나온다)
ROUND = {"MPG": 1, "PTS": 1, "REB": 1, "OREB": 1, "AST": 1, "STL": 1, "BLK": 1,
         "TOV": 1, "FGA": 1, "3PM": 1, "3PA": 1, "FTA": 1, "DD": 3,
         "FG%": 3, "3P%": 3, "FT%": 3, "A/T": 2}
LIFT = {"pts_lift": "PTS", "tov_lift": "TOV", "at_lift": "A/T", "dd_lift": "DD"}


def _fmt(v, col):
    if v is None:
        return ""
    if col in ROUND and isinstance(v, (int, float)):
        r = round(v, ROUND[col])
        return ("%g" % r)
    if isinstance(v, bool):
        return "True" if v else "False"
    return str(v)


def build():
    """CSV 전문을 문자열로 돌려준다. 파일을 쓰지 않는다 (validate.py가 이걸 대조한다)."""
    PL = json.load(io.open(BASE + "/data/players.json", encoding="utf-8"))
    F = json.load(io.open(BASE + "/data/stats_2025_26/measured_full.json",
                          encoding="utf-8"))["players"]
    Bpg = CM.baselines_per_game()

    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(COLS)
    for p in PL:
        n = p["name"]
        m = F.get(n) or {}
        ms = p.get("measured_source") or {}
        row = []
        for c in COLS:
            if c in LIFT:
                row.append(_fmt(CM.player_lift(n, LIFT[c], Bpg), c))
            elif c in ("GP", "season", "gp_qualified"):
                row.append(_fmt(ms.get(c, m.get(c)), c))
            elif c in ("MPG", "PTS", "REB", "OREB", "AST", "STL", "BLK", "TOV",
                       "FG%", "FGA", "3PM", "3PA", "3P%", "FT%", "FTA", "A/T", "DD"):
                row.append(_fmt(m.get(c), c))
            else:
                row.append(_fmt(p.get(c), c))
        w.writerow(row)
    return out.getvalue()


if __name__ == "__main__":
    new = build()
    old = io.open(CSV_PATH, encoding="utf-8").read() if os.path.exists(CSV_PATH) else ""
    io.open(CSV_PATH, "w", encoding="utf-8").write(new)
    if old == new:
        print("players.csv 변경 없음 (%d행)" % (new.count("\n") - 1))
    else:
        ol, nl = old.split("\n"), new.split("\n")
        diff = sum(1 for a, b in zip(ol, nl) if a != b) + abs(len(ol) - len(nl))
        print("players.csv 재생성: %d행 · %d열 · 이전과 다른 줄 %d개"
              % (len(nl) - 2, len(COLS), diff))
