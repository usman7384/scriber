import type { Param } from "../api";

function sliderRange(p: Param): [number, number] {
  const span = Math.abs(p.value) || 10;
  return [p.min ?? (p.value >= 0 ? Math.max(0, p.value - span) : p.value - span), p.max ?? p.value + span];
}

interface Props {
  param: Param;
  draft: string;
  onChange: (draft: string) => void;
}

export function ParamRow({ param, draft, onChange }: Props) {
  const [lo, hi] = sliderRange(param);
  const id = `param-${param.name}`;
  const { source, ref, quote } = param.provenance;
  return (
    <div className="param">
      <label htmlFor={id} title={param.description}>
        {param.label}
      </label>
      <span className="provenance" tabIndex={0} aria-describedby={`${id}-src`}>
        {source}
        <span role="tooltip" id={`${id}-src`}>
          {quote ? `“${quote}”` : "No quote"}
          {ref && <small> {ref}</small>}
        </span>
      </span>
      <input
        type="range"
        aria-label={`${param.label} slider`}
        min={lo}
        max={hi}
        step={0.1}
        value={Number(draft) || param.value}
        onChange={(e) => onChange(e.target.value)}
      />
      <input id={id} type="number" step="any" value={draft} onChange={(e) => onChange(e.target.value)} />
      <span className="unit">{param.unit}</span>
    </div>
  );
}
