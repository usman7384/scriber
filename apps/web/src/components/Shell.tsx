import { useMemo, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { useLang, useT } from "../i18n";
import { SlotsContext, useShell } from "../shell/context";
import { isMac, keyCaps, PALETTE_KEY } from "../shell/keys";
import { sheetLinkState } from "../shell/sheets";
import { Icon, type IconName } from "../ui/icons";
import { Kbd } from "../ui/Kbd";
import "../shell/shell.css";

const isWorkspace = (pathname: string) => /^\/(m|shared)\//.test(pathname);

function SearchButton({ label }: { label: string }) {
  const { openPalette } = useShell();
  return (
    <button
      type="button"
      className="shell-search"
      aria-keyshortcuts="Control+K"
      onClick={() => openPalette()}
    >
      <Icon name="search" />
      <span className="shell-label">{label}</span>
      <span aria-hidden="true" className="shell-search-keys">
        <Kbd keys={keyCaps(PALETTE_KEY, isMac())} />
      </span>
    </button>
  );
}

interface ItemProps {
  to: string;
  icon: IconName;
  end?: boolean;
  sheet?: boolean;
  children: ReactNode;
}

function NavItem({ to, icon, end, sheet, children }: ItemProps) {
  const location = useLocation();
  return (
    <NavLink to={to} end={end} state={sheet ? sheetLinkState(location) : undefined} className="shell-nav">
      <Icon name={icon} />
      {children}
    </NavLink>
  );
}

function HomeFrame({ setSide }: { setSide: (el: HTMLElement | null) => void }) {
  const t = useT();
  const [lang] = useLang();
  return (
    <div className="shell-home">
      <nav aria-label={t.nav.main} className="shell-side">
        <Link to="/" className="shell-brand">
          <Icon name="mark" />
          <span className="shell-label">Partwright</span>
        </Link>
        <SearchButton label={t.nav.search} />
        <NavItem to="/" end icon="grid">
          <span className="shell-label">{t.nav.projects}</span>
        </NavItem>
        <NavItem to="/library" icon="part">
          <span className="shell-label">{t.nav.library}</span>
        </NavItem>
        <div ref={setSide} className="shell-slot" />
        <div className="shell-side-foot">
          <NavItem to="/explore" icon="globe">
            <span className="shell-label">{t.nav.community}</span>
          </NavItem>
          <NavItem to="/settings" sheet icon="settings">
            <span className="shell-label">{t.nav.settings}</span>
            <span aria-hidden="true" className="shell-count">
              {lang.toUpperCase()}
            </span>
          </NavItem>
          <NavItem to="/help" sheet icon="help">
            <span className="shell-label">{t.nav.help}</span>
          </NavItem>
        </div>
      </nav>
      <main className="shell-main page">
        <Outlet />
      </main>
    </div>
  );
}

function WorkspaceFrame({ setTop }: { setTop: (el: HTMLElement | null) => void }) {
  const t = useT();
  return (
    <div className="shell-workspace">
      <header className="shell-top">
        <Link to="/" className="shell-mark" aria-label={t.nav.home}>
          <Icon name="mark" size={18} />
        </Link>
        <div ref={setTop} className="shell-slot-top" />
        <SearchButton label={t.nav.searchOrRun} />
      </header>
      <main className="shell-stage">
        <Outlet />
      </main>
    </div>
  );
}

// Home routes get the sidebar, model routes a top bar; pages add to either through ShellSlot.
export function Shell() {
  const { pathname } = useLocation();
  const [side, setSide] = useState<HTMLElement | null>(null);
  const [top, setTop] = useState<HTMLElement | null>(null);
  const slots = useMemo(() => ({ side, top }), [side, top]);
  return (
    <SlotsContext value={slots}>
      {isWorkspace(pathname) ? <WorkspaceFrame setTop={setTop} /> : <HomeFrame setSide={setSide} />}
    </SlotsContext>
  );
}
