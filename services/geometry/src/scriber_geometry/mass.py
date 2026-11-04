from scriber_geometry.models import PartMetrics, Vec
from scriber_ir import material


def density(text: str) -> float | None:
    found = material(text)
    return found.density_g_cm3 if found else None


def with_mass(part: PartMetrics, material: str | None) -> PartMetrics:
    rho = density(material) if material else None
    return part if rho is None else part.model_copy(update={"mass_g": part.volume * rho / 1000})


def assembly_mass(parts: list[PartMetrics]) -> tuple[float, Vec]:
    masses = [_known(p) for p in parts]
    total = sum(m for m, _ in masses)
    x, y, z = (sum(m * c[i] for m, c in masses) / total for i in range(3))
    return total, (x, y, z)


def _known(p: PartMetrics) -> tuple[float, Vec]:
    if p.mass_g is None or p.center_of_mass is None:
        raise ValueError(f"part {p.id!r} has no mass: give it a material with a known density")
    return p.mass_g, p.center_of_mass
