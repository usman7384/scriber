import type { ReactNode } from "react";

const hex = "M8 1.5 14 5v6l-6 3.5L2 11V5z";

const glyphs = {
  mark: (
    <>
      <rect x="2" y="2" width="12" height="12" rx="1" />
      <circle cx="10" cy="6" r="2" />
      <path d="M2 10h4v4" />
    </>
  ),
  search: (
    <>
      <circle cx="7" cy="7" r="4.5" />
      <path d="m10.5 10.5 3.5 3.5" />
    </>
  ),
  part: (
    <>
      <path d={hex} />
      <path d="M2 5l6 3.5L14 5M8 8.5v6" />
    </>
  ),
  face: (
    <>
      <path d={hex} opacity=".45" />
      <path d="M2 5l6 3.5L14 5 8 1.5z" />
    </>
  ),
  edges: (
    <>
      <path d="M2 5l6 3.5L14 5M8 8.5v6" />
      <path d={hex} strokeDasharray="2 2" />
    </>
  ),
  dimension: <path d="M2 4v8M14 4v8M2 8h12M4 6.5 2 8l2 1.5M12 6.5 14 8l-2 1.5" />,
  document: <path d="M4 1.5h5.5L13 5v9.5H4zM9.5 1.5V5H13M6 8.5h5M6 11h5" />,
  assumption: (
    <>
      <circle cx="8" cy="8" r="6" strokeDasharray="2.2 1.8" />
      <path d="M8 5v3.5M8 11v.01" />
    </>
  ),
  pass: (
    <>
      <circle cx="8" cy="8" r="6" />
      <path d="m5.5 8.2 1.8 1.8 3.3-3.6" />
    </>
  ),
  warn: <path d="M8 2 14.5 13.5h-13zM8 6.5v3M8 11.6v.01" />,
  fail: <path d="M5.5 1.5h5l4 4v5l-4 4h-5l-4-4v-5zM6 6l4 4m0-4-4 4" />,
  agent: (
    <>
      <circle cx="8" cy="8" r="2.5" />
      <path d="M8 1.5v3M8 11.5v3M1.5 8h3M11.5 8h3" />
    </>
  ),
  attach: (
    <path d="M10.5 4.5 5.8 9.2a1.5 1.5 0 0 0 2.1 2.1l5-5a3 3 0 0 0-4.2-4.2l-5 5a4.5 4.5 0 0 0 6.4 6.4l4.2-4.2" />
  ),
  send: <path d="M8 13V3M4 7l4-4 4 4" />,
  deliver: <path d="M8 2v8M5 5l3-3 3 3M3 9v4.5h10V9" />,
  eye: (
    <>
      <path d="M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z" />
      <circle cx="8" cy="8" r="2" />
    </>
  ),
  eyeOff: (
    <path d="M2 2l12 12M6.6 3.7A6 6 0 0 1 8 3.5c4 0 6.5 4.5 6.5 4.5a11 11 0 0 1-1.9 2.4M10.1 11.9A6 6 0 0 1 8 12.5C4 12.5 1.5 8 1.5 8a11 11 0 0 1 2.6-3" />
  ),
  chevronDown: <path d="m4 6 4 4 4-4" />,
  chevronUp: <path d="m4 10 4-4 4 4" />,
  chevronLeft: <path d="m10 4-4 4 4 4" />,
  chevronRight: <path d="m6 4 4 4-4 4" />,
  process: <path d="M6 1.5h4v6l-2 3-2-3zM3 14.5h10" />,
  clock: (
    <>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v3l2 1.5" />
    </>
  ),
  grid: <path d="M2 2h5v5H2zM9 2h5v5H9zM2 9h5v5H2zM9 9h5v5H9z" />,
  globe: (
    <>
      <circle cx="8" cy="8" r="6" />
      <path d="M2 8h12M8 2c2 2 2 10 0 12M8 2c-2 2-2 10 0 12" />
    </>
  ),
  plus: <path d="M8 3v10M3 8h10" />,
  close: <path d="m4 4 8 8m0-8-8 8" />,
  undo: <path d="M5 4 2 7l3 3M2 7h7.5a4 4 0 0 1 0 8H7" />,
  image: (
    <>
      <rect x="2" y="3" width="12" height="10" rx="1" />
      <path d="m2 11 3.5-3.5 3 3 2-2L14 12" />
    </>
  ),
  mesh: <path d="M8 2 14 6 11.5 13.5h-7L2 6zM8 2v6l6-2M8 8 2 6M8 8l-3.5 5.5M8 8l3.5 5.5" />,
  trash: <path d="M2.5 4h11M6 4V2.5h4V4M4 4l.7 10h6.6L12 4M6.8 6.5v5M9.2 6.5v5" />,
  settings: (
    <>
      <circle cx="8" cy="8" r="2.2" />
      <path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" />
    </>
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof glyphs;

interface Props {
  name: IconName;
  size?: number;
  className?: string;
}

export function Icon({ name, size = 16, className }: Props) {
  return (
    <svg
      className={className ? `ui-icon ${className}` : "ui-icon"}
      viewBox="0 0 16 16"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      data-icon={name}
    >
      {glyphs[name]}
    </svg>
  );
}
