from __future__ import annotations

import json
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TOKEN_KEYS = {
    "input": ("input_tokens",),
    "cached": ("cached_input_tokens", "cached_tokens"),
    "output": ("output_tokens",),
    "reasoning": ("reasoning_output_tokens", "reasoning_tokens"),
    "total": ("total_tokens", "tokens_total"),
}

CACHE_VERSION = 4


@dataclass
class TokenUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_mapping(cls, value: Any) -> "TokenUsage":
        if not isinstance(value, dict):
            return cls()
        usage = cls()
        usage.input_tokens = first_int(value, TOKEN_KEYS["input"])
        usage.cached_input_tokens = first_int(value, TOKEN_KEYS["cached"])
        usage.output_tokens = first_int(value, TOKEN_KEYS["output"])
        usage.reasoning_output_tokens = first_int(value, TOKEN_KEYS["reasoning"])
        usage.total_tokens = first_int(value, TOKEN_KEYS["total"])
        if usage.total_tokens <= 0:
            usage.total_tokens = (
                usage.input_tokens
                + usage.cached_input_tokens
                + usage.output_tokens
                + usage.reasoning_output_tokens
            )
        return usage

    def is_empty(self) -> bool:
        return self.total_tokens <= 0 and (
            self.input_tokens
            + self.cached_input_tokens
            + self.output_tokens
            + self.reasoning_output_tokens
        ) <= 0

    def add(self, other: "TokenUsage") -> None:
        self.input_tokens += max(0, other.input_tokens)
        self.cached_input_tokens += max(0, other.cached_input_tokens)
        self.output_tokens += max(0, other.output_tokens)
        self.reasoning_output_tokens += max(0, other.reasoning_output_tokens)
        self.total_tokens += max(0, other.total_tokens)

    def delta_from(self, previous: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=max(0, self.input_tokens - previous.input_tokens),
            cached_input_tokens=max(0, self.cached_input_tokens - previous.cached_input_tokens),
            output_tokens=max(0, self.output_tokens - previous.output_tokens),
            reasoning_output_tokens=max(0, self.reasoning_output_tokens - previous.reasoning_output_tokens),
            total_tokens=max(0, self.total_tokens - previous.total_tokens),
        )

    def as_stats(self) -> dict[str, int]:
        total = self.total_tokens
        component_sum = (
            self.input_tokens
            + self.cached_input_tokens
            + self.output_tokens
            + self.reasoning_output_tokens
        )
        if total <= 0:
            total = component_sum
        return {
            "tokens_total": total,
            "tokens_input": self.input_tokens,
            "tokens_output": self.output_tokens,
            "tokens_cached": self.cached_input_tokens,
            "tokens_reasoning": self.reasoning_output_tokens,
        }


def first_int(mapping: dict[str, Any], keys: tuple[str, ...]) -> int:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return 0


def discover_files(home: Path) -> list[Path]:
    files: list[Path] = []
    for root in (home / "sessions", home / "archived_sessions"):
        if root.exists():
            files.extend(root.rglob("rollout-*.jsonl"))
    history = home / "history.jsonl"
    if history.exists():
        files.append(history)
    return sorted(files)


class SummaryCache:
    def __init__(self, db_path: Path | None):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(db_path)
            self.conn.execute(
                """
                create table if not exists file_summary (
                  path text primary key,
                  size integer not null,
                  mtime_ns integer not null,
                  summary_json text not null,
                  updated_at real not null
                )
                """
            )
            self.conn.commit()

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def get(self, path: Path) -> dict[str, Any] | None:
        if self.conn is None:
            return None
        stat = path.stat()
        row = self.conn.execute(
            "select summary_json from file_summary where path=? and size=? and mtime_ns=?",
            (str(path), stat.st_size, stat.st_mtime_ns),
        ).fetchone()
        if not row:
            return None
        summary = json.loads(row[0])
        if summary.get("_cache_version") != CACHE_VERSION:
            return None
        summary["cache_hit"] = True
        return summary

    def set(self, path: Path, summary: dict[str, Any]) -> None:
        if self.conn is None:
            return
        stat = path.stat()
        clean = dict(summary)
        clean.pop("cache_hit", None)
        clean["_cache_version"] = CACHE_VERSION
        self.conn.execute(
            """
            insert into file_summary(path, size, mtime_ns, summary_json, updated_at)
            values (?, ?, ?, ?, ?)
            on conflict(path) do update set
              size=excluded.size,
              mtime_ns=excluded.mtime_ns,
              summary_json=excluded.summary_json,
              updated_at=excluded.updated_at
            """,
            (str(path), stat.st_size, stat.st_mtime_ns, json.dumps(clean, ensure_ascii=False), time.time()),
        )
        self.conn.commit()


