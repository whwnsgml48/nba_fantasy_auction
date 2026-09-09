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
import io, json, os, re, shutil, subprocess, sys, tempfile

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
    "data/prior_auction_2025_26/results.json",   # I26 실측 산포
    "tool/trigger_audit.py",                     # I26 발동 확률 모델
    "tool/tool_embed.py",                        # 39차 — 툴 임베드 상수 단일 소스
    "tool/pos_elig.py",                          # 40차 — 슬롯 자격 단일 소스 (I31)
    "tool/name_fields.py",                       # 2026-09-01 — 이름 필드 분류 단일 소스 (I38)
    "data/core_procurement.json",                # 2026-09-01 — 조달 배율(툴 CORES.proc 의 원천)
    "data/stats_2025_26/measured_full.json",
    "tool/auction-console.html",
    "tool/cat_model.py",
    "tool/divergence_rules.py",
    "tool/gen_players_csv.py",
    "data/players.csv",
    "data/core_value_tables.json",               # 42차 — 코어별 캣 진단표 (I40)
    "tool/declaration_conflicts.py",             # 42차 — 선언 모순 대조 단일 소스 (I43)
    "tool/walkaway_price.py",                    # 44차 — 기각 방법 재가동 감시 (I46)
]

TESTS = []


def test(iid, desc, expect, after=(), warn=False, expect_pass=False):
    """expect: `✗` 줄에 있어야 하는 문자열(하나 또는 튜플).
    after:  **전체 출력**에 있어야 하는 문자열 — 그 지점 이후의 검사가 실제로 실행됐다는
            증거다. 중단(crash)도 exit 1을 내므로 마커만으로는 절단을 구분할 수 없다.
    warn:   **경고 등급 검사**용(39차 신설). 경고는 err에 가산하지 않으므로 exit 0이고,
            위반 전제(exit 1 + `✗` 줄)로는 검사할 수 없다. 이 프로젝트에는 경고 등급이
            여럿인데(I21·I22·I24 예비비·I26 비구속·I27) **테스트가 하나도 없었다.**
            warn=True 면 마커를 `△` 줄에서 찾고 exit 0을 정상으로 본다.
    expect_pass: **검사가 발화하면 안 되는** 주입(40차 신설). 지금까지 이 하네스는
            「위반을 넣으면 걸리는가」만 물었고 **「정당한 것을 넣으면 안 걸리는가」는
            물은 적이 없다.** 그래서 검사가 과도하게 좁아져도 아무도 모른다 — 실제로
            I36 이 c5 의 **정당한** 강등을 막았고, 그 사실은 사람이 판단표를 고치다가
            발견했다. expect_pass=True 면 **exit 0 + `✗` 줄에 마커 없음**을 요구하고,
            `expect` 는 `after` 처럼 **전체 출력**에 있어야 하는 증거 문자열로 쓴다."""
    def deco(fn):
        TESTS.append((iid, desc, fn,
                      (expect,) if isinstance(expect, str) else tuple(expect),
                      (after,) if isinstance(after, str) else tuple(after),
                      "pass" if expect_pass else warn))
        return fn
    return deco


def _fingerprint(work, b):
    """샌드박스의 **모든 파일** + 아직 저장 안 된 메모리 상태를 지문으로 만든다 (42차).

    ⚠️ `b.players`·`b.cj` 는 `run()` 안의 `save()` 에서야 디스크에 쓰인다. 주입 직후
    시점에는 메모리에만 있으므로 파일 해시만으로는 안 잡힌다 — 둘 다 넣는다.
    """
    import hashlib
    h = {}
    for root, _dirs, files in os.walk(work):
        for f in files:
            fp = os.path.join(root, f)
            try:
                h[os.path.relpath(fp, work)] = hashlib.sha1(
                    io.open(fp, "rb").read()).hexdigest()
            except OSError:
                pass
    return (h,
            json.dumps(b.players, ensure_ascii=False, sort_keys=True),
            json.dumps(b.cj, ensure_ascii=False, sort_keys=True))


# 검증기 뒷부분 섹션이 실행됐는지 보는 표지. 위반 유무와 무관하게 항상 찍히는 줄들이다.
TAIL = ("P 배열", "과열 임계값:", "판단 순서:")


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

    def csv(self, fn):
        p = self.root + "/data/players.csv"
        s = io.open(p, encoding="utf-8").read()
        io.open(p, "w", encoding="utf-8").write(fn(s))

    def tool(self, rel, fn):
        """`tool/` 아래 파일을 직접 고친다 (42차 · I39 는 소스를 읽는 검사다)."""
        p = self.root + "/" + rel
        t = io.open(p, encoding="utf-8").read()
        io.open(p, "w", encoding="utf-8").write(fn(t))

    def cval(self, fn):
        """data/core_value_tables.json 을 고친다 (42차 · I40)."""
        p = self.root + "/data/core_value_tables.json"
        d = json.load(io.open(p, encoding="utf-8"))
        fn(d)
        json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def sim(self, fn):
        """data/matchup_sim.json 을 고친다 (44차 · I46)."""
        p = self.root + "/data/matchup_sim.json"
        d = json.load(io.open(p, encoding="utf-8"))
        fn(d)
        json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

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

