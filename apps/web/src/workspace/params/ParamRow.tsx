import type { KeyboardEvent } from "react";
import { Link } from "react-router";
import type { Param } from "../../api";
import { useT } from "../../i18n";
import { Popover } from "../../ui/Popover";
import { Provenance } from "../../ui/Provenance";
import { fixed, keyStep, numberOf, outOfBounds, sliderRange } from "./bounds";

interface Props {
  param: Param;
  draft: string;
  pinned?: boolean;
  sourcesHref?: string | undefined;
  onChange: (draft: string) => void;
}

// Label, provenance monogram, value field with its unit, and a hairline scrub track with the bounds under it.
export function ParamRow({ param, draft, pinned, sourcesHref, onChange }: Props) {
  const t = useT();
  const range = sliderRange(param);
  const id = `param-${param.name}`;
  const value = numberOf(draft);
  const edited = Number.isFinite(value) && value !== param.value;
  const bound = Number.isFinite(value) ? outOfBounds(param, value) : undefined;
  // The slider also takes Left / Right; in the field those keys keep moving the caret.
  const step = (e: KeyboardEvent<HTMLInputElement>, slider: boolean) => {
    const signs: Record<string, number> = { ArrowUp: 1, ArrowDown: -1 };
    if (slider) Object.assign(signs, { ArrowRight: 1, ArrowLeft: -1 });
    const sign = signs[e.key];
    if (!sign) return;
    e.preventDefault();
    const next = +((Number.isFinite(value) ? value : param.value) + sign * keyStep(range, e)).toFixed(6);
    onChange(String(slider ? Math.min(range[1], Math.max(range[0], next)) : next));
  };
  const note = bound
    ? t.params[bound.side](fixed(bound.limit, param.unit))
    : edited
      ? t.params.was(fixed(param.value, param.unit))
      : pinned && param.provenance.quote
        ? `“${param.provenance.quote}”`
        : "";
  return (
    <div
      className="param ws-param"
      data-edited={edited || undefined}
      data-pinned={pinned || undefined}
      data-invalid={bound ? true : undefined}
    >
      <label htmlFor={id} title={param.description}>
        {param.label}
      </label>
      <Source param={param} sourcesHref={sourcesHref} />
      <span className="ws-param-value">
        <input
          id={id}
          type="number"
          step="any"
          value={draft}
          aria-invalid={bound ? true : undefined}
          aria-describedby={note ? `${id}-note` : undefined}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => step(e, false)}
        />
        <span className="unit">{param.unit}</span>
      </span>
      <input
        type="range"
        className="ws-param-track"
        aria-label={t.params.slider(param.label)}
        min={range[0]}
        max={range[1]}
        step={0.1}
        value={Number.isFinite(value) ? value : param.value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => step(e, true)}
      />
      <span className="ws-param-meta mono">
        <span>{range[0]}</span>
        <span id={`${id}-note`} className="ws-param-note">
          {note}
        </span>
        <span>{range[1]}</span>
      </span>
    </div>
  );
}

function Source({ param, sourcesHref }: { param: Param; sourcesHref?: string | undefined }) {
  const t = useT();
  const { source, ref, quote } = param.provenance;
  const name = t.source[source] ?? source;
  return (
    <Popover
      label={t.params.sourceTitle}
      align="end"
      trigger={(p) => (
        <button {...p} type="button" className="ws-prov" aria-label={t.params.source(param.label, name)}>
          <Provenance source={source} />
        </button>
      )}
    >
      <div className="ws-source">
        <span className="eyebrow">{t.params.sourceTitle}</span>
        <strong>{name}</strong>
        {quote ? <q>{quote}</q> : <span>{t.params.noQuote}</span>}
        {ref && <code>{ref}</code>}
        {sourcesHref && (source === "document" || source === "rule") && (
          <Link to={sourcesHref}>{t.params.openSources}</Link>
        )}
      </div>
    </Popover>
  );
}
