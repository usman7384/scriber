import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useLocation, useNavigate } from "react-router";
import { api } from "../../api";
import { useResource } from "../../hooks";
import { useT, type Messages } from "../../i18n";
import { Icon, type IconName } from "../../ui/icons";
import { Kbd } from "../../ui/Kbd";
import { useActions, type Action, type ActionGroup } from "../actions";
import { isMac, keyCaps } from "../keys";
import { outOfBounds, parseAssignment, rank, remember, type Row } from "./match";

const RECENT = "palette-recent";
const loadRecent = () => localStorage.getItem(RECENT)?.split("\n").filter(Boolean) ?? [];

const groupIcon: Record<ActionGroup, IconName> = {
  suggested: "agent",
  parameters: "dimension",
  agent: "agent",
  navigate: "part",
  view: "eye",
  deliver: "deliver",
  settings: "settings",
  help: "help",
};

const loadPlaces = async () => {
  const projects = await api.projects();
  const models = await Promise.all(projects.map((p) => api.models(p.id)));
  return projects.map((project, i) => ({ project, models: models[i] ?? [] }));
};

// Projects, their sources and parts, fetched while the palette is open.
function usePlaces(t: Messages): Action[] {
  const navigate = useNavigate();
  const { data } = useResource("palette-places", loadPlaces);
  return useMemo(
    () =>
      (data ?? []).flatMap(({ project, models }): Action[] => [
        {
          id: `go.project.${project.id}`,
          group: "navigate",
          icon: "grid",
          label: () => project.name,
          hint: t.palette.project,
          run: () => navigate(`/p/${project.id}`),
        },
        {
          id: `go.sources.${project.id}`,
          group: "navigate",
          icon: "document",
          label: (m) => `${m.palette.sources} · ${project.name}`,
          run: () => navigate(`/p/${project.id}/context`),
        },
        ...models.map((model): Action => ({
          id: `go.part.${model.id}`,
          group: "navigate",
          icon: "part",
          label: () => model.title,
          hint: project.name,
          run: () => navigate(`/m/${model.id}`),
        })),
      ]),
    [data, navigate, t],
  );
}

const fixed = (n: number) => n.toFixed(2);

const blocked = ({ action, value }: Row) =>
  action.param !== undefined && value !== undefined && outOfBounds(action.param, value);

function detail({ action, value }: Row, query: string) {
  if (action.group === "agent") return `“${query.trim()}”`;
  if (!action.param || value === undefined) return action.hint;
  return `${fixed(action.param.value)} → ${fixed(value)} ${action.param.unit}`;
}

function bounds(row: Row, t: Messages) {
  const { param } = row.action;
  if (!param || row.value === undefined || param.min == null || param.max == null) return undefined;
  const range = `${fixed(param.min)}–${fixed(param.max)} ${param.unit}`;
  return blocked(row) ? `${t.palette.outOfBounds} ${range}` : range;
}

function PaletteBody({ initial, close }: { initial: string; close: () => void }) {
  const t = useT();
  const { pathname } = useLocation();
  const listId = useId();
  const [query, setQuery] = useState(initial);
  const [active, setActive] = useState(0);
  const registered = useActions();
  const places = usePlaces(t);
  const recent = loadRecent();
  const assigning = parseAssignment(query) !== undefined;
  const sections = rank(
    [...registered, ...places],
    query,
    { pathname, query },
    (a) => (a.param && assigning ? t.palette.set(a.param.label) : a.label(t)),
    recent,
  );
  const rows = sections.flatMap((s) => s.rows);
  const current = Math.min(active, rows.length - 1);
  const optionId = (i: number) => `${listId}-option-${i}`;
  const mac = isMac();

  useEffect(() => {
    document.getElementById(`${listId}-option-${current}`)?.scrollIntoView?.({ block: "nearest" });
  }, [listId, current]);

  const run = (row: Row) => {
    if (blocked(row)) return;
    localStorage.setItem(RECENT, remember(recent, row.action.id).join("\n"));
    close();
    row.action.run(row.value === undefined ? query.trim() : String(row.value));
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    const step = e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0;
    if (step && rows.length) {
      e.preventDefault();
      setActive((current + step + rows.length) % rows.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const row = e.ctrlKey || e.metaKey ? rows.find((r) => r.action.group === "agent") : rows[current];
      if (row) run(row);
    }
  };

  let index = 0;
  return (
    <>
      <div className="palette-query">
        <Icon name="search" />
        <input
          role="combobox"
          aria-expanded
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={rows.length ? optionId(current) : undefined}
          aria-label={t.palette.input}
          placeholder={t.palette.placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
          autoFocus
          spellCheck={false}
        />
      </div>
      <div id={listId} role="listbox" aria-label={t.palette.title} className="palette-list">
        {sections.map((section) => (
          <div key={section.group} role="group" aria-labelledby={`${listId}-${section.group}`}>
            <div id={`${listId}-${section.group}`} className="eyebrow palette-group">
              {section.group === "recent" ? t.palette.recent : t.palette.groups[section.group]}
            </div>
            {section.rows.map((row) => {
              const i = index++;
              const range = bounds(row, t);
              const shortcut = row.action.group === "agent" ? "mod+enter" : row.action.shortcut;
              return (
                <div
                  key={row.action.id}
                  id={optionId(i)}
                  role="option"
                  aria-selected={i === current}
                  aria-disabled={blocked(row) || undefined}
                  className="palette-item"
                  onClick={() => run(row)}
                  onMouseMove={() => i !== current && setActive(i)}
                >
                  <Icon name={row.action.icon ?? groupIcon[row.action.group]} />
                  <span className="palette-label" title={row.label}>
                    {row.label}
                  </span>
                  <span className="palette-detail mono">{detail(row, query)}</span>
                  {range && (
                    <span className="palette-bounds mono" data-blocked={blocked(row) || undefined}>
                      {range}
                    </span>
                  )}
                  {shortcut && <Kbd keys={keyCaps(shortcut, mac, t.agent.command.ctrl)} />}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {rows.length === 0 && <p className="palette-empty">{t.palette.noMatch}</p>}
    </>
  );
}

// Modal like a sheet: the browser traps focus, Esc closes and focus returns to the opener.
export function Palette({ query, onClose }: { query: string | undefined; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const open = query !== undefined;
  const t = useT();
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog?.open) dialog?.showModal();
    if (!open && dialog?.open) dialog.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      className="palette"
      aria-label={t.palette.title}
      onClose={() => open && onClose()}
      onClick={(e) => e.target === e.currentTarget && e.currentTarget.close()}
    >
      {open && (
        <PaletteBody
          initial={query}
          // The close event comes a task later; a Ctrl+K before it must open the palette, not toggle it shut.
          close={() => {
            ref.current?.close();
            onClose();
          }}
        />
      )}
    </dialog>
  );
}
