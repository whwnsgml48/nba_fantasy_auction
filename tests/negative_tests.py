#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate.py 음성 테스트 — 불변식마다 위반을 주입해 **실제로 잡히는지** 확인한다.

왜 필요한가 (38차)
  이 프로젝트의 대표 실패 형태는 「빠뜨려도 조용히 통과한다」이고 HANDOFF에 6건이
  기록돼 있다. 그중 둘은 **검사 자체가 무력화된** 사고였다:
    · I23이 `e["name"]`만 읽어 **슬롯 dict엔 name이 없어서** 슬롯 레벨 검사가 통째로
      통과했다 — 주입한 별칭 불일치·my_max 초과가 하나도 안 걸렸다 (35차)
    · `has_any_basis(hits_fn=None)`이 auto basis 27건을 **영구 유효**로 만들었다 (30차)
  둘 다 "위반을 일부러 주입해 잡히는지 본다"로 즉시 드러난다. 프로젝트 규칙에도
  「새 검사를 넣으면 반드시 음성 테스트를 돌릴 것」이 있는데 **테스트 파일이 없었다.**

설계 4원칙
  1. `data/`·`tool/`·`validate.py` 사본으로 **샌드박스**를 만든다. 원본은 건드리지 않는다.
     (`cat_model`·`divergence_rules`는 자기 `__file__` 기준으로 경로를 잡으므로 사본이 자립한다)
  2. 먼저 **무결 샌드박스가 exit 0**인지 확인한다. 이게 깨지면 이후 결과는 전부 무의미하다.
  3. 각 테스트는 위반 1건을 주입하고 **exit 1 + 의도한 마커 문자열**을 함께 요구한다.
     ⚠️ **exit code만 보면 안 된다** — 다른 검사가 대신 잡아도 통과해버리고, 그게 바로
     이 하네스가 막으려는 실패다. 마커는 그 검사만 내는 문장이어야 한다.
     ⚠️ **중단(Traceback)은 검출이 아니다.** 검증기가 예외로 죽어도 exit 1이므로
     exit code만 보면 "잡았다"로 읽힌다. 실제로는 그 지점 이후의 검사가 **한 건도
     실행되지 않는다** — 조용한 통과가 아니라 조용한 **절단**이다. 하네스는 이걸
     별도 상태(⚠)로 분리하고 요약에 모아 보고한다.
     ⚠️ 마커는 **`✗` 위반 줄에서만** 찾는다. `[I22]`·`[I23]`·`[I24]`는 위반이 0건일 때도
     요약 줄에 찍히므로, 전체 출력에서 찾으면 **위반을 주입하지 않아도 통과한다.**
     작성 당시 I22 테스트가 실제로 그 상태였다 — 이 하네스를 하네스로 검사해서 잡았다.
     그래서 0.5단계에서 **모든 마커가 무결 출력과 구별되는지** 먼저 확인한다.
  4. 불변식은 서로 얽혀 있어 한 주입이 여러 검사를 동시에 깨우는 것은 **정상**이다.
     테스트가 묻는 것은 "의도한 검사가 발화했는가" 하나뿐이다(동시 발화 수는 -v로 표시).

실행
  python3 tests/negative_tests.py          # 전체
  python3 tests/negative_tests.py -v       # 발화한 위반 줄까지 출력
  python3 tests/negative_tests.py I23      # id에 문자열이 포함된 것만
