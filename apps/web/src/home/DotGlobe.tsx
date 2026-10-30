import { useEffect, useRef } from "react";
import { lattice, turn, type Point } from "./globe";

const count = 900;
const speed = 0.05;
const frameMs = 1000 / 12;

type Colours = { dot: string; node: string };

const readColours = (el: Element): Colours => {
  const style = getComputedStyle(el);
  return { dot: style.getPropertyValue("--accent"), node: style.getPropertyValue("--accent-2") };
};

function draw(ctx: CanvasRenderingContext2D, points: Point[], spin: number, colours: Colours) {
  const { width, height } = ctx.canvas;
  const radius = Math.min(width, height) * 0.46;
  const dot = 2 * devicePixelRatio;
  ctx.clearRect(0, 0, width, height);
  ctx.globalAlpha = 0.25;
  ctx.strokeStyle = colours.dot;
  ctx.beginPath();
  ctx.arc(width / 2, height / 2, radius, 0, 2 * Math.PI);
  ctx.stroke();
  points.forEach((p, i) => {
    const [x, y, z] = turn(p, spin);
    if (z < -0.2) return;
    const [px, py] = [width / 2 + x * radius, height / 2 - y * radius];
    const node = i % 29 === 0;
    ctx.globalAlpha = (node ? 0.5 : 0.12) + 0.6 * ((z + 1) / 2);
    ctx.fillStyle = node ? colours.node : colours.dot;
    if (!node) return ctx.fillRect(px - dot / 2, py - dot / 2, dot, dot);
    ctx.beginPath();
    ctx.arc(px, py, 2.2 * devicePixelRatio, 0, 2 * Math.PI);
    ctx.fill();
  });
}

export function DotGlobe() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    canvas.width = canvas.clientWidth * devicePixelRatio;
    canvas.height = canvas.clientHeight * devicePixelRatio;
    const points = lattice(count);
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let colours = readColours(canvas);
    let spin = 0;
    const theme = new MutationObserver(() => {
      colours = readColours(canvas);
      draw(ctx, points, spin, colours);
    });
    theme.observe(document.documentElement, { attributeFilter: ["data-theme"] });
    draw(ctx, points, spin, colours);
    // A timer, not requestAnimationFrame: the slow spin needs few frames, and rAF asks for one every vsync.
    const timer = still
      ? undefined
      : setInterval(() => {
          spin = (performance.now() / 1000) * speed;
          draw(ctx, points, spin, colours);
        }, frameMs);
    return () => {
      clearInterval(timer);
      theme.disconnect();
    };
  }, []);
  return <canvas ref={ref} className="dot-globe" aria-hidden />;
}
