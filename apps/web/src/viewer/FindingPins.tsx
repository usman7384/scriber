import { Html } from "@react-three/drei";
import type { KeyboardEvent } from "react";
import type { Finding } from "../api";
import { Icon } from "../ui/icons";
import { severityState } from "./severity";
import { ownPointer } from "./stop";

export interface PinText {
  name: (f: Finding) => string;
  detail: (f: Finding) => string | undefined;
  rule: (f: Finding) => string;
  ask: string;
  showRule: string;
}

export interface PinActions {
  onSelect: (index: number) => void;
  onAsk: (f: Finding) => void;
  onShowRule: (f: Finding) => void;
}

interface Props {
  findings: Finding[];
  text: PinText;
  selected?: number | undefined;
  actions?: PinActions | undefined;
}

// A glyph at the finding's point with a dashed ring; its callout opens on hover, focus or selection.
// drei Html renders into its own React root, so text and callbacks come in as props.
export function FindingPins({ findings, text, selected, actions }: Props) {
  return findings.flatMap((f, i) => {
    if (!f.location) return [];
    const select = () => actions?.onSelect(i);
    const key = (e: KeyboardEvent) => e.target === e.currentTarget && e.key === "Enter" && select();
    const detail = text.detail(f);
    return (
      <Html key={i} position={f.location.point} center className="ws-pin-anchor" zIndexRange={[400, 201]}>
        <div
          role="group"
          tabIndex={0}
          className="ws-pin"
          data-finding={i}
          data-state={severityState(f.severity)}
          data-open={selected === i || undefined}
          aria-label={text.name(f)}
          {...ownPointer}
          onClick={(e) => {
            e.stopPropagation();
            select();
          }}
          onKeyDown={key}
        >
          <Icon name={severityState(f.severity)} size={14} />
          <div className="ws-callout">
            <div className="ws-callout-card">
              <div role="tooltip" className="ws-callout-text">
                <strong>{f.message}</strong>
                {detail && <span className="mono">{detail}</span>}
                {f.suggestion && <span>{f.suggestion}</span>}
                <span className="ws-callout-rule">{text.rule(f)}</span>
              </div>
              {actions && (
                <div className="ws-callout-actions">
                  <button type="button" className="ui-button" onClick={() => actions.onAsk(f)}>
                    {text.ask}
                  </button>
                  <button
                    type="button"
                    className="ui-button"
                    data-variant="ghost"
                    onClick={() => actions.onShowRule(f)}
                  >
                    {text.showRule}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </Html>
    );
  });
}
