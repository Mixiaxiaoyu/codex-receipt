from __future__ import annotations

import html
import json
import random
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any


CANVAS_W = 1080
PAPER_W = 560
PAPER_X = 260
PAPER_Y = 44
PAPER_H = 2540
FULL_PAPER_H = 3020


def _asset_uri(name: str) -> str:
    return (Path(__file__).resolve().parents[1] / "assets" / name).as_uri()


def _out_uri(out_dir: Path, name: str) -> str:
    return (out_dir / name).resolve().as_uri()


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _dim(payload: dict[str, Any], name: str) -> int:
    return int(payload.get("persona", {}).get("dimensions", {}).get(name, 0) or 0)


def _short_label(label: str) -> str:
    upper = label.upper()
    replacements = {
        "RESEARCH": "RESEARCH & PATTERNING",
        "WRITING": "WRITING / DOCUMENTATION",
        "DEBUG": "DEBUG / PROBLEM SOLVING",
        "CREATIVE": "CREATIVE DIRECTION",
        "DESIGN": "DESIGN / STRUCTURE",
        "MAINTENANCE": "MAINTENANCE / CLEANUP",
    }
    for prefix, replacement in replacements.items():
        if upper.startswith(prefix):
            return replacement
    return upper[:28]


ZH_LABELS = {
    "THREADS": "线程",
    "TURNS": "回合",
    "TOOLS": "工具调用",
    "COMMANDS": "命令",
    "TOKEN": "令牌",
    "TOKEN EST.": "令牌估算",
    "COVERAGE": "覆盖率",
    "EXPLORATION": "探索",
    "EXECUTION": "执行",
    "AUTOMATION": "自动化",
    "ENDURANCE": "耐力",
    "ITERATION": "迭代",
    "SYSTEMS": "系统",
    "CONTROL": "控制",
    "VERIFICATION": "验证",
    "COMMAND RUNS": "命令运行",
    "TOOL CALLS": "工具调用",
    "Research & Patterning": "研究与模式",
    "Writing / Documentation": "写作与文档",
    "Maintenance / Cleanup": "维护清理",
    "Design / Structure": "设计结构",
    "Creative Direction": "创意方向",
    "Debug / Problem Solving": "调试解题",
    "SOURCE": "来源等级",
    "TOKEN COV": "令牌覆盖",
    "PUBLIC SAFE": "公开安全",
    "CONFIDENCE": "置信度",
    "OUTPUT TIME": "输出时间",
    "ORDER": "编号",
    "PERIOD": "周期",
    "TOTAL": "合计",
    "LOCAL RECORD": "本地记录",
}

ZH_CONFIDENCE = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}
ZH_SECONDARY = {
    "Workflow Mechanic": "流程机械师",
    "Discovery Finisher": "探索收束者",
    "Pattern Diver": "模式潜航者",
    "Workflow Explorer": "流程探索者",
    "Structure Keeper": "结构守护者",
    "Automation Handler": "自动化处理者",
    "Quality Hunter": "质量猎手",
    "Loop Survivor": "循环幸存者",
    "Local Record Analyst": "本地记录分析员",
}


def _is_cn(payload: dict[str, Any]) -> bool:
    return str(payload.get("language") or "en").lower() in {"zh", "zh-cn", "cn", "@cn"}


def _label(payload: dict[str, Any], text: str) -> str:
    if not _is_cn(payload):
        return text
    return ZH_LABELS.get(text, ZH_LABELS.get(text.upper(), text))


def _value(payload: dict[str, Any], text: Any) -> Any:
    if not _is_cn(payload):
        return text
    return ZH_CONFIDENCE.get(str(text), ZH_SECONDARY.get(str(text), text))


def _title_lines(title: str) -> tuple[str, str]:
    words = [part for part in title.split(" ") if part]
    if len(words) <= 2:
        return title, ""
    if len(words) == 3:
        return words[0], " ".join(words[1:])
    mid = (len(words) + 1) // 2
    return " ".join(words[:mid]), " ".join(words[mid:])


def _row(label: str, value: Any, small: bool = False) -> str:
    cls = "row small" if small else "row"
    return (
        f'<div class="{cls}">'
        f'<span class="label">{_e(_short_label(label))}</span>'
        f'<span class="dotfill"></span>'
        f'<span class="value">{_e(value)}</span>'
        "</div>"
    )


