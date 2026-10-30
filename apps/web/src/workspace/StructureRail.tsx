import { useState, type MouseEvent } from "react";
import { Link } from "react-router";
import type { Component, FeatureNode } from "../api";
import { useT } from "../i18n";
import { Icon, type IconName } from "../ui/icons";

interface Props {
  components: Component[];
  selected?: string | undefined;
  face?: { part: string; param: string } | undefined;
  hidden: string[];
  features?: Record<string, FeatureNode[]> | undefined;
  feature?: { part: string; id: string } | undefined;
  onFeature?: ((part: string, feature: FeatureNode) => void) | undefined;
  counts: { files?: number | undefined; checks: string; assumed: number };
  sourcesHref?: string | undefined;
  onSelect: (id: string | undefined) => void;
  onHidden: (ids: string[]) => void;
  onChecks: () => void;
  onAssumptions: () => void;
  onProposals: () => void;
}

// The component tree (nested by parent, Alt-click isolates), each part's features in build order, and counted
// links to what surrounds the part.
export function StructureRail(p: Props) {
  const t = useT();
  const e = t.editor;
  const [open, setOpen] = useState<string[]>([]);
  const toggle = (id: string) => setOpen((o) => (o.includes(id) ? o.filter((x) => x !== id) : [...o, id]));
  const features = (c: Component) => {
    const list = p.features?.[c.id] ?? [];
    const shown = open.includes(c.id) || p.feature?.part === c.id;
    if (list.length === 0) return null;
    return (
      <>
        <button
          type="button"
          className="ws-tree-toggle"
          aria-expanded={shown}
          aria-label={e.showFeatures(c.name)}
          onClick={() => toggle(c.id)}
        >
          <Icon name={shown ? "chevronDown" : "chevronRight"} size={12} />
        </button>
        {shown && (
          <ol className="ws-features" aria-label={e.features(c.name)}>
            {list.map((f) => (
              <li key={f.id}>
                <button
                  type="button"
                  aria-pressed={p.feature?.part === c.id && p.feature.id === f.id}
                  title={f.intent || undefined}
                  onClick={() => p.onFeature?.(c.id, f)}
                >
                  <span className="ws-label">{f.name}</span>
                  <span className="ws-id">{f.kind.replaceAll("_", " ")}</span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </>
    );
  };
  const pick = (c: Component) => (ev: MouseEvent) => {
    if (!ev.altKey) return p.onSelect(c.id === p.selected ? undefined : c.id);
    const others = p.components.filter((x) => x.id !== c.id).map((x) => x.id);
    p.onHidden(p.hidden.length === others.length && !p.hidden.includes(c.id) ? [] : others);
  };
  const branch = (parent: string | null, label?: string) => (
    <ul className="ws-tree" aria-label={label}>
      {p.components
        .filter((c) => c.parent === parent)
        .map((c) => (
          <li key={c.id}>
            <button
              type="button"
              aria-pressed={c.id === p.selected}
              data-id={c.id}
              title={c.joint ?? undefined}
              onClick={pick(c)}
            >
              <Icon name="part" size={14} />
              <span className="ws-label">{c.name}</span> <span className="ws-id mono">{c.id}</span>
            </button>
            <label className="ws-eye" title={e.isolate}>
              <input
                type="checkbox"
                aria-label={e.show(c.name)}
                checked={!p.hidden.includes(c.id)}
                onChange={(ev) =>
                  p.onHidden(ev.target.checked ? p.hidden.filter((h) => h !== c.id) : [...p.hidden, c.id])
                }
              />
              <Icon name={p.hidden.includes(c.id) ? "eyeOff" : "eye"} size={14} />
            </label>
            {features(c)}
            {p.face?.part === c.id && (
              <span className="ws-tree-face">
                <Icon name="face" size={14} />
                <span className="ws-label">{e.face}</span>
                <span className="ws-id mono">{p.face.param}</span>
              </span>
            )}
            {p.components.some((k) => k.parent === c.id) && branch(c.id)}
          </li>
        ))}
    </ul>
  );
  const link = (icon: IconName, label: string, count?: string | number) => (
    <>
      <Icon name={icon} size={14} />
      <span className="ws-label">{label}</span>
      {count !== undefined && <span className="ws-count mono">{count}</span>}
    </>
  );
  return (
    <>
      {branch(null, e.components)}
      <ul className="ws-rail-links">
        <li>
          {p.sourcesHref ? (
            <Link to={p.sourcesHref}>{link("document", e.sources, p.counts.files)}</Link>
          ) : null}
        </li>
        <li>
          <button type="button" onClick={p.onChecks}>
            {link("warn", e.checks, p.counts.checks)}
          </button>
        </li>
        <li>
          <button type="button" onClick={p.onAssumptions}>
            {link("assumption", e.assumptions, p.counts.assumed)}
          </button>
        </li>
        <li>
          <button type="button" onClick={p.onProposals}>
            {link("agent", e.proposals)}
          </button>
        </li>
      </ul>
    </>
  );
}
