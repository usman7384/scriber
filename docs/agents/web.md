# Web app (M3 and M5, `apps/web`)

Branches `feat/web-m3`, then `feat/m5-web2` (assembly tree, face edit, suggestions, share page, progress, context selection, EN/DE; see `docs/agents/parity-web.md`). A Vite + React + TypeScript single-page app built against `docs/API.md` and tested against a mocked API (no running server needed).

## Run

```bash
cd apps/web
npm install                       # exact versions from package-lock.json
npm run dev                       # http://localhost:5173, proxies API paths to http://127.0.0.1:8000
npm run lint && npm run typecheck && npm test && npm run build
npx playwright install --only-shell chromium   # once, ~280 MB in %LOCALAPPDATA%\ms-playwright
npm run e2e                       # starts its own Vite server on 127.0.0.1:5199, API mocked
```

`VITE_API_URL` sets the API origin (for example `http://127.0.0.1:8000`; the server must then allow CORS). Unset, the app calls the same origin and the dev server proxies `/health /projects /models /jobs /batch /shares /s/ /hooks /tokens /bugs /docs /openapi.json`. App routes are `/`, `/library`, `/explore`, `/settings`, `/help`, `/p/:projectId`, `/p/:projectId/context`, `/m/:modelId`, `/shared/:shareId`, chosen so they never collide with API paths; a production server can serve `index.html` for those and proxy the rest.

## Pinned stack

vite 8.3.5, react / react-dom 19.3.1, three 0.186.1, @react-three/fiber 9.8.2, @react-three/drei 10.7.9, react-router 8.5.0, d3-force 3.0.0. Dev: **typescript 5.9.3** (7.0.2 exists but typescript-eslint 8.72 requires `<6.1`), vitest 5.0.5, jsdom 30.1.3, Testing Library (react 16.3.3, dom 10.4.2, jest-dom 7.0.1, user-event 14.6.8), @playwright/test 1.64.1, eslint 10.13.0 + typescript-eslint 8.72.0 (strict) + react-hooks 7.1.1, prettier 3.9.10. `.npmrc` has `save-exact=true`. tsconfig: `strict`, `noUncheckedIndexedAccess`, `noUnused*`, `verbatimModuleSyntax`. three.js is bundled (lazy editor chunk, ~1 MB), no CDN; the main e2e asserts no request leaves the app origin. `useGLTF(url, false)` keeps the Draco CDN decoder out of the path.

## Decisions

- **Data fetching: plain `fetch` + two small hooks** (`src/hooks.ts`). `useResource(key, load)` returns `{data, error, loading, reload}` keyed by a string; mutations call `reload()` on the resources they touch. `useJob(id)` wraps `streamJob` (one `EventSource` on `/jobs/{id}/events`, `step` / `done` / `failed` events, closed on the terminal event). The app has a handful of resources with no cross-page cache sharing, so TanStack Query would add a dependency without removing code.
- **State: component state and the URL.** No global store. The editor owns the selected version, current job and selected part; the parameter panel owns its drafts, tied to the params list it was given so a new version or reload starts clean while the "apply instantly" toggle survives.
- **API client: one module** (`src/api.ts`), hand-written types from `docs/API.md` plus `api.*` calls, `exportUrl`, `streamJob`, `waitForJob`.
- **Viewer frame.** The CAD exporter (build123d `export_gltf`) writes metres and rotates Z-up to Y-up (checked on `out/m2-sensor-plate`). `viewer/scene.ts` bakes the inverse (x1000, +90 deg about X) into each part's geometry, so the scene is CAD mm with Z up: bounding-box labels, `Finding.location.point` markers and camera poses all use API coordinates directly. Parts are glTF nodes (GLTFLoader keeps the node name in `userData.name`; per-face primitives are merged under it).
- **Measurements** come from the loaded geometry's bounding box (L/W/H labels in the scene and a text readout in the toolbar), so they do not depend on the shape of `metrics.bbox`.
- **Graph view: d3-force (ISC, ~20 kB) for layout, SVG for drawing.** The layout runs 300 ticks synchronously (`context/graph-layout.ts`), so it is deterministic and testable; fullscreen is a CSS overlay (Esc or the button exits), which works without the Fullscreen API.
- **Bug report stub.** No route exists in the contract. The dialog posts `POST /bugs {model_id, version, text, screenshot?}` (screenshot is a PNG data URL of the viewer canvas, `preserveDrawingBuffer` is on) and shows the server's error if the route is missing. Proposed for the API: store the JSON and return `201 {id}`.
- **Languages: a typed message table, no i18n library** (`src/i18n.ts`, aggregating the namespaces in `src/i18n/`). `de` is typed as `typeof en`, so a missing or misspelled key fails the typecheck; dynamic strings are small functions. `useT()` reads the language from a React context set in the shell; the Settings sheet and the palette store it in localStorage and sets `<html lang>`. Components outside the shell (unit tests) get English. drei `Html` renders in its own React root, so the viewer passes axis names and the finding label down as props. API enums shown in the UI (job and file status, origin, severity, provenance source, step kind) go through tables too; API text does not.
- **Components and selection by API id.** The tree is `GET /models/{id}/components?version=n`, nested by `parent`; selection holds the part id, the viewer maps a picked glTF node to the component with that name (the compiler labels each part with its name), and refine sends the id as `target`.
- **Face edit.** Select face in the viewer toolbar turns clicks into picks (`point` and face `normal` in CAD mm); `POST /models/{id}/face-driver` returns the parameter and its rate, and the Face edit form sends `PATCH /params` with `value + offset / rate` for that one parameter.
- **External tools.** The editor reads `GET /health` once; `tools.freecad` adds FreeCAD (.FCStd) to the Export menu and `tools.prusaslicer` adds Check printability under the manufacturability findings (only for versions with an STL). Both are hidden while `/health` is loading or fails. The FCStd item fetches the file before saving it (a blob link), because a plain download link cannot show the API's 422 text for a design FreeCAD cannot map; that text appears in the editor's error line.
- **Look and layout** follow `docs/design/UI_DIRECTION.md`; the integration is described in `ui-integration.md`. Tokens in `styles/tokens.css` (dark first, full light set; theme System / Light / Dark in Settings), self-hosted IBM Plex, primitives in `src/ui`, one CSS file per area on tokens only (`styles/tokens.test.ts` fails on a colour literal anywhere else).
- **One action registry** (`shell/actions.ts`): navigation, settings, parameters, the agent, views, version steps, exports, share, publish, printability and Report a bug are registered once; on-screen buttons, single-key shortcuts and the Ctrl+K palette run the same action.

