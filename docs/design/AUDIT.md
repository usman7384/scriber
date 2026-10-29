# UI audit (2026-10-29)

Screenshots of today's app against the mocked API (`e2e/mock-api.ts`, sensor-plate scenario) at 1440 × 900 (`-desktop`) and 390 × 844 (`-mobile`) are in [`audit/`](audit/). `-full` files are full-page captures. Light theme, English.

## Across every screen

- **It looks like an admin template.** Light grey page, white cards with 1 px borders and 8 px radius, a blue primary button, a horizontal text nav. Nothing says "engineering tool"; swap the content and it could be a ticketing system.
- **Numbers are body text.** Dimensions, tolerances and counts are set in the same proportional font as prose ("120 x 80 x 6 mm", "score 132 / 400"), mostly in prompts and grey meta lines. Only the viewer tags use a monospace face, and those are orange stickers.
- **Everything is a stacked section.** Each feature landed as its own heading-plus-box (Parameters, Requirement checks, Manufacturability, Printability (FDM), Suggestions, Components, History). The structure mirrors the API resources, not what the user is doing.
- **The top nav is a site map.** Projects, Library, Community, Settings, Help, API and a language `<select>` get equal weight on every page, including the editor, where none of them is needed.
- **Mobile is broken, not just cramped.** The nav and the editor header overflow (the editor page is 570 px wide at 390 px), the context table wraps file names letter by letter, and the editor stacks into a 1,600 px column with the components and history at the very bottom.
- **The agent is invisible after the fact.** The timeline exists only on the project page while a job runs; in the editor there is no trace of what the agent did, assumed or checked to produce the shown version.

## Per screen

| Screen | Feels generic because | Cluttered | Hard to understand |
|---|---|---|---|
| Projects `01` | Two small cards in a sea of grey; "New project name" field sits in the heading row like a filter. | — | What a project is for; why "0 context files" matters. Nothing to do here but click a card. |
| Project / Models `02`, `03` | A form card (label, textarea, chips, three "+ X" buttons, select, button) above a gallery. | Four long example chips wrap to two lines and dominate. Image / Mesh / Spec file are three buttons for one action. | The timeline after Generate is a list of grey bars ("answer of 1984 chars") with left-border colours; the useful part (what failed, what the repair changed) is one line of prose. Downloads and "Open model" appear below it with no preview. |
| Editor `04` | Three equal columns of boxes around a viewer on a soft gradient; a toolbar of checkboxes. | Header has five buttons of equal weight (New generation, Share, Publish, Export, Report a bug). Right column stacks params, checks, findings, printability and suggestions in one scroll. | Provenance is a tiny blue pill ("document", "standard") with no source shown until hover. The finding marker is a small "!" with no visible link to the warning in the right column. Target chip and refine box sit under the viewer, far from the selection. "Apply instantly" is a checkbox above the first slider that silently changes what every field does. Version history is a list of one big card. |
| Editor mobile `04-…-mobile` | Desktop columns stacked. | Everything visible at once, no priorities. | Horizontal scroll; the viewer is 350 px tall and the selection tree is 1,400 px below it. |
| Context `06` | A CRUD table with a Delete button on every row, a stats card, and a graph card with dots on grey. | Seven columns, per-row checkboxes plus a full-width "Use selected as context (0)" bar that is visible even when nothing is selected. | "Knowledge base level 1, score 132 / 400" is gamification without meaning. The graph shows 8 unlabeled dots. Facts (the actual value of the page) are hidden until a file name is clicked. |
| Library `07` | Same card grid as the project page with no filter, status or project label. | — | Duplicates the project gallery; no way to tell which parts pass their checks. |
| Community `08` | Same grid; "Fork into project" select sits above all cards, detached from the Fork button. | — | Where the fork will land is decided before you choose what to fork. |
| Settings `09` | Two boxes for two settings (theme radio, API URL). | — | A full page for two controls; language lives in the top bar instead of here. |
| Help `10` | Four paragraphs in cards. | — | Teaches in prose what the UI should teach in place. |
| Shared `11` | Editor viewer with an uppercase "SHARED, READ-ONLY" badge and a two-row table. | — | No checks, no units column, no way to download what is shared. |

## What already works (keep)

- Real geometry in the viewer, measurement tags on the model, finding markers at `location.point`.
- Provenance and bounds exist on every parameter; checks carry measured vs required values.
- A typed EN/DE table with a test that fails on any missing German string.
- Accessible names on almost every control, which the parity specs lean on.
