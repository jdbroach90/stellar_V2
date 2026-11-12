"""Small first-party demo analytics; disabled until explicitly configured.

IP addresses are observed network addresses, not verified people or businesses.
Browser playback events are best-effort telemetry, not proof of human attention.
"""

import csv
import hashlib
import hmac
import io
import ipaddress
import math
import os
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import click
from flask import Blueprint, Response, current_app, g, jsonify, render_template, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.exceptions import HTTPException


VIDEO_ID = "38ccab99e8156adae4abcfbb1d36cc0f"
TOKEN_TTL = 4 * 60 * 60
MAX_BODY_BYTES = 4096
RATE_PER_MINUTE = 120
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
EVENT_TYPES = {"video_started", "video_progress", "video_ended"}
REPORT_FIELDS = (
    "visit_id", "first_seen_utc", "last_seen_utc", "first_public_ip", "last_public_ip",
    "ip_source", "landing_page", "page_views", "demo_page_views", "video_started",
    "end_reached", "max_played_seconds", "max_coverage_percent", "max_position_seconds",
    *UTM_KEYS, "referrer_host", "probable_bot",
)
BOT_PATTERN = re.compile(r"bot\b|crawler|spider|headless|preview|lighthouse", re.I)
bp = Blueprint("cj_analytics", __name__)


class AnalyticsError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


def _enabled(value):
    return value is True or str(value).strip().lower() in {"1", "true", "yes"}


def _settings():
    c = current_app.config
    admin = c.get("CJ_ANALYTICS_ADMIN_TOKEN", "")
    origin_key = c.get("CJ_ANALYTICS_ORIGIN_KEY", "")
    mode = c.get("CJ_ANALYTICS_IP_MODE", "frontdoor")
    db_value = c.get("CJ_ANALYTICS_DB_PATH", "")
    if not isinstance(admin, str) or len(admin) < 32:
        raise AnalyticsError(503, "Analytics configuration is incomplete.")
    if mode not in {"frontdoor", "direct"}:
        raise AnalyticsError(503, "Analytics configuration is incomplete.")
    if mode == "frontdoor":
        if not isinstance(origin_key, str) or len(origin_key) < 32 or origin_key == admin:
            raise AnalyticsError(503, "Analytics configuration is incomplete.")
        try:
            fdid = str(uuid.UUID(str(c.get("CJ_ANALYTICS_FRONTDOOR_ID", ""))))
        except ValueError:
            raise AnalyticsError(503, "Analytics configuration is incomplete.") from None
    else:
        fdid = ""
        if not _enabled(c.get("CJ_ANALYTICS_LOCAL_DEV", False)):
            raise AnalyticsError(503, "Direct mode is limited to local development.")
    if not isinstance(db_value, str) or not db_value or not Path(db_value).is_absolute():
        raise AnalyticsError(503, "Analytics requires an absolute database path.")
    db_path = Path(db_value)
    static_path = Path(current_app.static_folder or current_app.root_path).resolve()
    if db_path.is_symlink() or db_path.resolve().is_relative_to(static_path):
        raise AnalyticsError(503, "Analytics database path is unsafe.")
    try:
        retention = int(c.get("CJ_ANALYTICS_RETENTION_DAYS", 30))
        if not 1 <= retention <= 90:
            raise ValueError
    except (TypeError, ValueError):
        raise AnalyticsError(503, "Analytics retention must be 1 to 90 days.") from None
    origins = c.get("CJ_ANALYTICS_ALLOWED_ORIGINS", "https://codejet.app,https://www.codejet.app")
    if not isinstance(origins, str):
        raise AnalyticsError(503, "Analytics origins are invalid.")
    allowed = set()
    for origin in origins.split(","):
        origin = origin.strip().rstrip("/")
        parts = urlsplit(origin)
        if not parts.netloc or parts.path or parts.query or parts.fragment or parts.username:
            raise AnalyticsError(503, "Analytics origins are invalid.")
        local_http = mode == "direct" and parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1"}
        if parts.scheme != "https" and not local_http:
            raise AnalyticsError(503, "Analytics origins require HTTPS.")
        allowed.add(origin)
    return {
        "admin": admin, "origin_key": origin_key, "mode": mode, "fdid": fdid,
        "db_path": db_path, "retention": retention, "origins": allowed,
    }