## Contract ambiguities and how they were resolved

| Item | Reading used |
|---|---|
| `GET /models/{id}` "Model + latest Version" (flat or nested?) | Only Model fields are read; versions come from `GET /models/{id}/versions`, latest = highest `number`. Works with either shape. |
| `File.facts`, `File.rules` | Counts (numbers); facts themselves come from `GET .../facts`. |
| Ingest `Job` has no file id | Upload returns jobs in `files[]` order; per-file status maps by index. Prompt attachments wait for the ingest jobs, then re-read `GET /context` and take the newest file with each name as the attachment id. A `file_id` on ingest jobs would remove the guess. |
| `metrics.bbox`, `metrics.holes` | Typed; labels still come from the GLB box, which PR-10 checks equals `metrics.bbox` to 0.01 mm. |
| `Finding.location.point` | `[x, y, z]` in mm, CAD frame. |
| `GraphView.counts` | Not relied on; counters show rendered nodes and edges, which equal the API's arrays. |
| Refine `target: part_id` | The component id from `GET /models/{id}/components`; the picked glTF node is matched to it by part name (nodes carry part labels, not ids). |
| Share `url` | The API's `url` is the JSON route; the web shows `/shared/{id}`, a read-only viewer that reads `GET /s/{id}`. |
| `POST .../suggestions/{sid}/ignore` | `docs/API.md` says 204; apps/api returns the suggestion with status `ignored`. The client accepts either. |
| SSE replay | Assumes the server replays earlier events for a late subscriber (Last-Event-ID design in the research note). |

## Screens (described)