def summarize_file(path: Path) -> dict[str, Any]:
    parsed_lines = 0
    failed_lines = 0
    turn_ids: set[str] = set()
    dates: set[str] = set()
    projects: set[str] = set()
    exact_by_turn: dict[str, tuple[str, TokenUsage]] = {}
    cumulative_by_thread: dict[str, list[tuple[str, TokenUsage]]] = defaultdict(list)
    event_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    hour_counts: Counter[str] = Counter()
    weekday_counts: Counter[str] = Counter()
    tool_calls = 0
    command_runs = 0
    file_modifications = 0
    completed_turns: set[str] = set()
    failed_turns: set[str] = set()
    interrupted_turns: set[str] = set()

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
            payload = record.get("payload") if isinstance(record, dict) else {}
            if not isinstance(payload, dict):
                payload = {}
            event_type = str(payload.get("type") or record.get("type") or "unknown")
            event_counts[event_type] += 1
            timestamp = find_timestamp(record) or ""
            if len(timestamp) >= 10:
                dates.add(timestamp[:10])
                add_time_buckets(timestamp, hour_counts, weekday_counts)
            thread_key = str(payload.get("id") or path.stem)
            turn_key = str(payload.get("turn_id") or "")
            if turn_key:
                turn_id = f"{thread_key}:{turn_key}"
                turn_ids.add(turn_id)
            else:
                turn_id = ""

            project = find_project_hint(record)
            if project:
                projects.add(project)

            if is_tool_event(event_type):
                tool_calls += 1
            if is_command_event(record):
                command_runs += 1
            if is_file_mod_event(record):
                file_modifications += 1
            if event_type in {"task_complete", "agent_message"} and turn_id:
                completed_turns.add(turn_id)
            if "error" in text.lower() or "failed" in text.lower():
                if turn_id:
                    failed_turns.add(turn_id)
            if "interrupted" in text.lower() or "cancelled" in text.lower() or "canceled" in text.lower():
                if turn_id:
                    interrupted_turns.add(turn_id)

            category = classify_event(record, event_type)
            if category:
                category_counts[category] += 1

            usage_info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
            last_usage = TokenUsage.from_mapping(usage_info.get("last_token_usage"))
            if turn_id and not last_usage.is_empty():
                exact_by_turn[turn_id] = (timestamp, last_usage)
            total_usage = TokenUsage.from_mapping(usage_info.get("total_token_usage"))
            if not total_usage.is_empty():
                cumulative_by_thread[thread_key].append((timestamp, total_usage))

    exact_usage = TokenUsage()
    for _, usage in exact_by_turn.values():
        exact_usage.add(usage)

    delta_usage = TokenUsage()
    for snapshots in cumulative_by_thread.values():
        previous = TokenUsage()
        for _, current in sorted(snapshots, key=lambda item: item[0]):
            delta_usage.add(current.delta_from(previous))
            previous = current

    source = "B" if not exact_usage.is_empty() else ("C" if not delta_usage.is_empty() else "E")
    usage = exact_usage if not exact_usage.is_empty() else delta_usage

    return {
        "parsed_lines": parsed_lines,
        "failed_lines": failed_lines,
        "turn_ids": sorted(turn_ids),
        "dates": sorted(dates),
        "projects": sorted(projects),
        "event_counts": dict(event_counts),
        "category_counts": dict(category_counts),
        "hour_counts": dict(hour_counts),
        "weekday_counts": dict(weekday_counts),
        "tool_calls": tool_calls,
        "command_runs": command_runs,
        "file_modifications": file_modifications,
        "completed_turns": sorted(completed_turns),
        "failed_turns": sorted(failed_turns),
        "interrupted_turns": sorted(interrupted_turns),
        "token_usage": usage.as_stats(),
        "exact_token_usage": exact_usage.as_stats(),
        "cumulative_token_usage": delta_usage.as_stats(),
        "token_source_grade": source,
        "turns_with_tokens": len(exact_by_turn) if not exact_usage.is_empty() else len(cumulative_by_thread),
        "exact_turns_with_tokens": len(exact_by_turn),
        "cumulative_threads_with_tokens": len(cumulative_by_thread),
        "cache_hit": False,
    }


