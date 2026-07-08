# Visual Style Contract

## Core Principle

The receipt must visually match the approved reference family by using a real cleaned receipt texture skin. Do not try to imitate the paper by drawing random rectangles and noise.

## Receipt Skin

The skill includes runtime template assets:

```text
assets/
  receipt-skin-top.png
  receipt-skin-mid.png
  receipt-skin-bottom.png
  stamp-output-time.png
  receipt-skin-manifest.json
```

These are cleaned, content-free texture skin assets derived from the approved receipt material after old text, stamp, barcode, and illustration are removed. They are not raw reference screenshots or intermediate full blank sources. The original reference screenshots must not be bundled.

Rules:

- Canvas width: `1080 px`.
- Paper width: `560 px`.
- Paper x: centered.
- Paper height: dynamic.
- Top skin and bottom skin stay fixed.
- Middle skin repeats or crops vertically to fit content height.
- The black background, paper edge, rough top/bottom, and paper texture come from the skin.
- `receipt.html` places all variable content above the skin as an HTML/CSS UI layer.
- The red `OUTPUT TIME` stamp uses a transparent distressed texture asset, then overlays the dynamic output time.
- A headless browser screenshots the HTML into the final PNG.

## Layout Layer

The HTML/CSS UI layer draws all variable content:

- `CODEX RECEIPT`
- `LOCAL RECORD`
- `NOT OFFICIAL BILLING`
- dotted dividers
- persona title and secondary role
- order/period/output metadata
- red `OUTPUT TIME` ticket
- stats rows
- persona illustration slot
- core capabilities
- top activity signals
- record details
- total/barcode/footer

Different data may change text and total height, but not the visual grammar.

## Illustration Layer

The persona illustration is a separate AI asset:

- generated from `persona-illustration-prompt.txt`
- processed into black/white plus optional blue
- processed with transparent paper pixels so ink prints directly onto the receipt skin
- placed into the fixed illustration slot
- never responsible for drawing the whole receipt
- generated as part of the normal user-facing skill run before final render; placeholder art is only for development/demo fallback

Style target:

- simple 1-bit or single-blue pixel art
- vertical portrait composition, roughly `4:5` to `2:3`
- one clear subject with two to four supporting props
- generous negative space and readable silhouette
- simple role/avatar, desk scene, room corner, field workstation, technical object, or object-totem
- avoids wide landscape-room composition
- avoids dense machinery, crowded wall diagrams, tool piles, cable tangles, and excessive tiny details
- no readable text, no barcode, no receipt page, no UI panel
- no 3D, anime, smooth vector, photorealism, gradients, or animal mapping

## Validation

`visual-check-report.json` must record:

- `receipt_contract: receipt-html-texture-v1`
- `background_strategy: html_css_texture_skin`
- `renderer: html-css-headless-browser`
- dynamic share size
- template skin assets present
- stamp texture present
- skin manifest says old content was removed and raw references were not embedded
- original reference images not embedded
- full receipt image generation disabled
- user-facing final runs record `ai_illustration_supplied: true`
