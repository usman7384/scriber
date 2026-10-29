import type { MouseEvent, RefObject } from "react";
import type { Version } from "../api";
import { useT } from "../i18n";
import { Icon } from "../ui/icons";
import { Popover } from "../ui/Popover";
import { Provenance } from "../ui/Provenance";
import { Status } from "../ui/Status";
import { severityState } from "../viewer/severity";
import { PrintCheck } from "./PrintCheck";
import type { PrintState } from "./usePrintCheck";
import { tally } from "./tally";

interface Props {
  version: Pick<Version, "checks" | "findings" | "params">;
  print?: PrintState | undefined;
  pill?: RefObject<HTMLButtonElement | null>;
  onFinding?: (index: number) => void;
  onParam?: (name: string) => void;
}

// The top-bar pill and its one popover: requirements, manufacturability, assumptions and printability.
export function ChecksPopover({ version, print, pill, onFinding, onParam }: Props) {
  const t = useT();
  const f = t.findings;
  const n = tally(version);
  const assumed = version.params.filter((p) => p.provenance.source === "default");
  const pick = (then: () => void) => (e: MouseEvent<HTMLElement>) => {
    e.currentTarget.closest<HTMLElement>("[popover]")?.hidePopover();
    then();
  };
  return (
    <Popover
      label={f.title}
      trigger={(p) => (
        <button
          {...p}
          ref={(el) => {
            p.ref.current = el;
            if (pill) pill.current = el;
          }}
          type="button"
          className="ws-pill"
          aria-label={f.pill(n.pass, n.warn, n.fail, n.assumed)}
        >
          <Status state="pass">{n.pass}</Status>
          {n.warn > 0 && <Status state="warn">{n.warn}</Status>}
          {n.fail > 0 && <Status state="fail">{n.fail}</Status>}
          {n.assumed > 0 && (
            <span className="ws-assumed">
              <Icon name="assumption" size={14} />
              <span className="ws-wide">{f.assumed(n.assumed)}</span>
            </span>
          )}
        </button>
      )}
    >
      <div className="ws-checks">
        <section className="ws-check-group" aria-label={f.region}>
          <h3 className="eyebrow">{f.checks}</h3>
          {version.checks.length === 0 && <p className="ws-muted">{f.noChecks}</p>}
          <ul className="ws-check-list">
            {version.checks.map((c, i) => (
              <li key={i}>
                <Status state={c.passed ? "pass" : "fail"} />
                <span>{c.description}</span>
                {c.actual !== null && <span className="mono ws-muted">{String(c.actual)}</span>}
              </li>
            ))}
          </ul>
          <h3 className="eyebrow">{f.dfm}</h3>
          {version.findings.length === 0 && <p className="ws-muted">{f.none}</p>}
          <ul className="ws-check-list">
            {version.findings.map((x, i) => (
              <li key={i}>
                <button type="button" className="ws-row-button" onClick={pick(() => onFinding?.(i))}>
                  <Icon
                    name={severityState(x.severity)}
                    size={14}
                    className={`ws-${severityState(x.severity)}`}
                  />
                  <span>{x.message}</span>
                </button>
              </li>
            ))}
          </ul>
          {version.findings.length === 0 && version.checks.length === 0 && (
            <p className="ws-muted">{f.noRules}</p>
          )}
        </section>
        {assumed.length > 0 && (
          <section className="ws-check-group">
            <h3 className="eyebrow">{t.editor.assumptions}</h3>
            <ul className="ws-check-list">
              {assumed.map((p) => (
                <li key={p.name}>
                  <button type="button" className="ws-row-button" onClick={pick(() => onParam?.(p.name))}>
                    <Provenance source="default" />
                    <span>{p.label}</span>
                    <span className="mono ws-muted">
                      {p.value.toFixed(2)} {p.unit}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
        {print && <PrintCheck print={print} />}
      </div>
    </Popover>
  );
}
