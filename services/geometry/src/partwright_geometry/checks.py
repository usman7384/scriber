from partwright_geometry.models import TOUCH_MM, AssemblyReport, Finding, PartMetrics


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


def assembly_findings(report: AssemblyReport) -> list[Finding]:
    out = [
        Finding(
            rule_id="ASM-INTERFERENCE",
            severity="error",
            message=f"{i.a} and {i.b} overlap by {i.volume:.3g} mm3",
            part=i.b,
            measured=i.volume,
            required=0.0,
            suggestion="move the connector the part is placed by, or resize one part, so the parts only touch",
        )
        for i in report.overlaps()
    ]
    out += [
        Finding(
            rule_id="ASM-MATE",
            severity="error",
            message=f"joint {m.joint}: {m.parent} and {m.child} do not touch (gap {m.gap:.3g} mm)",
            part=m.child,
            measured=m.gap,
            required=0.0,
            suggestion="put both connectors on the faces that meet",
        )
        for m in report.mates
        if m.gap > TOUCH_MM
    ]
    return out