위반이 잡히지 않은 테스트가 있으면 exit 1.
"""
import io, json, os, shutil, subprocess, sys, tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# validate.py 가 읽는 파일 전체. 하나라도 빠지면 무결 샌드박스가 깨지므로
# 여기가 곧 "검증기의 입력 목록" 문서 역할을 한다.
NEEDED = [
    "validate.py",
    "data/players.json",
    "data/cores.json",
    "data/divergence_state.json",
    "data/matchup_sim.json",
    "data/prior_auction_2025_26/proposed_market_refit.json",
    "data/stats_2025_26/measured_full.json",
    "tool/auction-console.html",
    "tool/cat_model.py",
    "tool/divergence_rules.py",
]

TESTS = []


def test(iid, desc, expect):
    """expect: 문자열 하나 또는 튜플(전부 포함돼야 함)."""
    def deco(fn):
        TESTS.append((iid, desc, fn, (expect,) if isinstance(expect, str) else expect))
        return fn
    return deco


class Box:
    """샌드박스 하나. 로드 → 변형 → 저장 → validate 실행."""

    def __init__(self, root):
        self.root = root
        self.players = json.load(io.open(root + "/data/players.json", encoding="utf-8"))
        self.pl = {p["name"]: p for p in self.players}
        self.cj = json.load(io.open(root + "/data/cores.json", encoding="utf-8"))

    # ── 조회 ────────────────────────────────────────────────────────
    def core(self, cid):
        return next(c for c in self.cj["cores"] if c["id"] == cid)

    def slot(self, cid, slot_name):
        return next(s for s in self.core(cid)["slots"] if s["slot"] == slot_name)

    def first(self, cid, slot_name):
        return self.slot(cid, slot_name)["candidates"][0]["name"]

    # ── 변형 헬퍼 ───────────────────────────────────────────────────
    def set_price_on(self, s, price, ceil=None):
        """슬롯 dict를 직접 받는다. `UTIL`·`BN`은 코어마다 2개씩 있어
        이름으로 찾으면 의도한 슬롯이 아닌 첫 번째가 잡힌다."""
        for d in (s, s["candidates"][0]):
            d["plan_price"] = price
            d["expected_cost"] = price
            if ceil is not None:
                d["bid_ceiling"] = ceil
            elif d.get("bid_ceiling", 0) < price:
                d["bid_ceiling"] = price

    def set_price(self, cid, slot_name, price, ceil=None):
        """가격 4중 보관(슬롯 plan/expected/bid + candidates[0])을 **함께** 갱신한다.
        하나만 고치면 I14·I23이 먼저 발화해 의도한 검사를 가린다."""
        s = self.slot(cid, slot_name)
        c0 = s["candidates"][0]
        for d in (s, c0):
            d["plan_price"] = price
            d["expected_cost"] = price
            if ceil is not None:
                d["bid_ceiling"] = ceil
            elif d.get("bid_ceiling", 0) < price:
                d["bid_ceiling"] = price

    def resync_totals(self, cid):
        """파생 합계를 실계산으로 맞춰 I14가 끼어들지 않게 한다."""
        co = self.core(cid)
        tot = sum(s["plan_price"] for s in co["slots"])
        co["planned_total"] = tot
        co["budget_slack"] = 200 - tot

    def html(self, fn):
        p = self.root + "/tool/auction-console.html"
        s = io.open(p, encoding="utf-8").read()
        io.open(p, "w", encoding="utf-8").write(fn(s))

    # ── 저장 · 실행 ─────────────────────────────────────────────────
    def save(self):
        json.dump(self.players, io.open(self.root + "/data/players.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        json.dump(self.cj, io.open(self.root + "/data/cores.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    def run(self):
        self.save()
        r = subprocess.run([sys.executable, self.root + "/validate.py"],
                           capture_output=True, text=True, cwd=self.root)
        return r.returncode, r.stdout + r.stderr


# ══════════════════════════════════════════════════════════════════════
# 테스트 — 불변식 번호는 HANDOFF 「반드시 지켜야 하는 불변식」과 같다
# ══════════════════════════════════════════════════════════════════════

@test("I1", "계획가가 my_max를 넘는다 (my_max를 내려 주입)", ("계획가 $", "> my_max $"))
def _(b):
    n = b.first("c1", "PF")
    b.pl[n]["my_max"] = b.slot("c1", "PF")["plan_price"] - 1

@test("I2", "9슬롯이 아니다 (슬롯 1개 삭제)", "슬롯 8개")
def _(b):
    b.core("c1")["slots"].pop()

@test("I3", "포지션 자격 불가 (C 슬롯 선수의 pos에서 C 제거)", "자격→C")
def _(b):
    b.pl[b.first("c1", "C")]["pos"] = "PF"

@test("I4", "총액이 $200을 넘는다", ("총액 $", "> $200"))
def _(b):
    n = b.first("c6", "BN")
    b.pl[n]["my_max"] = 90; b.pl[n]["market_high"] = 90
    b.set_price("c6", "BN", 60, ceil=90); b.resync_totals("c6")

@test("I5", "빅맨 예산이 상한을 넘는다 (상한을 내려 주입)", ("빅맨예산 $", "> 상한 $"))
def _(b):
    b.core("c6")["big_budget_cap"] = 30

@test("I6", "비앵커 슬롯에 대체 후보가 없다", "비앵커 슬롯 대체안 없음")
def _(b):
    for c in b.cj["cores"]:
        for s in c["slots"]:
            if not s.get("is_anchor") and len(s["candidates"]) > 1:
                s["candidates"] = s["candidates"][:1]; return
    raise AssertionError("비앵커 슬롯 없음")

@test("I7", "장기 부상 제외 선수가 로스터에 있다", "🚑 장기부상 포함")
def _(b):
    b.pl[b.first("c6", "PF")]["injury_exclude"] = True

# 마커는 검증기 **메시지 문구에 결합**돼 있다. 37차에 "미명시"→"필드 없음"으로
# 바뀌어 이 테스트가 빨개졌고, 그래서 안정적인 접두부만 남겼다.
@test("I8", "피벗에 노리는 캣/포기 캣이 명시되지 않았다", "피벗에 노리는 캣/포기 캣")
def _(b):
    for c in b.cj["cores"]:
        pv = c.get("pivot_plan")
        if pv and pv.get("targeted_cats"):
            pv.pop("targeted_cats"); return
    raise AssertionError("피벗 없음")

@test("M2", "팀 한계기여 <=0인 캣에 가중치를 부여했다", "[M2]")
def _(b):
    for p_ in b.players:
        cw = p_.get("cat_weights") or {}
        ms = p_.get("measured_source") or {}
        if ms.get("weights_data_verified") and (ms.get("GP") or 0) >= 40 and "BLK" not in cw:
            cw["BLK"] = 3
            p_["cats"] = (p_.get("cats") or "") + " BLK3"
            return
    raise AssertionError("대상 선수 없음")

@test("M1", "가중치가 실측의 단조함수가 아니다", "[M1]")
def _(b):
    # 같은 캣에서 실측이 더 낮은 선수에게 더 높은 등급을 준다.
    # M2와 주입 방식이 겹치지만, M1만 퇴행했을 때를 잡기 위해 따로 둔다.
    for p_ in b.players:
        cw = p_.get("cat_weights") or {}
        ms = p_.get("measured_source") or {}
        if ms.get("weights_data_verified") and (ms.get("GP") or 0) >= 40 and cw.get("BLK") in (None, 1):
            cw["BLK"] = 3
            p_["cats"] = (p_.get("cats") or "") + " BLK3"
            return
    raise AssertionError("대상 선수 없음")

@test("I9", "피벗 트리거가 임계값 단일 소스와 어긋난다", "트리거 규칙 불일치")
def _(b):
    for c in b.cj["cores"]:
        tg = (c.get("pivot_plan") or {}).get("triggers")
        if tg:
            tg[0]["rule"] = "> $999"; return
    raise AssertionError("트리거가 있는 코어 없음")

@test("I10a", "판단표에서 코어 하나가 빠졌다", "판단표에 누락된 코어")
def _(b):
    b.cj["decision_table"] = [d for d in b.cj["decision_table"] if d["core"] != "c5"]

@test("I10b", "우선순위 0이 코어 7이 아니다", "우선순위 0이 코어 7이 아님")
def _(b):
    b.cj["decision_table"][0]["core"] = "c6"

@test("I10c", "판단표 임계값이 my_max를 넘는다", "판단표 임계 $")
def _(b):
    for d in b.cj["decision_table"]:
        for r in (d.get("cond") or {}).get("rules") or []:
            if r.get("player") in b.pl:
                r["max"] = b.pl[r["player"]]["my_max"] + 20; return
    raise AssertionError("가격 조건 행 없음")

@test("I11a", "hot_bigs 선수 목록이 계층과 어긋난다", "hot_bigs 선수 목록이")
def _(b):
    for d in b.cj["decision_table"]:
        c = d.get("cond") or {}
        if c.get("type") == "hot_bigs":
            c["players"] = c["players"][:-1]; return
    raise AssertionError("hot_bigs 행 없음")

@test("I11b", "hot_bigs signal이 overheat_at이 아니다", "hot_bigs signal이")
def _(b):
    for d in b.cj["decision_table"]:
        c = d.get("cond") or {}
        if c.get("type") == "hot_bigs":
            c["signal"] = "threshold"; return
    raise AssertionError("hot_bigs 행 없음")

@test("I11c", "anchor 계층에 overheat_at이 채워졌다", "anchor 계층은 overheat_at이 null")
def _(b):
    for t in b.cj["overheat_thresholds"]:
        if t.get("tier") == "anchor":
            t["overheat_at"] = 30; t["overheat_rule"] = "> $30"; return
    raise AssertionError("anchor 계층 없음")

@test("I11d", "철수가가 최대 계획가보다 낮다 (플랜이 자기 피벗을 트리거)", "플랜이 자기 피벗을 트리거")
def _(b):
    planned = {s["candidates"][0]["name"] for c in b.cj["cores"] for s in c["slots"]}
    for t in b.cj["overheat_thresholds"]:
        if t["player"] in planned:
            t["threshold"] = 1; t["rule"] = "> $1"; t["walk_away"] = 1
            return
    raise AssertionError("플랜에 있는 임계값 선수 없음")

@test("I12a", "툴 DECISION_ONELINER가 cores.json과 어긋난다", "툴 DECISION_ONELINER 불일치")
def _(b):
    b.html(lambda s: s.replace("정상 시장: 코어 6 기본", "정상 시장: 코어 9 기본", 1))

@test("I12b", "툴 hotCenterCount가 overheated()를 쓰지 않는다", "hotCenterCount가 overheated()")
def _(b):
    import re
    b.html(lambda s: re.sub(r"function hotCenterCount\(\)\{.*?\n\}",
                            "function hotCenterCount(){\n  return hotBigs().length;\n}", s, count=1, flags=re.S))

@test("I13", "앵커 슬롯에 anchor_plan이 없다", "에 anchor_plan 없음")
def _(b):
    for c in b.cj["cores"]:
        for s in c["slots"]:
            if s.get("is_anchor") and "anchor_plan" in s:
                del s["anchor_plan"]; return
    raise AssertionError("앵커 없음")

@test("I14a", "슬롯 plan_price와 candidates[0]이 갈라졌다", ("슬롯 plan_price $", "≠ candidates[0]"))
def _(b):
    b.slot("c6", "SG")["candidates"][0]["plan_price"] += 3

@test("I14b", "planned_total이 실계산과 다르다", ("planned_total", "≠ 실계산"))
def _(b):
    b.core("c6")["planned_total"] += 7

@test("I14c", "budget_slack이 실계산과 다르다", ("budget_slack", "≠ 실계산"))
def _(b):
    b.core("c6")["budget_slack"] += 5

@test("I14d", "c_eligible_count가 실계산과 다르다", ("c_eligible_count", "≠ 실계산"))
def _(b):
    b.core("c6")["c_eligible_count"] += 1

@test("I18a", "cat_team_marginals 기록값이 실계산과 다르다", ("cat_team_marginals", "≠ 실계산"))
def _(b):
    m = b.core("c6")["cat_team_marginals"]
    k = next(iter(m)); m[k] = (m[k] or 0) + 99

@test("I18b", "포기 선언한 캣이 실제로는 확보돼 있다", "를 포기로 선언했으나 팀 한계기여")
def _(b):
    co = b.core("c6")
    cat = co["targeted_cats"][0]
    co["targeted_cats"] = [c for c in co["targeted_cats"] if c != cat]
    co["punted_cats"] = sorted(co["punted_cats"] + [cat])

@test("I19a", "cat_baselines에서 캣 하나가 빠졌다", "[I19] cat_baselines 누락 캣")
def _(b):
    cb = b.cj["opponent_baseline"]["cat_baselines"]; cb.pop(next(iter(cb)))

@test("I19b", "cat_baselines 값이 cat_model 계산과 척도가 어긋난다", ("[I19]", "척도 불일치"))
def _(b):
    cb = b.cj["opponent_baseline"]["cat_baselines"]
    e = cb["REB"]; e["baseline"] = e["baseline"] * 10 + 1

@test("I19c", "TOV의 lower_is_better 플래그가 사라졌다", "TOV에 lower_is_better 플래그 없음")
def _(b):
    b.cj["opponent_baseline"]["cat_baselines"]["TOV"].pop("lower_is_better", None)

@test("I20", "툴 P 배열의 my_max가 players.json과 어긋난다", "[I20] 툴 mx 불일치")
def _(b):
    b.pl["Rudy Gobert"]["my_max"] += 7

@test("I22", "예비비가 $4 미만이다", ("[I22]", "예비비 $", "< $"))
def _(b):
    co = b.core("c6")
    s = next(x for x in co["slots"] if not x.get("is_anchor"))
    n = s["candidates"][0]["name"]
    need = s["plan_price"] + (199 - co["planned_total"])   # 총액 $199 → 예비비 $1 (< $4)
    b.pl[n]["my_max"] = need + 10; b.pl[n]["market_high"] = need + 10
    b.set_price_on(s, need, ceil=need + 10)
    b.resync_totals("c6")

@test("I23", "plan_price가 expected_cost의 별칭이 아니다", ("[I23]", "별칭 불일치"))
def _(b):
    b.slot("c6", "SG")["expected_cost"] += 2

@test("I24", "피벗 swap의 out 선수가 base 1순위에 없다", ("[I24]", "stale swap"))
def _(b):
    for c in b.cj["cores"]:
        sw = (c.get("pivot_plan") or {}).get("swaps")
        if sw:
            sw[0]["out"]["name"] = "존재하지 않는 선수"; return
    raise AssertionError("swaps 없음")

@test("M3", "GP<40인데 weights_data_verified가 true다", "[M3]")
def _(b):
    for p in b.players:
        ms = p.get("measured_source")
        if ms and ms.get("weights_data_verified") and (ms.get("GP") or 0) >= 40:
            ms["GP"] = 12; return
    raise AssertionError("대상 선수 없음")

@test("M6", "tag 무관 큰 괴리에 근거가 없다", "[M6]")
def _(b):
    for p in b.players:
        vr = p.get("value_reference")
        if vr and "rank_divergence" in vr and not p.get("tag_basis") and not p.get("my_max_basis"):
            vr["rank_divergence"] = 120; return
    raise AssertionError("대상 선수 없음")


# ══════════════════════════════════════════════════════════════════════
def build_pristine(dst):
    for rel in NEEDED:
        src = BASE + "/" + rel
        if not os.path.exists(src):
            sys.exit("원본 없음: %s" % rel)
        d = dst + "/" + rel
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(src, d)


def violations(out):
    return [l.strip() for l in out.splitlines() if "✗" in l]


def crash_at(out):
    """Traceback 마지막 프레임의 파일:행 을 뽑는다."""
    loc, kind = "?", "?"
    for l in out.splitlines():
        t = l.strip()
        if t.startswith("File \"") and ", line " in t:
            loc = "validate.py:" + t.split(", line ")[1].split(",")[0]
        elif t and not t.startswith(("File \"", "Traceback", "~", "^")) and ":" in t and " " not in t.split(":")[0]:
            kind = t
    return "%s (%s)" % (loc, kind[:60])


def main():
    argv = [a for a in sys.argv[1:]]
    verbose = "-v" in argv
    argv = [a for a in argv if a != "-v"]
    selftest = "--selftest" in argv
    argv = [a for a in argv if a != "--selftest"]
    filt = argv[0] if argv else None

    tmp = tempfile.mkdtemp(prefix="nfa-negtest-")
    pristine = tmp + "/pristine"
    try:
        build_pristine(pristine)

        # ── --selftest: 하네스를 하네스로 검사한다 ────────────────────
        # validate.py의 err 가산을 전부 무력화하면 어떤 위반도 exit 1을 내지 못한다.
        # 그때 **33개 테스트가 전부 빨개져야** 각 테스트의 검출 팔이 살아 있다는 뜻이다.
        # 하나라도 초록이면 그 테스트는 검출과 무관하게 통과하고 있었다는 증거다.
        if selftest:
            vp = pristine + "/validate.py"
            src = io.open(vp, encoding="utf-8").read()
            n = src.count("err+=1") + src.count("err+=len")
            src = src.replace("err+=1", "err+=0").replace("err+=len", "err+=0*len")
            io.open(vp, "w", encoding="utf-8").write(src)
            print("[--selftest] validate.py의 err 가산 %d곳 무력화 — "
                  "모든 테스트가 빨개져야 정상이다.\n" % n)

        # ── 0단계: 무결 샌드박스가 통과해야 한다 ──────────────────────
        code, out = Box(pristine).run()
        if code != 0:
            print("✗ 무결 샌드박스가 exit %d — 이후 결과는 무의미하다." % code)
            for l in violations(out)[:10]:
                print("   ", l)
            return 1
        # ── 0.5단계: 전체 출력에서 찾으면 무효였을 마커를 드러낸다 ──────
        # 판정은 `✗` 줄로 한정하므로 아래 항목도 정상 동작한다. 다만 누군가 매칭을
        # 전체 출력으로 되돌리면 **그 테스트는 위반을 주입하지 않아도 통과한다.**
        # 작성 당시 I22가 정확히 그 상태였다 — 경고로 상시 노출해 재발을 막는다.
        amb = [(i, d, e) for i, d, _, e in TESTS if all(m in out for m in e)]
        print("무결 샌드박스: exit 0 · 테스트 %d개" % len(TESTS))
        if amb:
            print("△ 무결 출력에도 나타나는 마커 %d건 — `✗` 줄 한정 매칭이 이걸 막는다:" % len(amb))
            for i, d, e in amb:
                print("    %-6s %s" % (i, " + ".join(e)))
        print()

        # ── 1단계: 위반 주입 ─────────────────────────────────────────
        fails, skips, aborts = [], [], []
        for iid, desc, fn, expect in TESTS:
            if filt and filt not in iid:
                continue
            work = tmp + "/w"
            shutil.rmtree(work, ignore_errors=True)
            shutil.copytree(pristine, work)
            b = Box(work)
            try:
                fn(b)
            except (AssertionError, KeyError, StopIteration, IndexError) as ex:
                skips.append((iid, desc, "주입 불가: %r" % (ex,)))
                print("  ⊘ %-6s %s — 주입 불가 (%s)" % (iid, desc, ex))
                continue
            code, out = b.run()
            v = violations(out)
            vtext = "\n".join(v)
            hit = all(m in vtext for m in expect)
            crashed = "Traceback" in out
            if selftest and crashed:
                # 중단은 검출이 아니다 — err 가산을 껐는데도 exit 1이 나온 것은
                # 검사가 살아 있기 때문이 아니라 검증기가 죽었기 때문이다.
                hit = False
            if code != 0 and hit:
                if crashed:
                    aborts.append((iid, desc, crash_at(out)))
                    print("  ⚠ %-6s %s\n        검출은 됐으나 **검증기가 중단**됨 — %s"
                          % (iid, desc, crash_at(out)))
                else:
                    print("  ✓ %-6s %s" % (iid, desc))
                if verbose:
                    for l in v[:3]:
                        print("        %s" % l[:150])
                    if len(v) > 3:
                        print("        … 동시 발화 %d건" % len(v))
            else:
                why = ("exit 0 — 위반이 통과했다" if code == 0
                       else "exit 1이지만 마커 없음 — **다른 검사가 대신 잡았다**")
                print("  ✗ %-6s %s\n        %s\n        기대 마커: %s" % (iid, desc, why, " + ".join(expect)))
                for l in v[:4]:
                    print("        실제: %s" % l[:150])
                fails.append((iid, desc, why))

        # ── 요약 ────────────────────────────────────────────────────
        ran = sum(1 for i, _, _, _ in TESTS if not filt or filt in i)
        print("\n" + "-" * 66)
        print("실행 %d · 통과 %d (그중 검증기 중단 %d) · 실패 %d · 주입불가 %d"
              % (ran, ran - len(fails) - len(skips), len(aborts), len(fails), len(skips)))
        for iid, desc, where in aborts:
            print("  ⚠ %s %s — 검증기가 %s 에서 중단: 이후 검사가 실행되지 않는다" % (iid, desc, where))
        for iid, desc, why in fails:
            print("  ✗ %s %s — %s" % (iid, desc, why))
        for iid, desc, why in skips:
            print("  ⊘ %s %s — %s" % (iid, desc, why))
        if selftest:
            ok = len(fails) == ran and not skips
            print("[--selftest] %s — 검출 팔이 살아 있는 테스트 %d/%d"
                  % ("통과" if ok else "✗ 실패", len(fails), ran))
            if not ok:
                print("            초록으로 남은 테스트는 검출과 무관하게 통과하고 있다.")
            return 0 if ok else 1
        return 1 if fails else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
