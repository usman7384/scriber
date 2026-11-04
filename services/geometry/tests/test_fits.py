import math
from pathlib import Path

import numpy as np
import pytest
import trimesh

from scriber_geometry.deviation import distance_bounds, hausdorff
from scriber_geometry.fits import fit_circle, grid, polar, robust_circle, simplify
from scriber_geometry.mesh_sections import depths, section_loops


def ring(cx: float, cy: float, r: float, n: int = 64, noise: float = 0.0) -> np.ndarray:
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    p = np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]
    noisy: np.ndarray = p + np.random.default_rng(0).normal(0, noise, p.shape)
    return noisy


def test_circle_fit_is_exact_on_clean_points_and_close_under_noise() -> None:
    c = fit_circle(ring(3, -2, 7.5))
    assert (c.x, c.y, c.r) == pytest.approx((3, -2, 7.5), abs=1e-9)
    noisy = robust_circle(ring(3, -2, 3.3, n=400, noise=0.1))
    assert math.hypot(noisy.x - 3, noisy.y + 2) + abs(noisy.r - 3.3) < 0.03


def test_polar_and_grid_patterns_are_recognised() -> None:
    p = polar(ring(1, 2, 46, n=6), 0.05)
    assert p is not None and (p.x, p.y, p.diameter, p.start_angle) == pytest.approx((1, 2, 92, 0), abs=1e-6)
    g = grid(np.array([(-40, -25), (40, -25), (-40, 25), (40, 25)], dtype=float), 0.05)
    assert g is not None and (g.nx, g.ny, g.sx, g.sy) == (2, 2, 80, 50)
    assert polar(np.array([(0, 0), (10, 0), (0, 3)], dtype=float), 0.05) is None


def test_simplify_keeps_only_the_corners_of_a_square() -> None:
    side = np.linspace(0, 10, 11)[:-1]
    square = np.vstack([np.c_[side, 0 * side], np.c_[10 + 0 * side, side], np.c_[10 - side, 10 + 0 * side], np.c_[0 * side, 10 - side]])
    assert sorted(simplify(square, 0.01)) == [(0, 0), (0, 10), (10, 0), (10, 10)]


def test_section_of_a_tube_is_an_outer_loop_and_a_hole() -> None:
    loops = section_loops(trimesh.creation.annulus(r_min=5, r_max=10, height=4), 0.3)
    assert sorted(depths(loops)) == [0, 1]
    assert sorted(fit_circle(p).r for p in loops) == pytest.approx([5, 10], abs=0.05)


def test_hausdorff_of_a_shifted_box_is_the_shift(tmp_path: Path) -> None:
    a, b = trimesh.creation.box(extents=(10, 20, 30)), trimesh.creation.box(extents=(10, 20, 30))
    b.apply_translation((0.3, 0, 0))
    a.export(tmp_path / "a.stl")
    b.export(tmp_path / "b.stl")
    assert hausdorff(tmp_path / "a.stl", tmp_path / "b.stl") == pytest.approx(0.3, abs=1e-6)


def test_distance_bounds_never_undershoot_brute_force() -> None:
    mesh = trimesh.creation.annulus(r_min=5, r_max=10, height=4)
    points = np.random.default_rng(1).uniform(-12, 12, (300, 3))
    brute = [
        np.linalg.norm(trimesh.triangles.closest_point(mesh.triangles, np.repeat(p[None], len(mesh.faces), 0)) - p, axis=1).min()
        for p in points
    ]
    assert np.all(distance_bounds(points, mesh) >= np.array(brute) - 1e-9)
