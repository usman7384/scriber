import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    density_g_cm3: float
    youngs_modulus_gpa: float
    yield_mpa: float
    source: str


AL_6061 = Material("Aluminum 6061-T6", 2.70, 68.9, 276, "ASM Aerospace Specification Metals datasheet MA6061T6 (asm.matweb.com)")
AL_7075 = Material("Aluminum 7075-T6", 2.81, 71.7, 503, "ASM Aerospace Specification Metals datasheet MA7075T6 (asm.matweb.com)")
SS_14301 = Material(
    "Stainless steel 1.4301", 7.9, 200, 230, "EN 10088-1 Table A.1 (density, E); EN 10088-2 Table 7 (Rp0.2, cold-rolled strip)"
)
S235 = Material("Structural steel S235", 7.85, 210, 235, "EN 1993-1-1 §3.2.6 (E) and Table 3.1 (fy); EN 1991-1-1 Table A.4 (density)")
PETG = Material("PETG", 1.27, 2.01, 50, "Eastman Eastar 6763 datasheet (density, flexural modulus, tensile yield)")
PLA = Material("PLA", 1.24, 3.6, 60, "NatureWorks Ingeo 4043D datasheet (density, tensile modulus, tensile yield)")
ABS = Material("ABS", 1.04, 2.3, 45, "INEOS Styrolution Terluran GP-35 datasheet (density, tensile modulus, yield stress)")
PA12 = Material("PA12", 1.01, 1.4, 45, "Evonik Vestamid L1600 datasheet (density, tensile modulus, yield stress)")

# grades before families, so "aluminum 7075" does not fall back to 6061
ALIASES: tuple[tuple[str, Material], ...] = (
    ("6061", AL_6061),
    ("7075", AL_7075),
    ("1.4301", SS_14301),
    ("304", SS_14301),
    ("s235", S235),
    ("petg", PETG),
    ("pla", PLA),
    ("abs", ABS),
    ("pa12", PA12),
    ("stainless", SS_14301),
    ("aluminium", AL_6061),
    ("aluminum", AL_6061),
    ("steel", S235),
)


def material(text: str) -> Material | None:
    tokens = set(re.findall(r"[a-z0-9.]+", text.lower()))
    return next((m for alias, m in ALIASES if alias in tokens), None)
