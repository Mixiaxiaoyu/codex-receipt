# Visual Gap Analysis

## Failures In The Previous Version

- The full receipt was generated with image generation, so layout, paper, text, and illustration drifted between runs.
- The renderer was treated as a structural preview rather than the final artifact.
- The package either depended on raw reference PNG files or tried to fake the paper procedurally, so the visual system had no stable template layer.
- The visual language allowed market-collage labels, creature/specimen language, and fixed animal-like metaphors that did not match the requested stable receipt system.
- Persona illustration prompts could ask for the full receipt, which made text and layout unstable.

## Non-Negotiable Fixes

- Full receipt output must be deterministic code-rendered PNG.
- Image generation may produce only a persona illustration asset.
- The final skill package may contain only cleaned runtime skin assets under `assets/`; raw reference screenshots, inspiration images, and demo references are forbidden.
- The receipt layout must come from a fixed contract and fixed renderer coordinates.
- Paper texture, edge roughness, and adaptable length must come from the cleaned receipt texture skin.
- Text, stamp, barcode, and illustration must be placed by an HTML/CSS UI layer above the skin.
- Final PNG must be a headless-browser screenshot of `receipt.html`.
- The red ticket must use a distressed stamp texture, always read `OUTPUT TIME`, and use `generated_at_local`.
- The persona illustration must follow the pixel contract: simple 1-bit or single-accent, low-resolution, hard-edged, non-photographic, no animal mapping, no full receipt text, no dense machinery or busy technical collage.

## Reject Output If

- The whole receipt was made by image generation.
- Layout elements move based on prompt interpretation.
- The skill package contains raw reference images or any non-skin image assets.
- The illustration looks like a smooth mascot, animal mapping, 3D object, anime character, or modern vector icon.
- The illustration is too complex, crowded, or technical-collage-like.
- The output-time ticket uses a fictional expiry date.
- The public-safe disclaimer is missing.
- Any public output includes usernames, local paths, repository URLs, raw prompts, source code, secrets, or terminal raw output.
