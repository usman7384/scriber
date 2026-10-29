import { useRef, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { useT } from "../i18n";
import { SearchButton } from "../shell/SearchButton";
import { IconButton } from "../ui/IconButton";
import { Icon } from "../ui/icons";
import "./workspace.css";

type Snap = "peek" | "half" | "full";
type Tab = "inspect" | "activity" | "versions";

const snaps: Snap[] = ["peek", "half", "full"];

interface Props {
  title: string;
  version: number;
  project?: { href: string; name: string } | undefined;
  badges?: ReactNode;
  actions: ReactNode;
  viewport: ReactNode;
  inspector: ReactNode;
  rail?: ReactNode;
  // The agent I/O: stream and status line, command bar, version scrubber.
  stream?: ReactNode;
  command?: ReactNode;
  versions?: ReactNode;
}

// Full-bleed viewport with floating panels; under 768 px the inspector, activity and versions share a bottom sheet.
export function Workspace(p: Props) {
  const t = useT();
  const e = t.editor;
  const [rail, setRail] = useState(true);
  const [inspector, setInspector] = useState(true);
  const [snap, setSnap] = useState<Snap>("peek");
  const [tab, setTab] = useState<Tab>("inspect");
  const tabs: Tab[] = p.versions ? ["inspect", "activity", "versions"] : ["inspect"];
  // Tap or Enter cycles the snap points; a drag snaps to the nearest one where it is released.
  const press = useRef<{ y: number; dragged: boolean }>({ y: 0, dragged: false });
  const step = (by: number) =>
    setSnap(snaps[(snaps.indexOf(snap) + by + snaps.length) % snaps.length] ?? "peek");
  return (
    <div
      className="ws"
      data-rail={rail ? undefined : "collapsed"}
      data-inspector={inspector ? undefined : "collapsed"}
      data-snap={snap}
      data-tab={tab}
    >
      <header className="ws-top editor-head">
        <Link to="/" className="ws-mark" aria-label={t.nav.home}>
          <Icon name="mark" size={18} />
        </Link>
        {p.project && (
          <nav aria-label={e.location} className="ws-crumbs ws-wide">
            <Link to={p.project.href}>{p.project.name}</Link>
            <span aria-hidden="true">/</span>
          </nav>
        )}
        <h1 className="ws-title">{p.title}</h1>
        <span className="badge ws-version mono">v{p.version}</span>
        {p.badges}
        <span className="ws-spacer" />
        <SearchButton label={t.nav.searchOrRun} />
        {p.actions}
      </header>
      {p.rail && (
        <aside className="ws-rail ws-float" aria-label={e.structure}>
          <div className="ws-rail-head">
            <h2 className="eyebrow ws-label">{e.structure}</h2>
            <IconButton
              icon={rail ? "chevronLeft" : "chevronRight"}
              label={rail ? e.collapseRail : e.expandRail}
              aria-expanded={rail}
              onClick={() => setRail(!rail)}
            />
          </div>
          {p.rail}
        </aside>
      )}
      {p.viewport}
      <div className="ws-dock">
        <div className="ws-sheet-head">
          <button
            type="button"
            className="ws-handle"
            aria-label={e.resize}
            onPointerDown={(ev) => {
              ev.currentTarget.setPointerCapture(ev.pointerId);
              press.current = { y: ev.clientY, dragged: false };
            }}
            onPointerUp={(ev) => {
              if (Math.abs(press.current.y - ev.clientY) < 8) return;
              press.current.dragged = true;
              const height = innerHeight - ev.clientY;
              setSnap(height > innerHeight * 0.78 ? "full" : height > innerHeight * 0.52 ? "half" : "peek");
            }}
            onClick={() => (press.current.dragged ? (press.current.dragged = false) : step(1))}
          />
          {tabs.length > 1 && (
            <div role="tablist" className="ws-tabs">
              {tabs.map((name) => (
                <button
                  key={name}
                  type="button"
                  role="tab"
                  aria-selected={tab === name}
                  onClick={() => {
                    setTab(name);
                    if (snap === "peek") setSnap("half");
                  }}
                >
                  {e.tabs[name]}
                </button>
              ))}
            </div>
          )}
        </div>
        <aside className="ws-inspector ws-float" aria-label={e.inspector} data-pane="inspect">
          <IconButton
            className="ws-collapse"
            icon={inspector ? "chevronRight" : "chevronLeft"}
            label={inspector ? e.collapseInspector : e.expandInspector}
            aria-expanded={inspector}
            onClick={() => setInspector(!inspector)}
          />
          <div className="ws-inspector-body">{p.inspector}</div>
        </aside>
        {p.versions && (
          <>
            <div className="ws-stream" data-pane="activity">
              {p.stream}
            </div>
            <div className="ws-versions" data-pane="versions">
              {p.versions}
            </div>
          </>
        )}
        {p.command && <div className="ws-command">{p.command}</div>}
      </div>
    </div>
  );
}
