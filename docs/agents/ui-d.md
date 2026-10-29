# Home, Sources, Explore (work package D, `apps/web`)

Spec: [`docs/design/UI_DIRECTION.md`](../design/UI_DIRECTION.md) §2, §3 (Sources sheet, empty states) and §7 D. Closes no new parity row; keeps CX-1, CX-2, CX-3, CX-5, CX-6, WP-5, WP-9, WP-10 and `e2e/context.spec.ts` green. Screenshots (1440 × 900 and 390 × 844, dark and light): [`docs/design/built/d/`](../design/built/d/).

## What is there

- **`src/home`**. `HomePage` is one screen for `/`, `/library`, `/p/:id` and `/p/:id/context`, read from the URL: the sidebar (`HomeNav`, navigation `Main`) lists All parts, the projects with counts and an inline New project, the selected project's `Sources` (navigation `Project`), Explore and Settings. The heading names the scope (`Projects`, `All parts` or the project); the composer slot targets the selected project, or the newest one with "New part in …" when none is selected; `PartsGrid` (list `Models`) shows that project's parts or all of them, newest first or by name, thumbnails on viewport-coloured tiles, whole card clickable. With no projects the lead teaches what a project is and the New project field is open.
- **`src/sources`**. `SourcesSheet` (on the A1 `Sheet`) opens over Home at `/p/:id/context`; closing returns to `/p/:id`. One knowledge-meter line (level, score / next, files, facts, rules, used), the drop zone with per-file progress, search, the file list (still table `Context files`, laid out as two-line rows: checkbox, name, kind, facts, used-in links, date, parse status as glyph plus word with the failure reason, delete behind a confirm), facts of the opened file with quote and `p:l`, project rules (table `Project rules`, severity glyph, process name, source ref), and the knowledge graph preview with hover labels, legend and Fullscreen (Esc leaves fullscreen without closing the sheet). Selecting files shows the footer "Use *n* in the next generation", which returns to `/p/:id?context=…`; the composer carries those ids as `context_ids`.
- **Explore** (`home/ExplorePage`) is the same layout and grid over `GET /community`; each card's Fork opens a popover listing the projects, and picking one forks into it and opens the copy.
- Mobile (≤ 640 px): the sidebar becomes a header with the mark, a project switcher, New project and icon links; two-column grid; no horizontal scroll on any of these routes at 390 px, names truncate with an ellipsis instead of wrapping by letter.
- Styles: `home/home.css`, `sources/sources.css`, tokens only (`context/GraphPanel.tsx` left the colour-guard list; graph types use `--accent`, `--warn`, `--pass`, axis tokens). `ModelGallery` and `src/context` are gone; `pages/{Projects,Project,Library,Context,Community}Page.tsx` are one-line re-exports so `App.tsx` is untouched.

## Spec changes (D-owned specs, behaviour unchanged)

- CX-3, CX-6, WP-5: the project link `Context` is now `Sources`; "Use selected as context (*n*)" is "Use *n* in the next generation".
- CX-6 reads the meter's `dt` names `files`, `facts`, `rules`, `used`; `e2e/context.spec.ts` checks the region `Knowledge base` contains `Level 1`.
- WP-5: All parts (`/library`, heading `All parts`) replaces Library; the API docs step runs from `/help`, where the old top nav still has it (§6 moves the API link to Settings).
- WP-10: Fork opens the dialog `Fork into project`; picking `Bracket lab` lands on `/m/m4` directly instead of a status line with "Open the copy".

## Hand-offs

- **A2 (routes, shell).** Point `/`, `/library`, `/p/:projectId`, `/p/:projectId/context` at `home/HomePage` and `/explore` at `home/ExplorePage` (no redirects needed, the page reads the URL), then delete the five page re-exports and `ProjectNav.tsx` (unused now). Delete the shim at the top of `home/home.css` (hides the old top nav on Home and gives the sidebar the space under it) when the top nav goes. The sidebar is the only navigation `Main` on these routes; the language select stays yours (WP-13 finds it on `/`). The palette's search trigger belongs after the brand in `HomeNav` (mockup); WP-5's API step moves to Settings with the API link. WP-10 still reaches `/explore` through the old top nav from `/m/m1` and needs the breadcrumb or palette path once that nav is gone.
- **C (agent I/O).** The composer slot is `Composer` in `home/HomePage.tsx`: replace `PromptPanel` with `CommandBar({mode: "generate", projectId, contextIds, onJob})`, `contextIds` being the `?context=` ids the Sources sheet sets (removing them clears the param), and `JobTimeline` with `AgentStream({jobId, variant: "card", onDone})`; `onDone` keeps calling `onEnd` so the grid and counts reload. Starter cards and drop-anywhere go in the same slot.

## Not done

- Status glyphs on part cards (mockup) need a per-model check summary, an API gap listed in §8; one version request per card was not worth it.
- The parity and screenshot runs here hit intermittent "Unable to capture screenshot" errors from Chromium while other worktrees ran Playwright at the same time; each affected spec passed when rerun alone.
