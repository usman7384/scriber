import { splitQuantities } from "./quantities";

export function QuantityText({ text, mark = false }: { text: string; mark?: boolean }) {
  return splitQuantities(text).map((s, i) =>
    !s.quantity ? (
      s.text
    ) : mark ? (
      <mark key={i}>{s.text}</mark>
    ) : (
      <span key={i} className="mono">
        {s.text}
      </span>
    ),
  );
}