def _barcode(seed: str) -> str:
    rng = random.Random(sum((i + 1) * ord(ch) for i, ch in enumerate(seed)))
    bars: list[str] = []
    width = 0
    while width < 480:
        bar = rng.randint(2, 6)
        gap = rng.randint(2, 4)
        bars.append(f'<i style="width:{bar}px"></i><b style="width:{gap}px"></b>')
        width += bar + gap
    return '<div class="barcode">' + "".join(bars) + "</div>"


def _capability_rows(payload: dict[str, Any]) -> str:
    names = [
        "EXPLORATION",
        "EXECUTION",
        "AUTOMATION",
        "ENDURANCE",
        "ITERATION",
        "SYSTEMS",
        "CONTROL",
        "VERIFICATION",
    ]
    return "\n".join(_row(_label(payload, name), f"{_dim(payload, name)}%", True) for name in names)


def _activity_rows(payload: dict[str, Any]) -> str:
    stats = payload.get("statistics", {})
    rows = [
        _row(_label(payload, "COMMAND RUNS"), stats.get("command_runs", ""), True),
        _row(_label(payload, "TOOL CALLS"), stats.get("tool_calls", ""), True),
    ]
    categories = payload.get("categories", {})
    if isinstance(categories, dict):
        for key, value in list(categories.items())[:6]:
            rows.append(_row(_label(payload, key), value, True))
    return "\n".join(rows)


