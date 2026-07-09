from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .html_renderer import render_html_outputs


def render_outputs(payload: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    render_input = out_dir / "render-input.json"
    render_input.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    script = Path(__file__).with_name("render_receipt.ps1")
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        raise RuntimeError("PowerShell is required for PNG rendering in this dependency-free build.")
    subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-InputJson",
            str(render_input),
            "-OutputDir",
            str(out_dir),
        ],
        check=True,
    )
    render_html_outputs(payload, out_dir)
    render_input.unlink(missing_ok=True)


def write_character_svg(path: Path, payload: dict[str, Any] | None = None) -> None:
    dna = (payload or {}).get("character_dna") if isinstance(payload, dict) else {}
    if not isinstance(dna, dict):
        dna = {}
    color = str(dna.get("spot_color") or "#139FD8")
    label = str(dna.get("specimen_label") or dna.get("persona_title") or "CODEX-SPEC")[:24]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
<rect width="1024" height="1024" fill="none"/>
<g fill="none" stroke="{color}" stroke-width="24" stroke-linecap="square" stroke-linejoin="miter">
  <rect x="178" y="164" width="668" height="520"/>
  <path d="M178 306 H846"/>
  <path d="M262 684 V808 H762 V684"/>
  <path d="M286 408 H476 V574 H286 Z"/>
  <path d="M542 390 H762 V604 H542 Z"/>
  <path d="M584 438 H720 M584 486 H720 M584 534 H690"/>
  <path d="M356 348 V260 H470 V348"/>
  <path d="M376 742 H650"/>
  <path d="M250 840 H804"/>
  <path d="M246 126 H810"/>
</g>
<g fill="{color}">
  <rect x="332" y="444" width="24" height="24"/>
  <rect x="390" y="444" width="24" height="24"/>
  <rect x="332" y="502" width="82" height="24"/>
  <rect x="214" y="220" width="24" height="24"/>
  <rect x="262" y="220" width="24" height="24"/>
  <rect x="310" y="220" width="24" height="24"/>
</g>
<g fill="{color}" font-family="Consolas, monospace" font-size="38">
  <text x="250" y="980">{label}</text>
</g>
</svg>
"""
    path.write_text(svg, encoding="utf-8")