# ⚠️ 40차: 원래 이 테스트는 **c5** 를 뺐는데, 40차에 c5 가 정당하게 강등되면서
#   기준 샌드박스에 이미 없다 — 주입이 **무동작**이 되어 exit 0 으로 통과했다.
#   (검사가 죽은 게 아니라 **테스트가 죽었다.** I36 을 만들며 발견했다.)
#   살아 있는 행(c6 · 기본값)을 빼도록 바꾼다. 마커도 I36 신설로 바뀌었다.
@test("I10a", "판단표에서 살아 있는 코어가 빠졌다", "비활성 선언도 없는 코어")
def _(b):
    b.cj["decision_table"] = [d for d in b.cj["decision_table"] if d["core"] != "c6"]

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

@test("I13", "anchor_plan 결손 — 크래시 없이 위반으로 잡히고 뒤쪽 검사가 계속되는가",
      "anchor_plan", after=TAIL)
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

@test("I25a", "players.csv 값이 players.json과 갈라졌다", ("[I25]", "재생성 필요"),
      after=TAIL)
def _(b):
    # 손으로 유지되던 미러가 갈라지는 것이 실제 사고였다(도입 시 174행 전부 불일치).
    b.csv(lambda s: s.replace("Nikola Jokić,DEN", "Nikola Jokić,LAL", 1))

@test("I25b", "players.csv에서 한 행이 사라졌다", ("[I25]", "재생성 필요"), after=TAIL)
def _(b):
    b.csv(lambda s: "\n".join(l for l in s.split("\n") if not l.startswith("Rudy Gobert,")))

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


@test("I27", "판단표 임계값이 my_max보다 낮은데 threshold_basis가 없다",
      ("[I27]", "Nikola Jokić", "threshold_basis 없음"), after=TAIL, warn=True)
def _(b):
    # my_max만 올리고 임계값을 그대로 두는 상황 = 37차 c3가 실제로 그랬던 형태.
    # ⚠️ **무결 상태에서 이미 경고가 뜨는 선수를 고르면 안 된다** — c1 KAT·c5 Sabonis는
    #    지금도 I27에 걸려 있어서, 그들을 대상으로 삼으면 주입 없이도 마커가 잡힌다
    #    (하네스 0.5단계가 이걸 잡아줬다). 임계값 == my_max 인 Jokić를 쓴다.
    for r in b.cj["decision_table"]:
        for rule in (r.get("cond") or {}).get("rules") or []:
            if rule["player"] == "Nikola Jokić":
                b.pl["Nikola Jokić"]["my_max"] = rule["max"] + 20
                rule.pop("threshold_basis", None)
                return
    raise AssertionError("Jokić 가격 규칙이 없음")


@test("I28", "판단표 label 금액이 cond.rules와 갈라졌다",
      ("[I28]", "금액 불일치"), after=TAIL, warn=True)
def _(b):
    # A가 5d75250 에서 실제로 낸 형태: rules 만 고치고 label 을 안 고쳤다.
    # 툴은 rules 에서 화면 문자열을 따로 만들어 **화면은 맞고 데이터만 갈라진다**.
    for r in b.cj["decision_table"]:
        rules = (r.get("cond") or {}).get("rules") or []
        if len(rules) == 1 and ("$%d" % rules[0]["max"]) in (r.get("label") or ""):
            r["label"] = r["label"].replace("$%d" % rules[0]["max"],
                                            "$%d" % (rules[0]["max"] - 9))
            return
    raise AssertionError("label에 금액이 든 단일 규칙 행이 없음")


@test("I29", "슬롯 role이 선언한 캣을 후보가 못 준다",
      ("[I29]", "c1 C", "공급을 선언했는데"), after=TAIL, warn=True)
def _(b):
    # 사용자가 c6 BN에서 잡은 형태("3PT 소스"인데 2순위가 3PM 0.8)를 다른 슬롯에 주입한다.
    # ⚠️ c6 BN은 무결 상태에서 이미 발화하므로 대상으로 쓰면 주입 없이 통과한다.
    #    KAT은 BLK 가중치가 없어 'BLK 잠금'을 선언하면 반드시 걸린다.
    b.slot("c1", "C")["role"] = "BLK 잠금 전용 슬롯"
    return


# ── 40차 신설 ────────────────────────────────────────────────────────────────
@test("I31a", "선언된 슬롯에 그 선수를 넣을 수 없다 (라벨 오류)",
      ("[I31]", "에 뒀는데 자격은"), after=TAIL)
