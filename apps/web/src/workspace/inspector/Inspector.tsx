import type { ReactNode } from "react";
import type { Component, FaceDriver, Finding, Version } from "../../api";
import { useT } from "../../i18n";
import { Button } from "../../ui/Button";
import { Icon, type IconName } from "../../ui/icons";
import { Status } from "../../ui/Status";
import { severityState } from "../../viewer/severity";
import type { Hit } from "../../viewer/PartScene";
import { ParamPanel } from "../params/ParamPanel";
import { FaceEdit } from "./FaceEdit";
import { Facts } from "./Facts";
import { ParamTable } from "./ParamTable";

export type Selection =
  | { kind: "part"; id: string }
  | { kind: "face"; driver: FaceDriver; hit: Hit }
  | { kind: "finding"; index: number };

interface Props {
  title: string;
  version: Version;
  latest?: Version | undefined;
  components: Component[];
  selection?: Selection | undefined;
  busy?: boolean;
  sourcesHref?: string | undefined;
  proposals?: ReactNode;
  onApply?: ((values: Record<string, number>) => void) | undefined;
  onClearSelection?: () => void;
  onAsk?: ((finding: Finding) => void) | undefined;
  onBack?: () => void;
}

interface Head {
  icon: IconName;
  title: string;
  sub?: string | undefined;
}

function Rows({ rows }: { rows: [string, string | null | undefined][] }) {
  return (
    <dl className="ws-dl">
      {rows.map(([label, value]) =>
        value ? (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ) : null,
      )}
    </dl>
  );
}

// Shows what the selection needs: the whole part, a component, a picked face, a finding, or an older version.
// Each state keeps the parameters section under the same key, so drafts survive a change of selection.
export function Inspector(p: Props) {
  const t = useT();
  const { version, selection, components } = p;
  const material = components.find((c) => c.material)?.material;
  const preview = p.latest && p.latest.number !== version.number ? p.latest : undefined;
  const finding = selection?.kind === "finding" ? version.findings[selection.index] : undefined;
  const part = selection?.kind === "part" ? components.find((c) => c.id === selection.id) : undefined;
  const face = selection?.kind === "face" ? selection : undefined;
  const driven = face && version.params.find((x) => x.name === face.driver.param);

  const overview: Head = { icon: "part", title: p.title, sub: `v${version.number}` };
  let head = overview;
  let detail: ReactNode = (
    <>
      <Facts metrics={version.metrics} material={material} />
      {version.checks.length > 0 && (
        <ul className="ws-check-list">
          {version.checks.map((c, i) => (
            <li key={i}>
              <Status state={c.passed ? "pass" : "fail"} />
              <span>{c.description}</span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
  if (preview) {
    head = { icon: "clock", title: t.inspector.preview(version.number) };
    detail = (
      <>
        {p.onBack && (
          <Button variant="ghost" icon="undo" onClick={p.onBack}>
            {t.inspector.back(preview.number)}
          </Button>
        )}
        <Facts metrics={version.metrics} material={material} />
      </>
    );
  } else if (face) {
    head = { icon: "face", title: t.editor.face, sub: face.driver.part };
    detail = driven && p.onApply && (
      <FaceEdit
        key={`${face.driver.part}.${face.driver.feature}.${driven.name}`}
        driver={face.driver}
        param={driven}
        busy={p.busy ?? false}
        onApply={p.onApply}
        onClose={() => p.onClearSelection?.()}
      />
    );
  } else if (finding) {
    head = { icon: severityState(finding.severity), title: finding.message };
    detail = (
      <>
        <Rows
          rows={[
            [t.inspector.measured, finding.measured?.toFixed(2)],
            [t.inspector.required, finding.required?.toFixed(2)],
            [t.inspector.rule, `${finding.rule_id} · ${finding.binding}`],
            [t.inspector.suggestion, finding.suggestion],
          ]}
        />
        {p.onAsk && (
          <Button variant="primary" icon="agent" disabled={p.busy} onClick={() => p.onAsk?.(finding)}>
            {t.findings.ask}
          </Button>
        )}
      </>
    );
  } else if (part) {
    head = { icon: "part", title: part.name, sub: part.id };
    detail = (
      <Rows
        rows={[
          [t.editor.material, part.material ?? t.inspector.unset],
          [t.inspector.parent, components.find((c) => c.id === part.parent)?.name],
          [t.inspector.joint, part.joint],
        ]}
      />
    );
  }

  return (
    <>
      <header key="head" className="ws-insp-head">
        <Icon name={head.icon} />
        {/* The page's h1 already names the part; only a selection gets its own heading. */}
        {head === overview ? (
          <p className="ws-insp-name">{head.title}</p>
        ) : (
          <h2 className="ws-insp-name">{head.title}</h2>
        )}
        {head.sub && <span className="mono ws-faint">{head.sub}</span>}
      </header>
      <section key="detail" className="ws-insp-section">
        {detail}
      </section>
      <section key="params" className="ws-insp-section">
        {preview || !p.onApply ? (
          <ParamTable params={version.params} base={preview?.params} />
        ) : (
          <ParamPanel
            params={version.params}
            busy={p.busy ?? false}
            pinned={driven?.name}
            sourcesHref={p.sourcesHref}
            onApply={p.onApply}
          />
        )}
      </section>
      {!preview && p.proposals}
    </>
  );
}
