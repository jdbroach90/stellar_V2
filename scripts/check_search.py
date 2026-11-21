#!/usr/bin/env python3
"""Read-only checks of CodeJet's public search release; no account integration.

Examples:
    python scripts/check_search.py --local
    python scripts/check_search.py --base-url https://codejet.app
    python scripts/check_search.py --base-url https://codejet.app --require-video-schema

Network mode uses only the standard library and unauthenticated public GETs.
Local mode requires the existing Flask application's installed requirements.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree as ET


CANONICAL_ORIGIN = "https://codejet.app"
PAGES = (
    "/", "/demo", "/retail-analytics-software",
    "/retail-reporting-automation", "/retail-data-questions",
)
PNG_PATH = "/static/images/campaign/codejet-retail-analytics.png"
PUBLIC_PATHS = frozenset((*PAGES, "/robots.txt", "/sitemap.xml", PNG_PATH))
MAX_BYTES = 4 * 1024 * 1024
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9",
      "v": "http://www.google.com/schemas/sitemap-video/1.1"}


class PublicHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = []
        self.headings = []
        self.descriptions = []
        self.canonicals = []
        self.robots = []
        self.json_scripts = []
        self._title = self._heading = self._json = None

    def handle_starttag(self, tag, attrs):
        attrs = {key: value or "" for key, value in attrs}
        if tag == "title":
            self.titles.append([])
            self._title = self.titles[-1]
        elif tag == "h1":
            self.headings.append([])
            self._heading = self.headings[-1]
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.descriptions.append(attrs.get("content", ""))
            if name in {"robots", "googlebot", "oai-searchbot", "oai-adsbot"}:
                self.robots.append(attrs.get("content", ""))
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.json_scripts.append([])
            self._json = self.json_scripts[-1]

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = None
        elif tag == "h1":
            self._heading = None
        elif tag == "script":
            self._json = None

    def handle_data(self, data):
        for target in (self._title, self._heading, self._json):
            if target is not None:
                target.append(data)


class PublicRedirects(HTTPRedirectHandler):
    """Never follow a public check into a private path or unrelated host."""
    def __init__(self, hostname):
        self.hosts = {hostname}
        if hostname in {"codejet.app", "www.codejet.app"}:
            self.hosts.update({"codejet.app", "www.codejet.app"})

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if (parts.scheme != "https" or parts.hostname not in self.hosts
                or parts.username or parts.password or parts.path not in PUBLIC_PATHS
                or parts.query or parts.fragment):
            raise URLError("Redirect leaves the approved public resources")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def normalized_headers(items):
    result = {}
    for key, value in items:
        key = key.lower()
        result[key] = result.get(key, "") + (", " if key in result else "") + value
    return result


def network_fetcher(base_url, timeout):
    opener = build_opener(PublicRedirects(urlsplit(base_url).hostname))

    def fetch(path):
        if path not in PUBLIC_PATHS:
            raise ValueError("Only approved public resources may be checked")
        req = Request(base_url + path, method="GET", headers={
            "User-Agent": "CodeJet-Public-Release-Check/1.0",
            "Accept": "text/html,application/xml,text/plain,image/png,*/*;q=0.5",
        })
        try:
            response = opener.open(req, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Response exceeds the release check's 4 MiB limit")
            return response.status, normalized_headers(response.headers.items()), body
    return fetch


def local_fetcher():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    try:
        from server import app
    except ImportError as error:
        raise RuntimeError("Local mode needs the repository requirements; use its virtual-environment Python") from error
    client = app.test_client()

    def fetch(path):
        if path not in PUBLIC_PATHS:
            raise ValueError("Only approved public resources may be checked")
        result = client.get(path, base_url=CANONICAL_ORIGIN, follow_redirects=False)
        return result.status_code, normalized_headers(result.headers.items()), result.data
    return fetch


def walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def blocked_indexing(value):
    return bool(re.search(r"(?:^|[\s,:;])(noindex|none)(?:$|[\s,;])", value.lower()))


def robots_allows(text, agent, path):
    """Evaluate product-agent groups and longest matching Allow/Disallow rules.

    A first-match parser can wrongly let an Allow: / hide a later, more
    specific Disallow. Support the wildcard and end-anchor forms used by bots.
    """
    groups, agents, rules = [], [], []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif key in {"allow", "disallow"} and agents:
            rules.append((value, key == "allow"))
    if agents:
        groups.append((agents, rules))
    matching = []
    for names, group_rules in groups:
        weights = [0 if name == "*" else len(name) for name in names
                   if name and (name == "*" or name in agent.lower())]
        if weights:
            matching.append((max(weights), group_rules))
    if not matching:
        return True
    best = max(weight for weight, _ in matching)
    decisions = []
    for weight, group_rules in matching:
        if weight != best:
            continue
        for pattern, allow in group_rules:
            if not pattern:
                continue
            anchored = pattern.endswith("$")
            core = pattern[:-1] if anchored else pattern
            regex = "^" + re.escape(core).replace(r"\*", ".*") + ("$" if anchored else "")
            if re.search(regex, path):
                decisions.append((len(core.replace("*", "").encode("utf-8")), allow))
    return max(decisions)[1] if decisions else True


def reject_json_constant(_value):
    raise ValueError("Nonstandard JSON constant")


class Check:
    def __init__(self):
        self.failures = 0
        self.warnings = 0

    def fail(self, label, message):
        self.failures += 1
        print(f"FAIL {label}: {message}")

    def require(self, condition, label, message):
        if not condition:
            self.fail(label, message)
        return condition

    def warn(self, message):
        self.warnings += 1
        print(f"WARN {message}")


def run(fetch, require_video):
    check = Check()
    video_nodes = []

    def get(path):
        try:
            status, headers, body = fetch(path)
        except (OSError, ValueError, RuntimeError) as error:
            check.fail(path, f"public GET failed ({type(error).__name__})")
            return None
        if not check.require(status == 200, path, f"expected HTTP 200; received {status}"):
            return None
        return headers, body

    for path in PAGES:
        before = check.failures
        result = get(path)
        if result is None:
            continue
        headers, body = result
        check.require("text/html" in headers.get("content-type", "").lower(), path, "expected HTML content type")
        parsed = PublicHTML()
        parsed.feed(body.decode("utf-8", errors="replace"))
        for name, values in (("title", parsed.titles), ("H1", parsed.headings)):
            check.require(len(values) == 1 and bool("".join(values[0]).strip()), path, f"expected one nonempty {name}")
        check.require(len(parsed.descriptions) == 1 and bool(parsed.descriptions[0].strip()), path, "expected one nonempty meta description")
        check.require(parsed.canonicals == [CANONICAL_ORIGIN + path], path, "expected exactly one fixed production canonical without query parameters")
        directives = parsed.robots + [headers.get("x-robots-tag", "")]
        check.require(not any(blocked_indexing(item) for item in directives), path, "unexpected noindex/none directive")
        check.require(bool(parsed.json_scripts), path, "missing JSON-LD")
        for script in parsed.json_scripts:
            try:
                data = json.loads("".join(script), parse_constant=reject_json_constant)
                if not isinstance(data, (dict, list)):
                    raise ValueError
            except (ValueError, TypeError):
                check.fail(path, "JSON-LD is not a valid object or array")
                continue
            for node in walk_json(data):
                kind = node.get("@type")
                if path == "/demo" and (kind == "VideoObject" or isinstance(kind, list) and "VideoObject" in kind):
                    video_nodes.append(node)
        if check.failures == before:
            print(f"PASS {path}: public HTML, title, H1, description, canonical, and JSON-LD")

    if not video_nodes:
        if require_video:
            check.fail("/demo", "VideoObject required by --require-video-schema but absent")
        else:
            check.warn("VideoObject absent: opt-in video schema awaits verified original upload metadata; ordinary page checks continue")
    else:
        for node in video_nodes:
            check.require(bool(node.get("name")) and bool(node.get("thumbnailUrl")), "/demo", "VideoObject needs name and thumbnailUrl")
            try:
                uploaded = datetime.fromisoformat(str(node.get("uploadDate", "")).replace("Z", "+00:00"))
                valid_date = uploaded.tzinfo is not None and uploaded <= datetime.now(timezone.utc)
            except ValueError:
                valid_date = False
            check.require(valid_date, "/demo", "VideoObject needs a past original uploadDate with timezone")

    result = get("/robots.txt")
    if result is not None:
        before = check.failures
        headers, body = result
        text = body.decode("utf-8", errors="replace")
        check.require("text/plain" in headers.get("content-type", "").lower()
                      and bool(re.search(r"(?im)^\s*user-agent\s*:", text)),
                      "/robots.txt", "expected plain-text robots rules, not an HTML challenge")
        for agent in ("Googlebot", "OAI-SearchBot", "OAI-AdsBot"):
            for path in PAGES:
                check.require(robots_allows(text, agent, path), "/robots.txt", f"rules block {agent} from {path}")
        if check.failures == before:
            print("PASS /robots.txt: rules permit Googlebot, OAI-SearchBot, and OAI-AdsBot on public pages")

    result = get("/sitemap.xml")
    if result is not None:
        before = check.failures
        _, body = result
        try:
            root = ET.fromstring(body)
            locations = [node.text for node in root.findall("s:url/s:loc", NS)]
            expected = {CANONICAL_ORIGIN + path for path in PAGES}
            check.require(root.tag == "{" + NS["s"] + "}urlset" and len(locations) == len(PAGES)
                          and set(locations) == expected, "/sitemap.xml", "expected exactly the five canonical public page URLs, with no private or query URLs")
            demo_entries = [node for node in root.findall("s:url", NS)
                            if node.findtext("s:loc", namespaces=NS) == CANONICAL_ORIGIN + "/demo"]
            has_video = any(node.find("v:video", NS) is not None for node in demo_entries)
            check.require(has_video == bool(video_nodes), "/sitemap.xml", "demo video entry and page VideoObject must be enabled together")
        except ET.ParseError:
            check.fail("/sitemap.xml", "invalid XML")
        if check.failures == before:
            print("PASS /sitemap.xml: exactly five canonical public pages; video gating agrees")

    result = get(PNG_PATH)
    if result is not None:
        headers, body = result
        valid_png = (len(body) >= 24 and body[:8] == b"\x89PNG\r\n\x1a\n"
                     and body[12:16] == b"IHDR" and all(struct.unpack(">II", body[16:24])))
        if check.require("image/png" in headers.get("content-type", "").lower() and valid_png,
                         PNG_PATH, "expected PNG content with a valid signature and nonzero dimensions"):
            print("PASS social image: PNG endpoint serves image bytes")

    print(f"\nResult: {check.failures} failure(s), {check.warnings} warning(s).")
    print("This checks public release responses, not indexing, ranking, human traffic, or ad-account configuration.")
    return 1 if check.failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local", action="store_true", help="Use the existing Flask test client; no network")
    mode.add_argument("--base-url", help="Public HTTPS origin to check, such as https://codejet.app")
    parser.add_argument("--require-video-schema", action="store_true", help="Fail instead of warn when video schema is absent")
    parser.add_argument("--timeout", type=float, default=12, help="Timeout in seconds per network GET (default: 12)")
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 60:
        parser.error("--timeout must be greater than zero and at most 60")
    try:
        if args.local:
            fetch = local_fetcher()
        else:
            base = args.base_url.rstrip("/")
            parts = urlsplit(base)
            if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
                    or parts.path or parts.query or parts.fragment):
                parser.error("--base-url must be an HTTPS origin without credentials, path, query, or fragment")
            fetch = network_fetcher(base, args.timeout)
        return run(fetch, args.require_video_schema)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"FAIL setup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