def _(b):
    # 40차에 실제로 있던 형태 — `SF=Amen Thompson`(야후 자격 PG/SG).
    # 매칭은 성립하는데 **화면이 틀린 자리를 지시**한다.
    b.pl[b.first("c1", "SF")]["pos_yahoo"] = ["PG", "SG"]


@test("I31b", "9인이 9칸을 못 채운다 (SF 자격자를 전멸시킨다)",
      ("[I31]", "9인이 9칸을 못 채운다"), after=TAIL)
def _(b):
    # ⚠️ 라벨 오류만 주입하면 I31a 와 구별되지 않는다. **매칭 자체가 깨지도록**
    #    그 코어에서 SF 를 댈 수 있는 사람을 전부 없앤다.
    co = b.core("c1")
    for s in co["slots"]:
        for cd in s["candidates"]:
            p = b.pl.get(cd["name"])
            if p:
                p["pos_yahoo"] = ["C"]
                p["pos"] = "C"


@test("I31c", "대체후보가 그 슬롯에 못 들어간다",
      ("[I31]", "대체", "자격"), after=TAIL)
def _(b):
    s = b.slot("c1", "SF")
    b.pl[s["candidates"][1]["name"]]["pos_yahoo"] = ["C"]


@test("I32a", "surplus 가 my_max·시장중간과 갈라졌다", ("[I32]", "surplus"), after=TAIL)
def _(b):
    b.pl["Nikola Jokić"]["surplus"] = 99


@test("I32b", "못 사는 선수를 살 수 있다고 표시했다",
      ("[I32]", "못 사는 선수를 살 수 있다고 표시"), after=TAIL)
def _(b):
    # my_max < 시장 하단인데 obtainable=true — 40차에 실제로 3명이 이 상태였다.
    p = b.pl["Nikola Jokić"]
    p["my_max"] = p["market_low"] - 5
    p["surplus"] = p["my_max"] - round((p["market_low"] + p["market_high"]) / 2)
    p["obtainable"] = True


@test("I33a", "같은 자격 사실이 두 곳에서 다르다",
      ("[I33]", "같은 사실이 두 곳에서 다르다"), after=TAIL, warn=True)
def _(b):
    p = b.pl["Alperen Şengün"]          # 무결 상태에서 두 기록이 일치하는 선수를 고른다
    p["yahoo_eligibility_39"]["listed"] = "C, PF, SF"


@test("I34", "대체안으로 갈아타면 예산을 넘는다",
      ("[I34]", "살 수 없는 대안"), after=TAIL)
def _(b):
    # 40차에 실제로 4건 있었다. 대체안의 **가격 정합**은 통과하는데 전환하면 총액이 넘는다.
    s = b.slot("c7", "BN")
    cd = s["candidates"][1]
    n = cd["name"]
    b.pl[n]["market_low"] = 60; b.pl[n]["market_high"] = 70; b.pl[n]["my_max"] = 70
    b.pl[n]["surplus"] = 70 - 65; b.pl[n]["obtainable"] = True
    cd["plan_price"] = cd["expected_cost"] = 65; cd["bid_ceiling"] = 70


@test("I26a", "판단표 가격 조건이 절대 발동할 수 없다", ("[I26]", "절대 발동 불가"), after=TAIL)
def _(b):
    # Jokić <= $1 — 시장 $93-101 이고 작년 실적으로도 불가. 균등·실측 둘 다 0.
    for r in b.cj["decision_table"]:
        for rule in (r.get("cond") or {}).get("rules") or []:
            if rule["player"] in b.pl:
                rule["max"] = 1
                return
    raise AssertionError("가격 규칙을 가진 판단표 행이 없음")


@test("I26b", "판단표 가격 조건이 항상 참이라 게이트 역할이 없다",
      ("[I26]", "게이트 역할 없음"), after=TAIL)
def _(b):
    # my_max 를 함께 올려야 한다 — I10이 `임계값 <= my_max` 를 요구하므로 임계값만
    # 올리면 그쪽이 먼저 걸리고, my_max 안에서는 실측 P가 1.0까지 안 올라간다.
    # ⚠️ 규칙이 2개인 행(c1: KAT + Hali)을 고르면 안 된다 — 결합 확률이 곱이라
    #    한쪽만 1.0으로 만들어도 다른 쪽(Hali 0.33)이 곱해져 발화하지 않는다.
    for r in b.cj["decision_table"]:
        rules = (r.get("cond") or {}).get("rules") or []
        if len(rules) == 1 and rules[0]["player"] in b.pl:
            b.pl[rules[0]["player"]]["my_max"] = 999
            rules[0]["max"] = 999
            return
    raise AssertionError("가격 규칙이 정확히 1개인 판단표 행이 없음")


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


