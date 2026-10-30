import { useId, useRef, useState, type KeyboardEvent } from "react";
import { apiUrl, type Version } from "../api";
import { useLang, useT } from "../i18n";
import { Button } from "../ui/Button";
import { Icon } from "../ui/icons";
import { fixed, paramDiff, versionBefore } from "./diff";
import { ago, byAgent } from "./steps";

interface Props {
  versions: Version[];
  shown: number;
  onShow: (n: number) => void;
  // Restores that version as a new one.
  onRestore: (n: number) => void;
  // The shown version and the one it is compared with; undefined when the comparison ends.
  onCompare?: (pair?: [number, number]) => void;
}

export function VersionScrubber({ versions, shown, onShow, onRestore, onCompare }: Props) {
  const t = useT();
  const [lang] = useLang();
  const v = t.agent.versions;
  const id = useId();
  const lane = useRef<HTMLOListElement>(null);
  const [comparing, setComparing] = useState(false);
  const [other, setOther] = useState<number>();
  const sorted = [...versions].sort((a, b) => a.number - b.number);
  const latest = sorted.at(-1);
  const current = sorted.find((x) => x.number === shown) ?? latest;
  if (!latest || !current) return null;

  const at = sorted.indexOf(current);
  const go = (n?: number) => {
    if (n === undefined) return;
    onShow(n);
    lane.current?.querySelector<HTMLButtonElement>(`[data-n="${n}"]`)?.focus();
  };
  const keys = (e: KeyboardEvent) => {
    const steps: Record<string, number> = {
      "[": at - 1,
      ArrowLeft: at - 1,
      "]": at + 1,
      ArrowRight: at + 1,
      Home: 0,
      End: sorted.length - 1,
    };
    const to = steps[e.key];
    if (to === undefined) return;
    e.preventDefault();
    go(sorted[to]?.number);
  };
  const pick = (n: number) => {
    if (!comparing) return onShow(n);
    if (n === current.number) return;
    setOther(n);
    onCompare?.([current.number, n]);
  };
  const toggleCompare = () => {
    setComparing(!comparing);
    setOther(undefined);
    if (comparing) onCompare?.(undefined);
  };
  const against = comparing ? sorted.find((x) => x.number === other) : undefined;
  const diff = against && paramDiff(current.params, against.params);

  return (
    <div className="agent-scrub" role="group" aria-label={v.region}>
      {current !== latest && (
        <div className="agent-scrub-banner">
          <Icon name="eye" size={14} />
          <span>{v.viewing(current.number)}</span>
          <Button
            variant="primary"
            icon="undo"
            aria-label={v.restoreLabel(current.number, latest.number + 1)}
            onClick={() => onRestore(current.number)}
          >
            {v.restoreAs(latest.number + 1)}
          </Button>
          <Button variant="ghost" onClick={() => onShow(latest.number)}>
            {v.back(latest.number)}
          </Button>
        </div>
      )}
      {diff && against && (
        <table className="agent-diff" aria-label={v.diff}>
          <thead>
            <tr>
              <th>{v.param}</th>
              <th className="mono">v{current.number}</th>
              <th className="mono">v{against.number}</th>
            </tr>
          </thead>
          <tbody>
            {diff.length === 0 && (
              <tr>
                <td colSpan={3}>{v.same}</td>
              </tr>
            )}
            {diff.map((c) => (
              <tr key={c.name}>
                <td>{c.label}</td>
                <td className="mono">{fixed(c.from)}</td>
                <td className="mono">
                  {fixed(c.to)} <span className="agent-meta">{c.unit}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="agent-scrub-row">
        <Icon name="clock" className="agent-muted" />
        <ol ref={lane} className="agent-lane" aria-label={v.list}>
          {[...sorted].reverse().map((x) => {
            const before = versionBefore(sorted, x.number);
            const changed = before ? paramDiff(before.params, x.params).length : x.params.length;
            const card = `${id}-v${x.number}`;
            return (
              <li
                key={x.number}
                className="agent-tick-item"
                data-agent={byAgent(x) || undefined}
                data-other={x.number === against?.number || undefined}
              >
                <button
                  type="button"
                  className="agent-tick"
                  data-n={x.number}
                  tabIndex={x === current ? 0 : -1}
                  aria-current={x === current}
                  aria-describedby={card}
                  onClick={() => pick(x.number)}
                  onKeyDown={keys}
                >
                  <span className="agent-tick-mark" aria-hidden="true" />
                  <strong>v{x.number}</strong>
                </button>
                <div id={card} className="agent-tick-card">
                  {x.thumbnail_url && <img src={apiUrl(x.thumbnail_url)} alt="" width={96} height={96} />}
                  <span className="mono">
                    v{x.number} · {t.origin[x.origin] ?? x.origin}
                  </span>
                  {x.prompt && <span className="agent-tick-prompt">{x.prompt}</span>}
                  <span className="agent-meta">
                    {ago(x.created, lang)} · {t.agent.stream.changed(changed)}
                  </span>
                </div>
              </li>
            );
          })}
        </ol>
        <span className="agent-meta agent-scrub-label">
          {comparing && !against
            ? v.pick
            : t.agent.activity.latest(
                current.number,
                t.origin[current.origin] ?? current.origin,
                ago(current.created, lang),
              )}
        </span>
        <Button variant="ghost" aria-pressed={comparing} onClick={toggleCompare}>
          {v.compare}
        </Button>
      </div>
    </div>
  );
}
