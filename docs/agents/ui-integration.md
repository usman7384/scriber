# UI integration (packages A1, A2, B, C, D, `apps/web`)

Spec: [`docs/design/UI_DIRECTION.md`](../design/UI_DIRECTION.md). Branch `feat/ui-a1`, after merging main (live specs, `parity:live`, the dev-proxy env var). Closes no new parity row; every mocked e2e and parity spec passes with the selector changes below. Screenshots: [`docs/design/built/final/`](../design/built/final/) (dark and light, 1440 x 900 and 390 x 844; `SHOTS=<dir> npx playwright test screens` rewrites them).

## One product

- **Shell.** Home routes (`/`, `/library`, `/p/:id`, `/p/:id/context`) render `home/HomePage`, `/explore` renders `home/ExplorePage`; both sit in `HomeLayout`, whose `HomeNav` is the only navigation `Main` (brand, Search, Projects, All parts, the projects, New project, the project's Sources, Explore, Settings, Help; under 640 px an icon row and a project switcher row). Model routes render inside a bare `<main>`; the workspace brings its one top bar, which now holds the palette button. A2's sidebar frame, its `side` / `top` slots, `ProjectNav`, the five page re-exports and D's shim in `home.css` are deleted. `NotFound` uses the Home layout.
- **Agent I/O.** Home's composer is `CommandBar` (generate) plus `AgentStream` (card), resuming a running job from `GET /projects/{id}/jobs?active`. The workspace mounts `CommandBar` (refine; target from the part, face or finding selection; `/` opens the palette), `AgentStream` (dock) while a job runs and then `AgentStatus` (with Revert) under the collapsed dock, `VersionScrubber` (bottom strip on desktop, Versions tab on phones), and `Proposals` keyed by the latest version in the inspector. `PromptPanel`, `RefineBox`, `Timeline`, `VersionHistory`, `Suggestions`, `BugDialog`, `ShareButton`, their strings, C's harness and B's interim CSS are deleted.
- **Actions.** `workspace/useEditorActions.ts` registers each parameter (`name = value` in the palette), the agent ("As a change to *target*", Ctrl+Enter), `[` / `]` for the previous / next version and New generation; `Viewer` registers Top / Front / Right / Iso (1 2 3 0), Edges (E), Dimensions (M) and Select face (P), replacing its own key handler; `DeliverMenu` registers every export, FreeCAD, Share, Publish and Check printability. Handlers are read through a ref, so the lists change only with what they offer.
- **Share and Report a bug** (§6): Share is an item in Deliver (link, Copy, Revoke shown in the menu); Report a bug is the workspace's registered help action, reached from Help and the palette.
- **Styles.** `styles/app.css` is deleted; `base.css` gained heading and paragraph margins, link colour, table collapse, `.sr-only` and the loading line. The colour guard's legacy list is `styles/tokens.css` only.

## Fixes found on the way

- The palette cleared its state only on the dialog's `close` event, a task later; a Ctrl+K in between toggled it shut. It now clears when an action runs.
- `keyCaps` printed "Ctrl" in German; it takes the translated label (Strg).
- `body` has `min-height: 100dvh`, since the fixed workspace leaves nothing in flow.

## Spec changes (selectors only)

- `palette.spec`: All parts / Explore names; Projects anchored (`/^Projects/`) since the agent row echoes the query; waits for the Sources sheet and the page before pressing Ctrl+K; Ctrl+K is retried when dropped under load.
- `layout.spec`: no legacy exception at 390 px; waits for the canvas (the bbox readout is hidden on phones).
- `main-flow.spec`: step titles, restore through the scrubber's banner, Share inside Deliver.
- WP-5: waits for the Help sheet before Esc, and closes the modal Sources sheet before using the sidebar again. WP-10: Publish to Explore inside Deliver, Explore link, the breadcrumb back. WP-11 (mocked and live): Report a bug from the Help sheet. WP-13: the palette's listbox options; waits for the page before Ctrl+K. EX-6 (mocked and live): Share inside Deliver, the status inside the menu; live reads `Thickness 5.00 mm`. PR-7: `Hole X 20.00 → 15.00 mm`, Apply, Dismiss. CX-3: no Clear item in the source chips. Live CX-6: meter terms `files / facts / rules / used`, "Use 1 in the next generation" (the meter line has no generations count, so the API's `generations` is recorded but not compared).
- `workspace.spec`'s screenshot test moved to `screens.spec.ts`.

## Open

- Compare draws the parameter diff but no ghost outline (the viewer has no second model); `onCompare` is optional.
- Source chips in the generate bar cannot be removed in place; the Sources sheet or a new project link clears them.
- Status glyphs on part cards still need a per-model check summary (UI_DIRECTION §8).
