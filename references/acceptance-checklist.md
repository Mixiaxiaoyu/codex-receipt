# Acceptance Checklist

## Data And Privacy

- Local sessions and `history.jsonl` are parsed only from allowed Codex history locations.
- Credentials, keys, SSH data, browser profiles, and unrelated source trees are not scanned.
- Public output contains no usernames, local paths, repository URLs, emails, IPs, secrets, raw prompts, source code, or raw terminal output.
- `privacy-report.json` exists.

## Visual Output

- `receipt-share-final.png` exists and is `1080 px` wide.
- Height is dynamic and large enough for all content.
- `receipt-layout-contract.json` says `receipt-html-texture-v1`.
- `illustration-style-contract.json` says `ai-pixel-persona-simple-v4`.
- `visual-check-report.json` says `background_strategy: html_css_texture_skin`.
- `visual-check-report.json` says `stamp_texture_present: true`.
- `receipt.html` exists and is the source for the final screenshot render.
- Skin assets exist under `assets/`.
- Raw reference screenshots are not bundled.
- Full receipt image generation is disabled.
- Persona illustration prompt describes only the illustration, not the whole receipt.

## Package

- Allowed image assets are only the receipt skin template pieces and `stamp-output-time.png`.
- No intermediate full blank source image remains in the skill package.
- No old reference, demo, mood, or inspiration images remain.

## Tests

- Unit tests pass.
- Compile check passes.
- Demo mode runs without real Codex history.
- Real generation runs against local history when available.
- Same input and same illustration asset produce the same final PNG hash.
