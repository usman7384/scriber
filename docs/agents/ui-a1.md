# UI foundation (work package A1, `apps/web`)

Spec: [`docs/design/UI_DIRECTION.md`](../design/UI_DIRECTION.md) §4, §5 and §7 A1. Closes no parity row; WP-13 (language) and every existing e2e and parity spec keep passing.

## What is there

- **Tokens** in `src/styles/tokens.css`, the only file allowed colour literals (`src/styles/tokens.test.ts` fails on a hex, `rgb()` or `hsl()` anywhere else; legacy files are listed by name and each package deletes its entry when it moves a screen). Dark on `:root`, the full light set on `:root[data-theme="light"]`. `prefers-contrast: more` raises `--line` and drops `--blur`; `prefers-reduced-motion: reduce` shortens `--d-mid` / `--d-slow` to 80 ms and zeroes `--d-camera`.
- **Fonts**: IBM Plex Sans 400/500/600 and Mono 400/500 from `@fontsource/ibm-plex-sans` and `@fontsource/ibm-plex-mono` 5.3.0, pinned. `src/styles/fonts.css` declares woff2-only faces for latin and latin-ext with their unicode ranges, so Vite bundles ten files and nothing is fetched at runtime.
- **Base** in `src/styles/base.css`: box sizing, body type on tokens with tabular figures, the focus ring (2 px accent with a 2 px `--bg` gap), `.mono`, `.eyebrow`.
- **Primitives** in `src/ui`, each with a test in `ui.test.tsx`: `Button` (`default` / `primary` / `ghost`, optional icon, `aria-pressed` style), `IconButton` (named by `label`, which is also its tooltip), `Chip` (`accent` tone, truncates with a title, optional named remove), `Kbd`, `Status` (glyph plus word, translated), `Provenance` (monogram in an `abbr` titled with the translated source; `default` dashed warn), `Tooltip` (describes its trigger; `popover="hint"` in the top layer, opens on hover and keyboard focus, Esc closes), `Popover` (native `popover="auto"`: light dismiss, Esc and focus return from the browser; the trigger is a render prop that receives `ref`, `popoverTarget` and ARIA), `Sheet` (modal `<dialog>`: focus trap, Esc, focus return, 55 % scrim, bottom sheet under 640 px). Placement is the pure `place()` in `place.ts`.
- **Icons** in `src/ui/icons.tsx`: 32 glyphs on a 16 px grid, 1.5 px stroke, `currentColor`, `aria-hidden`. `public/favicon.svg` is the mark.
- **i18n**: `src/i18n/{common,shell,workspace,agent,home}.ts` each export `en` and `de: typeof en`; `src/i18n.ts` spreads them in one fixed order, so `messages`, `useT` and the language spec are unchanged. `src/i18n.test.ts` keeps keys disjoint across namespaces and German in English's shape and order (the language spec pairs strings by position).

## Notes for A2, B, C, D

- Primitive classes are `ui-` prefixed and `ui.css` loads after `app.css`, so the legacy global `button`, `dialog` and `[role="tooltip"]` rules do not leak in. Style new components in your own CSS file on tokens only.
- The theme is always resolved to `data-theme="light"` or `"dark"` on `<html>`; without the attribute the page is dark. A2's "system" option should resolve in JS (listen to `prefers-color-scheme`) and keep setting one of the two.
- Three.js needs real colours: read them with `getComputedStyle(document.documentElement).getPropertyValue("--part")` (and re-read on theme change) instead of adding literals. `--part`, `--part-edge`, `--grid-minor`, `--grid-major`, `--axis-*` and `--viewport` exist for the viewer.
- Namespaces: `common` (shared words, status, origin, source, process), `shell` (nav, settings, help, bug), `workspace` (editor, viewer, params, findings, face, share, export, printability), `agent` (prompt, timeline, refine, suggestions), `home` (projects, gallery, community, context, knowledge base, graph). Add keys in your own file, in the same order in `en` and `de`.
- `app.css` now reads the new token names (`--surface-solid`, `--field`, `--line-strong`, `--pass`, `--fail`, `--viewport`, `--r-2`, `--accent-ink`); its layout is unchanged. Delete it at integration.
- jsdom has neither `showModal` nor the popover API; `ui.test.tsx` shows the stubs to use in your tests.