def _safe_equal(provided, expected):
    if not isinstance(provided, str) or len(provided) > 1024:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def _authenticate_origin(s):
    if s["mode"] == "direct":
        try:
            if not ipaddress.ip_address(request.remote_addr or "").is_loopback:
                raise ValueError
        except ValueError:
            raise AnalyticsError(403, "Local development requests must use loopback.") from None
        return
    if not _safe_equal(request.headers.get("X-CodeJet-Origin-Key", ""), s["origin_key"]):
        raise AnalyticsError(403, "Trusted origin required.")
    if not _safe_equal(request.headers.get("X-Azure-FDID", "").lower(), s["fdid"]):
        raise AnalyticsError(403, "Trusted origin required.")


def _public_ip(s):
    # Do not use XFF, X-Azure-ClientIP, ProxyFix, or an IP supplied in JSON.
    raw = request.remote_addr if s["mode"] == "direct" else request.headers.get("X-Azure-SocketIP", "")
    try:
        if not raw or "%" in raw or "," in raw:
            raise ValueError
        address = ipaddress.ip_address(raw.strip())
        if getattr(address, "ipv4_mapped", None):
            address = address.ipv4_mapped
        if s["mode"] == "frontdoor" and not address.is_global:
            raise ValueError
    except ValueError:
        raise AnalyticsError(400, "A valid observed public IP is required.") from None
    source = "frontdoor_socket" if s["mode"] == "frontdoor" else "local_test"
    return str(address), source


@bp.before_request
def _guard():
    if request.endpoint == "cj_analytics.privacy":
        return None
    if not _enabled(current_app.config.get("CJ_ANALYTICS_ENABLED", False)):
        raise AnalyticsError(404, "Analytics is disabled.")
    request.max_content_length = MAX_BODY_BYTES
    s = _settings()
    g.cj_analytics_settings = s
    _authenticate_origin(s)
    if request.method == "POST":
        origin = request.headers.get("Origin", "")
        if origin not in s["origins"] or request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise AnalyticsError(403, "Same-origin browser request required.")
        if request.headers.get("Sec-GPC") == "1" or request.headers.get("DNT") == "1":
            return Response(status=204)
    return None


