export type Range = readonly [number, number];

const degrees = (radians: number) => (radians * 180) / Math.PI;

// The angle that moves a point on the orbit by `gap` px along the arc.
export const stepFor = (gap: number, radius: number) => degrees(Math.atan2(gap, radius));

// Spin 0 puts the newest part on top; the most negative spin puts the oldest there.
export const range = (count: number, step: number): Range => [
  -(Math.max(count, 1) - 1) * step - step / 2,
  step / 2,
];

export const clamp = (spin: number, [min, max]: Range) => Math.min(max, Math.max(min, spin));

// A wheel or swipe of `px` turns the horizon by the same arc length.
export const turnFor = (px: number, radius: number) => -degrees(px / radius);

// Idle drift that reverses at either end, so every part comes round in time.
export function drift(spin: number, velocity: number, seconds: number, bounds: Range) {
  const next = spin + velocity * seconds;
  if (next <= bounds[0]) return { spin: bounds[0], velocity: Math.abs(velocity) };
  if (next >= bounds[1]) return { spin: bounds[1], velocity: -Math.abs(velocity) };
  return { spin: next, velocity };
}
