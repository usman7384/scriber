import { useEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { Link } from "react-router";
import { apiUrl } from "../api";
import { byNewest } from "../format";
import { useT } from "../i18n";
import { Icon } from "../ui/icons";
import { clamp, drift, range, stepFor, turnFor } from "./orbit";
import type { Part } from "./PartsGrid";

const GAP = 132;
const IDLE = 0.25;
const TICK_MS = 100;
const PAUSE_MS = 4000;
// Wheel turns the horizon only where Home fits the screen; elsewhere the page scrolls as usual.
const TURNS_ON_WHEEL = "(min-width: 721px) and (min-height: 640px)";
const OWN_SCROLL = "textarea, select, dialog, .agent-stream";

// Past parts ride the horizon; scrolling turns it, and it drifts on its own to show there is more.
export function PartsOrbit({ label, parts, empty }: { label: string; parts: Part[]; empty: string }) {
  const t = useT().home;
  const section = useRef<HTMLElement>(null);
  const [sort, setSort] = useState<"newest" | "name">("newest");
  const shown =
    sort === "newest" ? byNewest(parts) : [...parts].sort((a, b) => a.title.localeCompare(b.title));
  const bring = useOrbit(section, shown.length);
  return (
    <section ref={section} className="orbit">
      <div className="home-horizon" aria-hidden="true" />
      {shown.length === 0 ? (
        <p className="orbit-empty">{empty}</p>
      ) : (
        <ul className="orbit-ring" aria-label={label}>
          {shown.map((p, i) => (
            <li
              key={p.id}
              className="orbit-item"
              style={{ "--i": i } as CSSProperties}
              onFocus={() => bring(i)}
            >
              <div className="orbit-thumb">
                {p.thumbnail ? <img src={apiUrl(p.thumbnail)} alt="" /> : <Icon name="part" size={20} />}
              </div>
              {p.href ? (
                <Link to={p.href} className="orbit-title card-title part-link">
                  {p.title}
                </Link>
              ) : (
                <span className="orbit-title card-title">{p.title}</span>
              )}
              <div className="orbit-meta">
                {p.meta}
                {p.action}
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="orbit-caption">
        <select
          aria-label={t.sort}
          value={sort}
          onChange={(e) => setSort(e.target.value as "newest" | "name")}
        >
          {(Object.keys(t.sorts) as ("newest" | "name")[]).map((s) => (
            <option key={s} value={s}>
              {t.sorts[s]}
            </option>
          ))}
        </select>
        <span>{t.turn}</span>
      </div>
    </section>
  );
}

// Writes --spin and --step on the section; returns a function that turns part i to the top.
function useOrbit(section: RefObject<HTMLElement | null>, count: number) {
  const state = useRef({ spin: 0, velocity: -IDLE, radius: 1, step: 1, paused: 0 });
  useEffect(() => {
    const el = section.current;
    const horizon = el?.querySelector<HTMLElement>(".home-horizon");
    if (!el || !horizon) return;
    const s = state.current;
    const apply = () => {
      el.style.setProperty("--spin", `${s.spin}deg`);
      el.style.setProperty("--step", `${s.step}deg`);
    };
    const turn = (px: number) => {
      s.spin = clamp(s.spin + turnFor(px, s.radius), range(count, s.step));
      s.paused = Date.now() + PAUSE_MS;
      apply();
    };
    const measure = () => {
      s.radius = horizon.offsetWidth / 2;
      s.step = stepFor(GAP, s.radius);
      s.spin = clamp(s.spin, range(count, s.step));
      apply();
    };
    const resize = new ResizeObserver(measure);
    resize.observe(horizon);
    measure();

    const wheel = (e: WheelEvent) => {
      if (!matchMedia(TURNS_ON_WHEEL).matches) return;
      if (e.target instanceof Element && e.target.closest(OWN_SCROLL)) return;
      e.preventDefault();
      turn(e.deltaY);
    };
    let touchX: number | undefined;
    const touchStart = (e: TouchEvent) => (touchX = e.touches[0]?.clientX);
    const touchMove = (e: TouchEvent) => {
      const x = e.touches[0]?.clientX;
      if (x === undefined || touchX === undefined) return;
      turn(touchX - x);
      touchX = x;
    };
    addEventListener("wheel", wheel, { passive: false });
    el.addEventListener("touchstart", touchStart, { passive: true });
    el.addEventListener("touchmove", touchMove, { passive: true });

    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    // A timer, not requestAnimationFrame: the drift is a fraction of a degree a second and needs few frames.
    const timer = still
      ? undefined
      : setInterval(() => {
          if (Date.now() < s.paused) return;
          Object.assign(s, drift(s.spin, s.velocity, TICK_MS / 1000, range(count, s.step)));
          apply();
        }, TICK_MS);
    return () => {
      resize.disconnect();
      removeEventListener("wheel", wheel);
      el.removeEventListener("touchstart", touchStart);
      el.removeEventListener("touchmove", touchMove);
      clearInterval(timer);
    };
  }, [section, count]);

  return (i: number) => {
    const s = state.current;
    s.spin = clamp(-i * s.step, range(count, s.step));
    s.paused = Date.now() + PAUSE_MS;
    section.current?.style.setProperty("--spin", `${s.spin}deg`);
  };
}
