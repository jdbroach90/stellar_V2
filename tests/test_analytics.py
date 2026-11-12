"""Behavior and privacy-boundary tests for the optional demo analytics module.

All traffic uses Flask's in-process test client. No production endpoint, video
host, mail service, or external IP service is contacted.
"""

import base64
from contextlib import closing
import csv
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from flask import Flask

from codejet_analytics import init_analytics


REPO = Path(__file__).resolve().parents[1]
VIDEO_ID = "38ccab99e8156adae4abcfbb1d36cc0f"
ADMIN_TOKEN = "test-admin-token-" + "a" * 48
ORIGIN_KEY = "test-origin-key-" + "b" * 48
FRONTDOOR_ID = "ef992e31-a324-4134-8c86-a607f2159845"
PUBLIC_IP = "8.8.8.8"


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = str(Path(self.temp.name) / "analytics.sqlite3")
        self.app = self.make_app()
        self.client = self.app.test_client()

    def make_app(self):
        app = Flask(__name__, template_folder=str(REPO / "templates"))
        app.config.update(
            TESTING=True,
            CJ_ANALYTICS_ENABLED=True,
            CJ_ANALYTICS_DB_PATH=self.db_path,
            CJ_ANALYTICS_ADMIN_TOKEN=ADMIN_TOKEN,
            CJ_ANALYTICS_ORIGIN_KEY=ORIGIN_KEY,
            CJ_ANALYTICS_FRONTDOOR_ID=FRONTDOOR_ID,
            CJ_ANALYTICS_ALLOWED_ORIGINS="https://codejet.app,https://www.codejet.app",
            CJ_ANALYTICS_IP_MODE="frontdoor",
            CJ_ANALYTICS_RETENTION_DAYS=30,
            CJ_ANALYTICS_LOCAL_DEV=False,
        )
        init_analytics(app)
        app.add_url_rule("/health", "health", lambda: ("healthy\n", 200))
        return app

    def edge_headers(self):
        return {
            "X-CodeJet-Origin-Key": ORIGIN_KEY,
            "X-Azure-FDID": FRONTDOOR_ID,
            "X-Azure-SocketIP": PUBLIC_IP,
        }

    def post(self, path, payload, *, headers=None, client=None):
        supplied = {**self.edge_headers(), "Origin": "https://codejet.app"}
        for key, value in (headers or {}).items():
            if value is None:
                supplied.pop(key, None)
            else:
                supplied[key] = value
        return (client or self.client).post(
            path, json=payload, headers=supplied, base_url="https://codejet.app"
        )

    def visit_payload(self, **changes):
        return {
            "event_id": str(uuid4()),
            "page": "/demo",
            "campaign": {},
            "referrer_host": "",
            **changes,
        }

    def create_visit(self, *, headers=None, client=None, **changes):
        response = self.post(
            "/_cj/analytics/visit", self.visit_payload(**changes),
            headers=headers, client=client,
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        data = response.get_json()
        self.assertIsInstance(data["visit_id"], str)
        self.assertIsInstance(data["visit_token"], str)
        self.assertGreater(data["expires_at"], time.time())
        return data

    def event_payload(self, visit, **changes):
        return {
            "event_id": str(uuid4()),
            "visit_token": visit["visit_token"],
            "event_type": "video_started",
            "page": "/demo",
            "video_id": VIDEO_ID,
            "position_seconds": 0,
            "duration_seconds": 120,
            "played_seconds": 0,
            **changes,
        }

    def admin_get(self, path="/_cj/analytics/report.csv", *, auth="bearer", client=None):
        headers = self.edge_headers()
        if auth == "bearer":
            headers["Authorization"] = "Bearer " + ADMIN_TOKEN
        elif auth == "basic":
            encoded = base64.b64encode(("codejet:" + ADMIN_TOKEN).encode()).decode()
            headers["Authorization"] = "Basic " + encoded
        elif auth is not None:
            headers["Authorization"] = auth
        return (client or self.client).get(
            path, headers=headers, base_url="https://codejet.app"
        )

    def rows(self, **kwargs):
        response = self.admin_get(**kwargs)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return list(csv.DictReader(io.StringIO(response.get_data(as_text=True).lstrip("\ufeff"))))

    def assert_private(self, response):
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertNotIn("X-CodeJet-Origin-Key", response.headers)
        self.assertNotIn("X-Azure-SocketIP", response.headers)
        body = response.get_data(as_text=True)
        self.assertNotIn(ORIGIN_KEY, body)
        self.assertNotIn(ADMIN_TOKEN, body)

    def test_recorded_ip_is_authenticated_frontdoor_socket_not_forwarded_chain(self):
        self.create_visit(headers={
            "X-Forwarded-For": "1.1.1.1, 9.9.9.9",
            "X-Azure-ClientIP": "1.1.1.1",
            "CF-Connecting-IP": "9.9.9.9",
        })
        row = self.rows()[0]
        self.assertEqual(row["first_public_ip"], PUBLIC_IP)
        self.assertEqual(row["last_public_ip"], PUBLIC_IP)
        self.assertNotIn("1.1.1.1", row.values())
        self.assertNotIn("9.9.9.9", row.values())

    def test_valid_ipv6_address_is_preserved(self):
        self.create_visit(headers={"X-Azure-SocketIP": "2606:4700:4700::1111"})
        self.assertEqual(self.rows()[0]["first_public_ip"], "2606:4700:4700::1111")

    def test_missing_or_wrong_origin_proof_cannot_create_visit(self):
        for headers in (
            {"X-CodeJet-Origin-Key": None},
            {"X-CodeJet-Origin-Key": "incorrect"},
            {"X-Azure-FDID": None},
            {"X-Azure-FDID": "a-different-front-door"},
        ):
            with self.subTest(headers=list(headers)):
                response = self.post("/_cj/analytics/visit", self.visit_payload(), headers=headers)
                self.assertEqual(response.status_code, 403)
                self.assert_private(response)
        self.assertEqual(self.rows(), [])

    def test_missing_malformed_and_nonpublic_socket_ips_are_rejected(self):
        for value in (None, "", "8.8.8.8, 1.1.1.1", "8.8.8.8:443", "not-an-ip", "127.0.0.1", "10.0.0.1", "::1"):
            with self.subTest(value=value):
                response = self.post("/_cj/analytics/visit", self.visit_payload(), headers={"X-Azure-SocketIP": value})
                self.assertIn(response.status_code, (400, 403))
                self.assert_private(response)

    def test_cross_origin_and_missing_origin_writes_are_rejected(self):
        for value in (None, "null", "https://attacker.example", "https://codejet.app.attacker.example", "http://codejet.app"):
            with self.subTest(value=value):
                response = self.post("/_cj/analytics/visit", self.visit_payload(), headers={"Origin": value})
                self.assertEqual(response.status_code, 403)
                self.assert_private(response)

    def test_configured_www_origin_is_allowed(self):
        self.create_visit(headers={"Origin": "https://www.codejet.app"})
        self.assertEqual(len(self.rows()), 1)

    def test_ip_cannot_be_supplied_in_browser_payload(self):
        response = self.post("/_cj/analytics/visit", self.visit_payload(ip="1.1.1.1"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.rows(), [])

    def test_valid_token_reuses_visit_and_first_campaign_attribution(self):
        initial = self.create_visit(page="/", campaign={"utm_campaign": "mailer-first"})
        revisited = self.create_visit(
            visit_token=initial["visit_token"], campaign={"utm_campaign": "later-value"}
        )
        self.assertEqual(initial["visit_id"], revisited["visit_id"])
        row = self.rows()[0]
        self.assertEqual(row["utm_campaign"], "mailer-first")
        self.assertEqual(int(row["page_views"]), 2)
        self.assertEqual(int(row["demo_page_views"]), 1)

    def test_page_view_retry_is_idempotent_even_without_returned_token(self):
        payload = self.visit_payload()
        first = self.post("/_cj/analytics/visit", payload)
        retry = self.post("/_cj/analytics/visit", payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(first.get_json()["visit_id"], retry.get_json()["visit_id"])
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["page_views"]), 1)

    def test_event_retry_is_idempotent_and_cannot_move_between_visits(self):
        visit = self.create_visit()
        payload = self.event_payload(visit, event_type="video_progress", position_seconds=30, played_seconds=30)
        for _ in range(2):
            response = self.post("/_cj/analytics/event", payload)
            self.assertEqual(response.status_code, 204)
            self.assert_private(response)
        other = self.create_visit()
        collision = self.post("/_cj/analytics/event", {**payload, "visit_token": other["visit_token"]})
        self.assertEqual(collision.status_code, 409)
        by_id = {row["visit_id"]: row for row in self.rows()}
        self.assertEqual(float(by_id[visit["visit_id"]]["max_played_seconds"]), 30)
        self.assertIn(by_id[other["visit_id"]]["max_played_seconds"], ("", "0", "0.0"))

    def test_invalid_and_expired_visit_tokens_are_rejected(self):
        visit = self.create_visit()
        invalid = self.post("/_cj/analytics/event", self.event_payload(visit, visit_token=visit["visit_token"] + "corrupted"))
        self.assertEqual(invalid.status_code, 401)
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=int(time.time()) - 18000):
            old_response = self.post("/_cj/analytics/visit", self.visit_payload())
            self.assertEqual(old_response.status_code, 200)
            old = old_response.get_json()
        expired = self.post("/_cj/analytics/event", self.event_payload(old))
        self.assertEqual(expired.status_code, 401)
        for response in (invalid, expired):
            self.assert_private(response)

    def test_invalid_token_cannot_silently_reset_existing_visit(self):
        response = self.post("/_cj/analytics/visit", self.visit_payload(visit_token="bad-token"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.rows(), [])

    def test_end_reached_is_separate_from_media_coverage(self):
        visit = self.create_visit()
        self.assertEqual(self.post("/_cj/analytics/event", self.event_payload(visit)).status_code, 204)
        response = self.post("/_cj/analytics/event", self.event_payload(
            visit, event_type="video_ended", position_seconds=120, played_seconds=5,
        ))
        self.assertEqual(response.status_code, 204)
        row = self.rows()[0]
        self.assertEqual(int(row["video_started"]), 1)
        self.assertEqual(int(row["end_reached"]), 1)
        self.assertEqual(float(row["max_played_seconds"]), 5)
        self.assertLess(float(row["max_coverage_percent"]), 10)
        self.assertEqual(float(row["max_position_seconds"]), 120)

    def test_unknown_coverage_stays_blank_in_report(self):
        visit = self.create_visit()
        response = self.post("/_cj/analytics/event", self.event_payload(
            visit, event_type="video_ended", position_seconds=120,
            duration_seconds=120, played_seconds=None,
        ))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.rows()[0]["max_coverage_percent"], "")

    def test_progress_maximum_is_not_overwritten_by_late_earlier_event(self):
        visit = self.create_visit()
        for seconds in (60, 15):
            response = self.post("/_cj/analytics/event", self.event_payload(
                visit, event_type="video_progress", position_seconds=seconds, played_seconds=seconds,
            ))
            self.assertEqual(response.status_code, 204)
        row = self.rows()[0]
        self.assertEqual(float(row["max_played_seconds"]), 60)
        self.assertEqual(float(row["max_coverage_percent"]), 50)

    def test_invalid_event_type_video_and_fields_are_rejected(self):
        visit = self.create_visit()
        for changes in (
            {"event_type": "invented"}, {"event_type": "page_view"},
            {"video_id": "somebody-elses-video"}, {"page": "/"},
            {"event_id": "not-a-uuid"}, {"admin": True},
        ):
            with self.subTest(changes=changes):
                response = self.post("/_cj/analytics/event", self.event_payload(visit, **changes))
                self.assertEqual(response.status_code, 400)
                self.assert_private(response)

    def test_object_and_list_values_receive_validation_errors_not_server_errors(self):
        visit = self.create_visit()
        for changes in ({"event_type": []}, {"event_type": {}}, {"page": []}, {"video_id": {}}, {"visit_token": []}):
            with self.subTest(changes=changes):
                response = self.post("/_cj/analytics/event", self.event_payload(visit, **changes))
                self.assertIn(response.status_code, (400, 401))
                self.assert_private(response)
        for changes in ({"page": []}, {"page": {}}, {"campaign": []}, {"referrer_host": {}}, {"event_id": []}):
            with self.subTest(changes=changes):
                response = self.post("/_cj/analytics/visit", self.visit_payload(**changes))
                self.assertEqual(response.status_code, 400)
                self.assert_private(response)

    def test_invalid_numeric_values_cannot_pollute_reports(self):
        visit = self.create_visit()
        for changes in (
            {"played_seconds": -1}, {"played_seconds": True},
            {"played_seconds": "30"}, {"played_seconds": float("nan")},
            {"duration_seconds": float("inf")}, {"duration_seconds": -1},
            {"position_seconds": 86401}, {"played_seconds": 180},
            {"position_seconds": 180}, {"played_seconds": 10**400},
        ):
            with self.subTest(changes=changes):
                response = self.post("/_cj/analytics/event", self.event_payload(visit, **changes))
                self.assertEqual(response.status_code, 400)
                self.assert_private(response)

    def test_unknown_campaign_fields_and_overlong_values_are_rejected(self):
        for campaign in ({"email": "visitor@example.com"}, {"utm_campaign": "x" * 101}):
            response = self.post("/_cj/analytics/visit", self.visit_payload(campaign=campaign))
            self.assertEqual(response.status_code, 400)

    def test_large_and_non_json_requests_are_rejected(self):
        headers = {**self.edge_headers(), "Origin": "https://codejet.app"}
        too_large = self.client.post(
            "/_cj/analytics/visit", data=json.dumps(self.visit_payload(padding="x" * 5000)),
            content_type="application/json", headers=headers, base_url="https://codejet.app",
        )
        self.assertEqual(too_large.status_code, 413)
        wrong_type = self.client.post(
            "/_cj/analytics/visit", data=json.dumps(self.visit_payload()),
            content_type="text/plain", headers=headers, base_url="https://codejet.app",
        )
        self.assertIn(wrong_type.status_code, (400, 415))
        self.assert_private(too_large)
        self.assert_private(wrong_type)

    def test_reports_require_credentials_and_accept_basic_and_bearer(self):
        self.create_visit()
        for path in ("/_cj/analytics", "/_cj/analytics/report.csv"):
            for auth in (None, "Bearer incorrect"):
                response = self.admin_get(path, auth=auth)
                self.assertEqual(response.status_code, 401)
                self.assertNotIn(PUBLIC_IP, response.get_data(as_text=True))
                self.assert_private(response)
            for auth in ("basic", "bearer"):
                response = self.admin_get(path, auth=auth)
                self.assertEqual(response.status_code, 200)
                self.assertIn(PUBLIC_IP, response.get_data(as_text=True))
                self.assert_private(response)

    def test_origin_secret_alone_is_not_report_authorization(self):
        response = self.admin_get(auth="Bearer " + ORIGIN_KEY)
        self.assertEqual(response.status_code, 401)

    def test_admin_credentials_do_not_bypass_origin_proof(self):
        response = self.client.get(
            "/_cj/analytics/report.csv",
            headers={"Authorization": "Bearer " + ADMIN_TOKEN},
            base_url="https://codejet.app",
        )
        self.assertEqual(response.status_code, 403)
        self.assert_private(response)

    def test_invalid_report_date_ranges_are_rejected(self):
        for days in ("0", "91", "-1", "1.5", "one", "1 OR 1=1"):
            with self.subTest(days=days):
                response = self.admin_get("/_cj/analytics/report.csv?days=" + days)
                self.assertEqual(response.status_code, 400)

    def test_csv_neutralizes_spreadsheet_formulas(self):
        self.create_visit(campaign={"utm_campaign": "=1+1"})
        value = self.rows()[0]["utm_campaign"]
        self.assertEqual(value, "'=1+1")

    def test_report_escapes_html_and_sql_is_treated_as_data(self):
        dangerous = "<script>alert(1)</script>'; DROP TABLE visits; --"
        self.create_visit(campaign={"utm_campaign": dangerous})
        response = self.admin_get("/_cj/analytics")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>alert(1)</script>", response.get_data(as_text=True))
        self.assertIn("&lt;script&gt;", response.get_data(as_text=True))
        self.assertEqual(self.rows()[0]["utm_campaign"], dangerous)
        self.create_visit()
        self.assertEqual(len(self.rows()), 2)

    def test_records_survive_new_application_instance(self):
        visit = self.create_visit(campaign={"utm_campaign": "durability-check"})
        restarted_app = self.make_app()
        restarted_client = restarted_app.test_client()
        rows = self.rows(client=restarted_client)
        self.assertEqual(rows[0]["visit_id"], visit["visit_id"])
        self.assertEqual(rows[0]["utm_campaign"], "durability-check")
        response = self.post("/_cj/analytics/event", self.event_payload(visit), client=restarted_client)
        self.assertEqual(response.status_code, 204)

    def test_report_prunes_expired_visits_and_events_from_database(self):
        old = self.create_visit(campaign={"utm_campaign": "expired-campaign"})
        current = self.create_visit(campaign={"utm_campaign": "current-campaign"})
        expired_at = time.time() - 31 * 86400
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("UPDATE visits SET created_at=?,last_seen=? WHERE visit_id=?", (expired_at, expired_at, old["visit_id"]))
            db.execute("UPDATE events SET received_at=? WHERE visit_id=?", (expired_at, old["visit_id"]))
        rows = self.rows()
        self.assertEqual([row["visit_id"] for row in rows], [current["visit_id"]])
        with closing(sqlite3.connect(self.db_path)) as db, db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM visits WHERE visit_id=?", (old["visit_id"],)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE visit_id=?", (old["visit_id"],)).fetchone()[0], 0)

    def test_valid_token_cannot_resurrect_deleted_visit(self):
        visit = self.create_visit()
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("DELETE FROM visits WHERE visit_id=?", (visit["visit_id"],))
        response = self.post("/_cj/analytics/event", self.event_payload(visit))
        self.assertEqual(response.status_code, 401)
        response = self.post("/_cj/analytics/visit", self.visit_payload(visit_token=visit["visit_token"]))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.rows(), [])

    def test_privacy_signal_skips_collection(self):
        for headers in ({"DNT": "1"}, {"Sec-GPC": "1"}):
            response = self.post("/_cj/analytics/visit", self.visit_payload(), headers=headers)
            self.assertEqual(response.status_code, 204)
            self.assert_private(response)
        self.assertFalse(Path(self.db_path).exists())

    def test_direct_mode_requires_opt_in_and_loopback(self):
        self.app.config["CJ_ANALYTICS_IP_MODE"] = "direct"
        response = self.post("/_cj/analytics/visit", self.visit_payload())
        self.assertEqual(response.status_code, 503)
        self.app.config["CJ_ANALYTICS_LOCAL_DEV"] = True
        response = self.client.post(
            "/_cj/analytics/visit", json=self.visit_payload(),
            headers={"Origin": "https://codejet.app"},
            environ_overrides={"REMOTE_ADDR": PUBLIC_IP}, base_url="https://codejet.app",
        )
        self.assertEqual(response.status_code, 403)
        self.create_visit()
        self.assertEqual(self.rows()[0]["first_public_ip"], "127.0.0.1")

    def test_disabled_tracking_does_not_write_or_expose_reports(self):
        self.app.config["CJ_ANALYTICS_ENABLED"] = False
        response = self.post("/_cj/analytics/visit", self.visit_payload())
        self.assertEqual(response.status_code, 404)
        self.assert_private(response)
        self.assertEqual(self.admin_get().status_code, 404)
        self.assertFalse(Path(self.db_path).exists())
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_storage_failure_is_contained_to_analytics(self):
        self.app.config["CJ_ANALYTICS_DB_PATH"] = self.temp.name  # A directory cannot be a SQLite file.
        response = self.post("/_cj/analytics/visit", self.visit_payload())
        self.assertEqual(response.status_code, 503)
        self.assert_private(response)
        self.assertNotIn(self.temp.name, response.get_data(as_text=True))
        self.assertEqual(self.client.get("/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()
