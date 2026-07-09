from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .analyzer import scan_codex_history as scan_history
from .renderer import render_outputs, write_character_svg


DIMENSION_BEHAVIOR: dict[str, str] = {
    "CONTROL": "tight framing, explicit constraints, careful output shape",
    "ITERATION": "repeat-and-refine loops, correction pressure, willingness to retry",
    "EXECUTION": "artifact production, command use, concrete delivery momentum",
    "SYSTEMS": "structure building, reusable workflows, schema and process thinking",
    "VERIFICATION": "checks, tests, evidence, distrust of unverified polish",
    "EXPLORATION": "mapping uncertain territory, broad search, option discovery",
    "AUTOMATION": "turning repeated work into tools, scripts, cached workflows",
    "ENDURANCE": "long-thread persistence, late sessions, staying with unresolved work",
}

DIMENSION_MARKS: dict[str, list[str]] = {
    "CONTROL": ["grid pressure", "ruler-like restraint", "cropped labels", "strict margins"],
    "ITERATION": ["overprinted revision ghosts", "loop marks", "duplicate stamps", "crossed-out versions"],
    "EXECUTION": ["printer teeth", "tool marks", "receipt-feed ribs", "output slots"],
    "SYSTEMS": ["node traces", "modular ribs", "index tabs", "schema folds"],
    "VERIFICATION": ["inspection ticks", "test-strip edges", "warning stamps", "calibration dots"],
    "EXPLORATION": ["map contour lines", "unknown-zone labels", "survey scratches", "compass-like scars"],
    "AUTOMATION": ["input-output channels", "batch stamps", "conveyor seams", "machine registration marks"],
    "ENDURANCE": ["long thread lines", "repair scars", "night scan bands", "worn repeated folds"],
}

RECEIPT_LAYOUT_CONTRACT: dict[str, Any] = {
    "version": "receipt-html-texture-v1",
    "deterministic_full_receipt": True,
    "renderer": "html-css-headless-browser",
    "canvas": {"width": 1080, "height": "dynamic", "background": "#050505"},
    "paper": {"x": 260, "y": 44, "width": 560, "height": "dynamic", "skin": "assets/receipt-skin-*.png"},
    "skin_assets": {
        "top": "assets/receipt-skin-top.png",
        "middle": "assets/receipt-skin-mid.png",
        "bottom": "assets/receipt-skin-bottom.png",
        "manifest": "assets/receipt-skin-manifest.json",
        "stamp": "assets/stamp-output-time.png",
    },
    "fixed_sections": [
        "header",
        "metadata",
        "metrics",
        "persona_illustration",
        "core_capabilities",
        "top_activity_signals",
        "record_details",
        "barcode_footer",
    ],
    "variable_regions": [
        "persona_title",
        "secondary_role",
        "order",
        "period",
        "generated_at_local",
        "statistics",
        "persona_illustration_slot",
        "capability_scores",
        "activity_signals",
    ],
    "forbidden": ["full_receipt_image_generation", "raw_reference_image_embedding", "layout_prompt_drift", "procedural_paper_imitation"],
}

ILLUSTRATION_STYLE_CONTRACT: dict[str, Any] = {
    "version": "ai-pixel-persona-simple-v4",
    "mode": "ai-generated-then-pixel-processed",
    "palette": ["#FFFFFA", "#111111", "#1A72B8"],
    "rules": [
        "1-bit or single-accent pixel illustration",
        "hard edges with no antialiasing after processing",
        "simple persona-specific room scene, desk scene, quiet object scene, or small field-operator vignette",
        "low visual density with one clear subject and two to four supporting props",
        "no readable text inside the illustration",
        "no full receipt layout; renderer places it into the skinned receipt",
        "no animal or creature mapping",
        "no 3D, anime, smooth vector, photorealism, gradients, or mascot blob",
    ],
}


def local_now() -> datetime:
    return datetime.now().astimezone()


def format_local(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_generated_at(value: str | None) -> datetime:
    if not value:
        return local_now()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).astimezone()
        except ValueError:
            continue
    raise SystemExit(f"Invalid --generated-at value: {value!r}. Use YYYY-MM-DD HH:MM.")


def default_output_dir() -> Path:
    return Path.cwd() / "output"


def codex_home() -> Path:
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".codex"


def safe_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def redacted_public_text(value: Any) -> str:
    text = str(value)
    home = str(Path.home())
    if home:
        text = text.replace(home, "[USER_HOME]")
    return text


def public_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    coverage = dict(payload.get("coverage") or {})
    data_sources = dict(coverage.get("data_sources") or {})
    coverage["data_sources"] = {
        "sessions": data_sources.get("sessions", "unknown"),
        "history_jsonl": data_sources.get("history_jsonl", "unknown"),
    }
    coverage["warnings"] = [redacted_public_text(item) for item in coverage.get("warnings") or []]

    performance = dict(payload.get("performance") or {})
    performance.pop("cache_path", None)

    return {
        "schema": payload.get("schema"),
        "mode": payload.get("mode"),
        "period": payload.get("period"),
        "generated_at_iso": payload.get("generated_at_iso"),
        "generated_at_local": payload.get("generated_at_local"),
        "generated_at_ticket": payload.get("generated_at_ticket"),
        "receipt": payload.get("receipt"),
        "statistics": payload.get("statistics"),
        "persona": payload.get("persona"),
        "rhythm": payload.get("rhythm"),
        "categories": payload.get("categories"),
        "easter_eggs": payload.get("easter_eggs"),
        "coverage": coverage,
        "privacy": payload.get("privacy"),
        "performance": performance,
        "character_dna": payload.get("character_dna"),
        "receipt_layout_contract": payload.get("receipt_layout_contract"),
        "illustration_style_contract": payload.get("illustration_style_contract"),
    }


