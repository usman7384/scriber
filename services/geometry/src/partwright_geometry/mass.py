import re

from partwright_geometry.models import PartMetrics, Vec

DENSITY_G_CM3 = {
    "1.4301": 7.9,
    "stainless": 7.9,
    "6061": 2.70,
    "aluminium": 2.70,
    "aluminum": 2.70,
    "steel": 7.85,
    "petg": 1.27,
    "pla": 1.24,
    "abs": 1.04,
    "pa12": 1.01,
}


def density(material: str) -> float | None:
    tokens = set(re.findall(r"[a-z0-9.]+", material.lower()))
    return next((d for name, d in DENSITY_G_CM3.items() if name in tokens), None)


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
