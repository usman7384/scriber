# DIN 6885-1 parallel keys: shaft diameter up to -> (width b, shaft depth t1, hub depth t2), mm
DIN_6885 = (
    (8, 2, 1.2, 1.0),
    (10, 3, 1.8, 1.4),
    (12, 4, 2.5, 1.8),
    (17, 5, 3.0, 2.3),
    (22, 6, 3.5, 2.8),
    (30, 8, 4.0, 3.3),
    (38, 10, 5.0, 3.3),
    (44, 12, 5.0, 3.3),
    (50, 14, 5.5, 3.8),
    (58, 16, 6.0, 4.3),
    (65, 18, 7.0, 4.4),
    (75, 20, 7.5, 4.9),
    (85, 22, 9.0, 5.4),
    (95, 25, 9.0, 5.4),
    (110, 28, 10.0, 6.4),
)


def din6885(d: float) -> tuple[float, float, float]:
    for top, b, t1, t2 in DIN_6885:
        if 6 < d <= top + 1e-9:
            return b, t1, t2
    raise ValueError(f"DIN 6885 keys cover shafts over 6 up to 110 mm, not {d:g} mm; give the keyway width and depth")
