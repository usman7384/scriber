from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

BACKGROUND = (0.0, 0.0, 0.0, 0.0)
COLOUR = (0.64, 0.64, 0.64, 1.0)


# camera directions in glTF axes (Y up): "top" looks down CAD +Z, "front" looks at the CAD -Y side; the straight views
# lean a few degrees so hole walls and steps show, since flat faces at different depths shade alike head-on
VIEWS = {"iso": (1.0, 0.9, 1.2), "top": (0.12, 1.0, 0.18), "front": (0.12, 0.18, 1.0), "right": (1.0, 0.18, 0.12)}


def render_thumbnail(glb: Path, png: Path, size: int = 256, view: str = "iso") -> Path:
    # Imported here so a machine without OpenGL can still build parts; the caller falls back to no thumbnail.
    import pyrender

    mesh = trimesh.load_scene(glb).to_mesh()
    centre, radius = mesh.bounding_box.centroid, float(np.linalg.norm(mesh.extents)) / 2 or 1.0
    material = pyrender.MetallicRoughnessMaterial(baseColorFactor=COLOUR, metallicFactor=0.1, roughnessFactor=0.7)
    scene = pyrender.Scene(bg_color=BACKGROUND, ambient_light=(0.35, 0.35, 0.35))
    scene.add(pyrender.Mesh.from_trimesh(mesh, material=material, smooth=False))
    direction = np.array(VIEWS[view])
    # a 30 degree view holds the bounding sphere whole only from radius / sin(15 deg), about 3.9 radii; 3 cut long parts off
    pose = _look_at(centre + direction / np.linalg.norm(direction) * radius * 4.0, centre)
    # the straight views are orthographic, like the views on a drawing
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 6) if view == "iso" else pyrender.OrthographicCamera(radius * 1.05, radius * 1.05)
    scene.add(camera, pose=pose)
    # light from the iso direction in every view, so holes and steps keep their shading in the straight views
    iso = np.array(VIEWS["iso"])
    scene.add(pyrender.DirectionalLight(intensity=3.0), pose=_look_at(centre + iso / np.linalg.norm(iso) * radius * 3.0, centre))
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
    up = [0.0, 0.0, -1.0] if abs(back[1]) > 0.99 else [0.0, 1.0, 0.0]
    right = np.cross(up, back)
    right /= np.linalg.norm(right)
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = right, np.cross(back, right), back, eye
    return pose
