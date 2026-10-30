# Figma kit spec: "Sci-fi UI Kit (Free)"

Source: Figma community file `2UpDZL2AakHgvakjVgOrxS`, read through the Figma MCP (`get_design_context`, `get_variable_defs`, asset SVGs) on 2026-10-30.

**Status: partial.** The Figma MCP returned "tool call limit reached on the Starter plan" after the Buttons page. Only **Buttons** was extracted from node data. Every other component is listed under "Not extracted" with its page id. Nothing below was guessed to fill a gap. Values marked "(from screenshot)" come from the render; "(inferred)" means derived from geometry or naming, not read directly.

Already known (not repeated here): colour ramps, fonts (Nippo display, Exo 2 body), type scale, spacing scale.

## Semantic button tokens (read via `get_variable_defs` on the Button set 51:5424)

| Variable | Hex | Probable ramp match (inferred) |
|---|---|---|
| Button/filled-default-on-dark | #ffffff | white |
| Button/filled-hover-on-dark | #d4d4d4 | Neutral 300 |
| Button/filled-pressed-on-dark | #a3a3a3 | Neutral 400 |
| Button/filled-disabled-on-dark | #525252 | Neutral 600 |
| Button/stroke-default-on-dark | #ffffff | white |
| Button/stroke-hover-on-dark | #d55d5d | Primary 400 |
| Button/stroke-pressed-on-dark | #e7a2a2 | Primary 200/300 |
| Button/stroke-disabled-on-dark | #737373 | Neutral 500 |
| Button/filled-default (light bg) | #000000 | Background/black |
| Button/filled-hover (light bg) | #404040 | Neutral 700 |
| Button/filled-pressed (light bg) | #262626 | Neutral 800 |
| Button/filled-disabled (light bg) | #a3a3a3 | Neutral 400 |
| Button/stroke-default (light bg) | #000000 | black |
| Button/stroke-hover (light bg) | #b83030 | Primary 600 |
| Button/stroke-pressed (light bg) | #6f1d1d | Primary 800 |
| Button/stroke-disabled (light bg) | #a3a3a3 | Neutral 400 |
| Text/neutral-primary | #171717 | Neutral 900 |
| Text/neutral-tertiary | #a3a3a3 | Neutral 400 |
| Text/white-primary | #f5f5f5 | Neutral 100 |
| Icon/white / Icon/default / Icon/neutral | #ffffff / #000000 / #a3a3a3 | |
| Mapped Text/Button 1 | Exo 2 Medium 16 / weight 500 / line-height 100% / letter-spacing 0 | |
| Mapped Text/Button 2 | Exo 2 Medium 12 / weight 500 / line-height 100% / letter-spacing 0 | |

The app is dark, so use the `-on-dark` set. The light-bg set is the same structure with inverted values.

## Buttons (page 1:6, component set 51:5424)

Properties: `Type` = Primary | Secondary | Single Stroke | Transparent; `State` = Default | Hover | Pressed | Disable; `Size` = Medium | Large; `onDark` = Yes | No; `Only Icon` = Yes | No. There is **no focus state** in the kit. Labels are always **UPPERCASE** (`text-transform: uppercase`). Default end icon is `arrow-right-02`. No shadows, glows, gradients or radii are used anywhere on buttons. Every corner is square or a 45° chamfer.

### Sizes

| Size | W×H (text + icon) | Icon-only W×H | Side walls | Top band | Body padding | Gap | Label | Icon | Bottom band |
|---|---|---|---|---|---|---|---|---|---|
| Large | 117×42 | 42×42 | 6px each | 4px | 8px all sides | 8px | Exo 2 500 16px uppercase | 19px | 3px |
| Medium | 92×32 | 36×32 | 6px each | 4px | 5px top, 6px bottom, 6px sides | 6px | Exo 2 500 12px uppercase | 16px | 3px |

Height check (Large): 4 top band + 8 + 19 + 8 body + 3 bottom band = 42.

### Primary (filled, "on dark")

The silhouette is built in Figma from solid fill strips plus small SVG triangles. In CSS it collapses to one `clip-path` on a solid background:

- Top-left: square. **Top-right: 6px 45° chamfer.** **Bottom-left: 6px 45° chamfer.** Bottom-right: square.
- **Top-edge notch**: a trapezoid cut 4px deep in the middle third of the body. The body is the width minus the two 6px walls. Its top band splits into three equal segments (fill / gap / fill) joined by 4px 45° slopes.
- **Bottom-edge double notch**: two V-notches, each 6px wide at the edge and 3px deep, with a 2px tooth between them, centred (14px total span).
- **Right-wall vents**: three tiny triangular holes in the right 6px wall, each 3px wide × 1.27px tall at a 2.54px pitch, inset 0.86px from the wall's inner edge, sitting in the lower part of the wall. On Large they sit about 29.6–35.9px from the top; on Medium about 23–29.3px. They point downward (inferred from the flips). The holes cannot be drawn with a single `polygon()`. Use a `mask` with an inline SVG, or an overlaid pseudo-element in the page background colour.

