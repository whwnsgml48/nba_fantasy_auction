#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Basketball Reference 리그 전체 per-game 스탯 수집.

기존 리더보드(캣별 top-25, 9종)는 174명 중 일부만 커버해서 대부분의 선수가
'검증 불가'로 남았다. 이 스크립트는 리그 전체 테이블(700+행)을 가져와 그 한계를 없앤다.

- 2025-26(NBA_2026) 우선. 결장으로 없는 선수는 2024-25(NBA_2025)로 폴백.
- 13캣 중 12캣 커버 (DD는 BBRef가 집계하지 않음 — 야후 판타지 전용 캣).
- 비율 캣 시도량(FGA·FTA·3PA)도 함께 받아 볼륨 레버리지 계산이 가능해진다.

실행: <venv>/bin/python tool/fetch_bbref.py
  (requests·bs4 필요. 이 프로젝트엔 venv가 없어 ../nba_2026/.venv 를 재사용해도 된다)
"""
import json, os, re, sys, time, csv
import requests
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(BASE, "data/stats_2025_26/bbref")
UA   = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
SEASONS = [("2025-26", 2026), ("2024-25", 2025)]
DELAY = 4.0   # BBRef 예의상 간격

# data-stat -> 우리 필드
COLS = {
 "name_display":"name","team_name_abbr":"team","pos":"pos","age":"age",
 "games":"GP","games_started":"GS","mp_per_g":"MPG",
 "fg_per_g":"FGM","fga_per_g":"FGA","fg_pct":"FG%",
 "fg3_per_g":"3PM","fg3a_per_g":"3PA","fg3_pct":"3P%",
 "ft_per_g":"FTM","fta_per_g":"FTA","ft_pct":"FT%",
 "orb_per_g":"OREB","drb_per_g":"DREB","trb_per_g":"REB",
 "ast_per_g":"AST","stl_per_g":"STL","blk_per_g":"BLK","tov_per_g":"TOV",
 "pts_per_g":"PTS",
}
NUM = set(COLS.values()) - {"name","team","pos"}

def fetch(season_year, sess):
    url = f"https://www.basketball-reference.com/leagues/NBA_{season_year}_per_game.html"
    r = sess.get(url, timeout=60); r.raise_for_status()
    raw = os.path.join(OUT, f"NBA_{season_year}_per_game.html")
    with open(raw, "wb") as f: f.write(r.content)
    soup = BeautifulSoup(r.content, "html.parser")
    t = soup.find("table", {"id": "per_game_stats"})
    if not t: raise RuntimeError(f"per_game_stats 테이블 없음: {url}")
    hdr = [th.get("data-stat") for th in t.find("thead").find_all("tr")[-1].find_all("th")]
    rows=[]
    for tr in t.find("tbody").find_all("tr"):
        if "thead" in (tr.get("class") or []): continue
        cells = tr.find_all(["th","td"])
        d={}
        for c in cells:
            ds=c.get("data-stat")
            if ds in COLS: d[COLS[ds]]=c.text.strip()
        if not d.get("name"): continue
        for k in NUM:
            v=d.get(k,"")
            d[k]=None if v=="" else (float(v) if "." in v or "%" in k else int(v))
        rows.append(d)
    return rows, len(t.find("tbody").find_all("tr"))

def dedupe(rows):
    """다팀 이적 선수는 합산 행(2TM/3TM/4TM)을 우선한다."""
    by={}
    for r in rows:
        n=r["name"]
        agg = bool(re.fullmatch(r"\dTM", r.get("team") or ""))
        cur=by.get(n)
        if cur is None: by[n]=r; continue
        cur_agg = bool(re.fullmatch(r"\dTM", cur.get("team") or ""))
        if agg and not cur_agg: by[n]=r
        elif agg==cur_agg and (r.get("GP") or 0) > (cur.get("GP") or 0): by[n]=r
    return by

def main():
    os.makedirs(OUT, exist_ok=True)
    sess=requests.Session(); sess.headers.update({"User-Agent":UA})
    out={}
    meta={"source":"basketball-reference.com /leagues/NBA_{year}_per_game.html",
          "fetched_at":None,"seasons":[],"note":
          "DD(더블더블)는 BBRef가 집계하지 않음 — 야후 판타지 전용 캣이라 별도 소스 필요."}
    for label, yr in SEASONS:
        print(f"[{label}] NBA_{yr}_per_game 요청...", flush=True)
        rows, nraw = fetch(yr, sess)
        by = dedupe(rows)
        print(f"   원본 {nraw}행 → 선수 {len(by)}명 (다팀 합산 정리)")
        meta["seasons"].append({"season":label,"year":yr,"raw_rows":nraw,"players":len(by)})
        out[label]=by
        with open(os.path.join(OUT, f"{label}_per_game.csv"), "w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["name","team","pos","age","GP","GS","MPG",
                "PTS","REB","OREB","DREB","AST","STL","BLK","TOV",
                "FGM","FGA","FG%","3PM","3PA","3P%","FTM","FTA","FT%"])
            w.writeheader()
            for n in sorted(by): w.writerow({k:by[n].get(k) for k in w.fieldnames})
        if (label,yr)!=SEASONS[-1]: time.sleep(DELAY)
    json.dump({"meta":meta,
               "2025-26":out["2025-26"], "2024-25":out["2024-25"]},
              open(os.path.join(OUT,"per_game.json"),"w",encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n저장: {OUT}/per_game.json · 시즌별 CSV 2종 · 원본 HTML 2종")

if __name__=="__main__":
    main()
