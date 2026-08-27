#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════
#  옛 지표 리터럴 색출 — 지표를 재계산한 뒤 **옛 값이 문서에 남았는지** 훑는다
#
#  왜 있는가 (40차 · 2026-08-27):
#    포지션 자격 보정으로 코어 승률이 전부 바뀌었다. 「보정 전 숫자」를 눈으로
#    훑었더니 **README 강도표 7행을 통째로 놓쳤다** — 승률 각주만 범주로 세고
#    표를 안 셌기 때문이다. 사용자가 드래프트 당일 가장 먼저 여는 문서에
#    틀린 1위가 표로 박혀 있었다.
#
#    범주로 훑으면 범주 밖이 남는다. 값을 직접 훑으면 누락이 안 생긴다.
#
#  🔴 이 스크립트는 **판정기가 아니라 목록 제공기**다.
#     오탐이 난다(다른 맥락의 84.2, 감도표의 옛 값 등). 사람이 걸러야 한다.
#     validate.py 는 이 파일을 부르지 않는다 — 게이트가 아니다.
#
#  실행:  python3 tests/stale_figures.py <옛-git-ref>
#         예) python3 tests/stale_figures.py 55c47a8
# ═══════════════════════════════════════════════════════════════════════════
import json, re, subprocess, sys, pathlib

TARGETS = ["README.md", "HANDOFF.md"] + sorted(str(p) for p in pathlib.Path("docs").glob("*.md")) \
          + ["tool/auction-console.html"]

def literals_at(ref):
    """<ref> 시점 툴의 DECISION 에서 코어 평균·최저를 소수점 1자리 문자열로."""
    src = subprocess.run(["git", "show", f"{ref}:tool/auction-console.html"],
                         capture_output=True, text=True, check=True).stdout
    m = re.search(r"const DECISION=(\[.*?\]);\n", src, re.S)
    if not m:
        sys.exit(f"✗ {ref} 에서 const DECISION 을 못 찾았다")
    rows = json.loads(m.group(1))
    out = {}
    for r in rows:
        s = r.get("str")
        if not s: continue
        out.setdefault("%.1f" % (s["mean"] * 100), []).append(r["core"] + " 평균")
        if s.get("min") is not None:
            out.setdefault("%.1f" % (s["min"] * 100), []).append(r["core"] + " 최저")
    means = [r["str"]["mean"] for r in rows if r.get("str")]
    if means:
        out.setdefault("%.1f%%p" % ((max(means) - min(means)) * 100), []).append("최고-최저 파생")
    return out

def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__ or "사용법: python3 tests/stale_figures.py <옛-git-ref>")
    ref = sys.argv[1]
    lits = literals_at(ref)
    print(f"기준 ref: {ref} · 리터럴 {len(lits)}개")
    for v, who in sorted(lits.items(), key=lambda x: -float(x[0].rstrip("%p"))):
        print(f"   {v:>7}  {' · '.join(who)}")
    print("-" * 66)

    total = 0
    for path in TARGETS:
        p = pathlib.Path(path)
        if not p.exists(): continue
        hits = []
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            # 툴의 생성 데이터 행(const DECISION 등)은 sync_tool 이 덮어쓰므로 제외
            if path.endswith(".html") and re.match(r"const (DECISION|CORES|PIVOTS|P)=", line):
                continue
            for v in lits:
                if v in line:
                    hits.append((i, v, line.strip()[:96]))
                    break
        if hits:
            print(f"\n▸ {path}  ({len(hits)}건)")
            for i, v, txt in hits:
                print(f"   {i:>5}  [{v}]  {txt}")
            total += len(hits)

    print("\n" + "-" * 66)
    if total:
        print(f"△ 옛 값 리터럴 {total}건 — **사람이 하나씩 확인해서 0건으로 만들 것.**")
        print("   오탐(다른 맥락의 같은 숫자 · 옛 값을 의도적으로 인용한 감사 기록)은 넘어간다.")
    else:
        print("✅ 옛 값 리터럴 0건")

if __name__ == "__main__":
    main()