```css
/* Primary / Large and Medium: same polygon, only the height changes */
.btn-primary {
  --seg: calc((100% - 20px) / 3);
  background: var(--fill);
  color: var(--text);
  clip-path: polygon(
    0 0,
    calc(6px + var(--seg)) 0,
    calc(10px + var(--seg)) 4px,
    calc(10px + 2 * var(--seg)) 4px,
    calc(14px + 2 * var(--seg)) 0,
    calc(100% - 6px) 0,
    100% 6px,
    100% 100%,
    calc(50% + 7px) 100%,
    calc(50% + 4px) calc(100% - 3px),
    calc(50% + 1px) 100%,
    calc(50% - 1px) 100%,
    calc(50% - 4px) calc(100% - 3px),
    calc(50% - 7px) 100%,
    6px 100%,
    0 calc(100% - 6px)
  );
  padding: 12px 14px 11px; /* Large: 6 wall + 8 body sides; 4 band + 8 top; 8 + 3 band bottom */
}
```

Medium padding equivalent: `9px 12px 9px` (4+5 top, 6+3 bottom, 6+6 sides).

| State | Fill | Label colour | Icon |
|---|---|---|---|
| Default | #ffffff | #171717 | black arrow |
| Hover | #d4d4d4 | #171717 | black arrow |
| Pressed | #a3a3a3 | #171717 | black arrow |
| Disable | #525252 | #a3a3a3 (Text/neutral-tertiary) | grey arrow (different asset) |

The notches and vents expose whatever sits behind the button, so they only read correctly on a dark backdrop.

### Secondary (outline, "on dark")

- The silhouette matches Primary: chamfered top-right and bottom-left. The chamfer is a **1px** line drawn as a rotated 1px bar in a 6.707px box. The square corners and the straight edges are 1px lines (`border-top` and `border-bottom` on the body, 1px vertical bars in the walls).
- Background: none (transparent).
- **Top tab (inverse of Primary's notch)**: a solid trapezoid in the stroke colour hangs 4px down from the top border across the middle third. It is wide at the top and narrower by 4px on each side at the bottom (45° sides).
- **Corner accent**: a solid 4×4px right triangle sits in the cut-away bottom-left corner, outside the chamfer line. Its right angle is at the outer bottom-left and it runs parallel to the chamfer. There is no matching accent at top-right.
- Bottom band: 3px with 12px side padding. Its two "Polygon" layers are empty, so nothing shows.
- Label and icon colour = stroke colour.

| State | Stroke, tab, accent and label |
|---|---|
| Default | #ffffff |
| Hover | #d55d5d |
| Pressed | #e7a2a2 |
| Disable | #737373 |

Hover, pressed and disabled were read from the variable set. That the label follows the stroke colour in those states is inferred from the default variant, where both use `Button/stroke-default-on-dark`.

How to draw it: an absolutely positioned inline SVG frame (`preserveAspectRatio="none"` will not keep the 45° corners, so draw the path at the button's measured width, or build it from a 9-slice `border-image`). A cheaper alternative is two stacked `clip-path` layers: the outer polygon in the stroke colour, then an inner polygon inset 1px in the background colour, plus a pseudo-element for the tab.

### Single Stroke (text + underline accent)

- Padding: 12px top, 9px bottom, 14px sides. Gap 8px. Label 16px uppercase, colour = stroke var. Height 42 (Large).
- Under the content are two 1px rules: **row 1 covers only the right half** of the width, and **row 2 covers the full width** directly below it. Colour = stroke var (the same per-state table as Secondary).

```css
.btn-single-stroke {
  background:
    linear-gradient(var(--stroke), var(--stroke)) right bottom 1px / 50% 1px no-repeat,
    linear-gradient(var(--stroke), var(--stroke)) left bottom / 100% 1px no-repeat;
}
```

### Transparent (text only)

- Padding: 12px top, 11px bottom, 14px sides. Gap 8px. Label 16px uppercase, colour = stroke var. No decoration.

### Icon-only variants

- 42×42 (Large) and 36×32 (Medium). They use the same type and state matrix, with the label removed. Node data was not read, so treat them as the same frame construction with the icon centred.

### Icon observed: `arrow-right-02`

- Drawn as **filled outlines, not live strokes**. It is a chevron about 2.25px thick at the tips plus a 1.58px horizontal shaft whose end tapers into the chevron. It sits in a 19px box (16px on Medium) with insets of 8.33% top, 23.63% right, 9.17% bottom and 20.83% left.
- Sharp, mitred, geometric corners with no rounding.
- It is exportable as SVG: the MCP served it as a standalone SVG (`Group 15`, 10.55×15.67 viewBox).

## Not extracted (blocked by the Figma MCP Starter-plan call limit)

These need another pass once the MCP quota resets or the plan allows more calls. Node ids are ready for `get_metadata` and `get_design_context`:

| Component | Page id |
|---|---|
| Cover / page background (dot grid, glows) | 0:1 |
| Icons system | 1:12 |
| Checkboxes | 1:14 |
| Dropdown | 1:18 |
| Links | 131:1234 |
| Loaders | 1:21 |
| Radio buttons | 1:15 |
| Sliders | 1:17 |
| Tag | 4037:8 |
| Text fields | 1:7 |
| Toggles | 1:16 |
| Avatar | 4009:1252 |
| Search bar | 1:22 |
| Content switcher | 4042:400 |
| Breadcrumbs | 1:26 |
| Pagination | 1:27 |
| Navigation Bar | 4009:1429 |
| Toast message | 4009:1540 |

Partial observation from the Buttons documentation frame (51:5422), read from metadata only (no colours or sizes beyond those listed): each page's doc header has a 10px-tall "top element" band. It is made of three 345px bars separated by two 10×10 triangles, followed by a 7px row of small chevron vectors (one 37.8×7 lead piece plus seven 18.55×7 repeats at about 17.55px pitch) on the left and a 14×7 vector on the right. This is the kit's recurring divider ornament.
