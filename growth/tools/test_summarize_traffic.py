"""Synthetic-only tests for the local campaign report. No private fixtures."""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

import summarize_traffic as report


FIELDS = [
    "visit_id", "first_seen_utc", "last_seen_utc", "first_public_ip", "last_public_ip",
    "ip_source", "landing_page", "page_views", "demo_page_views", "video_started",
    "end_reached", "max_played_seconds", "max_coverage_percent", "max_position_seconds",
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "referrer_host", "probable_bot",
]


def row(visit="synthetic-session-a", **changes):
    value = dict.fromkeys(FIELDS, "")
    value.update(
        visit_id=visit, first_seen_utc="2026-11-01T10:00:00Z", last_seen_utc="2026-11-01T10:01:00Z",
        first_public_ip="192.0.2.123", last_public_ip="192.0.2.124", ip_source="synthetic",
        landing_page="/retail-analytics-software", page_views="1", demo_page_views="0",
        video_started="0", end_reached="0", probable_bot="0", utm_source="google",
        utm_medium="cpc", utm_campaign="retail_analytics", utm_content="sales_question",
    )
    value.update(changes)
    return value


def write_csv(path, rows, fields=FIELDS):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def load(self, rows):
        return report.load_sessions([write_csv(self.root / "input.csv", rows)])

    def test_overlaps_merge_max_metrics_without_double_counting(self):
        a = write_csv(self.root / "first.csv", [row(demo_page_views="1", video_started="1", max_coverage_percent="51")])
        b = write_csv(self.root / "second.csv", [row(last_seen_utc="2026-11-01T10:05:00Z", demo_page_views="2", max_coverage_percent="93", probable_bot="1")])
        sessions, count = report.load_sessions([a, b, a])
        summary, groups = report.summarize(sessions, count)
        self.assertEqual(summary["unique_sessions"], 1)
        self.assertEqual(summary["duplicate_rows_merged"], 2)
        self.assertEqual(summary["cohorts"]["all"]["demo_sessions"], 1)
        self.assertEqual(summary["cohorts"]["all"]["video_start_sessions"], 1)
        self.assertEqual(summary["cohorts"]["all"]["coverage_90_sessions"], 1)
        self.assertEqual(summary["cohorts"]["all"]["engaged_50_sessions"], 1)
        self.assertEqual(summary["cohorts"]["probable_bot_flagged"]["sessions"], 1)
        self.assertEqual(summary["cohorts"]["unflagged"]["sessions"], 0)
        self.assertEqual(len(groups), 4)

    def test_end_reached_is_not_full_coverage_and_missing_coverage_stays_unknown(self):
        sessions, count = self.load([
            row("a", end_reached="1", max_position_seconds="999", max_coverage_percent="10"),
            row("b", video_started="1", max_coverage_percent="", probable_bot=""),
            row("c", max_coverage_percent="89.999"),
            row("d", max_coverage_percent="90"),
        ])
        summary, _ = report.summarize(sessions, count)
        all_metrics = summary["cohorts"]["all"]
        self.assertEqual(all_metrics["end_reached_sessions"], 1)
        self.assertEqual(all_metrics["coverage_50_sessions"], 2)
        self.assertEqual(all_metrics["coverage_90_sessions"], 1)
        self.assertEqual(all_metrics["coverage_unknown_sessions"], 1)
        self.assertEqual(all_metrics["engaged_50_sessions"], 0)
        self.assertEqual(summary["cohorts"]["flag_unknown"]["sessions"], 1)

    def test_attribution_is_deterministic_and_does_not_mix_conflicting_tags(self):
        early = row(utm_campaign="first", first_seen_utc="2026-10-31T10:00:00Z")
        later = row(utm_source="email", utm_campaign="second")
        first = write_csv(self.root / "one.csv", [early, later])
        second = write_csv(self.root / "two.csv", [later, early])
        s1, c1 = report.load_sessions([first])
        s2, c2 = report.load_sessions([second])
        self.assertEqual(report.summarize(s1, c1), report.summarize(s2, c2))
        summary, groups = report.summarize(s1, c1)
        self.assertEqual(groups[0]["campaign"], "first")
        self.assertEqual(groups[0]["source"], "google")
        self.assertEqual(summary["sessions_with_attribution_conflicts"], 1)

    def test_referrer_and_direct_fallback_do_not_claim_organic(self):
        direct = row("direct", **dict.fromkeys(report.UTM_FIELDS, ""))
        referral = row("referral", **dict.fromkeys(report.UTM_FIELDS, ""), referrer_host="chatgpt.com")
        sessions, count = self.load([direct, referral])
        _, groups = report.summarize(sessions, count)
        all_groups = [g for g in groups if g["cohort"] == "all"]
        self.assertEqual({g["source"] for g in all_groups}, {"(direct or unknown)", "chatgpt.com"})
        self.assertEqual(next(g for g in all_groups if g["source"] == "chatgpt.com")["medium"], "referral")

    def test_spend_costs_keep_whole_spend_and_blank_zero_denominators(self):
        sessions, count = self.load([row("a", video_started="1", max_coverage_percent="90"), row("b", video_started="1", probable_bot="1")])
        _, groups = report.summarize(sessions, count)
        fields = [*report.DIMENSIONS, "spend", "currency"]
        spends = [dict(source="google", medium="cpc", campaign="retail_analytics", content="sales_question", spend="20.00", currency="USD"),
                  dict(source="google", medium="cpc", campaign="no_visits", content="", spend="10", currency="USD")]
        output = report.spend_summary(write_csv(self.root / "spend.csv", spends, fields), groups)
        matched = next(x for x in output if x["campaign"] == "retail_analytics")
        self.assertEqual(matched["cost_per_all_video_start"], "10.00")
        self.assertEqual(matched["cost_per_unflagged_video_start"], "20.00")
        self.assertEqual(matched["cost_per_all_coverage_90"], "20.00")
        unmatched = next(x for x in output if x["campaign"] == "no_visits")
        self.assertEqual(unmatched["cost_per_all_video_start"], "")
        self.assertEqual(unmatched["matched_traffic"], "false")

    def test_duplicate_spend_is_rejected(self):
        spend = dict(source="google", medium="cpc", campaign="test", content="", spend="5", currency="USD")
        path = write_csv(self.root / "spend.csv", [spend, spend], [*report.DIMENSIONS, "spend", "currency"])
        with self.assertRaisesRegex(report.ReportError, "duplicate group"):
            report.spend_summary(path, [])

    def test_invalid_values_are_rejected_without_echoing_the_value(self):
        for field, value in (("max_coverage_percent", "101"), ("max_coverage_percent", "NaN"), ("demo_page_views", "-1"), ("probable_bot", "private-token")):
            with self.subTest(field=field, value=value):
                with self.assertRaises(report.ReportError) as caught:
                    self.load([row(**{field: value})])
                self.assertNotIn("private-token", str(caught.exception))

    def test_blank_id_cannot_silently_merge_visitors(self):
        with self.assertRaisesRegex(report.ReportError, "blank visit_id"):
            self.load([row(" ")])

    def test_aggregate_files_do_not_contain_ip_or_visit_id(self):
        path = write_csv(self.root / "input.csv", [row("synthetic-private-session-id", demo_page_views="1")])
        destination = self.root / "out"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(report.main([str(path), "--output-dir", str(destination)]), 0)
        for output in destination.iterdir():
            text = output.read_text(encoding="utf-8-sig")
            for forbidden in ("synthetic-private-session-id", "192.0.2.123", "192.0.2.124", "first_public_ip"):
                self.assertNotIn(forbidden, text)
        summary = json.loads((destination / "summary.json").read_text())
        self.assertFalse(summary["manual_spend_supplied"])
        self.assertIn("does not verify a human", " ".join(summary["interpretation"]))

    def test_safe_campaign_values_and_identifier_guard(self):
        self.assertEqual(report.safe_dimension("=1+1"), "'=1+1")
        self.assertEqual(report.safe_dimension("192.0.2.1"), report.REDACTED)
        self.assertEqual(report.safe_dimension("example@example.invalid"), report.REDACTED)
        self.assertEqual(report.safe_dimension("123e4567-e89b-12d3-a456-426614174000"), report.REDACTED)

    def test_legacy_csv_without_bot_flag_is_unknown(self):
        old_fields = [name for name in FIELDS if name != "probable_bot"]
        legacy = row()
        del legacy["probable_bot"]
        path = write_csv(self.root / "legacy.csv", [legacy], old_fields)
        sessions, count = report.load_sessions([path])
        summary, _ = report.summarize(sessions, count)
        self.assertEqual(summary["cohorts"]["flag_unknown"]["sessions"], 1)
        self.assertEqual(summary["cohorts"]["unflagged"]["sessions"], 0)

    def test_empty_export_is_valid_and_preserves_headers(self):
        sessions, count = self.load([])
        summary, groups = report.summarize(sessions, count)
        self.assertEqual(summary["unique_sessions"], 0)
        self.assertIsNone(summary["earliest_observed_first_seen_utc"])
        self.assertEqual(groups, [])

    def test_cli_prevents_overwriting_an_input(self):
        path = write_csv(self.root / "traffic_by_campaign.csv", [row()])
        before = path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(report.main([str(path), "--output-dir", str(self.root)]), 2)
        self.assertEqual(path.read_bytes(), before)

    def test_rerun_without_spend_clears_previous_spend_output(self):
        path = write_csv(self.root / "input.csv", [row()])
        destination = self.root / "out"
        destination.mkdir()
        (destination / "spend_summary.csv").write_text("old,stale,costs\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(report.main([str(path), "--output-dir", str(destination)]), 0)
        with (destination / "spend_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, report.SPEND_FIELDS)
            self.assertEqual(list(reader), [])


if __name__ == "__main__":
    unittest.main()
