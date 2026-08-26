#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/ 스냅샷 + 구조적 diff. 이 프로젝트는 git 저장소가 아니라서 이게 되돌리기 수단이다.

사용법
  python3 tool/snapshot_data.py snap <작업명>     # data/ 를 <날짜>_<작업명>/ 로 복사
  python3 tool/snapshot_data.py diff [작업명]     # 스냅샷 대비 변경 요약 (생략 시 최신 스냅샷)
  python3 tool/snapshot_data.py list              # 스냅샷 목록

저장 위치는 환경변수 SNAPSHOT_ROOT · 없으면 CLAUDE_SCRATCHPAD/data-snapshots ·
둘 다 없으면 /tmp/nba_auction_snapshots.

왜 `diff -r`을 안 쓰는가
  players.json은 174개 객체 × 수십 필드를 indent=1로 쓰기 때문에, 한 선수의 my_max가
  $1 바뀌어도 텍스트 diff는 수백 줄을 뱉는다. 배열 순서가 바뀌면 전부 변경으로 잡힌다.
  그래서 **경로 단위로 평탄화**해서 비교하고, 경로의 인덱스·선수명을 `*`로 뭉쳐
  "어떤 필드가 몇 명/몇 곳 바뀌었나"로 요약한다. players.json은 배열 인덱스가 아니라
  선수 이름으로 키를 잡아서 정렬 변경이 노이즈가 되지 않게 한다.