- **Home** (`/`, `/library`, `/p/:id`): sidebar (Search, Projects, All parts, each project with its part count, New project, the selected project's Sources, Explore, Settings, Help; a project switcher in the header under 640 px). The composer is the generate command bar (Attach, drop anywhere, paste, process chip, source chips, starter cards); Generate turns into the agent card (steps, checks and repairs, progress hairline, Open model and Download STL when done). Below, the parts grid, newest first or by name.
- **Sources** (`/p/:id/context`): a sheet over Home with the knowledge-meter line, drop zone, search, file rows with status glyphs, facts with quote and page:line, project rules, the knowledge graph (fullscreen), and "Use *n* in the next generation".
- **Explore** (`/explore`): the same grid over published parts; Fork picks a project and opens the copy.
- **Workspace** (`/m/:id`): full-bleed viewport with grid, triad, L/W/H reference dimensions and finding pins; top bar with the breadcrumb, version, checks pill, Search and Deliver (exports, FreeCAD, share link with Copy and Revoke, Publish to Explore, Check printability); structure rail; inspector by selection (overview, part, picked face with its driving chip, finding, version preview); the refine command bar with the selection as target; the agent dock while a job runs and the status line with Revert after it; the version scrubber with preview, restore and compare. Under 768 px the inspector, Activity and Versions share a bottom sheet.
- **Shared view** (`/shared/:id`): the workspace read-only; Deliver lists only the shared files.
- **Settings, Help** (`/settings`, `/help`): sheets over the page they were opened from; Help has the shortcut table, how-tos and Report a bug.

## Tests

- Unit and component (vitest, `npm test`): primitives, palette matching and ranking, the action registry and key layer, command bar, agent stream, version scrubber, quantities, parameter panel and bounds, parts grid, file list, graph view, scene maths, i18n shape, the colour guard.
- e2e (`npm run e2e`, API mocked in `e2e/mock-api.ts`): `main-flow.spec.ts` (generate, stream, open, edit, restore, refine with a target, share, no off-origin request), `workspace.spec.ts`, `palette.spec.ts`, `layout.spec.ts` (every route at 390 and 1440 px without sideways scroll), `context.spec.ts`. `SHOTS=<dir> npx playwright test screens` writes the screenshots in `docs/design/built/final/`.
- Parity (`npm run parity`, mocked) and live (`npm run parity:live`, real API and model): see `parity-web.md` and `parity-web-live.md`.

## Checklist rows advanced (client side; none closed, each still needs the live API and a recorded demo)

| Row | Evidence |
|---|---|
| WP-1 viewer, view buttons, orbit | `main-flow.spec.ts` (GLB loads, Top pressed), `scene.test.ts` (camera direction per view) |
| WP-2 composer with attachments | `CommandBar.test.tsx` (3 attachments uploaded then referenced in one generate) |
| WP-3 editor header, target chip | `main-flow.spec.ts` (title, target chip switches to the selected component) |
| WP-4 example chips | `CommandBar.test.tsx`, `main-flow.spec.ts` |
| WP-5 navigation | Home sidebar, Sources, Settings and Help sheets, API docs link in Settings; `parity/project.spec.ts`, `palette.spec.ts` |
| WP-6 live progress | `AgentStream.test.tsx`, `main-flow.spec.ts`; progress bar in `parity/project.spec.ts` |
| WP-8 thumbnails shown | gallery, history and step thumbnails in `PartsGrid.test.tsx`, `VersionScrubber.test.tsx`, `main-flow.spec.ts` |
| WP-9 gallery sorted by date | `PartsGrid.test.tsx` |
| WP-11 report a bug | dialog posts `{model_id, version, text, screenshot}` to the `/bugs` stub; no test (needs the API route) |
| PR-1 parameter panel | `ParamPanel.test.tsx`, `main-flow.spec.ts` |
| PR-2 (client) edit, then regenerate | `main-flow.spec.ts` (PATCH `{values}`, new version shown) |
| PR-3 apply instantly | `ParamPanel.test.tsx` |
| PR-4 (client) refine | `main-flow.spec.ts` |
| PR-9 history and restore | `VersionScrubber.test.tsx`, `main-flow.spec.ts` |
| PR-10 bbox labels | `main-flow.spec.ts`; labels against `metrics.bbox` in `parity/model.spec.ts` |
| VM-4 finding pop-up in the viewer | `main-flow.spec.ts` (marker at the location, suggestion on hover) |
| CX-1 multi-file upload, per-file status | `UploadZone` status and ingest progress per file; `parity/context.spec.ts` |
| CX-2 context table | `FileList.test.tsx`, `context.spec.ts` |
| CX-5 KG view | `GraphView.test.tsx`, `context.spec.ts` |
| CX-6 KB level | `context.spec.ts` |
| AS-1 (web) | tree from the components API, viewer click selects the API id; `parity/model.spec.ts` |
| PR-6 (web + API test) | Select face, Face edit, `POST /models/{id}/face-driver`; `parity/model.spec.ts`, `apps/api/tests/test_faces.py` |
| PR-7 (web) | Proposals in the inspector (Apply, Dismiss); `parity/editor.spec.ts` |
| EX-6 (web) | `/shared/:id`, Revoke; `parity/share.spec.ts` |
| WP-13 | EN/DE in Settings and the palette; `parity/language.spec.ts` |
| WP-14 (web) | Download STL on the finished generation; `parity/project.spec.ts` |
| CX-3, CX-6 (web) | context selection and Used in links, KB numbers against the formula; `parity/context.spec.ts` |
| IN-16 (client) | generate carries all attachment ids, `CommandBar.test.tsx` |
| EX-4 (web) | Export menu FreeCAD (.FCStd), API error text for unmapped designs, hidden without FreeCAD; `parity/tools.spec.ts` |
| VM-9 (web) | Check printability shows the slice report under the findings, hidden without PrusaSlicer; `parity/tools.spec.ts` |
| IN-17 | not advanced: `POST /models/{id}/refine` has no attachments field in the contract |

## Gaps

- IN-17 needs `attachments` on refine in the contract.
- No API-token page.
- Upload progress is the ingest job's progress per file, not upload bytes.
- Finding markers sit at `location.point`; face highlighting (`location.face`) needs face ids in the GLB.
- Parameter drafts typed while a job is running are dropped when the new version arrives.
- The viewer needs WebGL; without it the editor shows a message instead of the 3D view.
- Editor chunk is ~1 MB (three + drei, ~280 kB gzip), loaded only on the editor route.

## Disk

`apps/web/node_modules` is 373 MB (drei pulls in hls.js, stats-gl, mediapipe and three-stdlib). Playwright's Chromium headless shell (~280 MB) was already in `%LOCALAPPDATA%\ms-playwright`; nothing new was downloaded.
