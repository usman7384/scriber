import { useThree } from "@react-three/fiber";
import { useEffect, useEffectEvent } from "react";
import type { Box3, OrthographicCamera, PerspectiveCamera, Vector3 } from "three";
import { fitDistance, fitZoom, frameOffset, viewPose, type Frame, type View } from "./scene";

type Camera = PerspectiveCamera | OrthographicCamera;

// Frames the part in the free area between the floating panels, not the window centre.
export function CameraRig({ view, box, free }: { view: { name: View }; box: Box3; free: Frame | undefined }) {
  const camera = useThree((s) => s.camera) as Camera;
  const size = useThree((s) => s.size);
  const controls = useThree((s) => s.controls) as { target: Vector3; update: () => void } | null;
  const invalidate = useThree((s) => s.invalidate);
  const get = useThree((s) => s.get);

  useEffect(() => {
    if (free) {
      const [x, y] = frameOffset(size, free);
      camera.setViewOffset(size.width, size.height, x, y, size.width, size.height);
    } else camera.clearViewOffset();
    invalidate();
  }, [camera, size, free, invalidate]);

  const pose = useEffectEvent(() => {
    const camera = get().camera as Camera;
    const frame = free ?? { left: 0, top: 0, width: size.width, height: size.height };
    const fov = "fov" in camera ? camera.fov : 35;
    const { position, target } = viewPose(view.name, box, fitDistance(box, frame, size.height, fov));
    camera.position.copy(position);
    camera.lookAt(target);
    if (!("fov" in camera)) camera.zoom = fitZoom(box, frame);
    camera.updateProjectionMatrix();
    controls?.target.copy(target);
    controls?.update();
    invalidate();
  });
  const measured = free !== undefined;
  useEffect(() => pose(), [view, box, camera, controls, measured]);
  return null;
}
