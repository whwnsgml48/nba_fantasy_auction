#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""players.json의 value_reference를 재산정한다. 파이프라인 정식 단계.

⚠️ 26차에 임시 스크립트에서 승격시킨 이유
  23차부터 이 작업을 scratchpad의 plant.py로 돌려왔다. 24차에 DD를 편입할 때는
  그 파일을 고치지 않고 **인라인 스크립트로 따로** 돌렸고, 26차에 다시 plant.py를
  돌리자 model 문구가 "12캣(DD 제외)"로 **퇴행**하고 gp_adjust_basis가 사라졌다.
  z 값 자체는 value_model에서 오므로 13캣이 맞았지만 라벨이 거짓이 됐다 —
  "임시 스크립트는 파이프라인에서 조용히 낡는다"는 이 프로젝트의 반복 함정이다.
  이제 저장소 안에 있고 README·HANDOFF의 파이프라인에 들어간다.

value_reference는 my_max의 **참고선**이다. 판정에 쓰이는 곳:
  validate.py M5  — tag(buy/burn)과 rank_divergence의 부호 모순 검사
  validate.py M5b — tag_basis가 인용한 div가 실제와 일치하는지
"""
import sys, json, io, os, statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from value_model import values, pool, CATS

F   = f"{BASE}/data/players.json"
pl  = json.load(io.open(F, encoding="utf-8"))
P   = {p["name"]: p for p in pl}

V, repl = values()
REF = statistics.mean([(P[p["name"]].get("measured_source") or {}).get("GP") or 0 for p in pool()])
byz = sorted(V.items(), key=lambda x: -x[1]["z_total"]); rz = {n: i+1 for i, (n, _) in enumerate(byz)}
bym = sorted(V, key=lambda n: -P[n]["my_max"]);          rm = {n: i+1 for i, n in enumerate(bym)}

MODEL = (f"z-score {len(CATS)}캣 · GP 가중 · 지명풀 126명 표준화 · tool/value_model.py "
         "(24차부터 DD 포함 — 정규근사 추정)")
CAVEAT = ("dollar_naive는 z 합산상 상단이 압축된다(절대 달러가 아니라 **순위 대조**용). "
          "DD는 실측이 아니라 정규근사 추정(실측 25명 검증: 절대오차중앙값 2.13) — "
          "독립 가정 때문에 두 스탯이 10 근처인 빅맨에서 저추정 경향. "
          "13캣을 **동일 가중**하므로, 우리가 의도적으로 포기하는 캣에 특화된 선수는 "
          "이 모델에서 과대평가로 보일 수 있다(26차 검증: 그 보정은 코어 의존적이라 "
          "일괄 방어 논리로는 성립하지 않는다).")

for n, v in V.items():
    p  = P[n]
    gp = (p.get("measured_source") or {}).get("GP") or 0
    # 26차: GP 보정 기준을 항상 현재 my_max로 통일했다. my_max_basis.prior를 base로 쓰면
    # 26차 사용자 결정(Kessler·Curry·LeBron)의 prior까지 잡혀 엉뚱한 기준이 된다.
    # 🔴 37차 — 이 값은 my_max에서 파생되므로 **상향에 재적용하면 발산한다**.
    #    GP>64.7 이면 gp_adj > my_max 라, 상향을 적용한 뒤 다시 돌리면 또 그만큼 높은
    #    값이 나온다(KAT: 62 → 71 → 81 → 92 …). 23차 하향은 GP<55 조건이라 반대 방향으로
    #    수렴했지만, 37차에 대칭 상향을 적용하면서 이 비대칭이 드러났다.
    #    → 이미 상향이 적용된 선수는 **고정점(my_max)** 을 보고하고 원값은 raw에 남긴다.
    gp_raw = max(1, round(p["my_max"] * gp / REF)) if gp else None
    _applied = "GP 출장 보정 상향" in ((p.get("my_max_basis") or {}).get("revised") or "")
    gp_adj = p["my_max"] if (_applied and gp_raw and gp_raw > p["my_max"]) else gp_raw
    p["value_reference"] = {
        "model": MODEL,
        "z_total": v["z_total"], "z_by_cat": v["z"], "dollar_naive": v["value"],
        "rank_by_value": rz[n], "rank_by_my_max": rm[n],
        "rank_divergence": rm[n] - rz[n],
        "gp": gp, "gp_ref": round(REF, 1),
        "gp_adjusted_my_max": gp_adj,
        "gp_adjusted_raw": gp_raw,
        "gp_adjust_applied": _applied,
        "gp_adjust_basis": ("상향 적용 완료(37차) — 재적용 금지. 원값은 gp_adjusted_raw"
                            if _applied else
                            "현재 my_max 기준 · 23차 GP 보정 이미 반영됨"
                            if "GP" in ((p.get("my_max_basis") or {}).get("revised") or "")
                            else "현재 my_max 기준"),
        "caveat": CAVEAT,
    }

json.dump(pl, io.open(F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
d = [abs(P[n]["value_reference"]["rank_divergence"]) for n in V]
print(f"value_reference 재산정 {len(V)}명 · {len(CATS)}캣 · 기준 GP {REF:.1f} · "
      f"평균 |순위괴리| {statistics.mean(d):.1f}")
