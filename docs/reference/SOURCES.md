# Reference sources (M0 Phase 0)

All sources accessed 2026-10-25. Public access only: no logins, no paywalls bypassed, no calls to the reference product's API or app. Source IDs (S#) are cited from every other file in `docs/reference/`.

Method notes:
- kyrall.com is a client-rendered single-page app (Vite bundle; empty HTML shell). It was read by rendering it in a browser like a normal visitor.
- Videos were not "watched" for audio. Where a video exposed public auto-captions (YouTube ASR) these were read; otherwise frames were sampled visually. Video frame timestamps are approximate (±10 s for short videos, ±30 s for the talk, because player seeking snaps to keyframes).
- X posts were read only through X's public embed (publish.twitter.com oEmbed / platform.twitter.com embed / syndication JSON used by embeds). Long-post text beyond the embed truncation was not available.
- Cookie banners: always "Reject all" / "decline".

| # | Source | URL | Accessed | Status | Notes |
|---|---|---|---|---|---|
| S1 | kyrall.com homepage | https://kyrall.com/ | 2026-10-25 | read | Rendered in browser; all sections, FAQ, pricing block, image alt texts, link targets. See website.md |
| S2 | Pricing page | https://kyrall.com/pricing | 2026-10-25 | read | Plan cards + "Compare plans" table (checkmarks read visually) |
| S3 | API documentation page | https://kyrall.com/documentation | 2026-10-25 | read | Public page. Endpoints listed; API itself NOT called. See docs-api.md |
| S4 | Contact, Imprint, Terms | https://kyrall.com/contact, /impressum, /terms-and-conditions | 2026-10-25 | skipped | Legal/contact, out of scope |
| S5 | Sign-in / sign-up / dashboard | https://kyrall.com/signin, /signup?redirect=/dashboard/api-docs | 2026-10-25 | inaccessible: login required (not attempted by rule) | Only the link targets were recorded |
| S6 | Blog index + RSS | https://kyrall.ghost.io/ , https://kyrall.ghost.io/rss/ | 2026-10-25 | read | 7 posts found (Jul 2025 – Jul 2026) |
| S7 | Blog: Introducing Kyrall (2025-07-03) | https://kyrall.ghost.io/introducing-kyrall/ | 2026-10-25 | read | |
| S8 | Blog: Avoiding the Horseless Carriage (2025-08-26) | https://kyrall.ghost.io/avoiding-the-horseless-carriage/ | 2026-10-25 | read | Contains an AI-generated UI concept image (filename "ChatGPT-Image…") |
| S9 | Blog: Beyond the Chatbox (2025-09-26) | https://kyrall.ghost.io/beyond-the-chatbox-rethinking-interfaces-for-ai-first-products/ | 2026-10-25 | read | |
| S10 | Blog: From Whale Oil to Coal (2025-10-31) | https://kyrall.ghost.io/from-whale-oil-to-coal-and-non-linear-thinking/ | 2026-10-25 | read | No product features |
| S11 | Blog: You Don't Need Full Control (2026-03-09) | https://kyrall.ghost.io/you-dont-need-full-control-in-3d-design-you-need-the-right-result/ | 2026-10-25 | read | |
| S12 | Blog: The Strawman Critique of "Text-to-CAD" (2026-04-24) | https://kyrall.ghost.io/the-strawman-critique-of-text-to-cad/ | 2026-10-25 | read | |
| S13 | Blog: Today, we're officially launching Kyrall (2026-07-06) | https://kyrall.ghost.io/today-were-officially-launching-kyrall/ | 2026-10-25 | read | 2 product screenshots viewed (Editor; Context Manager + Knowledge Graph) |
| S14 | DEVELOP3D launch article (2026-07-06) | https://develop3d.com/cad/kyrall-launches-its-ai-automated-cad-modeller/ | 2026-10-25 | read | 2 product images viewed (editor, newer Context Manager) |
| S15 | deutsche-startups.de tag page | https://www.deutsche-startups.de/tag/kyrall/ | 2026-10-25 | read | One relevant article |
| S16 | deutsche-startups.de "5 neue Startups" (2025-07-30) | https://www.deutsche-startups.de/2025/07/30/neue-startups-cupped-go-ava-colibrie-nghty-berlin-kyrall/ | 2026-10-25 | read | WebFetch got 403; read via normal browser rendering. Names founders |
| S17 | Industrial AI Network talk write-up (talk 2026-09-25) | https://www.industrial-ai-network.com/events/monthly-industrial-ai-call-2026-09/talks/kyrall | 2026-10-25 | read | Links YouTube recording fYg4AnrUTMA |
| S18 | Industrial AI Network event page | https://www.industrial-ai-network.com/events/monthly-industrial-ai-call-2026-09 | 2026-10-25 | partial: page stuck on "Loading events…" | No agenda text obtained |
| S19 | Industrial AI Network company profile | https://www.industrial-ai-network.com/companies/kyrall | 2026-10-25 | inaccessible: rendered empty (likely member-only content) | |
| S20 | YouTube talk recording (12:09) | https://youtu.be/fYg4AnrUTMA | 2026-10-25 | read | Title, description, publish date, full public English auto-captions, ~20 sampled slide frames. See talk-2026-09.md |
| S21 | Xometry Pro interview "Clicking in CAD by Itself Is Not Engineering" (2026-06-16) | https://xometry.pro/en/articles/ai-interviews-kyrall/ | 2026-10-25 | read | Contains the "text-to-CAD is a bad name" remark; 4 product images viewed |
| S22 | Xometry Pro "We Tested 7 Text-to-CAD Tools" (2025-08-26) | https://xometry.pro/en/articles/text-to-cad-tools-test/ | 2026-10-25 | partial | Kyrall not mentioned in the read portion; not relevant |
| S23 | Xometry Pro AI Engineering Tools Directory | https://xometry.pro/en/tools/ai-engineering-tools-directory/ | 2026-10-25 | partial | Kyrall entry read; rest of page not needed |
| S24 | X launch post by @osaAtwi (2026-07-06) | https://x.com/osaAtwi/status/2074154043375595984 | 2026-10-25 | partial: public embed only; long-post text truncated by X | Full text recovered from the identical LinkedIn repost (S28). Attached 107 s video viewed via public embed media (same video as S40) |
| S25 | X @kyrall_ profile and other @osaAtwi posts | https://x.com/kyrall_ , https://x.com/osaAtwi | 2026-10-25 | inaccessible: timelines require login | Search snippet only: account joined May 2025, few posts, first post is the launch |
| S26 | X post by @marcusyul (paid partnership, 2026-07-06) | https://x.com/marcusyul/status/2074170897821245905 | 2026-10-25 | partial: public embed, text truncated | Third-party promo; 72 s video not reviewed |
| S27 | X article "We're Bringing SimArena to TUM" | https://x.com/i/article/2099717573810278433 | 2026-10-25 | inaccessible: X articles require login | Search snippet only: Kyrall listed as a hackathon challenge (design a gripper from a part description, manufacture, test on a real arm) |
| S28 | LinkedIn company page (guest view) | https://www.linkedin.com/company/kyrall | 2026-10-25 | read | About section + 9 visible posts (Feb–Oct 2026) |
| S29 | LinkedIn founder profiles (Osama Atwi, Ben Stickelbrucks) | https://www.linkedin.com/in/ben-stickelbrucks/ | 2026-10-25 | inaccessible: profile detail requires login | Founder posts were read where reposted on S28 |
| S30 | LinkedIn post video: Onshape batch gripper generation (~Mar 2026) | (video embedded in S28 post) | 2026-10-25 | read | 22 s video, frames sampled |
| S31 | Ashby job board (public posting API) | https://jobs.ashbyhq.com/kyrall | 2026-10-25 | read | 3 open postings. See jobs.md |
| S32 | Indeed company jobs | https://de.indeed.com/cmp/Kyrall/jobs | 2026-10-25 | read | Same 3 postings. A search snippet referenced a "Full-Stack Engineer (Frontend + Backend)" posting that is no longer listed |
| S33 | Built In company page | https://builtin.com/company/kyrall/jobs | 2026-10-25 | partial: search snippet only | 11 employees, founded 2025 |
| S34 | GitHub repo havenousername/fullstack-kyrall (2026-04-16) | https://github.com/havenousername/fullstack-kyrall | 2026-10-25 | read (README) | Third-party "Fullstack Developer Test"; attribution to Kyrall is inferred from the repo name only |
| S35 | GitHub org | https://github.com/kyrall | 2026-10-25 | inaccessible: no such org | GitHub user "Kyrall" exists with 0 public repos, created 2021; no evidence it is the company |
| S36 | Dealroom | https://app.dealroom.co/companies/kyrall | 2026-10-25 | inaccessible: 403 / Cloudflare bot verification (not bypassed) | |
| S37 | Caplight | https://www.caplight.com/company/kyrall | 2026-10-25 | inaccessible: sign-up wall | Search snippet only |
| S38 | MakerSpace workshop listing "M-CAD-007E Generative Design Workshop with Kyrall" | https://makerspace.spaces.nexudus.com/events/1415695219/m-cad-007e-generative-design-workshop-with-kyrall/tickets?v=latest | 2026-10-25 | partial: page rendered empty; search snippet only | Snippet: status CANCELLED; participants design a functional part, prepare it for printing, get 3 months free access. Dates from S28: 2026-02-26 Munich, 2026-03-07 Garching |
| S39 | YouTube channel @Kyrall_Gen | https://www.youtube.com/@Kyrall_Gen | 2026-10-25 | read | 4 videos + 1 short |
| S40 | YouTube "This Drone-frame Was Designed By AI" (107 s, 2026-07-06) | https://www.youtube.com/watch?v=08i69Bye5n8 | 2026-10-25 | read | Public auto-captions + frames (frames sampled from the identical X embed video) |
| S41 | YouTube Short "AI-generated 3D models you can actually use" (45 s, 2026-07-02) | https://www.youtube.com/watch?v=D8eXeQFqBpk | 2026-10-25 | read | Auto-captions + 4 frames |
| S42 | YouTube: "3D Printing Parts for a Blended Wing Drone" (40 s), "Air Intake Timelapse" (15 s), "Aircraft Conceptual Design Exploration with Kyrall.com" (2 s) | https://www.youtube.com/watch?v=G0FAPj9hHU4 , …=djf4s4PWLcw , …=C6KUD4AxuUM | 2026-10-25 | partial: metadata only | No captions; frames not sampled |
| S43 | Product Hunt listing | https://www.producthunt.com/products/kyrall | 2026-10-25 | read | Launched ~June 2026, 13 points, 4 comments |
| S44 | hunted.space | https://hunted.space/product/kyrall | 2026-10-25 | partial: search snippet only | 14 upvotes, #35 daily |
| S45 | runtimewire article (2026-07-08) | https://runtimewire.com/article/kyrall-parametric-cad-ai-hardware | 2026-10-25 | read | Secondary summary; no new facts |
| S46 | docs.kyrall.com | https://docs.kyrall.com | 2026-10-25 | inaccessible: host does not resolve / no response | API docs live at S3 instead |
| S47 | TikTok @kyrall_gen, Instagram @kyrall_gen, Discord invite | https://www.tiktok.com/@kyrall_gen , https://www.instagram.com/kyrall_gen/ , https://discord.gg/gCvZgGyx | 2026-10-25 | inaccessible: not fetched (login/app walls; Discord requires an account) | Links taken from S1 footer |
| S48 | Vimeo, podcasts, other conference talks | web search (EN + DE) | 2026-10-25 | searched, none found | Only S20 talk and the LinkedIn-mentioned AllgäuGoesAdditive 2026 talk (no recording found) |
