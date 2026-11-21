#!/usr/bin/env python3
"""Summarize CodeJet dashboard CSV exports locally, without network access."""

from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


DIMENSIONS = ("source", "medium", "campaign", "content")
UTM_FIELDS = tuple("utm_" + name for name in DIMENSIONS)
REQUIRED_FIELDS = {
    "visit_id", "first_seen_utc", "last_seen_utc", "demo_page_views",
    "video_started", "end_reached", "max_coverage_percent",
}
COHORTS = ("all", "probable_bot_flagged", "unflagged", "flag_unknown")
METRICS = (
    "sessions", "demo_sessions", "video_start_sessions", "end_reached_sessions",
    "coverage_50_sessions", "coverage_90_sessions", "engaged_50_sessions", "coverage_unknown_sessions",
)
NOT_SET = "(not set)"
REDACTED = "(redacted identifier)"


class ReportError(ValueError):
    """Invalid input, described without printing an individual record."""


def _time(value: str, field_name: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(timezone.utc)
    except (ValueError, AttributeError):
        raise ReportError(f"{field_name} must be an ISO timestamp with a timezone.") from None


def _number(value: str, field_name: str, *, optional: bool = False) -> Decimal | None:
    value = value.strip()
    if not value and optional:
        return None
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ReportError(f"{field_name} must be a number.") from None
    if not result.is_finite() or result < 0:
        raise ReportError(f"{field_name} must be finite and nonnegative.")
    return result


def _flag(value: str, field_name: str, *, optional: bool = False) -> bool | None:
    value = value.strip().lower()
    if value in {"1", "1.0", "true", "yes"}:
        return True
    if value in {"0", "0.0", "false", "no"}:
        return False
    if not value and optional:
        return None
    raise ReportError(f"{field_name} must be 0/1, false/true, or no/yes.")


def safe_dimension(value: str) -> str:
    """Keep campaign labels, but suppress obvious identifiers and formula cells."""
    value = " ".join(value.split())[:253]
    if not value:
        return ""
    # Campaign tags should never contain personal data. This is a conservative
    # extra guard; it is not a general-purpose anonymization system.
    if re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        return REDACTED
    try:
        ipaddress.ip_address(value.strip("[]"))
        return REDACTED
    except ValueError:
        pass
    try:
        uuid.UUID(value)
        return REDACTED
    except ValueError:
        pass
    if value.startswith(("=", "+", "-", "@")):
        value = "'" + value
    return value


def _read_csv(path: Path, required: set[str]):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ReportError("CSV contains duplicate column names.")
        missing = required - set(headers)
        if missing:
            raise ReportError("CSV is missing columns: " + ", ".join(sorted(missing)))
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ReportError(f"CSV row {reader.line_num} has the wrong number of columns.")
            yield reader.line_num, row


@dataclass
class Session:
    first_seen: datetime
    last_seen: datetime
    metadata: tuple[str, ...]
    metadata_rank: tuple
    demo: bool
    started: bool
    ended: bool
    coverage: Decimal | None
    bot: bool | None
    metadata_seen: set[tuple[str, ...]] = field(default_factory=set)

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Session":
        first = _time(row["first_seen_utc"], "first_seen_utc")
        last = _time(row["last_seen_utc"], "last_seen_utc")
        if last < first:
            raise ReportError("last_seen_utc cannot precede first_seen_utc.")
        demo = _number(row["demo_page_views"], "demo_page_views")
        if demo != demo.to_integral_value():
            raise ReportError("demo_page_views must be a whole number.")
        coverage = _number(row["max_coverage_percent"], "max_coverage_percent", optional=True)
        if coverage is not None and coverage > 100:
            raise ReportError("max_coverage_percent cannot exceed 100.")
        metadata = tuple(safe_dimension(row.get(key, "")) for key in UTM_FIELDS)
        referrer = safe_dimension(row.get("referrer_host", "").strip().lower())
        metadata = (*metadata, referrer)
        priority = 0 if any(metadata[:4]) else 1 if referrer else 2
        # Prefer explicit attribution, then the earliest observation; use a
        # deterministic lexical tie-break when exports disagree at the same time.
        rank = (priority, first, metadata)
        return cls(
            first, last, metadata, rank, demo > 0,
            _flag(row["video_started"], "video_started"),
            _flag(row["end_reached"], "end_reached"), coverage,
            _flag(row.get("probable_bot", ""), "probable_bot", optional=True),
            {metadata} if any(metadata) else set(),
        )

    def merge(self, other: "Session") -> None:
        self.first_seen = min(self.first_seen, other.first_seen)
        self.last_seen = max(self.last_seen, other.last_seen)
        if other.metadata_rank < self.metadata_rank:
            self.metadata, self.metadata_rank = other.metadata, other.metadata_rank
        self.metadata_seen.update(other.metadata_seen)
        self.demo = self.demo or other.demo
        self.started = self.started or other.started
        self.ended = self.ended or other.ended
        available = [x for x in (self.coverage, other.coverage) if x is not None]
        self.coverage = max(available) if available else None
        # A positive bot flag survives overlapping exports. Unknown plus false
        # becomes false only because at least one export explicitly assessed it.
        if self.bot is True or other.bot is True:
            self.bot = True
        elif self.bot is False or other.bot is False:
            self.bot = False

    def group(self) -> tuple[str, ...]:
        if any(self.metadata[:4]):
            return tuple(value or NOT_SET for value in self.metadata[:4])
        if self.metadata[4]:
            return (self.metadata[4], "referral", NOT_SET, NOT_SET)
        return ("(direct or unknown)", NOT_SET, NOT_SET, NOT_SET)

    def cohort(self) -> str:
        return "probable_bot_flagged" if self.bot is True else "unflagged" if self.bot is False else "flag_unknown"


def load_sessions(paths: list[Path]) -> tuple[dict[str, Session], int]:
    sessions: dict[str, Session] = {}
    rows_read = 0
    for file_number, path in enumerate(paths, start=1):
        try:
            for row_number, row in _read_csv(path, REQUIRED_FIELDS):
                rows_read += 1
                if not row["visit_id"].strip():
                    raise ReportError(f"Row {row_number} has a blank visit_id; cannot deduplicate.")
                try:
                    session = Session.from_row(row)
                except ReportError as exc:
                    raise ReportError(f"Row {row_number}: {exc}") from None
                key = row["visit_id"].strip()
                if key in sessions:
                    sessions[key].merge(session)
                else:
                    sessions[key] = session
        except (ReportError, csv.Error, UnicodeError) as exc:
            # Never include the full record, ID, IP, or a parsed invalid value.
            raise ReportError(f"Input {file_number}: {exc}") from None
    return sessions, rows_read


def empty_metrics() -> dict[str, int]:
    return dict.fromkeys(METRICS, 0)


def add_session(metrics: dict[str, int], session: Session) -> None:
    metrics["sessions"] += 1
    metrics["demo_sessions"] += int(session.demo)
    metrics["video_start_sessions"] += int(session.started)
    metrics["end_reached_sessions"] += int(session.ended)
    metrics["coverage_50_sessions"] += int(session.coverage is not None and session.coverage >= 50)
    metrics["coverage_90_sessions"] += int(session.coverage is not None and session.coverage >= 90)
    metrics["engaged_50_sessions"] += int(session.started and session.coverage is not None and session.coverage >= 50)
    metrics["coverage_unknown_sessions"] += int(session.coverage is None)


def summarize(sessions: dict[str, Session], rows_read: int) -> tuple[dict, list[dict]]:
    totals = {cohort: empty_metrics() for cohort in COHORTS}
    groups: dict[tuple[str, ...], dict[str, dict[str, int]]] = {}
    for session in sessions.values():
        group = groups.setdefault(session.group(), {cohort: empty_metrics() for cohort in COHORTS})
        for cohort in ("all", session.cohort()):
            add_session(totals[cohort], session)
            add_session(group[cohort], session)
    rows = []
    for key in sorted(groups):
        for cohort in COHORTS:
            rows.append(dict(zip(DIMENSIONS, key)) | {"cohort": cohort} | groups[key][cohort])
    iso = lambda value: value.isoformat(timespec="seconds").replace("+00:00", "Z")
    summary = {
        "input_rows": rows_read,
        "unique_sessions": len(sessions),
        "duplicate_rows_merged": rows_read - len(sessions),
        "sessions_with_attribution_conflicts": sum(len(s.metadata_seen) > 1 for s in sessions.values()),
        "earliest_observed_first_seen_utc": iso(min(s.first_seen for s in sessions.values())) if sessions else None,
        "latest_observed_last_seen_utc": iso(max(s.last_seen for s in sessions.values())) if sessions else None,
        "cohorts": totals,
        "interpretation": [
            "Unflagged means the exported bot flag is false; it does not verify a human visitor.",
            "End reached may include seeking and is not equivalent to a full watch.",
            "Coverage thresholds use reported played-range coverage, not the furthest playback position.",
            "Missing coverage is unknown, not zero. Video starts and coverage are separate reported signals.",
            "engaged_50_sessions requires a reported video start and coverage >=50%; use the unflagged cohort as an engagement proxy, not proof of a human viewer.",
            "The date bounds describe observed sessions, not verified complete export or spend windows.",
            "Overlapping exports are merged by visit_id with maximum observed engagement, never summed per visit.",
        ],
    }
    return summary, rows


def spend_summary(path: Path, traffic_rows: list[dict]) -> list[dict]:
    traffic = {(tuple(row[key] for key in DIMENSIONS), row["cohort"]): row for row in traffic_rows}
    required = {*DIMENSIONS, "spend", "currency"}
    results = []
    seen = set()
    for row_number, row in _read_csv(path, required):
        key = tuple(safe_dimension(row[name]) or NOT_SET for name in DIMENSIONS)
        if key in seen:
            raise ReportError(f"Spend row {row_number}: duplicate group; combine its spend into one row.")
        seen.add(key)
        amount = _number(row["spend"], "spend")
        currency = row["currency"].strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ReportError(f"Spend row {row_number}: currency must be a three-letter code.")
        result = dict(zip(DIMENSIONS, key)) | {
            "currency": currency,
            "spend": format(amount, "f"),
            "matched_traffic": str((key, "all") in traffic).lower(),
        }
        for cohort in ("all", "unflagged"):
            metrics = traffic.get((key, cohort), empty_metrics())
            for metric, label in (("video_start_sessions", "video_start"), ("coverage_90_sessions", "coverage_90")):
                count = metrics[metric]
                result[f"{cohort}_{metric}"] = count
                result[f"cost_per_{cohort}_{label}"] = format(amount / count, ".2f") if count else ""
        results.append(result)
    return sorted(results, key=lambda row: tuple(row[key] for key in DIMENSIONS))


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


SPEND_FIELDS = [*DIMENSIONS, "currency", "spend", "matched_traffic"] + [
    name
    for cohort in ("all", "unflagged")
    for metric, label in (("video_start_sessions", "video_start"), ("coverage_90_sessions", "coverage_90"))
    for name in (f"{cohort}_{metric}", f"cost_per_{cohort}_{label}")
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_files", nargs="+", type=Path, help="One or more dashboard CSV exports (overlaps are deduplicated).")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "private_reports")
    parser.add_argument("--spend", type=Path, help="Optional manually prepared spend CSV covering the same reporting scope.")
    args = parser.parse_args(argv)
    try:
        sessions, row_count = load_sessions(args.csv_files)
        summary, rows = summarize(sessions, row_count)
        costs = spend_summary(args.spend, rows) if args.spend else None
        outputs = [args.output_dir / name for name in ("summary.json", "traffic_by_campaign.csv", "report.txt", "spend_summary.csv")]
        input_paths = {path.resolve() for path in args.csv_files}
        if args.spend:
            input_paths.add(args.spend.resolve())
        if any(path.resolve() in input_paths for path in outputs):
            raise ReportError("An output path would overwrite an input file; choose another output directory.")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        _write_csv(outputs[1], [*DIMENSIONS, "cohort", *METRICS], rows)
        summary["manual_spend_supplied"] = costs is not None
        outputs[0].write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        lines = ["CodeJet aggregate traffic report", "", f"Unique sessions: {len(sessions)}", f"Overlapping rows merged: {row_count - len(sessions)}", ""]
        for cohort in COHORTS:
            m = summary["cohorts"][cohort]
            lines.append(f"{cohort}: {m['sessions']} sessions; {m['demo_sessions']} demo; {m['video_start_sessions']} video starts; {m['coverage_50_sessions']} coverage >=50%; {m['coverage_90_sessions']} coverage >=90%; {m['engaged_50_sessions']} started + coverage >=50%.")
        lines += ["", *summary["interpretation"]]
        if summary["sessions_with_attribution_conflicts"]:
            lines += ["", "Some overlapping records disagreed on attribution. The report uses explicit UTM data first, then the earliest observation, with a deterministic tie-break. Review export provenance before interpreting attribution."]
        _write_csv(outputs[3], SPEND_FIELDS, costs or [])
        if costs is not None:
            lines += ["", "Spend is manual and must cover the same time and campaign scope. Costs use the entire matched group spend; no spend is removed for flagged traffic. Blank cost means no denominator. Currencies are not combined."]
        else:
            lines += ["", "No manual spend supplied. spend_summary.csv contains headers only."]
        outputs[2].write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        print("\nAggregate report files written to:", args.output_dir)
        return 0
    except (OSError, ReportError, csv.Error, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
