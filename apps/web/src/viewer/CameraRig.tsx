import { useThree } from "@react-three/fiber";
import { useEffect } from "react";
import type { Box3, Vector3 } from "three";
import { viewPose, type View } from "./scene";

export function CameraRig({ view, box }: { view: { name: View }; box: Box3 }) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as { target: Vector3; update: () => void } | null;
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    const { position, target } = viewPose(view.name, box);
    camera.position.copy(position);
    camera.lookAt(target);
    controls?.target.copy(target);
    controls?.update();
    invalidate();
  }, [view, box, camera, controls, invalidate]);
  return null;
}