def cautions(out):
    """`△` 줄 + **그 뒤에 이어지는 들여쓰기 상세 줄**.

    ⚠️ 39차: `△` 줄만 보면 안 된다. I21 요약 줄(`△ [I21 경고] … 0건`)은 위반이 없어도
    **항상 찍히므로**, 마커를 `[I21`로 잡으면 주입 없이 통과한다 — I22가 당했던 것과
    같은 형태다(테스트가 초록인데 검출과 무관). 개수>0 일 때만 나오는 상세 줄이
    필요하고, 그 줄에는 `△`가 없다."""
    out_lines, keep, on = out.splitlines(), [], False
    for l in out_lines:
        if "△" in l:
            on = True; keep.append(l.strip()); continue
        if on and l[:6].isspace() and l.strip():
            keep.append(l.strip()); continue
        on = False
    return keep


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


# ── I30 툴 JS 구조 ────────────────────────────────────────────────────────
# 39차: sync_tool 이 injOut 을 끼워넣으며 행 끝 쉼표를 잘라먹어 const P 배열이 깨졌고
# 툴 전체가 SyntaxError 로 죽었다. mx·mk 값 대조는 전부 통과했다 — **값이 맞는 것과
# 파일이 실행되는 것은 다른 질문**이고, 검사 체계에 후자가 없었다.

@test("I30", "const P 행 끝 쉼표가 사라지면 잡는가 (배열 파손)", "행 종결 이상", after=TAIL)
def _i30_comma(b):
    def f(s):
        m = re.search(r'const P=\[\n(.*?)\n\];', s, re.S)
        ls = m.group(1).split("\n")
        hit = [i for i, l in enumerate(ls) if l.startswith('{n:"')][3]
        assert ls[hit].endswith("},")
        ls[hit] = ls[hit][:-1]                      # 쉼표만 뗀다
        return s[:m.start(1)] + "\n".join(ls) + s[m.end(1):]
    b.html(f)


@test("I30", "const P 행이 players.json 인원과 다르면 잡는가", "≠ players.json", after=TAIL)
def _i30_count(b):
    def f(s):
        m = re.search(r'const P=\[\n(.*?)\n\];', s, re.S)
        ls = m.group(1).split("\n")
        hit = [i for i, l in enumerate(ls) if l.startswith('{n:"')][-2]
        del ls[hit]                                  # 한 행을 없앤다
        return s[:m.start(1)] + "\n".join(ls) + s[m.end(1):]
    b.html(f)


# ── M4 · M5 · M5b · I21 (39차 신설) ───────────────────────────────────────
# 커버리지 공백이었다. M4·M5·M5b 는 위반 등급이고 I21 은 경고 등급이라 warn=True 로 본다.
# (I15·I16·I17 은 별도 마커가 없다 — 다른 검사에 접혀 있어 주입 지점이 없다.)

@test("M4", "캣 가중치 w3인데 flag가 그 캣을 '엘리트 아님'이라 부른다", "[M4]", after=TAIL)
def _m4(b):
    for p in b.players:
        w = p.get("cat_weights") or {}
        cat = next((c for c, v in w.items() if v == 3), None)
        if cat and not (p.get("flag") or ""):
            p["flag"] = "%s 엘리트 아님" % cat
            return
    raise AssertionError("대상 선수 없음")


@test("M5", "tag=burn 인데 div가 '우리가 과소' 방향이고 tag_basis가 없다", "[M5]", after=TAIL)
def _m5(b):
    for p in b.players:
        vr = p.get("value_reference")
        if vr and "rank_divergence" in vr and not p.get("tag_basis") and not p.get("tag_basis_auto"):
            p["tag"] = "burn"            # 안 산다고 선언했는데
            vr["rank_divergence"] = 60   # 우리 가치모델은 과소평가라고 한다 — 모순
            return
    raise AssertionError("대상 선수 없음")


@test("M5b", "tag_basis의 div 인용이 실제와 어긋난다 (드리프트)",
      ("[M5b]", "드리프트"), after=TAIL)
def _m5b(b):
    for p in b.players:
        vr = p.get("value_reference")
        if vr and isinstance(vr.get("rank_divergence"), int) and not p.get("tag_basis_auto"):
            # 실제 div 와 크게 다른 값을 인용시킨다(허용 오차 ±2).
            p["tag_basis"] = "div %+d — 근거 기록" % (vr["rank_divergence"] + 40)
            return
    raise AssertionError("대상 선수 없음")


@test("I21", "계획가가 시장 상단을 넘으면 경고로 잡는가",
      ("[I21", "시장상단 $"), after=TAIL, warn=True)