def _css(paper_h: int, canvas_h: int, full: bool, language: str = "en") -> str:
    illus_top = 700 if not full else 680
    illus_h = 780 if not full else 900
    core_top = illus_top + illus_h + 75
    font_stack = 'Consolas, "Courier New", monospace'
    if language == "zh-cn":
        font_stack = '"Microsoft YaHei", "Noto Sans CJK SC", SimSun, Consolas, monospace'
    return f"""
@page {{ size: {CANVAS_W}px {canvas_h}px; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: {CANVAS_W}px; height: {canvas_h}px; overflow: hidden; background: #050505; }}
body {{ font-family: {font_stack}; color: #111; }}
.canvas {{ position: relative; width: {CANVAS_W}px; height: {canvas_h}px; background: #050505; }}
.paper {{ position: absolute; left: {PAPER_X}px; top: {PAPER_Y}px; width: {PAPER_W}px; height: {paper_h}px; overflow: hidden; }}
.skin {{ position: absolute; left: 0; width: {PAPER_W}px; pointer-events: none; }}
.skin.top {{ top: 0; height: 260px; background: url('{_asset_uri("receipt-skin-top.png")}') top left / 560px 260px no-repeat; }}
.skin.mid {{ top: 260px; bottom: 300px; background: url('{_asset_uri("receipt-skin-mid.png")}') top left / 560px 220px repeat-y; }}
.skin.bottom {{ bottom: 0; height: 300px; background: url('{_asset_uri("receipt-skin-bottom.png")}') bottom left / 560px 300px no-repeat; }}
.content {{ position: absolute; inset: 0; padding: 0 40px; text-rendering: geometricPrecision; }}
.center {{ text-align: center; }}
.title {{ margin-top: 54px; font-size: 38px; line-height: 42px; font-weight: 800; letter-spacing: 1px; }}
.subhead {{ margin-top: 14px; font-size: 16px; line-height: 19px; font-weight: 700; }}
.rule {{ height: 8px; margin: 20px auto 0; width: 480px; background: radial-gradient(circle, #111 2.4px, transparent 2.8px) left center / 14px 8px repeat-x; }}
.specimen {{ margin-top: 45px; font-size: 17px; font-weight: 700; }}
.persona-title {{ margin-top: 16px; font-size: 36px; line-height: 40px; font-weight: 900; letter-spacing: 1px; }}
.secondary {{ margin-top: 7px; font-size: 20px; font-weight: 600; }}
.meta {{ position: absolute; left: 40px; top: 382px; width: 480px; font-size: 16px; line-height: 28px; font-weight: 700; }}
.ticket {{ position: absolute; right: 0; top: 8px; width: 190px; height: 86px; color: #c42a20; background: url('{_asset_uri("stamp-output-time.png")}') center / 190px 86px no-repeat; text-align: center; mix-blend-mode: multiply; }}
.ticket strong, .ticket .dots {{ display: none; }}
.ticket span {{ position: absolute; left: 0; top: 57px; width: 190px; display: block; font-size: 15px; line-height: 18px; font-weight: 900; letter-spacing: .2px; color: transparent; background: radial-gradient(circle, rgba(255,255,250,.96) 0 1px, transparent 1.25px) 3px 2px / 11px 7px, linear-gradient(rgba(196,42,32,.82), rgba(196,42,32,.82)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; filter: drop-shadow(.42px 0 rgba(196,42,32,.38)) drop-shadow(-.28px 0 rgba(196,42,32,.2)); }}
.ticket span::after {{ content: ""; position: absolute; inset: 0 18px; background: linear-gradient(90deg, transparent 0 18%, rgba(255,255,250,.65) 18% 20%, transparent 20% 100%) 0 0 / 41px 100%; opacity: .2; mix-blend-mode: screen; pointer-events: none; }}
.rule.stats {{ position: absolute; left: 40px; top: 488px; margin: 0; }}
.stats-block {{ position: absolute; left: 40px; top: 533px; width: 480px; }}
.row {{ display: flex; align-items: baseline; height: 28px; font-size: 17px; line-height: 24px; font-weight: 700; white-space: nowrap; }}
.row.small {{ height: 22px; font-size: 14px; line-height: 19px; font-weight: 700; }}
.label {{ flex: 0 0 auto; min-width: 144px; }}
.row.small .label {{ min-width: 168px; }}
.dotfill {{ flex: 1 1 auto; height: 8px; margin: 0 9px 2px 10px; background: radial-gradient(circle, currentColor 1.35px, transparent 1.75px) left center / 11px 8px repeat-x; opacity: .96; }}
.value {{ flex: 0 0 auto; text-align: right; min-width: 34px; }}
.illustration {{ position: absolute; left: 30px; top: {illus_top}px; width: 500px; height: {illus_h}px; display: flex; align-items: center; justify-content: center; }}
.illustration img {{ display: block; max-width: 500px; max-height: {illus_h}px; image-rendering: pixelated; }}
.rule.after-illustration {{ position: absolute; left: 40px; top: {core_top - 35}px; margin: 0; }}
.core {{ position: absolute; left: 40px; top: {core_top}px; width: 480px; }}
.section-title {{ font-size: 20px; line-height: 24px; font-weight: 900; margin-bottom: 10px; }}
.rule.tight {{ width: 480px; margin: 7px 0 22px; }}
.activity {{ margin-top: 6px; }}
.record {{ margin-top: 16px; }}
.note {{ margin-top: 9px; font-size: 12px; line-height: 17px; font-weight: 700; }}
.total-row {{ display: flex; align-items: baseline; margin-top: 18px; height: 30px; font-size: 19px; font-weight: 900; }}
.total-row .label {{ min-width: 76px; }}
.barcode {{ display: flex; align-items: stretch; width: 480px; height: 70px; margin-top: 10px; overflow: hidden; }}
.barcode i {{ display: block; height: 70px; background: #111; }}
.barcode b {{ display: block; height: 70px; background: transparent; }}
.footer {{ margin-top: 20px; text-align: center; font-weight: 800; }}
.footer .dup {{ font-size: 20px; line-height: 25px; }}
.footer .keep {{ font-size: 14px; line-height: 22px; }}
.footer .small {{ font-size: 13px; line-height: 18px; font-weight: 700; }}
"""


