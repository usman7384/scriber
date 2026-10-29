import type { Page } from "@playwright/test";

export type Vec = [number, number, number];

export interface Pose {
  forward: Vec;
  up: Vec;
  position: Vec;
  target: Vec;
}

// Reads the live three.js camera from react-three-fiber's root registry, through the module the dev server already loaded.
export const cameraPose = (page: Page) =>
  page.evaluate(async (): Promise<Pose> => {
    interface V3 {
      clone(): V3;
      set(x: number, y: number, z: number): V3;
      applyQuaternion(q: unknown): V3;
      toArray(): Vec;
    }
    interface Camera {
      position: V3;
      quaternion: unknown;
      getWorldDirection(into: V3): V3;
    }
    type State = { camera: Camera; controls: { target: V3 } | null };
    type Roots = Map<Element, { store: { getState(): State } }>;
    const url = performance
      .getEntriesByType("resource")
      .map((e) => e.name)
      .find((n) => n.includes("/@react-three_fiber.js"));
    const canvas = document.querySelector(".viewer canvas");
    if (!url || !canvas) throw new Error("viewer not loaded");
    const { _roots } = (await import(url)) as { _roots: Roots };
    const state = _roots.get(canvas)?.store.getState();
    if (!state?.controls) throw new Error("no camera controls");
    const { camera } = state;
    return {
      forward: camera.getWorldDirection(camera.position.clone()).toArray(),
      up: camera.position.clone().set(0, 1, 0).applyQuaternion(camera.quaternion).toArray(),
      position: camera.position.toArray(),
      target: state.controls.target.toArray(),
    };
  });

export interface Probe {
  // CAD-mm bounding box of each part mesh, by glTF node name
  parts: Record<string, { min: Vec; max: Vec }>;
  // page coordinates of the given CAD points under the live camera
  screen: [number, number][];
}

export const probe = (page: Page, points: Vec[] = []) =>
  page.evaluate(async (points): Promise<Probe> => {
    interface V3 {
      x: number;
      y: number;
      z: number;
      clone(): V3;
      set(x: number, y: number, z: number): V3;
      project(camera: unknown): V3;
    }
    interface Obj {
      isMesh?: boolean;
      name: string;
      geometry?: { boundingBox: { min: V3; max: V3 } | null };
      traverse(fn: (o: Obj) => void): void;
    }
    type State = { camera: { position: V3 }; scene: Obj };
    type Roots = Map<Element, { store: { getState(): State } }>;
    const url = performance
      .getEntriesByType("resource")
      .map((e) => e.name)
      .find((n) => n.includes("/@react-three_fiber.js"));
    const canvas = document.querySelector(".viewer canvas");
    if (!url || !canvas) throw new Error("viewer not loaded");
    const { _roots } = (await import(url)) as { _roots: Roots };
    const state = _roots.get(canvas)?.store.getState();
    if (!state) throw new Error("no viewer state");
    const parts: Probe["parts"] = {};
    const arr = (v: V3): Vec => [v.x, v.y, v.z];
    state.scene.traverse((o) => {
      const box = o.isMesh && o.name ? o.geometry?.boundingBox : null;
      if (!box) return;
      const seen = parts[o.name];
      parts[o.name] = seen
        ? {
            min: seen.min.map((v, i) => Math.min(v, arr(box.min)[i] ?? v)) as Vec,
            max: seen.max.map((v, i) => Math.max(v, arr(box.max)[i] ?? v)) as Vec,
          }
        : { min: arr(box.min), max: arr(box.max) };
    });
    const rect = canvas.getBoundingClientRect();
    const screen = points.map(([x, y, z]): [number, number] => {
      const p = state.camera.position.clone().set(x, y, z).project(state.camera);
      return [rect.left + ((p.x + 1) / 2) * rect.width, rect.top + ((1 - p.y) / 2) * rect.height];
    });
    return { parts, screen };
  }, points);

export const centre = (b: { min: Vec; max: Vec }): Vec =>
  b.min.map((v, i) => (v + (b.max[i] ?? v)) / 2) as Vec;

export const size = (b: { min: Vec; max: Vec }): Vec => b.min.map((v, i) => (b.max[i] ?? v) - v) as Vec;

export const round = (v: Vec, digits = 3): Vec => v.map((x) => +x.toFixed(digits) + 0) as Vec;

export const near = (a: Vec, b: Vec, tol: number) => a.every((x, i) => Math.abs(x - (b[i] ?? NaN)) <= tol);

export const distance = (a: Vec, b: Vec) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

export interface Hole {
  enclosed: boolean;
  centre: [number, number];
  diameterPx: number;
  plateLeftPx: number;
  plateRightPx: number;
}

// Flood-fills the see-through pixels under a screen point of the viewer canvas: a through-hole is an enclosed transparent region.
export const holeUnder = (page: Page, at: { x: number; y: number }) =>
  page.evaluate((at): Hole | null => {
    const canvas = document.querySelector<HTMLCanvasElement>(".viewer canvas");
    const copy = document.createElement("canvas");
    const ctx = copy.getContext("2d");
    if (!canvas || !ctx) throw new Error("viewer not loaded");
    const { width: w, height: h } = canvas;
    copy.width = w;
    copy.height = h;
    ctx.drawImage(canvas, 0, 0);
    const alpha = ctx.getImageData(0, 0, w, h).data.filter((_, i) => i % 4 === 3);
    const rect = canvas.getBoundingClientRect();
    const sx = Math.round(((at.x - rect.left) * w) / rect.width);
    const sy = Math.round(((at.y - rect.top) * h) / rect.height);
    const solid = (x: number, y: number) => (alpha[y * w + x] ?? 0) > 128;
    if (solid(sx, sy)) return null;
    const limit = Math.min(w, h) / 4;
    const seen = new Set([sy * w + sx]);
    const queue = [[sx, sy]];
    let enclosed = true;
    let cx = 0;
    let cy = 0;
    for (let i = 0; i < queue.length; i++) {
      const [x = 0, y = 0] = queue[i] ?? [];
      cx += x;
      cy += y;
      for (const [nx, ny] of [
        [x + 1, y],
        [x - 1, y],
        [x, y + 1],
        [x, y - 1],
      ] as const) {
        if (Math.hypot(nx - sx, ny - sy) > limit) enclosed = false;
        else if (!seen.has(ny * w + nx) && !solid(nx, ny)) {
          seen.add(ny * w + nx);
          queue.push([nx, ny]);
        }
      }
    }
    const row = Math.round(cy / queue.length);
    const solidCols = Array.from({ length: w }, (_, x) => x).filter((x) => solid(x, row));
    return {
      enclosed,
      centre: [((cx / queue.length) * rect.width) / w + rect.left, (row * rect.height) / h + rect.top],
      diameterPx: (2 * Math.sqrt(queue.length / Math.PI) * rect.width) / w,
      plateLeftPx: ((solidCols[0] ?? 0) * rect.width) / w + rect.left,
      plateRightPx: ((solidCols.at(-1) ?? 0) * rect.width) / w + rect.left,
    };
  }, at);