def _i21(b):
    # my_max 가 시장 상단보다 높은 슬롯을 골라 계획가를 my_max 까지 올린다.
    # I1(계획가 <= my_max)은 지키면서 I21(계획가 > 시장 상단)만 건드린다.
    for co in b.cj["cores"]:
        for s in co["slots"]:
            q = b.pl.get(s["candidates"][0]["name"])
            if q and q["my_max"] > q["market_high"] and s["plan_price"] <= q["market_high"]:
                b.set_price_on(s, q["my_max"])
                b.resync_totals(co["id"])
                return
    raise AssertionError("대상 슬롯 없음")


# ── I36 판단표 도달 가능성 ────────────────────────────────────────────────
# 40차: c5 를 판단표에서 **의도적으로** 내리자 무명 검사가 걸렸다. 그 검사가 막던 것은
# 「존재하지만 아무도 고를 수 없는 코어」이고 그건 지켜야 한다 — 그래서 지우지 않고
# **좁혔다**: 판단표에 없으면 `status` 가 active:false · reason · revert 를 다 갖춰야 통과.
#
# ⚠️ 마커를 `[I36` 으로 잡으면 **주입 없이도 통과한다** — 요약 줄
#   `[I36] 판단표 도달 가능성: …` 이 위반 유무와 무관하게 항상 찍히기 때문이다.
#   I21 이 실제로 당했던 형태다(cautions 주석 참조). `✗` 줄에만 있는 문구로 잡는다.

def _drop_c5_row(b):
    """판단표에서 c5 행을 뺀다. 세 테스트가 공유하는 전제."""
    b.cj["decision_table"] = [r for r in b.cj["decision_table"] if r["core"] != "c5"]


@test("I36", "판단표에서 코어를 빼고 비활성 선언이 없으면 잡는가",
      "비활성 선언도 없는 코어", after=TAIL)
def _i36_no_status(b):
    _drop_c5_row(b)
    b.core("c5").pop("status", None)


@test("I36", "비활성 선언에 revert 가 없으면 잡는가 (되돌릴 길이 없다)",
      "status 에 revert 가 없다", after=TAIL)
def _i36_no_revert(b):
    _drop_c5_row(b)
    st = b.core("c5").setdefault("status", {})
    st["active"] = False
    st["reason"] = "테스트 주입"
    st.pop("revert", None)


@test("I36", "비활성 선언이 완비되면 통과하는가 (정당한 강등을 막지 않는가)",
      "명시적 비활성 1개", after=TAIL, expect_pass=True)