def _html(payload: dict[str, Any], out_dir: Path, *, full: bool) -> tuple[str, int]:
    paper_h = FULL_PAPER_H if full else PAPER_H
    canvas_h = paper_h + PAPER_Y * 2
    stats = payload.get("statistics", {})
    persona = payload.get("persona", {})
    receipt = payload.get("receipt", {})
    language = "zh-cn" if _is_cn(payload) else "en"
    title = persona.get("title_cn") if language == "zh-cn" else persona.get("title")
    line1, line2 = _title_lines(str(title or "NIGHT SHIFT FIELD OPERATOR"))
    illustration = _out_uri(out_dir, "persona-illustration-processed.png")
    css = _css(paper_h, canvas_h, full, language)
    subhead = "本地记录<br>非官方账单" if language == "zh-cn" else "LOCAL RECORD<br>NOT OFFICIAL BILLING"
    specimen = "工作人格样本" if language == "zh-cn" else "WORKING PERSONA SPECIMEN"
    note = "注：所有标识仅属于本地记录。<br>不外传。无个人数据。" if language == "zh-cn" else "NOTE: All identifiers are local to this record.<br>No external transmission. No personal data."
    dup = "*** 副本 ***" if language == "zh-cn" else "*** DUPLICATE COPY ***"
    keep = "请保留记录" if language == "zh-cn" else "KEEP FOR YOUR RECORDS"
    footer = "所有记录均保存在本地 Codex。<br>仅在可信场景分享。" if language == "zh-cn" else "All records are local to Codex.<br>Share only with trust."
    content = f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
<main class="canvas">
  <article class="paper">
    <div class="skin top"></div>
    <div class="skin mid"></div>
    <div class="skin bottom"></div>
    <div class="content">
      <div class="center title">CODEX RECEIPT</div>
      <div class="center subhead">{subhead}</div>
      <div class="rule"></div>
      <div class="center specimen">{specimen}</div>
      <div class="center persona-title">{_e(line1)}<br>{_e(line2)}</div>
      <div class="center secondary">{_e(_value(payload, persona.get("secondary", "")))}</div>
      <section class="meta">
        <div>{_e(_label(payload, "ORDER"))}: {_e(receipt.get("order", ""))}</div>
        <div>{_e(_label(payload, "PERIOD"))}: {_e(payload.get("period", "all"))}</div>
        <div>{_e(_label(payload, "OUTPUT TIME"))}:</div>
        <div class="ticket"><strong>OUTPUT TIME</strong><i class="dots"></i><span>{_e(payload.get("generated_at_local", ""))}</span></div>
      </section>
      <div class="rule stats"></div>
      <section class="stats-block">
        {_row(_label(payload, "THREADS"), stats.get("threads", ""))}
        {_row(_label(payload, "TURNS"), stats.get("turns", ""))}
        {_row(_label(payload, "TOOLS"), stats.get("tool_calls", ""))}
        {_row(_label(payload, "COMMANDS"), stats.get("command_runs", ""))}
        {_row(_label(payload, stats.get("token_display_label", "TOKEN")), stats.get("tokens_total", ""))}
        {_row(_label(payload, "COVERAGE"), f'{stats.get("coverage_score", "")}%')}
      </section>
      <section class="illustration"><img src="{illustration}" alt=""></section>
      <div class="rule after-illustration"></div>
      <section class="core">
        <div class="section-title">{_e("核心能力" if language == "zh-cn" else "CORE CAPABILITIES")}</div>
        {_capability_rows(payload)}
        <div class="rule tight"></div>
        <div class="section-title activity">{_e("主要活动信号" if language == "zh-cn" else "TOP ACTIVITY SIGNALS")}</div>
        {_activity_rows(payload)}
        <div class="rule tight"></div>
        <div class="section-title record">{_e("记录详情" if language == "zh-cn" else "RECORD DETAILS")}</div>
        {_row(_label(payload, "SOURCE"), stats.get("source_grade", ""), True)}
        {_row(_label(payload, "TOKEN COV"), stats.get("token_coverage_label", ""), True)}
        {_row(_label(payload, "PUBLIC SAFE"), "是" if language == "zh-cn" else "YES", True)}
        {_row(_label(payload, "CONFIDENCE"), _value(payload, persona.get("confidence", "")), True)}
        {_row(_label(payload, "OUTPUT TIME"), payload.get("generated_at_local", ""), True)}
        <div class="note">{note}</div>
        <div class="total-row"><span class="label">{_e(_label(payload, "TOTAL"))}</span><span class="dotfill"></span><span class="value">{_e(_label(payload, "LOCAL RECORD"))}</span></div>
        {_barcode(str(receipt.get("order", "")))}
        <div class="footer">
          <div class="dup">{dup}</div>
          <div class="keep">{keep}</div>
          <div class="small">{footer}</div>
        </div>
      </section>
    </div>
  </article>
