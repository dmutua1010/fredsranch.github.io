"""Actual -> KPI score -> weighted contribution -> dimension (KRA) score -> overall BSC.
Evidence gate: a record without evidence is INCOMPLETE and is NOT silently scored."""

def kpi_score(actual: float, target: float, direction: str, cap: float = 120.0) -> float:
    if target == 0:
        return 0.0
    if direction == "higher":
        ratio = actual / target
    else:                                  # lower is better (e.g. cost ratio, wait time)
        ratio = cap / 100 if actual == 0 else target / actual
    return round(max(0.0, min(ratio * 100, cap)), 2)

def record_status(rec, require_evidence: bool = True) -> str:
    if rec.actual is None:
        return "INCOMPLETE"
    if require_evidence and not (rec.evidence_ref and rec.evidence_ref.strip()):
        return "INCOMPLETE"
    return "COMPLETE"

def rag(score: float, t: dict) -> str:
    return "green" if score >= t["green"] else "amber" if score >= t["amber"] else "red"

def build_scorecard(kpis, records_by_kpi, pack: dict) -> dict:
    cap, gate = pack["scoring"]["cap_percent"], pack["evidence_gate"]["required"]
    dims: dict[str, dict] = {}
    total = complete = 0
    for k in kpis:
        total += 1
        d = dims.setdefault(k.kra, {"items": [], "wsum": 0.0, "ssum": 0.0})
        rec = records_by_kpi.get(k.code)
        status = record_status(rec, gate) if rec else "MISSING"
        score = None
        if status == "COMPLETE":
            complete += 1
            score = kpi_score(rec.actual, k.target, k.direction, cap)
            d["wsum"] += k.weight
            d["ssum"] += score * k.weight
        d["items"].append({"kpi": k.code, "name": k.name, "position": k.position_code, "target": k.target,
                           "actual": rec.actual if rec else None, "evidence": rec.evidence_ref if rec else None,
                           "status": status, "score": score})
    out, num, den = [], 0.0, 0.0
    for name, d in dims.items():
        score = round(d["ssum"] / d["wsum"], 2) if d["wsum"] else None
        w = pack["dimensions"].get(name, 0)
        if score is not None:
            num += score * w; den += w
        out.append({"dimension": name, "weight": w, "score": score,
                    "rag": rag(score, pack["scoring"]["rag"]) if score is not None else None, "items": d["items"]})
    overall = round(num / den, 2) if den else None
    return {"overall": overall,
            "overall_rag": rag(overall, pack["scoring"]["rag"]) if overall is not None else None,
            "evidence_completeness_pct": round(100 * complete / total, 1) if total else 0.0,   # proposition P2
            "dimensions": out}