"""
import json, io, os, re, sys, shutil, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

def root():
    r = os.environ.get("SNAPSHOT_ROOT")
    if r: return r
    sp = os.environ.get("CLAUDE_SCRATCHPAD")
    if sp: return os.path.join(sp, "data-snapshots")
    return "/tmp/nba_auction_snapshots"

def today(): return datetime.date.today().isoformat()

def slug(s):
    s = re.sub(r"[^\w가-힣-]+", "-", s.strip()).strip("-")
    return s or "untitled"

# ── 평탄화 ───────────────────────────────────────────────────────────────
LABELS = ("id", "name", "slot", "player", "cat", "stat")

def flatten(o, path="", out=None, keyfield=None):
    """중첩 구조를 {경로: 스칼라} 로 펼친다.

    keyfield가 주어지면(players.json → name) 리스트 인덱스를 **버리고** 그 값만 쓴다.
    정렬이 바뀌어도 같은 선수가 같은 경로가 되어 재정렬이 노이즈로 잡히지 않는다.

    keyfield가 없으면 인덱스를 유지하되 라벨을 덧붙인다(`[0:c1]`). 인덱스를 버리면
    cores.json의 슬롯처럼 같은 라벨이 둘 이상일 때(BN 슬롯 2개) 경로가 충돌해
    서로 다른 값을 같은 것으로 비교하게 된다 — 조용히 틀린 diff가 나온다."""
    if out is None: out = {}
    if isinstance(o, dict):
        for k, v in o.items(): flatten(v, f"{path}.{k}" if path else k, out, keyfield)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if keyfield and isinstance(v, dict) and isinstance(v.get(keyfield), str):
                seg = v[keyfield]
            else:
                seg = str(i)
                if isinstance(v, dict):
                    for lb in LABELS:
                        if isinstance(v.get(lb), str): seg = f"{i}:{v[lb]}"; break
            flatten(v, f"{path}[{seg}]", out, keyfield)
    else:
        out[path] = o
    return out

def group(path):
    """경로에서 개체 식별자를 지워 필드 시그니처로 만든다."""
    return re.sub(r"\[[^\]]*\]", "[*]", path)

def ident(path):
    """경로의 첫 식별자 — 요약에서 '누가/어디가' 바뀌었는지 보여줄 때 쓴다."""
    m = re.search(r"\[([^\]]*)\]", path)
    return m.group(1) if m else path.split(".")[0]

def fmt(v, n=34):
    s = "없음" if v is None else (json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
    s = str(s)
    return s if len(s) <= n else s[:n-1] + "…"

# ── diff ────────────────────────────────────────────────────────────────
def diff_file(old_path, new_path, keyfield=None, label=""):
    def load(p):
        try: return json.load(io.open(p, encoding="utf-8"))
        except FileNotFoundError: return None
    a, b = load(old_path), load(new_path)
    if a is None and b is None: return 0
    if a is None:
        print(f"  + {label} 신규 파일"); return 1
    if b is None:
        print(f"  − {label} 삭제됨"); return 1

    A, B = flatten(a, keyfield=keyfield), flatten(b, keyfield=keyfield)
    added   = [p for p in B if p not in A]
    removed = [p for p in A if p not in B]
    changed = [p for p in A if p in B and A[p] != B[p]]
    if not (added or removed or changed):
        print(f"  = {label} 변경 없음")
        return 0

    # 최상위 개체 수 (players.json이면 선수 수)
    if isinstance(a, list) and isinstance(b, list):
        na, nb = {x.get(keyfield) for x in a if isinstance(x, dict)}, {x.get(keyfield) for x in b if isinstance(x, dict)}
        if len(na) != len(nb) or na != nb:
            plus, minus = sorted(nb - na), sorted(na - nb)
            print(f"  {label}: 개체 {len(na)} → {len(nb)}"
                  + (f" · 추가 {', '.join(map(str,plus))}" if plus else "")
                  + (f" · 삭제 {', '.join(map(str,minus))}" if minus else ""))

    print(f"  {label}: 변경 {len(changed)} · 신규 {len(added)} · 제거 {len(removed)}")
    buckets = {}
    for p in changed: buckets.setdefault(group(p), {"chg": [], "new": [], "del": []})["chg"].append(p)
    for p in added:   buckets.setdefault(group(p), {"chg": [], "new": [], "del": []})["new"].append(p)
    for p in removed: buckets.setdefault(group(p), {"chg": [], "new": [], "del": []})["del"].append(p)

    order = sorted(buckets.items(), key=lambda kv: -(len(kv[1]["chg"]) + len(kv[1]["new"]) + len(kv[1]["del"])))
    for sig, d in order:
        tot = len(d["chg"]) + len(d["new"]) + len(d["del"])
        tags = []
        if d["chg"]: tags.append(f"변경 {len(d['chg'])}")
        if d["new"]: tags.append(f"신규 {len(d['new'])}")
        if d["del"]: tags.append(f"제거 {len(d['del'])}")
        print(f"    {sig[:56]:<56} {tot:>4}건  ({' · '.join(tags)})")
        for p in d["chg"][:3]:
            print(f"        {ident(p)}: {fmt(A[p])} → {fmt(B[p])}")
        if len(d["chg"]) > 3: print(f"        … 그 외 {len(d['chg'])-3}건")
        for p in d["new"][:2]:
            print(f"        {ident(p)}: (없음) → {fmt(B[p])}")
        if len(d["new"]) > 2: print(f"        … 그 외 신규 {len(d['new'])-2}건")
        for p in d["del"][:2]:
            print(f"        {ident(p)}: {fmt(A[p])} → (제거)")
        if len(d["del"]) > 2: print(f"        … 그 외 제거 {len(d['del'])-2}건")
    return len(changed) + len(added) + len(removed)

KEYFIELD = {"players.json": "name"}   # 이 파일들은 이름으로 키를 잡는다

def walk_json(d):
    for dp, _, fns in os.walk(d):
        for fn in sorted(fns):
            if fn.endswith(".json"):
                yield os.path.relpath(os.path.join(dp, fn), d)

def cmd_snap(name):
    dest = os.path.join(root(), f"{today()}_{slug(name)}")
    if os.path.exists(dest):
        i = 2
        while os.path.exists(f"{dest}-{i}"): i += 1
        dest = f"{dest}-{i}"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copytree(DATA, dest)
    n = sum(len(f) for _, _, f in os.walk(dest))
    sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(dest) for f in fs)
    print(f"스냅샷 저장: {dest}\n  파일 {n}개 · {sz/1024:.0f}KB")
    return dest

def snapshots():
    r = root()
    if not os.path.isdir(r): return []
    return sorted(d for d in os.listdir(r) if os.path.isdir(os.path.join(r, d)))

def cmd_diff(name=None):
    snaps = snapshots()
    if not snaps:
        print("스냅샷이 없다. 먼저 `snap <작업명>`."); return 1
    if name:
        cand = [s for s in snaps if slug(name) in s]
        if not cand:
            print(f"'{name}' 에 맞는 스냅샷 없음. 있는 것: {', '.join(snaps)}"); return 1
        snap = cand[-1]
    else:
        snap = snaps[-1]
    old = os.path.join(root(), snap)
    print(f"=== data/ diff · 기준 스냅샷 {snap} ===")
    files = sorted(set(walk_json(old)) | set(walk_json(DATA)))
    total = 0
    for rel in files:
        total += diff_file(os.path.join(old, rel), os.path.join(DATA, rel),
                           KEYFIELD.get(os.path.basename(rel)), rel)
    # JSON 외 파일은 존재/크기만
    def others(d):
        return {r: os.path.getsize(os.path.join(d, r))
                for dp, _, fs in os.walk(d) for f in fs
                if not f.endswith(".json")
                for r in [os.path.relpath(os.path.join(dp, f), d)]}
    oa, ob = others(old), others(DATA)
    for rel in sorted(set(oa) | set(ob)):
        if rel not in oa:   print(f"  + {rel} 신규 ({ob[rel]/1024:.0f}KB)"); total += 1
        elif rel not in ob: print(f"  − {rel} 삭제"); total += 1
        elif oa[rel] != ob[rel]:
            print(f"  ~ {rel} 크기 {oa[rel]/1024:.0f} → {ob[rel]/1024:.0f}KB"); total += 1
    print(f"--- 합계 변경 {total}건 ---")
    return 0

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in ("snap", "diff", "list"):
        print(__doc__); sys.exit(2)
    if args[0] == "snap":
        if len(args) < 2: print("작업명이 필요하다: snap <작업명>"); sys.exit(2)
        cmd_snap(" ".join(args[1:]))
    elif args[0] == "diff":
        sys.exit(cmd_diff(" ".join(args[1:]) or None))
    else:
        r = root()
        print(f"스냅샷 루트: {r}")
        for s in snapshots(): print("  " + s)
