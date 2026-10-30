export type Point = [number, number, number];

const tilt = 0.38;

// Fibonacci lattice: near-even dots on a unit sphere.
export const lattice = (n: number): Point[] =>
  Array.from({ length: n }, (_, i) => {
    const y = 1 - (2 * i + 1) / n;
    const r = Math.sqrt(1 - y * y);
    const t = i * Math.PI * (3 - Math.sqrt(5));
    return [Math.cos(t) * r, y, Math.sin(t) * r];
  });

export const turn = ([x, y, z]: Point, spin: number): Point => {
  const [sx, cx] = [Math.sin(spin), Math.cos(spin)];
  const [rx, rz] = [x * cx + z * sx, z * cx - x * sx];
  const [st, ct] = [Math.sin(tilt), Math.cos(tilt)];
  return [rx, y * ct - rz * st, y * st + rz * ct];
};
