# Website: kyrall.com (S1, S2)

Accessed 2026-10-25. All text summarised in our own words; quotes are short and attributed. API docs page is in `docs-api.md`.

## Technical observations (public HTML shell, S1)

- Client-rendered SPA. The HTML only contains `<div id="app">`; scripts are Vite-style hashed modules.
- Preloaded vendor chunks named for: three.js (3D viewer), lottie (animations), lucide and tabler (icon sets), Sentry (error monitoring). This is the only first-party stack evidence found.
- Navbar: Pricing, Blog (links to `kyrall.ghost.io`), Career (links to Ashby), Contact Us, a language selector showing "English", "Get started" (to `/signin`).
- Footer: Career, Contact, Imprint, Documentation (`/documentation`), Terms; socials LinkedIn, Discord, TikTok (@kyrall_gen), YouTube (@Kyrall_Gen), Instagram (@kyrall_gen), X (@kyrall_). Address Ridlerstraße 31, 80339 Munich. Kyrall GmbH.

## Homepage sections, in order

1. **Hero.** Large drone render: an X-configuration quadcopter frame (central body plate, four arms, motor-mount pads at arm tips). A vertical before/after slider divides it: left half rendered dark carbon-fibre look, right half plain white CAD look. Image alt texts "White Quad Frame" and "Rendered Quad Frame"; slider handle button "START BUILDING NOW". Tagline: from concept to manufacturable model "in minutes".
2. **Prompt card** titled "How engineering should be": a text box (placeholder asks for a description to generate a 3D model), attachment buttons IMAGE, MESH, FILE, and a GENERATE button. All controls link to sign-in.
3. **"How it works"** heading, four feature tiles:
   - *Bring your ideas. In any format.* Inputs named: a text file with exact specifications, a sketch or image of a part, or a high-level prompt, turned into a parametric 3D model. Visual: blocky white assembly with floating input badges "TEXT PROMPT", "MESH", "FILE", "IMAGE".
   - *Design at the speed of thought.* Claim: less manual drafting/clicking, faster design-to-manufacturing. Visual: a white glider/sailplane model with an AI suggestion bubble "Increase length to 450mm for higher fineness" and two buttons IGNORE / ACCEPT.
   - *Ready to manufacture.* Claim: generates functional parametric CAD instead of static mesh files. Visual: a round pipe flange (hub plus bolt circle) with three format tags GLB, STL, STEP.
   - *Build on your own terms.* Claim: adjust any model with parameters and prompts. Visual: a flanged adapter (rectangular base plate with four bolt holes, tubular body, round top flange with holes) next to a dark "Parameters" panel with sliders and numeric fields:
     - Adapter Height 60.0 MM
     - Base Bolt Dia 8.5 MM
     - Base Bolt Spacing X 85.0 MM
     - Base Bolt Spacing Y 60.0 MM
4. **"Move faster / Connect your workflows"**: three stage cards Ideate (chips REQUIREMENT ENGINEERING, DESIGN LOOP), Generate (DETAILED DEVELOPMENT), Manufacture (FINAL DELIVERY). Line: less time modeling, more time building.
5. **API block**: "Plug into your stack": call the product from your own backend or tools to automate CAD workflows. Buttons VIEW API DOCS (`/documentation`) and GET API ACCESS (`/signup?redirect=/dashboard/api-docs`, i.e. API tokens live in a dashboard page "api-docs").
6. **Pricing** (same as S2, below).
7. **FAQ** (four answers, paraphrased):
   - What can I generate? Fully parametric, editable 3D models from text, sketches and mesh inputs.
   - Need CAD experience? No; works from high-level instructions, aimed at beginners too.
   - Can I refine/customise? Yes; every model is parametric, so you adjust dimensions and features by selecting edges, faces or parameters.
   - Just tell it what I want? Yes; provide text, images, sketches or meshes. More context gives better output, so upload as many inputs as needed.
8. **Example prompt chips** near the CTA: "Hollow cylinder, 50mm height, 2mm wall thickness" and "T-joint bracket for 2020 aluminum extrusion".
9. **Final CTA** "Ready to build?" / "Fix your workflow".

No demo video is embedded on the site; motion is SVG/lottie illustration only.

## Pricing (S1, S2)

| | Starter | Premium | Enterprise |
|---|---|---|---|
| Price | Free | €20/month monthly, €16/month billed yearly ("save 20%") | Custom ("talk to us") |
| Generations ("Kyrall Generate") | 10 | Unlimited | Unlimited |
| Card bullets | 10 generations; online model editor; segment selection & assemblies | Unlimited generations; API access; Knowledge Graph; Context Manager | Advanced integrations; custom workflows; built to your compliance standards; dedicated onboarding |
| API access | – | yes | yes |
| Knowledge Graph | – | yes | yes |
| Editor, History, Measurements, Share, Export, AI suggestion | "First 10 generations only" | yes | yes |
| Custom | – | – | yes |

Takeaways for parity: named product surfaces are **Editor, History, Measurements, Share, Export, AI suggestion, Segment selection & assemblies, Knowledge Graph, Context Manager, API**. Quota/plan gating exists but is a business feature.

## Claims inventory (website)

- Speed: "In minutes" (concept to manufacturable model). No benchmark given.
- Output: fully functional, parametric CAD, not static meshes; exports GLB, STL, STEP.
- Editing: parameters + prompts; edge/face/parameter selection.
- "Ready to manufacture": asserted, no DFM details on the site (DFM detail is in S21).
- API: yes, see `docs-api.md`.
- No accuracy claims on the site.
