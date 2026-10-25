from partwright_geometry.models import Finding, PartMetrics


def validity_findings(parts: list[PartMetrics]) -> list[Finding]:
    out: list[Finding] = []
    for p in parts:
        if not p.valid:
            out.append(Finding(rule_id="GEO-VALID", severity="error", message="B-rep is not valid", part=p.id))
        if p.solids != 1:
            msg = f"part has {p.solids} solids; expected one connected solid (a feature may float or split the body)"
            out.append(Finding(rule_id="GEO-ONE-SOLID", severity="error", message=msg, part=p.id))
        if p.volume <= 0:
            out.append(Finding(rule_id="GEO-VOLUME", severity="error", message="part has no volume", part=p.id))
    return out