@bp.after_request
def _private_response(response):
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.endpoint in {"cj_analytics.report", "cj_analytics.report_csv"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
    return response


@bp.errorhandler(AnalyticsError)
def _analytics_error(error):
    response = jsonify(error=error.message)
    response.status_code = error.status
    if error.status == 429:
        response.headers["Retry-After"] = "60"
    return response


@bp.errorhandler(HTTPException)
def _http_error(error):
    return jsonify(error="Invalid analytics request."), error.code


@bp.errorhandler(sqlite3.Error)
@bp.errorhandler(OSError)
def _storage_error(error):
    # Never log the request, credentials, IPs, SQL values, or exception message.
    current_app.logger.error("Demo analytics storage unavailable (%s)", type(error).__name__)
    return jsonify(error="Analytics storage is temporarily unavailable."), 503


def _json(allowed, required):
    if not request.is_json:
        raise AnalyticsError(415, "JSON required.")
    try:
        value = request.get_json()
    except (ValueError, RecursionError):
        raise AnalyticsError(400, "Invalid analytics JSON.") from None
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise AnalyticsError(400, "Invalid analytics fields.")
    return value


def _uuid(value):
    if not isinstance(value, str) or len(value) != 36:
        raise AnalyticsError(400, "Invalid event identifier.")
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise AnalyticsError(400, "Invalid event identifier.") from None


def _text(value, length=100):
    if not isinstance(value, str) or len(value) > length or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise AnalyticsError(400, "Invalid analytics text.")
    return value


def _signer(s):
    return URLSafeTimedSerializer(s["admin"], salt="codejet-demo-visit-v1")


def _visit_id(token, s):
    if not isinstance(token, str) or len(token) > 512:
        raise AnalyticsError(401, "Visit token is invalid or expired.")
    try:
        value = _signer(s).loads(token, max_age=TOKEN_TTL)
        return str(uuid.UUID(value))
    except (BadSignature, SignatureExpired, ValueError, TypeError, AttributeError):
        raise AnalyticsError(401, "Visit token is invalid or expired.") from None


SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
    visit_id TEXT PRIMARY KEY, created_at REAL NOT NULL, last_seen REAL NOT NULL,
    first_ip TEXT NOT NULL, last_ip TEXT NOT NULL, ip_source TEXT NOT NULL,
    landing_page TEXT NOT NULL,
    utm_source TEXT NOT NULL, utm_medium TEXT NOT NULL, utm_campaign TEXT NOT NULL,
    utm_content TEXT NOT NULL, utm_term TEXT NOT NULL,
    referrer_host TEXT NOT NULL, probable_bot INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS visits_last_seen ON visits(last_seen);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY, visit_id TEXT NOT NULL REFERENCES visits(visit_id) ON DELETE CASCADE,
    received_at REAL NOT NULL, event_type TEXT NOT NULL, page TEXT NOT NULL,
    video_id TEXT, client_ip TEXT NOT NULL, ip_source TEXT NOT NULL,
    position_seconds REAL, duration_seconds REAL, played_seconds REAL
);
CREATE INDEX IF NOT EXISTS events_visit_time ON events(visit_id, received_at);
CREATE INDEX IF NOT EXISTS events_time ON events(received_at);
CREATE TABLE IF NOT EXISTS rate_limits (
    bucket TEXT NOT NULL, minute INTEGER NOT NULL, hits INTEGER NOT NULL,
    PRIMARY KEY (bucket, minute)
);
"""


@contextmanager
def _database(s):
    path = s["db_path"]
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    except FileExistsError:
        pass
    os.chmod(path, 0o600)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA secure_delete=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)
        with connection:
            yield connection
    finally:
        connection.close()


def _prune(connection, s, now):
    cutoff = now - s["retention"] * 86400
    connection.execute("DELETE FROM events WHERE received_at < ?", (cutoff,))
    connection.execute("DELETE FROM visits WHERE created_at < ? OR last_seen < ?", (cutoff, cutoff))
    connection.execute("DELETE FROM rate_limits WHERE minute < ?", (int(now // 60) - 2,))


def _rate_limit(connection, s, ip, now):
    bucket = hmac.new(s["admin"].encode(), ip.encode(), hashlib.sha256).hexdigest()
    minute = int(now // 60)
    connection.execute(
        "INSERT INTO rate_limits(bucket, minute, hits) VALUES (?, ?, 1) "
        "ON CONFLICT(bucket,minute) DO UPDATE SET hits=hits+1",
        (bucket, minute),
    )
    count = connection.execute(
        "SELECT hits FROM rate_limits WHERE bucket=? AND minute=?", (bucket, minute)
    ).fetchone()["hits"]
    if count > RATE_PER_MINUTE:
        raise AnalyticsError(429, "Analytics request limit reached.")


def _insert_event(connection, event_id, visit_id, now, event_type, page, ip, source,
                  video_id=None, position=None, duration=None, played=None):
    previous = connection.execute(
        "SELECT visit_id,event_type FROM events WHERE event_id=?", (event_id,)
    ).fetchone()
    if previous:
        if previous["visit_id"] != visit_id or previous["event_type"] != event_type:
            raise AnalyticsError(409, "Event identifier already used.")
        return False
    connection.execute(
        "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (event_id, visit_id, now, event_type, page, video_id, ip, source, position, duration, played),
    )
    return True


@bp.post("/_cj/analytics/visit")
def visit():
    s = g.cj_analytics_settings
    data = _json({"event_id", "page", "visit_token", "campaign", "referrer_host"}, {"event_id", "page"})
    event_id = _uuid(data["event_id"])
    if not isinstance(data["page"], str) or data["page"] not in {"/", "/demo"}:
        raise AnalyticsError(400, "Invalid analytics page.")
    campaign = data.get("campaign", {})
    if not isinstance(campaign, dict) or set(campaign) - set(UTM_KEYS):
        raise AnalyticsError(400, "Invalid campaign.")
    campaign_values = [_text(campaign.get(key, "")) for key in UTM_KEYS]
    referrer = _text(data.get("referrer_host", ""), 253).lower()
    if referrer and not re.fullmatch(r"[a-z0-9.-]+", referrer):
        raise AnalyticsError(400, "Only a referrer hostname may be recorded.")
    ip, source = _public_ip(s)
    now = time.time()
    given_token = data.get("visit_token")
    visit_id = _visit_id(given_token, s) if given_token else None
    with _database(s) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _prune(connection, s, now)
        _rate_limit(connection, s, ip, now)
        duplicate = connection.execute(
            "SELECT visit_id,event_type,page FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if duplicate:
            if (duplicate["event_type"] != "page_view" or duplicate["page"] != data["page"]
                    or (visit_id and duplicate["visit_id"] != visit_id)):
                raise AnalyticsError(409, "Event identifier already used.")
            visit_id = duplicate["visit_id"]
        if visit_id:
            existing = connection.execute("SELECT 1 FROM visits WHERE visit_id=?", (visit_id,)).fetchone()
            if not existing:
                raise AnalyticsError(401, "Visit token is invalid or expired.")
        else:
            visit_id = str(uuid.uuid4())
            bot = int(bool(BOT_PATTERN.search(request.headers.get("User-Agent", "")[:512])))
            connection.execute(
                "INSERT INTO visits VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (visit_id, now, now, ip, ip, source, data["page"], *campaign_values, referrer, bot),
            )
        inserted = _insert_event(connection, event_id, visit_id, now, "page_view", data["page"], ip, source)
        if inserted:
            connection.execute(
                "UPDATE visits SET last_seen=?,last_ip=? WHERE visit_id=?", (now, ip, visit_id)
            )
    return jsonify(visit_id=visit_id, visit_token=_signer(s).dumps(visit_id), expires_at=int(now) + TOKEN_TTL)


def _metric(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalyticsError(400, "Invalid playback metric.")
    if not 0 <= value <= 86400 or not math.isfinite(value):
        raise AnalyticsError(400, "Invalid playback metric.")
    return round(float(value), 3)


@bp.post("/_cj/analytics/event")
def event():
    s = g.cj_analytics_settings
    data = _json(
        {"event_id", "visit_token", "event_type", "page", "video_id",
         "position_seconds", "duration_seconds", "played_seconds"},
        {"event_id", "visit_token", "event_type", "page", "video_id"},
    )
    event_id = _uuid(data["event_id"])
    visit_id = _visit_id(data["visit_token"], s)
    if (not isinstance(data["event_type"], str) or data["event_type"] not in EVENT_TYPES
            or data["page"] != "/demo" or data["video_id"] != VIDEO_ID):
        raise AnalyticsError(400, "Invalid video event.")
    position = _metric(data.get("position_seconds"))
    duration = _metric(data.get("duration_seconds"))
    played = _metric(data.get("played_seconds"))
    if duration is not None and duration > 0:
        if (position is not None and position > duration + 2) or (played is not None and played > duration + 1):
            raise AnalyticsError(400, "Playback metrics exceed video duration.")
    ip, source = _public_ip(s)
    now = time.time()
    with _database(s) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _prune(connection, s, now)
        _rate_limit(connection, s, ip, now)
        if not connection.execute("SELECT 1 FROM visits WHERE visit_id=?", (visit_id,)).fetchone():
            raise AnalyticsError(401, "Visit token is invalid or expired.")
        inserted = _insert_event(connection, event_id, visit_id, now, data["event_type"], data["page"],
                                 ip, source, VIDEO_ID, position, duration, played)
        if inserted:
            connection.execute(
                "UPDATE visits SET last_seen=?,last_ip=? WHERE visit_id=?", (now, ip, visit_id)
            )
    return Response(status=204)


def _admin():
    s = g.cj_analytics_settings
    authorization = request.headers.get("Authorization", "")
    valid = False
    if authorization.startswith("Bearer "):
        valid = _safe_equal(authorization[7:], s["admin"])
    else:
        auth = request.authorization
        if auth and auth.type == "basic":
            valid = _safe_equal(auth.username or "", "codejet") and _safe_equal(auth.password or "", s["admin"])
    if not valid:
        return Response(
            "Authentication required.", status=401,
            headers={"WWW-Authenticate": 'Basic realm="CodeJet demo analytics", charset="UTF-8"'},
            mimetype="text/plain",
        )
    return None


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _report_data():
    s = g.cj_analytics_settings
    try:
        days = int(request.args.get("days", "7"))
        if not 1 <= days <= 90:
            raise ValueError
    except ValueError:
        raise AnalyticsError(400, "Days must be 1 to 90.") from None
    now = time.time()
    since = now - min(days, s["retention"]) * 86400
    with _database(s) as connection:
        _prune(connection, s, now)
        records = connection.execute(
            """
            SELECT v.*,
              SUM(CASE WHEN e.event_type='page_view' THEN 1 ELSE 0 END) page_views,
              SUM(CASE WHEN e.event_type='page_view' AND e.page='/demo' THEN 1 ELSE 0 END) demo_page_views,
              MAX(CASE WHEN e.event_type='video_started' THEN 1 ELSE 0 END) video_started,
              MAX(CASE WHEN e.event_type='video_ended' THEN 1 ELSE 0 END) end_reached,
              MAX(e.played_seconds) max_played_seconds,
              MAX(CASE WHEN e.duration_seconds > 0 AND e.played_seconds IS NOT NULL
                  THEN MIN(100.0, e.played_seconds * 100.0 / e.duration_seconds) END) max_coverage_percent,
              MAX(e.position_seconds) max_position_seconds
            FROM visits v JOIN events e ON v.visit_id=e.visit_id
            WHERE e.received_at >= ?
            GROUP BY v.visit_id ORDER BY v.last_seen DESC LIMIT 10001
            """, (since,),
        ).fetchall()
    truncated = len(records) > 10000
    rows = []
    for r in records[:10000]:
        row = {
            "visit_id": r["visit_id"], "first_seen_utc": _iso(r["created_at"]),
            "last_seen_utc": _iso(r["last_seen"]), "first_public_ip": r["first_ip"],
            "last_public_ip": r["last_ip"], "ip_source": r["ip_source"],
            "landing_page": r["landing_page"], "referrer_host": r["referrer_host"],
            "probable_bot": r["probable_bot"],
        }
        for key in ("page_views", "demo_page_views", "video_started", "end_reached",
                    "max_played_seconds", "max_coverage_percent", "max_position_seconds", *UTM_KEYS):
            value = r[key]
            row[key] = round(value, 2) if isinstance(value, float) else value
        rows.append(row)
    summary = {
        "visits": len(rows), "public_ips": len({r["first_public_ip"] for r in rows}),
        "demo_visits": sum(r["demo_page_views"] > 0 for r in rows),
        "started": sum(r["video_started"] > 0 for r in rows),
        "ended": sum(r["end_reached"] > 0 for r in rows),
        "coverage_90": sum((r["max_coverage_percent"] or 0) >= 90 for r in rows),
    }
    return rows, summary, days, truncated


@bp.get("/_cj/analytics")
def report():
    denied = _admin()
    if denied is not None:
        return denied
    rows, summary, days, truncated = _report_data()
    return render_template(
        "demo_analytics_report.html", rows=rows[:500], summary=summary, days=days,
        truncated=truncated or len(rows) > 500, retention=g.cj_analytics_settings["retention"],
    )


def _csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@bp.get("/_cj/analytics/report.csv")
def report_csv():
    denied = _admin()
    if denied is not None:
        return denied
    rows, _summary, _days, truncated = _report_data()
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=REPORT_FIELDS, lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _csv_cell(row.get(k)) for k in REPORT_FIELDS})
    response = Response("\ufeff" + output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = 'attachment; filename="codejet-demo-visits.csv"'
    if truncated:
        response.headers["X-CodeJet-Report-Truncated"] = "true"
    return response


@bp.get("/demo-privacy")
def privacy():
    try:
        retention = int(current_app.config.get("CJ_ANALYTICS_RETENTION_DAYS", 30))
    except (TypeError, ValueError):
        retention = 30
    return render_template("demo_analytics_privacy.html", retention=retention)


def init_analytics(app):
    defaults = {
        "CJ_ANALYTICS_ENABLED": "0", "CJ_ANALYTICS_DB_PATH": "",
        "CJ_ANALYTICS_ADMIN_TOKEN": "", "CJ_ANALYTICS_ORIGIN_KEY": "",
        "CJ_ANALYTICS_FRONTDOOR_ID": "", "CJ_ANALYTICS_IP_MODE": "frontdoor",
        "CJ_ANALYTICS_LOCAL_DEV": "0", "CJ_ANALYTICS_RETENTION_DAYS": "30",
        "CJ_ANALYTICS_ALLOWED_ORIGINS": "https://codejet.app,https://www.codejet.app",
    }
    for name, default in defaults.items():
        app.config.setdefault(name, os.getenv(name, default))
    app.register_blueprint(bp)

    @app.context_processor
    def analytics_context():
        return {"cj_analytics_enabled": _enabled(app.config.get("CJ_ANALYTICS_ENABLED", False))}

    @app.cli.command("analytics-prune")
    def analytics_prune():
        """Delete expired analytics records. Does not change website content."""
        if not _enabled(app.config.get("CJ_ANALYTICS_ENABLED", False)):
            raise click.ClickException("Analytics is disabled.")
        try:
            s = _settings()
            with _database(s) as connection:
                before = connection.total_changes
                _prune(connection, s, time.time())
                deleted = connection.total_changes - before
            click.echo(f"Pruned {deleted} expired analytics/rate-limit rows.")
        except (AnalyticsError, OSError, sqlite3.Error) as error:
            raise click.ClickException(f"Analytics maintenance failed ({type(error).__name__}).") from None
