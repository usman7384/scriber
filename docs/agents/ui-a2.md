# App shell, sheets and command palette (work package A2, `apps/web`)

Spec: [`docs/design/UI_DIRECTION.md`](../design/UI_DIRECTION.md) §2, §3 (Command palette), §5 and §7 A2. Closes no parity row; WP-5, WP-10, WP-11 and WP-13 keep passing.

## What is there

- **Shell** (`components/Shell.tsx`, `shell/shell.css`): no top nav. Home routes get a 224 px sidebar, `navigation "Main"` (brand, Search, Projects, Library, a slot, Community, Settings with the language code, Help); below 768 px it is a 44 px icon bar with the same accessible names. `/m/*` and `/shared/*` get a floating top bar (mark linking home as "Partwright home", a slot, "Search or run…") over a full-bleed stage.
- **Routes** (`App.tsx`): `/settings` and `/help` are sheets over the page they were opened from (`location.state.backdrop`), or over Home for a deep link; Esc goes back. Links into a sheet pass `sheetLinkState(location)`; code calls `useOpenSheet()("settings" | "help")`.
- **Provider** (`shell/ShellProvider.tsx`): theme, language, the action registry, the palette and the bug sheet for every route. Theme is `system | light | dark`, stored as `theme`; `system` follows `prefers-color-scheme` in JS so `<html data-theme>` is always `light` or `dark`.
- **Settings sheet**: theme (System / Light / Dark), Language, API server and the API docs link. **Help sheet**: shortcut table, four how-tos, Report a bug (enabled when a part registered the bug action).
- **Palette** (`shell/palette/*`): Ctrl/⌘ K anywhere (again to close), or the Search buttons. A modal combobox and listbox: Recent first on an empty query, then groups in §3 order; fuzzy match on label and hint; `name = value` (unit and comma decimal allowed) becomes "Set *label* 6.00 → 7.00 mm" with bounds, refused outside them; Ctrl Enter runs the first "agent" action with the query. Built in: Projects, Library, Community, every project, its Sources and its parts (fetched on open), Settings, Theme ×3, Language ×2, Help (`?`), API docs.
- **Shortcut layer** (`shell/keys.ts`): one window listener; Ctrl/⌘ K always, other registered shortcuts only outside fields and dialogs.

## Action registry (`src/shell/actions.ts`)

```ts
type ActionGroup = "suggested" | "parameters" | "agent" | "navigate" | "view" | "deliver" | "settings" | "help";

interface Action {
  id: string;                                // unique; a later registration of the same id wins
  group: ActionGroup;
  label: (t: Messages) => string;            // from your i18n namespace, so it follows the language
  hint?: string;                             // secondary text: a project name, a current value
  icon?: IconName;                           // defaults per group
  shortcut?: string;                         // "mod+shift+e", "1", "[", "?"; mod = Ctrl or Cmd
  when?: (ctx: { pathname: string; query: string }) => boolean;
  param?: Pick<Param, "name" | "label" | "value" | "unit" | "min" | "max">;
  run: (query: string) => void;              // agent: the query; param row: the value as text; else the query
}

useRegisterActions(actions: readonly Action[]): void   // registered while the component is mounted
useActions(): readonly Action[]                        // live list (palette, Help)
```

- Pass a **memoised** array (`useMemo`); a new array re-registers on every render.
- A registered `shortcut` is bound by the shortcut layer and shown in the palette; a button on screen should call the same `run`.
- Parameters (B): one action per parameter with `group: "parameters"` and `param`; `run("7")` sets 7, `run("")` (picked without a value) can focus the row.
- Agent (C): one `group: "agent"` action, label like "As a change to *target*"; it shows whenever the query is not empty and Ctrl Enter runs it.
- Others: `useShell().openPalette(query?)` opens the palette (C's leading `/`); `useShell().reportBug` / `useBugAction({ modelId, version, screenshot })` from `shell/bug.ts` registers Report a bug with the canvas screenshot (B; replaces `<BugDialog>`, which is now a transitional button over that hook).
- Slots: `<ShellSlot name="side">` renders into the Home sidebar between Library and the footer (D: project list, Sources); `<ShellSlot name="top">` into the workspace top bar between the mark and Search (B: breadcrumb, checks pill, Deliver). The top bar is `position: fixed`, `z-index: 20`.

## Tests

`shell/actions.test.ts`, `shell/keys.test.ts`, `shell/palette/match.test.ts`, `shell/palette/Palette.test.tsx`, `theme.test.ts`; e2e `palette.spec.ts` (Ctrl+K and Esc focus return on every route, every route reachable, theme incl. system, language, a registered action) and `layout.spec.ts` (every route at 390 and 1440 px, no sideways scroll, screenshots attached). Screens: `docs/design/built/a2/`.

## For the integrator

- Spec edits outside A2's files, forced by sheets and the removed top nav, selectors only: WP-5 (`project.spec.ts`: Esc closes the Settings and Help sheets; the API link moved into Settings as "API docs") and WP-10 (`community.spec.ts`: from the editor, the mark leads home before Main → Community).
- Kept until D lands, so D's specs stay green: routes `/library` and `/p/:id/context` still mount D's pages (swap for the Home redirects in `App.tsx`), `ProjectNav.tsx` (delete when D's pages stop importing it), the link name "Community" (rename to Explore with `community.spec.ts`), the `page` class on the Home `<main>` (goes with `app.css`).
- `layout.spec.ts` lists `/p/p1/context` at 390 px as a known sideways scroll (the legacy context table); remove it when D's Sources sheet replaces the page.