def write_html(path: Path, title: str, payload: dict[str, Any], public: bool) -> None:
    report_payload = public_report_payload(payload) if public else payload
    body = escape_html(json.dumps(report_payload, ensure_ascii=False, indent=2))
    privacy = "PUBLIC SAFE VIEW" if public else "PRIVATE LOCAL VIEW"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ background:#080808; color:#f8f8f4; font-family: Consolas, monospace; margin:40px; }}
    main {{ max-width: 980px; margin:auto; }}
    pre {{ white-space: pre-wrap; background:#111; padding:24px; border:1px solid #333; }}
    h1, h2 {{ letter-spacing: 0.08em; }}
  </style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <h2>{privacy}</h2>
  <p>This is a personal local activity summary, not official billing.</p>
  <pre>{body}</pre>
</main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def demo_payload(generated_at: datetime) -> dict[str, Any]:
    generated_local = format_local(generated_at)
    return {
        "schema": "codex-receipt.v1",
        "mode": "demo",
        "period": "all",
        "generated_at_iso": generated_at.isoformat(),
        "generated_at_local": generated_local,
        "generated_at_ticket": generated_local,
        "receipt": {
            "order": "LOOP-CRT-051783-ASM",
            "store": "CODEX RECEIPT",
            "title": "CODEX RECEIPT",
            "disclaimer": "LOCAL RECORD / PERSONAL SUMMARY / NOT OFFICIAL BILLING",
        },
        "statistics": {
            "active_days": 183,
            "threads": 426,
            "archived_threads": 74,
            "turns": 7193,
            "completed_turns": 6802,
            "failed_turns": 184,
            "interrupted_turns": 207,
            "tool_calls": 28405,
            "command_runs": 934,
            "file_modifications": 1486,
            "projects": 38,
            "tokens_total": 88391744,
            "tokens_input": 38422610,
            "tokens_output": 12874401,
            "tokens_cached": 32781000,
            "tokens_reasoning": 4313733,
            "coverage_score": 94,
            "source_grade": "A-",
        },
        "persona": {
            "title": "NIGHT SHIFT LOOP CARTOGRAPHER",
            "title_cn": "夜行型循环制图师",
            "secondary": "Workflow Mechanic",
            "verdict": "You do not just ask Codex to work. You tune the machine until the work has rhythm.",
            "confidence": "HIGH",
            "dimensions": {
                "CONTROL": 79,
                "ITERATION": 92,
                "EXECUTION": 83,
                "SYSTEMS": 77,
                "VERIFICATION": 65,
                "EXPLORATION": 89,
                "AUTOMATION": 61,
                "ENDURANCE": 72,
            },
        },
        "rhythm": {
            "focus": "02:14:19",
            "build": "01:46:08",
            "verify": "00:54:31",
            "reflect": "00:38:12",
        },
        "categories": {
            "Creative Direction": 84,
            "Research & Patterning": 67,
            "Writing / Documentation": 59,
            "Debug / Problem Solving": 48,
            "Design / Structure": 27,
            "Maintenance / Cleanup": 15,
        },
        "easter_eggs": {
            "Loop Detected": 13,
            "Recursion Depth": 7,
            "Coffee Cycles": 9,
            "Night Mode Activations": 3,
            "Glitches Embraced": 2,
            "Serendipity Bonus": "+8.73%",
        },
        "coverage": {
            "data_sources": {"demo": "available", "codex_history": "not used"},
            "scanned_files": 0,
            "parsed_lines": 0,
            "failed_lines": 0,
            "threads": 426,
            "turns": 7193,
            "turns_with_tokens": 7193,
            "time_range": "demo",
            "coverage_score": 94,
            "warnings": ["Demo data is synthetic and intended for visual regression."],
        },
        "privacy": {
            "public_safe": True,
            "redactions": ["[USER]", "[PROJECT_PATH]", "[REPOSITORY]", "[REDACTED_EMAIL]"],
            "raw_prompts_in_public_output": False,
            "official_billing_claim": False,
        },
        "performance": {},
    }


def recursive_token_sum(value: Any, buckets: dict[str, int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lk = str(key).lower()
            if isinstance(item, int):
                if "cached" in lk and "token" in lk:
                    buckets["tokens_cached"] += item
                elif "reason" in lk and "token" in lk:
                    buckets["tokens_reasoning"] += item
                elif "input" in lk and "token" in lk:
                    buckets["tokens_input"] += item
                elif "output" in lk and "token" in lk:
                    buckets["tokens_output"] += item
                elif lk in {"total_tokens", "tokens_total"}:
                    buckets["tokens_total"] += item
            recursive_token_sum(item, buckets)
    elif isinstance(value, list):
        for item in value:
            recursive_token_sum(item, buckets)


def find_timestamp(record: Any) -> str | None:
    if isinstance(record, dict):
        for key in ("timestamp", "created_at", "updated_at", "time"):
            value = record.get(key)
            if isinstance(value, str) and len(value) >= 10:
                return value
        for value in record.values():
            found = find_timestamp(value)
            if found:
                return found
    elif isinstance(record, list):
        for value in record:
            found = find_timestamp(value)
            if found:
                return found
    return None


def find_project_hint(record: Any) -> str | None:
    if isinstance(record, dict):
        for key in ("cwd", "workdir", "project", "workspace"):
            value = record.get(key)
            if isinstance(value, str) and value:
                return f"PROJECT-{abs(hash(value)) % 10000:04d}"
        for value in record.values():
            found = find_project_hint(value)
            if found:
                return found
    elif isinstance(record, list):
        for value in record:
            found = find_project_hint(value)
            if found:
                return found
    return None


def date_range(dates: set[str]) -> str:
    if not dates:
        return "N/A"
    ordered = sorted(dates)
    return f"{ordered[0]}:{ordered[-1]}"


def scan_codex_history() -> dict[str, Any]:
    home = codex_home()
    files: list[Path] = []
    for root in (home / "sessions", home / "archived_sessions"):
        if root.exists():
            files.extend(root.rglob("rollout-*.jsonl"))
    history = home / "history.jsonl"
    if history.exists():
        files.append(history)

    stats = {
        "active_days": 0,
        "threads": 0,
        "archived_threads": 0,
        "turns": 0,
        "completed_turns": 0,
        "failed_turns": 0,
        "interrupted_turns": 0,
        "tool_calls": 0,
        "command_runs": 0,
        "file_modifications": 0,
        "projects": 0,
        "tokens_total": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "tokens_cached": 0,
        "tokens_reasoning": 0,
        "coverage_score": 0,
        "source_grade": "C",
    }
    parsed_lines = 0
    failed_lines = 0
    dates: set[str] = set()
    projects: set[str] = set()
    threads: set[str] = set()
    warnings: list[str] = []
    token_buckets = {
        "tokens_total": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "tokens_cached": 0,
        "tokens_reasoning": 0,
    }

    for path in files:
        threads.add(path.stem)
        if "archived_sessions" in str(path):
            stats["archived_threads"] += 1
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    text = line.strip()
                    if not text:
                        continue
                    try:
                        record = json.loads(text)
                    except json.JSONDecodeError:
                        failed_lines += 1
                        continue
                    parsed_lines += 1
                    stats["turns"] += 1
                    lower = text.lower()
                    if "tool" in lower:
                        stats["tool_calls"] += 1
                    if "shell_command" in lower or "exec_command" in lower or "command" in lower:
                        stats["command_runs"] += 1
                    if "apply_patch" in lower or "file_change" in lower or "write" in lower:
                        stats["file_modifications"] += 1
                    if "error" in lower or "failed" in lower:
                        stats["failed_turns"] += 1
                    else:
                        stats["completed_turns"] += 1
                    recursive_token_sum(record, token_buckets)
                    ts = find_timestamp(record)
                    if ts:
                        dates.add(ts[:10])
                    project = find_project_hint(record)
                    if project:
                        projects.add(project)
        except OSError as exc:
            warnings.append(f"Could not read {path.name}: {exc}")

    stats.update(token_buckets)
    if stats["tokens_total"] == 0:
        stats["tokens_total"] = (
            stats["tokens_input"] + stats["tokens_output"] + stats["tokens_cached"] + stats["tokens_reasoning"]
        )
    stats["threads"] = len(threads)
    stats["projects"] = len(projects)
    stats["active_days"] = len(dates)
    normalize_tokens(stats, warnings)
    stats["coverage_score"] = 94 if parsed_lines and stats["tokens_total"] else (72 if parsed_lines else 0)
    if not files:
        warnings.append(f"No Codex history files found under {home}.")

    return {
        "statistics": stats,
        "coverage": {
            "data_sources": {
                "codex_home": str(home),
                "sessions": "available" if any((home / name).exists() for name in ("sessions", "archived_sessions")) else "missing",
                "history_jsonl": "available" if history.exists() else "missing",
            },
            "scanned_files": len(files),
            "parsed_lines": parsed_lines,
            "failed_lines": failed_lines,
            "threads": stats["threads"],
            "turns": stats["turns"],
            "turns_with_tokens": stats["turns"] if stats["tokens_total"] else 0,
            "time_range": date_range(dates),
            "coverage_score": stats["coverage_score"],
            "warnings": warnings,
        },
    }


def normalize_tokens(stats: dict[str, Any], warnings: list[str]) -> None:
    turns = int(stats.get("turns") or 0)
    total = int(stats.get("tokens_total") or 0)
    if turns <= 0 or total <= 0:
        return
    max_reasonable = turns * 200_000
    if total <= max_reasonable:
        return
    estimated_total = turns * 6_000
    stats["tokens_total"] = estimated_total
    stats["tokens_input"] = int(estimated_total * 0.44)
    stats["tokens_output"] = int(estimated_total * 0.18)
    stats["tokens_cached"] = int(estimated_total * 0.31)
    stats["tokens_reasoning"] = estimated_total - stats["tokens_input"] - stats["tokens_output"] - stats["tokens_cached"]
    stats["source_grade"] = "D"
    warnings.append(
        "Token fields appear cumulative or duplicated in local logs; token total was replaced with an EST. visible-data estimate."
    )


def clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def persona_from_stats(stats: dict[str, Any], features: dict[str, Any] | None = None) -> dict[str, Any]:
    features = features or {}
    turns = max(int(stats.get("turns") or 0), 1)
    threads = max(int(stats.get("threads") or 0), 1)
    categories = features.get("categories") or {}
    event_counts = features.get("event_counts") or {}
    hours = features.get("hours") or {}
    tools_density = density(stats.get("tool_calls", 0), turns, 25)
    command_density = density(stats.get("command_runs", 0), turns, 20)
    file_density = density(stats.get("file_modifications", 0), turns, 10)
    completed_ratio = stats.get("completed_turns", 0) / turns
    failed_ratio = stats.get("failed_turns", 0) / turns
    turns_per_thread = turns / threads
    night_ratio = night_ratio_from_hours(hours)
    category_total = max(sum(int(v) for v in categories.values()), 1)
    research_ratio = int(categories.get("Research & Patterning", 0)) / category_total
    design_ratio = int(categories.get("Design / Structure", 0)) / category_total
    debug_ratio = int(categories.get("Debug / Problem Solving", 0)) / category_total
    writing_ratio = int(categories.get("Writing / Documentation", 0)) / category_total
    reasoning_ratio = int(event_counts.get("reasoning", 0)) / max(sum(int(v) for v in event_counts.values()), 1)
    dimensions = {
        "CONTROL": clamp(42 + file_density * 32 + command_density * 14 + writing_ratio * 12),
        "ITERATION": clamp(38 + min(turns_per_thread, 80) * 0.75 + reasoning_ratio * 50 + failed_ratio * 35),
        "EXECUTION": clamp(45 + completed_ratio * 18 + command_density * 30 + file_density * 16),
        "SYSTEMS": clamp(40 + min(stats.get("projects", 0), 40) * 0.8 + design_ratio * 36 + file_density * 24),
        "VERIFICATION": clamp(34 + debug_ratio * 60 + command_density * 30 + failed_ratio * 16),
        "EXPLORATION": clamp(40 + min(stats.get("projects", 0), 50) * 1.2 + research_ratio * 70 + category_diversity(categories) * 20),
        "AUTOMATION": clamp(36 + tools_density * 42 + command_density * 28),
        "ENDURANCE": clamp(40 + min(stats.get("active_days", 0), 90) * 0.55 + min(turns_per_thread, 100) * 0.28 + night_ratio * 28),
    }
    confidence = "LOW" if turns < 10 else ("MEDIUM" if turns < 50 else "HIGH")
    title = persona_title(dimensions, hours)
    return {
        "title": title["en"] if turns >= 10 else "PROVISIONAL CODEX SPECIMEN",
        "title_cn": title["cn"] if turns >= 10 else "临时人格",
        "secondary": title["secondary"],
        "verdict": persona_verdict(dimensions, turns, stats),
        "confidence": confidence,
        "dimensions": dimensions,
    }


def night_ratio_from_hours(hours: dict[str, Any]) -> float:
    total = sum(int(v) for v in hours.values())
    if total <= 0:
        return 0
    night = sum(int(v) for hour, v in hours.items() if int(hour) >= 22 or int(hour) < 6)
    return night / total


def density(count: Any, turns: int, cap_per_turn: float) -> float:
    if turns <= 0:
        return 0
    return min(float(count or 0) / turns / cap_per_turn, 1)


def category_diversity(categories: dict[str, Any]) -> float:
    total = sum(int(v) for v in categories.values())
    if total <= 0:
        return 0
    active = sum(1 for v in categories.values() if int(v) > 0)
    return min(active / 6, 1)


def persona_title(dimensions: dict[str, int], hours: dict[str, Any]) -> dict[str, str]:
    top = sorted(dimensions, key=lambda key: dimensions[key], reverse=True)[:2]
    pair = tuple(top)
    primary_map = {
        ("ITERATION", "EXPLORATION"): ("LOOP CARTOGRAPHER", "循环制图师", "Pattern Diver"),
        ("EXPLORATION", "ITERATION"): ("FIELD CARTOGRAPHER", "场域制图师", "Pattern Diver"),
        ("EXPLORATION", "EXECUTION"): ("FIELD OPERATOR", "场域执行者", "Discovery Finisher"),
        ("EXECUTION", "EXPLORATION"): ("OUTPUT CARTOGRAPHER", "产出制图师", "Discovery Finisher"),
        ("EXPLORATION", "AUTOMATION"): ("SURVEY MECHANIC", "勘探机械师", "Workflow Explorer"),
        ("AUTOMATION", "EXPLORATION"): ("FLOW CARTOGRAPHER", "流程制图师", "Workflow Explorer"),
        ("SYSTEMS", "CONTROL"): ("GRID ARCHITECT", "网格架构师", "Structure Keeper"),
        ("CONTROL", "SYSTEMS"): ("PRECISION ARCHITECT", "精密架构师", "Structure Keeper"),
        ("EXECUTION", "AUTOMATION"): ("OUTPUT MECHANIC", "产出机械师", "Automation Handler"),
        ("AUTOMATION", "EXECUTION"): ("FLOW MECHANIC", "流程机械师", "Automation Handler"),
        ("VERIFICATION", "CONTROL"): ("CHECKPOINT KEEPER", "校验守门人", "Quality Hunter"),
        ("CONTROL", "VERIFICATION"): ("CONTROL INSPECTOR", "控制检验员", "Quality Hunter"),
        ("ENDURANCE", "ITERATION"): ("LONG THREAD TUNER", "长线程调音师", "Loop Survivor"),
        ("ITERATION", "ENDURANCE"): ("PERSISTENT TUNER", "持续调音师", "Loop Survivor"),
    }
    en, cn, secondary = primary_map.get(pair, ("CODEX WORK PATTERNIST", "Codex 工作纹样师", "Local Record Analyst"))
    modifier_en, modifier_cn = rhythm_modifier(hours)
    return {"en": f"{modifier_en} {en}", "cn": f"{modifier_cn}{cn}", "secondary": secondary}


def rhythm_modifier(hours: dict[str, Any]) -> tuple[str, str]:
    if not hours:
        return "LOCAL", "本地型"
    peak = max(hours.items(), key=lambda item: int(item[1]))[0]
    hour = int(peak)
    if hour >= 22 or hour < 6:
        return "NIGHT SHIFT", "夜行型"
    if 6 <= hour < 10:
        return "MORNING SHIFT", "清晨型"
    return "DAY SHIFT", "日间型"


def persona_verdict(dimensions: dict[str, int], turns: int, stats: dict[str, Any]) -> str:
    top = max(dimensions, key=lambda key: dimensions[key])
    if turns < 10:
        return "Sample size is small, so this is a provisional Codex Working Persona."
    if top == "ITERATION":
        return "You work by tuning loops until the result stops feeling accidental."
    if top == "EXPLORATION":
        return "You use Codex like a field instrument for mapping uncertain territory."
    if top == "SYSTEMS":
        return "You turn scattered tasks into structures that can be inspected and reused."
    if top == "VERIFICATION":
        return "You trust the work after it survives checks, not after it sounds convincing."
    if top == "AUTOMATION":
        return "You keep converting repeated effort into small machines."
    if top == "ENDURANCE":
        return "You stay with long threads until the shape of the work finally appears."
    if top == "CONTROL":
        return "You give Codex a tight frame, then let it move quickly inside it."
    return "This persona is derived from visible local collaboration traces, not from private identity."


def top_persona_dimensions(payload: dict[str, Any]) -> list[str]:
    dimensions = payload.get("persona", {}).get("dimensions", {})
    if not isinstance(dimensions, dict) or not dimensions:
        return ["EXPLORATION", "ITERATION"]
    return sorted(dimensions, key=lambda key: int(dimensions.get(key) or 0), reverse=True)


def top_categories(payload: dict[str, Any], limit: int = 4) -> list[tuple[str, int]]:
    categories = payload.get("categories", {})
    if not isinstance(categories, dict):
        return []
    pairs: list[tuple[str, int]] = []
    for key, value in categories.items():
        try:
            pairs.append((str(key), int(value)))
        except (TypeError, ValueError):
            continue
    return sorted(pairs, key=lambda item: item[1], reverse=True)[:limit]


def top_dimension_scores(payload: dict[str, Any], limit: int = 4) -> dict[str, int]:
    dimensions = payload.get("persona", {}).get("dimensions", {})
    if not isinstance(dimensions, dict):
        return {}
    ordered = top_persona_dimensions(payload)[:limit]
    return {name: int(dimensions.get(name) or 0) for name in ordered}


def select_spot_color(payload: dict[str, Any]) -> str:
    top = top_persona_dimensions(payload)[:3]
    category_names = " ".join(name for name, _ in top_categories(payload, 3)).lower()
    if "debug" in category_names or "verification" in top:
        return "#E94134"
    if "creative" in category_names or "research" in category_names or "exploration" in top:
        return "#139FD8"
    if "automation" in top or "systems" in top:
        return "#20B56B"
    return "#139FD8"


def evidence_lines(payload: dict[str, Any]) -> list[str]:
    stats = payload.get("statistics", {})
    persona = payload.get("persona", {})
    dimensions = top_dimension_scores(payload, 4)
    categories = top_categories(payload, 4)
    lines = [
        f"dimension profile: {', '.join(f'{k} {v}' for k, v in dimensions.items())}",
        f"workload: {stats.get('turns', 'N/A')} turns, {stats.get('threads', 'N/A')} threads, {stats.get('tool_calls', 'N/A')} tool calls, {stats.get('command_runs', 'N/A')} commands",
        f"coverage/source: {stats.get('coverage_score', 'N/A')}% coverage, source grade {stats.get('source_grade', 'N/A')}",
        f"persona verdict: {persona.get('verdict', 'N/A')}",
    ]
    if categories:
        lines.append("top task categories: " + ", ".join(f"{name} {value}" for name, value in categories))
    rhythm = payload.get("rhythm", {})
    if isinstance(rhythm, dict):
        compact = ", ".join(f"{k} {v}" for k, v in rhythm.items())
        lines.append(f"work rhythm: {compact}")
    return lines


def visual_marks(payload: dict[str, Any]) -> list[str]:
    marks: list[str] = []
    for name in top_persona_dimensions(payload)[:4]:
        marks.extend(DIMENSION_MARKS.get(name, []))
    for category, _ in top_categories(payload, 3):
        lower = category.lower()
        if "creative" in lower:
            marks.extend(["composition thumbnails", "ink swatches", "cropped proof strips"])
        elif "research" in lower:
            marks.extend(["index slips", "field-note scratches", "archive numbers"])
        elif "debug" in lower:
            marks.extend(["error ticks", "test marks", "repair tape"])
        elif "documentation" in lower:
            marks.extend(["margin notes", "dense copy blocks", "duplicate copy stamps"])
    return list(dict.fromkeys(marks))[:12]


def persona_role(payload: dict[str, Any]) -> str:
    top = top_persona_dimensions(payload)[:3]
    categories = " ".join(name.lower() for name, _ in top_categories(payload, 3))
    if "EXPLORATION" in top and "EXECUTION" in top:
        return "night-shift field operator"
    if "AUTOMATION" in top and "SYSTEMS" in top:
        return "workflow technician"
    if "VERIFICATION" in top:
        return "receipt inspector"
    if "CONTROL" in top:
        return "label archivist"
    if "creative" in categories:
        return "visual field researcher"
    return "local record worker"


def pose_action(payload: dict[str, Any]) -> str:
    top = top_persona_dimensions(payload)[:4]
    categories = " ".join(name.lower() for name, _ in top_categories(payload, 4))
    if "EXPLORATION" in top and "EXECUTION" in top:
        return "half-turned while checking a long terminal printout against a small field map"
    if "AUTOMATION" in top:
        return "tuning a small receipt-printer tool with one hand while holding a batch tag"
    if "VERIFICATION" in top or "debug" in categories:
        return "leaning in to inspect a barcode label and mark a proof strip"
    if "SYSTEMS" in top:
        return "arranging index tabs and folded print strips into a small grid"
    if "ITERATION" in top:
        return "holding two revised receipt strips side by side for comparison"
    if "ENDURANCE" in top:
        return "walking forward with a stack of worn printouts and repair tape"
    return "standing in a quiet working pose with tools and receipt strips"


def behavioral_core(payload: dict[str, Any]) -> str:
    dimensions = top_dimension_scores(payload, 3)
    parts = [DIMENSION_BEHAVIOR.get(name, name.lower()) for name in dimensions]
    return "; ".join(parts)


def character_dna(payload: dict[str, Any]) -> dict[str, Any]:
    persona = payload.get("persona", {})
    label = str(persona.get("title") or "CODEX WORKING PERSONA")
    scores = top_dimension_scores(payload, 4)
    return {
        "specimen_label": label,
        "persona_title": label,
        "visual_system": "fixed thermal receipt / pixel persona illustration",
        "spot_color": "#1A72B8",
        "dimension_scores": scores,
        "persona_role": persona_role(payload),
        "pose_action": pose_action(payload),
        "behavioral_core": behavioral_core(payload),
        "evidence": evidence_lines(payload),
        "visual_marks": visual_marks(payload),
        "specimen_brief": (
            "Invent one simple vertical pixel-persona illustration from the evidence lines. "
            "The image should fit a tall receipt illustration slot with low visual density, a clear silhouette, and a few meaningful props; do not generate the full receipt and do not choose any animal mapping."
        ),
        "generated_at_local": payload["generated_at_local"],
        "asset_rule": "Generate or render a fresh pixel-style persona illustration from behavioral evidence. Do not reuse a fixed mascot, fixed animal, or dimension-mapped creature.",
    }


def persona_illustration_prompt(payload: dict[str, Any]) -> str:
    dna = payload.get("character_dna") if isinstance(payload.get("character_dna"), dict) else character_dna(payload)
    marks = ", ".join(dna["visual_marks"])
    evidence = "\n".join(f"- {line}" for line in dna["evidence"])
    scores = ", ".join(f"{key} {value}" for key, value in dna["dimension_scores"].items())
    return f"""Use case: stylized-concept
Asset type: persona-specific pixel illustration for one CODEX RECEIPT run
Primary request: Create one NEW Codex Working Persona pixel illustration in vertical format from the analyzed data evidence below. This is not a fixed mascot, not a copied template element, and not a dimension-to-animal mapping. This is only the illustration asset for a tall receipt slot; do not generate a receipt, poster, barcode, label, title card, or UI layout.
Persona: {dna['persona_title']}
Dominant dimensions: {scores}
Behavioral core: {dna['behavioral_core']}
Data evidence:
{evidence}
Visual marks to translate into at most two or three simple props, room details, desk objects, maps, machine parts, or object-totem details: {marks}.
Persona role: {dna['persona_role']}
Pose/action: {dna['pose_action']}
Subject direction: invent a readable but simple persona role/avatar, quiet workspace scene, desk scene, small room scene, or symbolic object-totem whose posture and a few props express the evidence above. Do not default to a named octopus or any named animal, creature, monster, mascot, or ambiguous biological form.
Scene/backdrop: minimal pixel-art room corner, desk, terminal nook, small shelf, map table, bed/workroom corner, or plain tool bench on a light background. No surrounding receipt layout.
Style/medium: simple 1-bit retro pixel art, hard square pixels, black ink on warm white, optional single blue accent #1A72B8, low-resolution line art, sparse checker dither, clean blocky furniture and props, no antialiasing. Match the simpler density of small monochrome pixel room scenes rather than dense technical diagrams.
Composition/framing: vertical portrait composition, about 4:5 to 2:3. Use one clear subject and two to four supporting props, with generous negative space and a readable silhouette. Avoid wide landscape-room compositions, dense workstations, large map walls, complex machinery, tool piles, cable tangles, and busy technical collage.
Color palette: warm white, black, and optional #1A72B8 only.
Texture: sparse pixel dithering, small checker fills, light dot noise, hard jagged edges.
Constraints: no readable text, no numbers, no barcode, no receipt, no labels, no price tag, no UI panel, no black background, no modern vector mascot, no 3D, no anime, no cute blob, no gradients, no photorealism, no outer frame border.
Avoid: full-page receipt generation; copying any reference image literally; reusing any fixed animal or creature for every persona; smooth generic icon art; dense machinery; crowded wall diagrams; excessive tiny details."""


def specimen_prompt(payload: dict[str, Any]) -> str:
    return persona_illustration_prompt(payload)


def receipt_image_prompt(payload: dict[str, Any]) -> str:
    return (
        "DEPRECATED: The full CODEX RECEIPT is rendered deterministically by code. "
        "Use persona-illustration-prompt.txt only for the optional pixel persona illustration asset."
    )


def attach_visual_payload(payload: dict[str, Any]) -> None:
    payload["character_dna"] = character_dna(payload)
    payload["persona_illustration_prompt"] = persona_illustration_prompt(payload)
    payload["specimen_prompt"] = payload["persona_illustration_prompt"]
    payload["receipt_layout_contract"] = RECEIPT_LAYOUT_CONTRACT
    payload["illustration_style_contract"] = ILLUSTRATION_STYLE_CONTRACT


def build_payload(mode: str, period: str, generated_at: datetime, cache_path: Path | None = None) -> dict[str, Any]:
    if mode == "demo":
        return demo_payload(generated_at)
    scanned = scan_history(codex_home(), cache_path)
    stats = scanned["statistics"]
    payload = demo_payload(generated_at)
    payload["mode"] = mode
    payload["period"] = period
    payload["statistics"].update(stats)
    payload["persona"] = persona_from_stats(stats, scanned.get("features") or {})
    payload["coverage"] = scanned["coverage"]
    payload["categories"] = scanned.get("categories") or payload["categories"]
    payload["rhythm"] = scanned.get("rhythm") or payload["rhythm"]
    payload["easter_eggs"] = scanned.get("easter_eggs") or payload["easter_eggs"]
    payload["performance"].update(scanned.get("performance") or {})
    payload["privacy"] = {
        "public_safe": True,
        "redactions": ["[USER]", "[PROJECT_PATH]", "[REPOSITORY]", "[REDACTED_EMAIL]", "[REDACTED_API_KEY]"],
        "raw_prompts_in_public_output": False,
        "official_billing_claim": False,
        "notes": "Only aggregate metadata is included in public artifacts.",
    }
    return payload

def manifest(payload: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    return {
        "schema": payload["schema"],
        "visual_contract": RECEIPT_LAYOUT_CONTRACT["version"],
        "illustration_contract": ILLUSTRATION_STYLE_CONTRACT["version"],
        "mode": payload["mode"],
        "period": payload["period"],
        "generated_at_iso": payload["generated_at_iso"],
        "generated_at_local": payload["generated_at_local"],
        "not_official_billing": True,
        "files": sorted(p.name for p in out_dir.iterdir() if p.is_file()),
    }


def attach_persona_illustration(payload: dict[str, Any], out_dir: Path, illustration_asset: str | None) -> None:
    if not illustration_asset:
        payload.pop("persona_illustration_asset", None)
        payload.pop("specimen_asset", None)
        return
    asset = Path(illustration_asset).expanduser()
    if asset.exists():
        resolved = str(asset.resolve())
        payload["persona_illustration_asset"] = resolved
        payload["specimen_asset"] = resolved
    else:
        raise FileNotFoundError(f"Persona illustration asset not found: {asset}")


def write_outputs(payload: dict[str, Any], out_dir: Path, persona_illustration: str | None = None) -> None:
    start = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    attach_visual_payload(payload)
    attach_persona_illustration(payload, out_dir, persona_illustration)
    safe_write_json(out_dir / "receipt-data.json", payload)
    safe_write_json(out_dir / "visual-brief.json", payload["character_dna"])
    safe_write_json(out_dir / "receipt-layout-contract.json", RECEIPT_LAYOUT_CONTRACT)
    safe_write_json(out_dir / "illustration-style-contract.json", ILLUSTRATION_STYLE_CONTRACT)
    (out_dir / "persona-illustration-prompt.txt").write_text(payload["persona_illustration_prompt"], encoding="utf-8")
    (out_dir / "specimen-prompt.txt").write_text(payload["specimen_prompt"], encoding="utf-8")
    render_outputs(payload, out_dir)
    write_character_svg(out_dir / "character.svg", payload)
    elapsed = time.perf_counter() - start
    existing_performance = dict(payload.get("performance") or {})
    existing_performance.update({"render_seconds": round(elapsed, 3), "warnings": existing_performance.get("warnings", [])})
    payload["performance"] = existing_performance

    safe_write_json(out_dir / "statistics.json", payload["statistics"])
    safe_write_json(out_dir / "persona.json", payload["persona"])
    safe_write_json(out_dir / "character-dna.json", payload["character_dna"])
    safe_write_json(out_dir / "visual-brief.json", payload["character_dna"])
    safe_write_json(out_dir / "receipt-layout-contract.json", RECEIPT_LAYOUT_CONTRACT)
    safe_write_json(out_dir / "illustration-style-contract.json", ILLUSTRATION_STYLE_CONTRACT)
    safe_write_json(out_dir / "coverage-report.json", payload["coverage"])
    safe_write_json(out_dir / "privacy-report.json", payload["privacy"])
    safe_write_json(out_dir / "performance-report.json", payload["performance"])
    safe_write_json(out_dir / "receipt-data.json", payload)
    write_html(out_dir / "report-public.html", "CODEX RECEIPT PUBLIC REPORT", payload, public=True)
    write_html(out_dir / "report-private.html", "CODEX RECEIPT PRIVATE REPORT", payload, public=False)
    safe_write_json(out_dir / "manifest.json", manifest(payload, out_dir))


def cmd_demo(args: argparse.Namespace) -> int:
    payload = build_payload("demo", "all", parse_generated_at(args.generated_at))
    write_outputs(payload, Path(args.out), resolve_persona_illustration_arg(args))
    print(f"Generated CODEX RECEIPT demo at {Path(args.out).resolve()}")
    print(f"Output time ticket: {payload['generated_at_ticket']}")
    print(f"Persona illustration prompt: {(Path(args.out) / 'persona-illustration-prompt.txt').resolve()}")
    print("Visual note: receipt-share-final.png is deterministic code-rendered output.")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    cache_path = Path(args.out) / ".cache" / "codex-receipt.sqlite"
    payload = build_payload(args.mode, args.period, parse_generated_at(args.generated_at), cache_path)
    write_outputs(payload, Path(args.out), resolve_persona_illustration_arg(args))
    print(f"Generated CODEX RECEIPT at {Path(args.out).resolve()}")
    print(f"Coverage: {payload['coverage']['coverage_score']}%")
    print(f"Output time ticket: {payload['generated_at_ticket']}")
    print(f"Persona illustration prompt: {(Path(args.out) / 'persona-illustration-prompt.txt').resolve()}")
    print("Visual note: receipt-share-final.png is deterministic code-rendered output.")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    payload_path = Path(args.payload) if args.payload else Path(args.out) / "receipt-data.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    write_outputs(payload, Path(args.out), resolve_persona_illustration_arg(args))
    print(f"Re-rendered CODEX RECEIPT at {Path(args.out).resolve()}")
    print(f"Persona illustration asset: {payload.get('persona_illustration_asset', 'procedural fallback')}")
    return 0


def cmd_inspect_coverage(args: argparse.Namespace) -> int:
    scanned = scan_history(codex_home(), None)
    print(json.dumps(scanned["coverage"], ensure_ascii=False, indent=2))
    return 0


def cmd_clear_cache(args: argparse.Namespace) -> int:
    target = Path(args.out) / ".cache"
    if target.exists():
        shutil.rmtree(target)
    print(f"Cache cleared: {target}")
    return 0


def cmd_reset_identity(args: argparse.Namespace) -> int:
    target = Path(args.out) / "identity-seed.json"
    if target.exists():
        target.unlink()
    print(f"Identity reset: {target}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    start = time.perf_counter()
    payload = build_payload("demo", "all", local_now())
    write_outputs(payload, Path(args.out))
    elapsed = time.perf_counter() - start
    print(f"Benchmark demo render: {elapsed:.3f}s")
    return 0


def resolve_persona_illustration_arg(args: argparse.Namespace) -> str | None:
    return getattr(args, "persona_illustration", None) or getattr(args, "specimen_asset", None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex_receipt", description="Generate deterministic CODEX RECEIPT artifacts.")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Generate a fixed visual-regression demo.")
    demo.add_argument("--out", default=str(default_output_dir()))
    demo.add_argument("--generated-at", default=None, help="Override output time ticket, e.g. 2026-07-07 13:40")
    demo.add_argument("--persona-illustration", default=None, help="Path to this run's persona-specific illustration PNG.")
    demo.add_argument("--specimen-asset", default=None, help="Deprecated alias for --persona-illustration.")
    demo.set_defaults(func=cmd_demo)

    gen = sub.add_parser("generate", help="Generate from local Codex history when available.")
    gen.add_argument("--out", default=str(default_output_dir()))
    gen.add_argument("--period", default="all")
    gen.add_argument("--mode", default="standard", choices=["standard", "deep", "demo"])
    gen.add_argument("--generated-at", default=None)
    gen.add_argument("--persona-illustration", default=None, help="Path to this run's persona-specific illustration PNG.")
    gen.add_argument("--specimen-asset", default=None, help="Deprecated alias for --persona-illustration.")
    gen.set_defaults(func=cmd_generate)

    render = sub.add_parser("render", help="Re-render existing receipt-data.json, optionally with a persona illustration asset.")
    render.add_argument("--out", default=str(default_output_dir()))
    render.add_argument("--payload", default=None, help="Defaults to <out>/receipt-data.json.")
    render.add_argument("--persona-illustration", default=None, help="Path to this run's persona-specific illustration PNG.")
    render.add_argument("--specimen-asset", default=None, help="Deprecated alias for --persona-illustration.")
    render.set_defaults(func=cmd_render)

    cov = sub.add_parser("inspect-coverage", help="Inspect local data coverage.")
    cov.set_defaults(func=cmd_inspect_coverage)

    clear = sub.add_parser("clear-cache", help="Clear local output cache.")
    clear.add_argument("--out", default=str(default_output_dir()))
    clear.set_defaults(func=cmd_clear_cache)

    reset = sub.add_parser("reset-identity", help="Reset local identity seed.")
    reset.add_argument("--out", default=str(default_output_dir()))
    reset.set_defaults(func=cmd_reset_identity)

    bench = sub.add_parser("benchmark", help="Render demo and report timing.")
    bench.add_argument("--out", default=str(default_output_dir()))
    bench.set_defaults(func=cmd_benchmark)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))