def _i36_complete(b):
    # 이것만 **통과를 확인하는** 테스트다(expect_pass). 나머지 둘과 달리 위반을 만들지
    # 않는다 — 검사가 과도하게 좁아져 **정당한 강등까지 막으면** 여기서 걸린다.
    # 이 하네스에 원래 없던 축이고, I36 이 실제로 정당한 강등을 막은 것이 계기다.
    _drop_c5_row(b)
    st = b.core("c5").setdefault("status", {})
    st["active"] = False
    st.setdefault("reason", "테스트 주입 — 왜 내렸는가")
    st.setdefault("revert", "테스트 주입 — 어떻게 되돌리는가")


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
            # ⚠️ 공백 변형에 걸리면 안 된다. 38차에 I25를 `err += 1`(공백 있음)으로
            # 써서 무력화를 빠져나갔고, 11개 테스트가 검출과 무관하게 초록이었다.
            # 문자열 매칭 대신 정규식으로 모든 형태를 잡는다.
            src, n1 = re.subn(r"\berr\s*\+=\s*1\b", "err+=0", src)
            src, n2 = re.subn(r"\berr\s*\+=\s*len", "err+=0*len", src)
            n = n1 + n2
            io.open(vp, "w", encoding="utf-8").write(src)
            leftover = re.findall(r"\berr\s*\+=\s*(?!0)\S+", src)
            if leftover:
                print("[--selftest] ✗ 무력화 못 한 err 가산 %d곳: %s"
                      % (len(leftover), ", ".join(sorted(set(leftover))[:5])))
                return 1
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
        amb = [(i, d, e) for i, d, _, e, _a, _w in TESTS if all(m in out for m in e)]
        print("무결 샌드박스: exit 0 · 테스트 %d개" % len(TESTS))
        if amb:
            print("△ 무결 출력에도 나타나는 마커 %d건 — `✗` 줄 한정 매칭이 이걸 막는다:" % len(amb))
            for i, d, e in amb:
                print("    %-6s %s" % (i, " + ".join(e)))
        print()

        # ── 1단계: 위반 주입 ─────────────────────────────────────────
        fails, skips = [], []
        for iid, desc, fn, expect, after, wmode in TESTS:
            if filt and filt not in iid:
                continue
            work = tmp + "/w"
            shutil.rmtree(work, ignore_errors=True)
            shutil.copytree(pristine, work)
            b = Box(work)
            # 🔴 40차: **주입이 무동작이면 테스트가 죽는다.** I10a 가 그랬다 —
            #   "c5 를 판단표에서 뺀다"는 주입이었는데 c5 가 정당하게 강등되면서
            #   기준 샌드박스에 이미 없었고, 아무것도 안 바꾸고 exit 0 으로 **초록**이 났다.
            #   검사가 죽은 게 아니라 테스트가 죽은 것이고, 그건 더 나쁘다(아무도 모른다).
            #   c5 만의 문제가 아니다 — 코어·선수·판단표 행을 지우는 변경마다 생긴다.
            #   → 주입 전후를 비교해서 **정말 뭔가 바뀌었는지** 본다.
            # 🔴 42차: 감시 대상이 **4개 파일 하드코딩**이었다. 그래서 `tool/*.py` 나
            #   `data/core_value_tables.json` 을 고치는 주입은 「아무것도 안 바꿨다」로
            #   보고됐다 — 검사가 죽었는지 테스트가 죽었는지 구분할 수 없는 상태다.
            #   목록을 세지 말고 **샌드박스 전체를 해시**한다(NEEDED 가 늘어도 따라온다).
            _before = _fingerprint(work, b)
            try:
                fn(b)
            except (AssertionError, KeyError, StopIteration, IndexError) as ex:
                skips.append((iid, desc, "주입 불가: %r" % (ex,)))
                print("  ⊘ %-6s %s — 주입 불가 (%s)" % (iid, desc, ex))
                continue
            code, out = b.run()
            _after = _fingerprint(work, b)
            if _before == _after and wmode != "pass":
                # expect_pass 는 「정당한 것을 넣어도 안 걸리는가」라 무동작일 수 있다.
                why = "주입이 아무것도 바꾸지 않았다 — 이 테스트는 검출과 무관하게 통과한다"
                print("  ✗ %-6s %s\n        %s" % (iid, desc, why))
                fails.append((iid, desc, why)); continue
            if wmode == "pass":
                # 「정당한 것을 넣으면 안 걸리는가」. exit 0 이고 ✗ 줄에 마커가 없어야 한다.
                bad = [l for l in violations(out) if any(m in l for m in expect)]
                missing = [m for m in (expect + after) if m not in out]
                if "Traceback" in out:
                    print("  ✗ %-6s %s\n        검증기 중단(%s)" % (iid, desc, crash_at(out)))
                    fails.append((iid, desc, "중단"))
                elif code == 0 and not bad and not missing:
                    print("  ✓ %-6s %s  (통과 확인)" % (iid, desc))
                else:
                    why = ("검사가 과도하게 발화했다: " + bad[0][:110]) if bad else (
                           "exit %d — 다른 위반이 났다" % code if code else
                           "증거 문자열 없음: %s" % ", ".join(missing))
                    print("  ✗ %-6s %s\n        %s" % (iid, desc, why))
                    fails.append((iid, desc, why))
                continue
            v = cautions(out) if wmode else violations(out)
            vtext = "\n".join(v)
            hit = all(m in vtext for m in expect)
            crashed = "Traceback" in out
            if wmode:
                # 경고 등급 — exit code는 판정에 쓰지 않는다(err 미가산이라 0이 정상).
                if crashed:
                    print("  ✗ %-6s %s\n        검증기 중단(%s)" % (iid, desc, crash_at(out)))
                    fails.append((iid, desc, "중단")); continue
                if hit and not [m for m in after if m not in out]:
                    print("  ✓ %-6s %s  (경고 등급)" % (iid, desc))
                    if verbose:
                        for l in v[:3]: print("        %s" % l[:150])
                else:
                    why = ("경고가 뜨지 않았다" if not hit
                           else "뒤쪽 검사 미실행: %s" % ", ".join(m for m in after if m not in out))
                    print("  ✗ %-6s %s\n        %s\n        기대 마커: %s"
                          % (iid, desc, why, " + ".join(expect)))
                    for l in v[:4]: print("        실제: %s" % l[:150])
                    fails.append((iid, desc, why))
                continue
            if selftest and crashed:
                # 중단은 검출이 아니다 — err 가산을 껐는데도 exit 1이 나온 것은
                # 검사가 살아 있기 때문이 아니라 검증기가 죽었기 때문이다.
                hit = False
            missing_after = [m for m in after if m not in out]
            if code != 0 and hit and not crashed and not missing_after:
                print("  ✓ %-6s %s" % (iid, desc))
                if verbose:
                    for l in v[:3]:
                        print("        %s" % l[:150])
                    if len(v) > 3:
                        print("        … 동시 발화 %d건" % len(v))
            else:
                # 크래시는 실패다 — 38차에 anchor_plan 결손이 검증기를 죽여 뒤쪽 검사
                # (I20·I11·I10)가 통째로 안 돌았고, exit 1이라 "잡았다"로 보였다.
                if crashed:
                    why = ("검증기가 **중단**됨(%s) — 조용한 통과가 아니라 조용한 **절단**"
                           % crash_at(out))
                elif code == 0:
                    why = "exit 0 — 위반이 통과했다"
                elif missing_after:
                    why = ("exit 1인데 **뒤쪽 검사가 실행되지 않았다** — 없는 표지: %s"
                           % ", ".join(missing_after))
                else:
                    why = "exit 1이지만 마커 없음 — **다른 검사가 대신 잡았다**"
                print("  ✗ %-6s %s\n        %s\n        기대 마커: %s" % (iid, desc, why, " + ".join(expect)))
                for l in v[:4]:
                    print("        실제: %s" % l[:150])
                fails.append((iid, desc, why))

        # ── 요약 ────────────────────────────────────────────────────
        ran = sum(1 for i, _, _, _, _a, _w in TESTS if not filt or filt in i)
        print("\n" + "-" * 66)
        print("실행 %d · 통과 %d · 실패 %d · 주입불가 %d"
              % (ran, ran - len(fails) - len(skips), len(fails), len(skips)))
        for iid, desc, why in fails:
            print("  ✗ %s %s — %s" % (iid, desc, why))
        for iid, desc, why in skips:
            print("  ⊘ %s %s — %s" % (iid, desc, why))
        if selftest:
            # 경고 등급 테스트는 `err` 가산을 쓰지 않으므로 무력화해도 빨개지지 않는다.
            # 기대 대상에서 빼야 한다 — 안 그러면 정상 동작이 실패로 보고된다(39차).
            # 경고 등급과 **통과 확인**(expect_pass)은 err 가산을 안 쓰므로 무력화해도
            # 빨개지지 않는다. 둘 다 기대 대상에서 뺀다.
            nwarn = sum(1 for i, _, _, _, _a, w in TESTS
                        if w and (not filt or filt in i))
            expect_red = ran - nwarn
            ok = len(fails) == expect_red and not skips
            print("[--selftest] %s — 검출 팔이 살아 있는 테스트 %d/%d"
                  % ("통과" if ok else "✗ 실패", len(fails), expect_red))
            if nwarn:
                _np = sum(1 for i, _, _, _, _a, w in TESTS
                          if w == "pass" and (not filt or filt in i))
                print("            경고 등급 %d건 · 통과 확인 %d건은 err 무력화와 무관하므로"
                      " 제외했다 (둘 다 exit code 를 바꾸지 않는다)." % (nwarn - _np, _np))
            if not ok:
                print("            초록으로 남은 테스트는 검출과 무관하게 통과하고 있다.")
            return 0 if ok else 1
        return 1 if fails else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════
