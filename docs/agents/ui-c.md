# Agent I/O (work package C, `apps/web`)

Spec: [`docs/design/UI_DIRECTION.md`](../design/UI_DIRECTION.md) §3 and §7 C. Closes no new parity row; keeps WP-2, WP-4, WP-6, WP-14, WP-8, PR-7, CX-3 and `main-flow.spec.ts` passing (verified with the components mounted, see below). Screenshots: [`docs/design/built/c/`](../design/built/c/).

## Components (`src/agent`)

| Module | Props | Notes |
|---|---|---|
| `CommandBar` | `{mode: "generate", projectId, contextIds, onJob, starters?, onCommand?}` or `{mode: "refine", modelId, target?: {id, label, kind: "part" \| "face"}, onClearTarget, onJob, busy?, onCommand?}` | Generate: multi-line, Ctrl+Enter, Attach + drop anywhere + paste, process chip (a `select`), source chips for `contextIds`, starter cards under it unless `starters={false}`; sends one `generate` with every ready attachment id after pending ones settle. Refine: Enter, target chip (Backspace in an empty bar clears it), `process` only when not "any". A leading `/` goes to `onCommand(query)`. `onJob(job, resend)`: `resend` repeats the same request for Retry. `busy` blocks sending and says why. |
| `AttachmentTray`, `useAttachments(projectId)` | `{items, onRetry, onRemove}` | Used by the generate bar. Per file: uploading % (XHR), reading % (ingest job), ready with its fact count, or failed with the API's reason, Retry, Remove. Uploads run one at a time so ids keep their order. |
| `StarterCards` | `{onPick}` | Four starters, quantities in mono. Rendered by the generate bar. |
| `AgentStream` | `{jobId, variant: "card" \| "dock", onDone?, onRetry?}` | The one SSE subscriber for a job (the mock's drip mode splits events between subscribers). Steps in arrival order with title, attempt, elapsed, thumbnail; checks and repairs expand; a check followed by a repair is shown failed and the repair says it fixes it. Hairline `<progress>` named Progress. On done: parameter diff against the previous version; `card` adds Open model and Download STL; `dock` collapses. Failed: the error and Retry when `onRetry` is given. `onDone` fires on done and on failed. |
| `AgentStatus` | `{job?, versions, onRevert}` | One `aria-live` line: running step, failure, or `v4 · refine · 2 minutes ago · 3/4 checks pass`. Revert shows when the latest version is an agent one; `onRevert(n)` gets the version to restore as a new one. |
| `VersionScrubber` | `{versions, shown, onShow, onRestore, onCompare}` | Ticks (agent hollow circle, user filled square, shown accent) with hover/focus cards (thumbnail, origin, prompt, time, parameters changed). Click previews (`onShow`); a banner offers Restore as v*n* (`onRestore(shown)`) and Back. `[` `]` / arrows / Home / End step while a tick has focus. Compare: pick another tick, see the parameter diff; `onCompare([shown, other])`, `onCompare()` when it ends (for the ghost outline). |
| `Proposals` | `{modelId, onApplied}` | The suggestions API: change as `Hole X 20.00 → 15.00 mm`, rationale, Apply (`onApplied(job)`), Dismiss; "Suggest changes" in its header. Mount with `key={latestVersion}` so it reloads with the model. |

Pure helpers with tests: `quantities.ts` (the recognised-number parser), `diff.ts` (parameter diffs), `steps.ts` (step verdicts, agent origins, relative time). Styles: `agent.css` on tokens only. Strings: `agent` key in `i18n/agent.ts`; the stable accessible names reuse the existing `prompt`, `timeline`, `refine`, `suggestions` keys. `api.uploadWithProgress` is the only addition to `api.ts`.

## Mounting (B and D)

```tsx
// D, Home / project composer
<CommandBar mode="generate" projectId={id} contextIds={selected} onJob={(job, resend) => setRun({ id: job.id, resend })} />
{run && <AgentStream key={run.id} jobId={run.id} variant="card" onDone={models.reload} onRetry={() => run.resend().then((j) => setRun({ ...run, id: j.id }))} />}

// B, workspace
<CommandBar mode="refine" modelId={id} target={sel && { id: sel, label: nameOf(sel), kind: "part" }} onClearTarget={clear} busy={running} onJob={(j) => setJob(j.id)} onCommand={openPalette} />
{job ? <AgentStream key={job} jobId={job} variant="dock" onDone={ended} /> : <AgentStatus job={last} versions={all} onRevert={restore} />}
<VersionScrubber versions={all} shown={shown} onShow={setPicked} onRestore={restore} onCompare={setGhost} />
<Proposals key={latest} modelId={id} onApplied={(j) => setJob(j.id)} />
```

Global `[` `]` (UI_DIRECTION §5) belong to A2's key layer; it should call the same `onShow`. The parameter row's ghost value for an open proposal and the marker at its target part are B's (read `api.suggestions`).

## Spec changes when the pages mount these

Checked by mounting the components in today's `ProjectPage` and `EditorPage` locally (not committed) and running `npm run e2e` and `npm run parity`: everything passed after these selector changes, and only these (WP-5 flaked once under load and passed alone; it does not touch these components). WP-2's change is already committed (works with both). The others go in with the mount:

- `main-flow.spec.ts`: `.step-kind` reads `["Requirements", "Model written", "Check", "Repair", "Done"]`; restoring is `history.getByRole("button", { name: "v1", exact: true }).click()` then `page.getByRole("button", { name: "Restore v1" }).click()` (the banner button is named `Restore v1 as v3`).
- `parity/editor.spec.ts` PR-7: `Hole X 20.00 → 15.00 mm`, `Apply` for Accept, `Dismiss` for Ignore.
- `parity/context.spec.ts` (D) `generateWithContext`: the `Context files` list has `names.length` items (no Clear item; the selection lives in the Sources sheet).

Then delete `PromptPanel`, `RefineBox`, `Timeline`, `VersionHistory`, `Suggestions` and their tests, and the `prompt.kinds`, `prompt.clearContext`, `timeline.title`, `suggestions.accept/ignore` strings.

## API gaps (UI_DIRECTION §8)

- `Step.detail`: steps show `message`; a check's verdict is read from the next step; the done diff comes from the two versions.
- Cancelling a job: no control until the API has it.
- A job's kind is unknown until it ends (no `GET /jobs/{id}`), so a running stream is titled "Agent at work · *step*".

## Harness

`e2e/harness/agent.html` mounts the components on their own (`?view=home|workspace&theme=light&lang=de&target&context=f3&job=…`) against the mocked API; `e2e/agent.spec.ts` drives them (attach and generate, failure and retry, refine, Revert, proposals, scrubber keys, compare, restore, 390 px). `UI_SHOTS=1 npx playwright test agent` refreshes the screenshots. Delete both once the pages mount the components and their specs cover the same flows.