def scan_codex_history(home: Path, cache_path: Path | None = None) -> dict[str, Any]:
    files = discover_files(home)
    cache = SummaryCache(cache_path)
    started = time.perf_counter()
    summaries: list[dict[str, Any]] = []
    cache_hits = 0
    warnings: list[str] = []
    bytes_read = 0
    try:
        for path in files:
            cached = cache.get(path)
            if cached is not None:
                cache_hits += 1
                summaries.append(cached)
                continue
            try:
                summary = summarize_file(path)
                cache.set(path, summary)
                summaries.append(summary)
                bytes_read += path.stat().st_size
            except OSError as exc:
                warnings.append(f"Could not read {path.name}: {exc}")
    finally:
        cache.close()

    aggregate = aggregate_summaries(home, files, summaries, warnings)
    aggregate["performance"] = {
        "scan_seconds": round(time.perf_counter() - started, 3),
        "scanned_files": len(files),
        "read_bytes": bytes_read,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / len(files), 4) if files else 0,
        "cache_path": str(cache_path) if cache_path else None,
    }
    return aggregate


def aggregate_summaries(home: Path, files: list[Path], summaries: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    turn_ids: set[str] = set()
    dates: set[str] = set()
    projects: set[str] = set()
    completed: set[str] = set()
    failed: set[str] = set()
    interrupted: set[str] = set()
    token_usage = TokenUsage()
    exact_token_usage = TokenUsage()
    cumulative_token_usage = TokenUsage()
    categories: Counter[str] = Counter()
    hours: Counter[str] = Counter()
    weekdays: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    parsed_lines = 0
    failed_lines = 0
    turns_with_tokens = 0
    exact_turns_with_tokens = 0
    cumulative_threads_with_tokens = 0
    tool_calls = 0
    command_runs = 0
    file_modifications = 0
    source_grades: list[str] = []

    for summary in summaries:
        parsed_lines += int(summary.get("parsed_lines") or 0)
        failed_lines += int(summary.get("failed_lines") or 0)
        turn_ids.update(summary.get("turn_ids") or [])
        dates.update(summary.get("dates") or [])
        projects.update(summary.get("projects") or [])
        completed.update(summary.get("completed_turns") or [])
        failed.update(summary.get("failed_turns") or [])
        interrupted.update(summary.get("interrupted_turns") or [])
        categories.update(summary.get("category_counts") or {})
        hours.update(summary.get("hour_counts") or {})
        weekdays.update(summary.get("weekday_counts") or {})
        event_counts.update(summary.get("event_counts") or {})
        tool_calls += int(summary.get("tool_calls") or 0)
        command_runs += int(summary.get("command_runs") or 0)
        file_modifications += int(summary.get("file_modifications") or 0)
        turns_with_tokens += int(summary.get("turns_with_tokens") or 0)
        token_usage.add(TokenUsage.from_mapping(reverse_stat_keys(summary.get("token_usage") or {})))
        exact_token_usage.add(TokenUsage.from_mapping(reverse_stat_keys(summary.get("exact_token_usage") or {})))
        cumulative_token_usage.add(TokenUsage.from_mapping(reverse_stat_keys(summary.get("cumulative_token_usage") or {})))
        exact_turns_with_tokens += int(summary.get("exact_turns_with_tokens") or 0)
        cumulative_threads_with_tokens += int(summary.get("cumulative_threads_with_tokens") or 0)
        source_grades.append(str(summary.get("token_source_grade") or "E"))

    if not files:
        warnings.append(f"No Codex history files found under {home}.")
    stats = {
        "active_days": len(dates),
        "threads": len({Path(p).stem for p in files}),
        "archived_threads": sum(1 for p in files if "archived_sessions" in str(p)),
        "turns": len(turn_ids) if turn_ids else parsed_lines,
        "completed_turns": len(completed),
        "failed_turns": len(failed),
        "interrupted_turns": len(interrupted),
        "tool_calls": tool_calls,
        "command_runs": command_runs,
        "file_modifications": file_modifications,
        "projects": len(projects),
        "coverage_score": 0,
        "source_grade": choose_source_grade(source_grades),
    }
    stats.update(token_usage.as_stats())
    stats["tokens_observed_total"] = int(stats.get("tokens_total") or 0)
    stats["tokens_exact_total"] = exact_token_usage.as_stats()["tokens_total"]
    stats["tokens_cumulative_delta_total"] = cumulative_token_usage.as_stats()["tokens_total"]
    stats["token_exact_turns"] = exact_turns_with_tokens
    stats["token_cumulative_threads"] = cumulative_threads_with_tokens
    stats["token_coverage_label"] = f"{turns_with_tokens}/{stats['turns']}"
    if stats["tokens_total"] <= 0 and parsed_lines:
        estimate_tokens(stats, warnings)
    else:
        normalize_tokens(stats, warnings)
    annotate_token_display(stats)
    stats["coverage_score"] = coverage_score(parsed_lines, failed_lines, stats, turns_with_tokens)

    return {
        "statistics": stats,
        "coverage": {
            "data_sources": {
                "codex_home": str(home),
                "sessions": "available" if any((home / name).exists() for name in ("sessions", "archived_sessions")) else "missing",
                "history_jsonl": "available" if (home / "history.jsonl").exists() else "missing",
            },
            "scanned_files": len(files),
            "parsed_lines": parsed_lines,
            "failed_lines": failed_lines,
            "threads": stats["threads"],
            "turns": stats["turns"],
            "turns_with_tokens": turns_with_tokens,
            "time_range": date_range(dates),
            "coverage_score": stats["coverage_score"],
            "warnings": warnings,
        },
        "categories": top_categories(categories),
        "rhythm": rhythm_summary(hours),
        "easter_eggs": easter_eggs(event_counts, command_runs, failed, projects),
        "features": {
            "hours": dict(hours),
            "weekdays": dict(weekdays),
            "categories": dict(categories),
            "event_counts": dict(event_counts),
            "turns_with_tokens": turns_with_tokens,
        },
    }


def reverse_stat_keys(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "input_tokens": int(stats.get("tokens_input") or 0),
        "cached_input_tokens": int(stats.get("tokens_cached") or 0),
        "output_tokens": int(stats.get("tokens_output") or 0),
        "reasoning_output_tokens": int(stats.get("tokens_reasoning") or 0),
        "total_tokens": int(stats.get("tokens_total") or 0),
    }


def normalize_tokens(stats: dict[str, Any], warnings: list[str]) -> None:
    turns = int(stats.get("turns") or 0)
    total = int(stats.get("tokens_total") or 0)
    if turns <= 0 or total <= 0:
        return
    max_reasonable = turns * 200_000
    if total <= max_reasonable:
        return
    stats["tokens_observed_total"] = total
    estimate_tokens(stats, warnings)
    warnings.append("Token fields looked cumulative after Turn-level dedupe; replaced with EST. visible-data estimate.")


def estimate_tokens(stats: dict[str, Any], warnings: list[str]) -> None:
    turns = max(int(stats.get("turns") or 0), 1)
    estimated_total = turns * 6_000
    stats["tokens_estimated_total"] = estimated_total
    stats["tokens_total"] = estimated_total
    stats["tokens_input"] = int(estimated_total * 0.44)
    stats["tokens_output"] = int(estimated_total * 0.18)
    stats["tokens_cached"] = int(estimated_total * 0.31)
    stats["tokens_reasoning"] = estimated_total - stats["tokens_input"] - stats["tokens_output"] - stats["tokens_cached"]
    stats["source_grade"] = "D"
    if not any("EST." in warning for warning in warnings):
        warnings.append("Token total is EST. because exact Turn token data was unavailable or inconsistent.")


def annotate_token_display(stats: dict[str, Any]) -> None:
    if int(stats.get("tokens_estimated_total") or 0):
        stats["token_count_mode"] = "visible_estimate"
        stats["token_display_label"] = "TOKEN EST."
        return
    grade = str(stats.get("source_grade") or "")
    if grade == "B":
        stats["token_count_mode"] = "exact_turn_usage"
        stats["token_display_label"] = "TOKEN"
    elif grade == "C":
        stats["token_count_mode"] = "cumulative_delta"
        stats["token_display_label"] = "TOKEN"
    else:
        stats["token_count_mode"] = "unavailable"
        stats["token_display_label"] = "TOKEN"


def coverage_score(parsed_lines: int, failed_lines: int, stats: dict[str, Any], turns_with_tokens: int) -> int:
    if parsed_lines <= 0:
        return 0
    parse_score = max(0, 1 - failed_lines / parsed_lines)
    token_score = 1 if turns_with_tokens else 0.55
    source_score = {"A": 1, "A-": 0.97, "B": 0.94, "C": 0.86, "D": 0.72, "E": 0.35}.get(
        str(stats.get("source_grade")), 0.72
    )
    return int(round(100 * min(parse_score, token_score, source_score)))


def choose_source_grade(grades: list[str]) -> str:
    order = {"A": 0, "A-": 1, "B": 2, "C": 3, "D": 4, "E": 5}
    available = [grade for grade in grades if grade and grade != "E"]
    if not available:
        return "E"
    return sorted(available, key=lambda grade: order.get(grade, 5))[0]


def classify_event(record: dict[str, Any], event_type: str) -> str:
    text = json.dumps(safe_subset(record), ensure_ascii=False).lower()
    if event_type in {"web_search_call"} or "research" in text:
        return "Research & Patterning"
    if "apply_patch" in text or "file_change" in text:
        return "Writing / Documentation" if ".md" in text else "Design / Structure"
    if "test" in text or "pytest" in text or "typecheck" in text or "lint" in text:
        return "Debug / Problem Solving"
    if "figma" in text or "image" in text or "visual" in text or "design" in text:
        return "Creative Direction"
    if "shell_command" in text or "command" in text:
        return "Maintenance / Cleanup"
    return "Writing / Documentation" if event_type in {"message", "agent_message", "user_message"} else "Research & Patterning"


def safe_subset(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload") if isinstance(record, dict) else {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, Any] = {
        "type": payload.get("type"),
        "name": payload.get("name"),
        "status": payload.get("status"),
        "action": payload.get("action"),
        "cwd": bool(payload.get("cwd")),
    }
    content = payload.get("content")
    if isinstance(content, list):
        result["content_types"] = [item.get("type") for item in content if isinstance(item, dict)]
    return result


def top_categories(counter: Counter[str]) -> dict[str, int]:
    if not counter:
        return {
            "Creative Direction": 0,
            "Research & Patterning": 0,
            "Writing / Documentation": 0,
            "Debug / Problem Solving": 0,
            "Design / Structure": 0,
            "Maintenance / Cleanup": 0,
        }
    return dict(counter.most_common(6))


def rhythm_summary(hours: Counter[str]) -> dict[str, str]:
    if not hours:
        return {"focus": "N/A", "build": "N/A", "verify": "N/A", "reflect": "N/A"}
    peak = hours.most_common(1)[0][0]
    night = sum(count for hour, count in hours.items() if int(hour) >= 22 or int(hour) < 6)
    total = sum(hours.values())
    return {
        "focus": f"peak {peak}:00",
        "build": f"{round(100 * night / total)}% night",
        "verify": f"{total} timed events",
        "reflect": "local rhythm",
    }


def easter_eggs(event_counts: Counter[str], command_runs: int, failed: set[str], projects: set[str]) -> dict[str, Any]:
    return {
        "Loop Detected": int(event_counts.get("reasoning", 0)),
        "Tool Signals": int(event_counts.get("function_call", 0) + event_counts.get("custom_tool_call", 0)),
        "Command Runs": command_runs,
        "Failure Recoveries": len(failed),
        "Project Signals": len(projects),
        "Specimen Rarity": "UNCOMMON" if command_runs < 100 else "RARE",
    }


def add_time_buckets(timestamp: str, hour_counts: Counter[str], weekday_counts: Counter[str]) -> None:
    normalized = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return
    hour_counts[f"{dt.hour:02d}"] += 1
    weekday_counts[str(dt.weekday())] += 1


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


def is_tool_event(event_type: str) -> bool:
    return event_type in {
        "function_call",
        "custom_tool_call",
        "web_search_call",
    }


def is_command_event(record: Any) -> bool:
    payload = record.get("payload") if isinstance(record, dict) else {}
    if isinstance(payload, dict) and payload.get("name") in {"shell_command", "exec_command"}:
        return True
    text = json.dumps(safe_subset(record), ensure_ascii=False).lower() if isinstance(record, dict) else ""
    return "shell_command" in text or "exec_command" in text


def is_file_mod_event(record: Any) -> bool:
    payload = record.get("payload") if isinstance(record, dict) else {}
    if isinstance(payload, dict) and payload.get("name") == "apply_patch":
        return True
    text = json.dumps(safe_subset(record), ensure_ascii=False).lower() if isinstance(record, dict) else ""
    return "apply_patch" in text or "file_change" in text
