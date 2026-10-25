# Public API documentation (S3) and docs search (S35, S46)

Source: https://kyrall.com/documentation (public page, read 2026-10-25). The API itself was **not** called or probed.

## What the page documents

- Purpose: programmatically generate and edit parametric 3D models from your own apps, services or automation workflows.
- **Auth**: per-user API token, created and revoked in the dashboard under "API Docs" after sign-in. Token prefix shown as `kyr_api_…`. Sent either as header `X-API-Token: <token>` or `Authorization: Bearer <token>`.
- **Base URL**: `https://core.kyrall.com/api/v1`. All endpoints require a token.
- **Endpoints** (all POST):

| Endpoint | Documented purpose |
|---|---|
| `/api/v1/generate` | Create a new model from a text prompt, optionally with image or mesh references |
| `/api/v1/modify` | Update an existing model from natural-language instructions |
| `/api/v1/edit` | Apply targeted parametric edits to specific components of an existing model |
| `/api/v1/download` | Export a model as GLB, STEP or STL |

- **Example request**: JSON body with a single `prompt` field; the example prompt asks for a metal bracket with angled support and screw holes.
- Batch processing, complex integrations and custom workflows are offered on request ("contact us").
- Not documented publicly: request/response schemas beyond `prompt`, job/async model, polling or webhooks, rate limits, quotas, error codes, model IDs, how attachments are uploaded, how components are addressed in `/edit`.

## Other API/automation evidence

- S21 (interview): API is offered besides the browser tool; with coding copilots you can build narrow apps on top, examples given: an app that takes an STL of a tool and builds a shadow box around it; an app that generates jigs and fixtures from a part.
- S41 (YouTube short): an API-built custom app that designs a personalised phone holder on demand.
- S20 (talk, Blended Wing Drone slide): aircraft sizing tool → XML → "API" → generated aircraft body, "no manual input required".
- S13 (launch post): the public release includes an API for teams building on top.

## Docs search results

- `docs.kyrall.com`: does not resolve (S46).
- GitHub: no `kyrall` organisation; no SDK, OpenAPI spec or examples found (S35). One third-party repo named `fullstack-kyrall` exists (see jobs.md, S34).
- No OpenAPI/Swagger document linked from the public docs page.
