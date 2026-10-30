import { useFrame } from "@react-three/fiber";
import type { RefObject } from "react";
import { Quaternion, Vector3 } from "three";

const axes = [new Vector3(1, 0, 0), new Vector3(0, 1, 0), new Vector3(0, 0, 1)];
const names = ["X", "Y", "Z"];
const centre = 28;
const length = 18;

export function TriadSvg({ ref }: { ref: RefObject<SVGSVGElement | null> }) {
  return (
    <svg ref={ref} className="ws-triad" viewBox="0 0 56 56" aria-hidden="true">
      {names.map((n, i) => (
        <g key={n} data-axis={i}>
          <line x1={centre} y1={centre} x2={centre} y2={centre} />
          <text>{n}</text>
        </g>
      ))}
    </svg>
  );
}

// Lives inside the Canvas and turns the DOM triad with the camera on every rendered frame.
export function TriadSync({ svg }: { svg: RefObject<SVGSVGElement | null> }) {
  const inverse = new Quaternion();
  const v = new Vector3();
  useFrame(({ camera }) => {
    inverse.copy(camera.quaternion).invert();
    svg.current?.querySelectorAll("g").forEach((g, i) => {
      v.copy(axes[i] ?? v).applyQuaternion(inverse);
      const [x, y] = [centre + v.x * length, centre - v.y * length];
      g.querySelector("line")?.setAttribute("x2", String(x));
      g.querySelector("line")?.setAttribute("y2", String(y));
      g.querySelector("text")?.setAttribute("x", String(centre + v.x * (length + 7)));
      g.querySelector("text")?.setAttribute("y", String(centre - v.y * (length + 7) + 3));
    });
  });
  return null;
}
