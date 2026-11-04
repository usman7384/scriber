from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

BACKGROUND = (0.0, 0.0, 0.0, 0.0)
COLOUR = (0.64, 0.64, 0.64, 1.0)


def render_thumbnail(glb: Path, png: Path, size: int = 256) -> Path:
    # Imported here so a machine without OpenGL can still build parts; the caller falls back to no thumbnail.
    import pyrender

    mesh = trimesh.load_scene(glb).to_mesh()
    centre, radius = mesh.bounding_box.centroid, float(np.linalg.norm(mesh.extents)) / 2 or 1.0
    material = pyrender.MetallicRoughnessMaterial(baseColorFactor=COLOUR, metallicFactor=0.1, roughnessFactor=0.7)
    scene = pyrender.Scene(bg_color=BACKGROUND, ambient_light=(0.35, 0.35, 0.35))
    scene.add(pyrender.Mesh.from_trimesh(mesh, material=material, smooth=False))
    pose = _look_at(centre + np.array([1.0, 0.9, 1.2]) / np.linalg.norm([1.0, 0.9, 1.2]) * radius * 3.0, centre)
    scene.add(pyrender.PerspectiveCamera(yfov=np.pi / 6), pose=pose)
    scene.add(pyrender.DirectionalLight(intensity=3.0), pose=pose)
    renderer = pyrender.OffscreenRenderer(size, size)
    try:
        # Transparent background, so the part sits on whatever the page draws behind it.
        colour, _ = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
    finally:
        renderer.delete()
    Image.fromarray(colour).save(png)
    return png


def _look_at(eye: np.ndarray, target: np.ndarray) -> np.ndarray:
    # glTF is Y-up, so the camera's up vector is +Y.
    back = (eye - target) / np.linalg.norm(eye - target)
    right = np.cross([0.0, 1.0, 0.0], back)
    right /= np.linalg.norm(right)
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = right, np.cross(back, right), back, eye
    return pose
