import { useRef, type ComponentProps } from "react";
import { api, type Process } from "../api";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Icon } from "../ui/icons";
import { QuantityText } from "./QuantityText";
import "./agent.css";

export interface Target {
  id: string;
  label: string;
  kind: "part" | "face";
}

interface FieldProps extends ComponentProps<"textarea"> {
  id: string;
  label: string;
  value: string;
}

// A mirror under the transparent textarea paints the recognised quantities.
export function QuantityField({ id, label, value, ...rest }: FieldProps) {
  const marks = useRef<HTMLDivElement>(null);
  return (
    <div className="agent-field">
      <label className="agent-sr" htmlFor={id}>
        {label}
      </label>
      <div ref={marks} className="agent-field-marks" aria-hidden="true">
        <QuantityText text={value} mark />
        {"\n"}
      </div>
      <textarea
        id={id}
        value={value}
        onScroll={(e) => {
          if (marks.current) marks.current.scrollTop = e.currentTarget.scrollTop;
        }}
        {...rest}
      />
    </div>
  );
}

export function ProcessChip({ value, onChange }: { value: Process; onChange: (p: Process) => void }) {
  const t = useT();
  return (
    <span className="agent-chip agent-process">
      <Icon name="process" size={14} />
      <select
        aria-label={t.prompt.process}
        value={value}
        onChange={(e) => onChange(e.target.value as Process)}
      >
        {Object.entries(t.processes).map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
    </span>
  );
}

export function SourceChips({ projectId, ids }: { projectId: string; ids: string[] }) {
  const t = useT();
  const context = useResource(`agent-sources:${projectId}:${ids.join()}`, () =>
    ids.length ? api.context(projectId) : Promise.resolve(undefined),
  );
  const files = context.data?.files.filter((f) => ids.includes(f.id)) ?? [];
  if (files.length === 0) return null;
  return (
    <ul className="agent-chips" aria-label={t.prompt.context}>
      {files.map((f) => (
        <li key={f.id} className="agent-chip">
          <Icon name="document" size={14} />
          <span className="agent-chip-text" title={f.name}>
            {f.name}
          </span>
          {f.status === "processed" && <Icon name="pass" size={12} className="agent-pass" />}
        </li>
      ))}
    </ul>
  );
}

export function TargetChip({ target, onClear }: { target?: Target | undefined; onClear: () => void }) {
  const t = useT();
  return (
    <span className="chip agent-target" data-empty={!target || undefined}>
      <Icon name={target?.kind ?? "part"} size={14} />
      <span className="agent-sr">{t.refine.target} </span>
      <span className="agent-chip-text">{target?.label ?? t.refine.whole}</span>
      {target && (
        <button type="button" className="agent-chip-x" aria-label={t.clear} onClick={onClear}>
          <Icon name="close" size={12} />
        </button>
      )}
    </span>
  );
}