# 42차 — I39(주간 경기수 단일 소스) · I40(코어별 캣 진단표)
#
# 🔴 왜 이 다섯이 필요한가
#   I39: 38차가 세 파일의 3.5 를 cat_model 로 모았는데 **40차에 lineup_feasibility 가
#        다시 복제했다.** 두 값이 우연히 같아서 아무도 몰랐고, 42차에 한쪽을 바꾸자
#        사용률 표가 따라오지 않았다. 검사가 실제로 발화하는지 확인한다.
#   I40: 코어별 선수 가격/순위를 두 번 만들었고 두 번 다 기각했다. 다음 사람이
#        「순위 정도는 괜찮겠지」로 되살리는 경로를 막는 검사다 — 그 검사가 죽어 있으면
#        아무 의미가 없다.
# ══════════════════════════════════════════════════════════════════════

@test("I39a", "GAMES_PER_WEEK 를 다른 파일에 복제한다 (40차 사고 재현)",
      "를 **복제**한 파일")
def _(b):
    b.tool("tool/divergence_rules.py",
           lambda t: t + "\n\nGAMES_PER_WEEK = 3.299   # 복제 — 잡혀야 한다\n")


@test("I39b", "cat_model 의 지지집합 가드를 지운다 (조용히 틀리는 경로)",
      "지지집합 가드가 1/2 자리만 남았다")
def _(b):
    b.tool("tool/cat_model.py",
           lambda t: t.replace("팀당 주간 경기수 범위(1~9) 밖이다", "범위 밖", 1))


@test("I39c", "cat_model 의 세계 주입 경로를 지운다 (세계 비교 불가)",
      "주입 경로")
def _(b):
    b.tool("tool/cat_model.py",
           lambda t: t.replace('os.environ.get("STANDARD_WEEK_GAMES")', 'None', 1))


@test("I40a", "코어별 **선수 순위**를 되살린다 (42차에 두 번 기각된 산출)",
      "선수 가격/순위**가 되살아났다")
def _(b):
    def f(d):
        c = next(iter(d["cores"].values()))
        c["players"] = {"Nikola Jokić": {"rank_core": 1, "rank_shift": 0}}
    b.cval(f)


@test("I40b", "cores.json 에 core_value_42 를 넣는다 (32차 core_hits 오염 재현)",
      "core_value_42 가 남아 있다")