</main>
</body>
</html>
"""
    return content, canvas_h


def _browser() -> str:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome") or "",
        shutil.which("msedge") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError("Chrome or Edge is required for HTML receipt rendering.")


def _screenshot(html_path: Path, png_path: Path, height: int) -> None:
    browser = _browser()
    user_data = Path(tempfile.mkdtemp(prefix="codex_receipt_chrome_"))
    chrome_png = png_path.with_name(f"{png_path.stem}.chrome{png_path.suffix}")
    chrome_png.unlink(missing_ok=True)
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--disable-gpu-compositing",
        "--disable-accelerated-2d-canvas",
        "--disable-accelerated-video-decode",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--disable-features=Translate,DawnGraphite,Vulkan,UseSkiaRenderer,CanvasOopRasterization",
        "--force-device-scale-factor=1",
        f"--user-data-dir={str(user_data)}",
        f"--window-size={CANVAS_W},{height}",
        f"--screenshot={chrome_png}",
        html_path.resolve().as_uri(),
    ]
    try:
        result = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not _valid_png(chrome_png):
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Headless browser screenshot failed with exit code {result.returncode}: {stderr}")
        shutil.move(str(chrome_png), str(png_path))
    finally:
        chrome_png.unlink(missing_ok=True)
        if user_data.exists():
            shutil.rmtree(user_data)


def _valid_png(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 24:
        return False
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    width, height = struct.unpack(">II", header[16:24])
    return width == CANVAS_W and height > 0


def _write_visual_check(out_dir: Path, payload: dict[str, Any], share_h: int) -> None:
    asset_dir = Path(__file__).resolve().parents[1] / "assets"
    manifest_path = asset_dir / "receipt-skin-manifest.json"
    skin_manifest: dict[str, Any] = {}
    if manifest_path.exists():
        skin_manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    report = {
        "schema": "codex-receipt.visual-check.v5",
        "deterministic_full_receipt": True,
        "receipt_contract": "receipt-html-texture-v1",
        "illustration_contract": "ai-pixel-persona-simple-v4",
        "language": payload.get("language", "en"),
        "background_strategy": "html_css_texture_skin",
        "renderer": "html-css-headless-browser",
        "share_size": f"{CANVAS_W}x{share_h}",
        "persona_illustration_source": payload.get("persona_illustration_source", "unknown"),
        "ai_illustration_supplied": payload.get("persona_illustration_source") == "supplied-ai-asset",
        "full_receipt_image_generation": False,
        "original_reference_images_embedded": False,
        "template_skin_assets_present": all(
            (asset_dir / name).exists()
            for name in ["receipt-skin-top.png", "receipt-skin-mid.png", "receipt-skin-bottom.png"]
        ),
        "stamp_texture_present": (asset_dir / "stamp-output-time.png").exists(),
        "stamp_strategy": "stamp-output-time.png plus dynamic time",
        "skin_manifest_raw_reference_images_embedded": skin_manifest.get("raw_reference_images_embedded"),
        "skin_manifest_old_text_and_illustration_removed": skin_manifest.get("old_text_and_illustration_removed"),
        "checks": {
            "receipt_html_exists": (out_dir / "receipt.html").exists(),
            "receipt_share_final_exists": (out_dir / "receipt-share-final.png").exists(),
            "receipt_share_exists": (out_dir / "receipt-share.png").exists(),
            "persona_illustration_processed_exists": (out_dir / "persona-illustration-processed.png").exists(),
            "output_time_source": str(payload.get("generated_at_local", "")),
            "public_disclaimer": "LOCAL RECORD / PERSONAL SUMMARY / NOT OFFICIAL BILLING",
        },
    }
    (out_dir / "visual-check-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def render_html_outputs(payload: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    share_html, share_h = _html(payload, out_dir, full=False)
    full_html, full_h = _html(payload, out_dir, full=True)
    share_html_path = out_dir / "receipt.html"
    full_html_path = out_dir / "receipt-full.html"
    share_html_path.write_text(share_html, encoding="utf-8")
    full_html_path.write_text(full_html, encoding="utf-8")
    share_png = out_dir / "receipt-share-final.png"
    _screenshot(share_html_path, share_png, share_h)
    shutil.copyfile(share_png, out_dir / "receipt-share.png")
    _screenshot(full_html_path, out_dir / "receipt-full-01.png", full_h)
    _write_visual_check(out_dir, payload, share_h)
