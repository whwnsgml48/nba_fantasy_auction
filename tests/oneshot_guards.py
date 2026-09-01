#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`tool/apply_*.py` · `tool/fix_*.py` 는 **전부 재실행 가드를 가진다** (2026-09-01 신설).

왜 검사로 만드는가
  두 번 물렸다. `fix_preseason_gates`(잠재) · `guard_tilt_search`(실제로 손으로 쓴
  판정을 날림). 둘 다 **물린 뒤에 하나씩 고쳤다** — 그게 인스턴스 수리다.
  다음에 누가 `tool/apply_무엇.py` 를 새로 만들면 같은 자리에 또 선다.
  🔴 **`validate.py` 는 이걸 못 잡는다** — 덮어쓴 문장도 문법과 불변식이 멀쩡하다.
  그래서 「가드가 있는가」를 **파일 존재 자체로** 검사한다.

무엇을 검사하나
  ① 대상 스크립트가 `oneshot.spent(...)` 를 호출한다
  ② `did` · `breaks` · `instead` 를 **셋 다** 채웠다
     — 「1회성이다」만 있으면 다음 사람이 가드를 지우고 돌린다.
       왜 막혔는지와 그래도 하려면 무엇을 하는지가 있어야 멈춘다
  ③ 가드가 **파일의 첫 부수효과보다 앞**에 있다 (쓰기 전에 멈춰야 의미가 있다)
  ④ 실제로 실행해서 **0이 아닌 코드로 멈추는지** 본다 — 주석만 있고 안 걸리는 것을 막는다

예외
  EXEMPT 에 이름과 **이유**를 적으면 통과한다. 이유 없는 예외는 검사가 거부한다.
"""
import ast
import glob
import io
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS = ("tool/apply_*.py", "tool/fix_*.py")

# 이름 → 왜 1회성 가드가 필요 없는가. **이유 없는 예외는 거부된다.**
EXEMPT = {
    # 예) "tool/fix_something.py": "멱등이고 생성기다 — 입력이 같으면 출력이 같다",
}

MIN_LEN = {"did": 15, "breaks": 25, "instead": 15}


def targets():
    out = []
    for p in PATTERNS:
        out += sorted(glob.glob(os.path.join(BASE, p)))
    return out


def guard_call(tree):
    """oneshot.spent(...) 호출 노드를 찾는다."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "spent":
                if isinstance(f.value, ast.Name) and f.value.id == "oneshot":
                    return node
    return None


def main():
    fails, checked = [], 0
    print("1회성 스크립트 재실행 가드 검사\n")
    for path in targets():
        rel = os.path.relpath(path, BASE)
        if rel in EXEMPT:
            why = EXEMPT[rel]
            if len(why.strip()) < 20:
                fails.append("%s: 예외로 등록됐지만 **이유가 부실하다** — 예외는 이유가 있어야 한다" % rel)
            else:
                print("  · %-30s 예외 — %s" % (rel, why))
            continue
        checked += 1
        src = io.open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            fails.append("%s: 파싱 실패 — %s" % (rel, e))
            continue

        call = guard_call(tree)
        if call is None:
            fails.append("%s: 🔴 **재실행 가드가 없다.** `oneshot.spent(__file__, did=..., "
                         "breaks=..., instead=...)` 를 main() 맨 앞에 넣어라 — tool/oneshot.py 참고" % rel)
            continue

        kw = {k.arg: k.value for k in call.keywords}
        for field, need in MIN_LEN.items():
            v = kw.get(field)
            txt = v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else ""
            if len(txt.strip()) < need:
                fails.append("%s: `%s=` 가 비었거나 너무 짧다(%d자 < %d). "
                             "「1회성이다」만 적으면 다음 사람이 가드를 지우고 돌린다"
                             % (rel, field, len(txt.strip()), need))

        # ③ 가드가 첫 쓰기보다 앞인가
        writes = [n.lineno for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and (
                      (isinstance(n.func, ast.Attribute) and n.func.attr in ("dump", "write"))
                      or (isinstance(n.func, ast.Name) and n.func.id == "open"))]
        # io.open(..., "w") 만 쓰기로 본다 — 읽기 open 은 무해하다
        wl = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("dump", "open"):
                if any(isinstance(a, ast.Constant) and a.value == "w" for a in n.args):
                    wl.append(n.lineno)
                elif n.func.attr == "dump":
                    wl.append(n.lineno)
        if wl and min(wl) < call.lineno:
            fails.append("%s: 가드(%d행)가 첫 쓰기(%d행)보다 **뒤**에 있다 — 쓰기 전에 멈춰야 한다"
                         % (rel, call.lineno, min(wl)))

        # ④ 실제로 멈추는가
        r = subprocess.run([sys.executable, path], cwd=BASE,
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            fails.append("%s: 가드 호출은 있는데 **실행이 성공했다**(exit 0) — 실제로 안 막힌다" % rel)
        elif "소진된 1회성" not in (r.stdout + r.stderr):
            fails.append("%s: exit %d 로 멈췄지만 가드 메시지가 아니다 — 다른 이유로 죽은 것일 수 있다"
                         % (rel, r.returncode))
        else:
            print("  ✅ %-30s 가드 있음 · 실행 차단 확인(exit %d)" % (rel, r.returncode))

    print("\n" + "-" * 66)
    if fails:
        print("🔴 %d건 실패\n" % len(fails))
        for f in fails:
            print("   " + f)
        raise SystemExit(1)
    print("검사 %d개 · 실패 0 ✅  (예외 %d개)" % (checked, len(EXEMPT)))


if __name__ == "__main__":
    main()