def _(b):
    b.cj["cores"][0]["core_value_42"] = {"overpay_vs_core_ceiling": []}


@test("I40c", "price_override 에 근거(why)가 없다", "price_override 에 `why` 가 없다")
def _(b):
    b.slot("c6", "PG")["candidates"][0]["price_override"] = {"bid_ceiling": 1}


# ══════════════════════════════════════════════════════════════════════
# 42차 작업5 — I41 (방이 낸 값)
#   🔴 이 검사가 지키는 것은 「추정이 맞나」가 아니라 **「관측이 왜곡 없이 실렸는가」**다.
#      회귀를 하지 않았으므로 검증할 모델이 없다 — 그래서 검사가 더 단순하고,
#      단순한 검사일수록 죽어 있어도 아무도 모른다.
# ══════════════════════════════════════════════════════════════════════

@test("I41a", "room_price 가 실낙찰가 × 1.117 과 어긋난다", "관측 환산 불일치")
def _(b):
    for p in b.players:
        if p.get("prior_auction_price") is not None:
            p["room_price"] = p["room_price"] + 7
            return
    raise AssertionError("실낙찰가 보유 선수 없음")


@test("I41b", "작년 미지명 선수에 **추정 가격**을 만들어 넣는다",
      "미지명 선수에 추정 가격이 붙어 있다")
def _(b):
    for p in b.players:
        if p.get("prior_auction_price") is None and p.get("room_prior_class"):
            p["room_price"] = 12
            return
    raise AssertionError("미지명 선수 없음")


@test("I41c", "툴 P 배열의 rp 가 players.json 과 갈라진다",
      "툴 P 배열의 rp/rc 가")
def _(b):
    import re as _r
    b.html(lambda s: _r.sub(r',rp:\d+', ',rp:999', s, count=1))


# 42차 작업4b — I42 (태우기 ∩ 계획)
#   🔴 42차에 `Myles Turner` 가 태우기이면서 c2 UTIL 후보2 였다. 어떤 검사도 대조하지
#      않았고 tag_basis 가 null 이라 M5 도 안 걸렸다 — 조용히 통과하던 모순이다.

@test("I42", "계획 1순위를 태우기 명단에 올린다 (탈출로를 스스로 닫는다)",
      "태우기 명단이 계획과 충돌")
def _(b):
    n = b.first("c6", "PG")
    for p in b.players:
        if p["name"] == n:
            p["tag"] = "burn"
            return
    raise AssertionError("c6 PG 1순위를 못 찾음")


# 44차 — I46 (파이프라인 산출물 결측)
#   🔴 이 저장소가 **두 번** 조용히 잃었다: 42차에 gp_sensitivity·walkaway_40,
#      44차에 standard_error·assumption_stress. 두 번 다 `matchup_sim.py` 를 뒤에
#      돌려 덮은 것이고, **두 번 다 validate 0건 · negative 전건 통과**였다.
#      검사가 「값이 맞는가」만 묻고 **「있기는 한가」를 안 물었다.**

@test("I46", "matchup_sim.json 의 파이프라인 산출물 키를 지운다 (뒤 단계가 안 돈 상태)",
      "파이프라인 산출물이 **없다**")
def _(b):
    b.sim(lambda d: d.pop("assumption_stress", None))


@test("I46", "콘솔 임베드 상수를 빈 객체로 만든다 (sync_tool 폴백이 켜진 상태)",
      "콘솔 임베드 상수가 **비어 있다**")
def _(b):
    b.html(lambda s: re.sub(r'const STRESS=\{.*?\};', 'const STRESS={};', s, count=1, flags=re.S))


# 42차 작업6 — I43 (선언 모순 전수 대조)
#   개별 검사 대신 **대조 하나**를 뒀다. 새 선언이 생기면 자동으로 걸려야 한다 —
#   그 「자동」이 실제로 작동하는지 확인한다.

@test("I43", "판정되지 않은 선언 상충을 새로 만든다 (앵커에 코어 전환을 겹친다)",
      "판정되지 않은 선언 상충")
def _(b):
    # c6 PF 1순위에 철수가를 계획가 아래로 박아 WALK↔BUY 상충을 만든다
    n = b.first("c6", "PF")
    pp = b.slot("c6", "PF")["candidates"][0]["expected_cost"]
    for t in b.cj["overheat_thresholds"]:
        if t["player"] == n:
            t["threshold"] = max(1, pp - 5)
            return
    b.cj["overheat_thresholds"].append(
        {"player": n, "threshold": max(1, pp - 5), "rule": "> $%d" % max(1, pp - 5),
         "tier": "anchor", "expected_2026_27": pp, "overheat_at": None, "walk_away": max(1, pp - 5)})


if __name__ == "__main__":
    sys.exit(main())
