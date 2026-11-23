"""Public search pages and metadata; no ad accounts or tracking pixels.

Canonical URLs never depend on an incoming Host header. Video structured data
is opt-in until the owner verifies the video's original publication date.
"""
import json
import hmac
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

from flask import Response, current_app, redirect, render_template, request

ORIGIN = "https://codejet.app"
VIDEO_ID = "38ccab99e8156adae4abcfbb1d36cc0f"
VIDEO_HOST = "https://customer-0k2chsytrbkmpgjr.cloudflarestream.com"
VIDEO_EMBED = f"{VIDEO_HOST}/{VIDEO_ID}/iframe"
VIDEO_THUMBNAIL = f"{VIDEO_HOST}/{VIDEO_ID}/thumbnails/thumbnail.jpg?time=20s&height=600"
SOCIAL_IMAGE = ORIGIN + "/static/images/campaign/codejet-retail-analytics.png"
CONTENT_PATHS = ("/retail-analytics-software", "/retail-reporting-automation", "/retail-data-questions")
TRACKED_PAGES = ("/", "/demo", *CONTENT_PATHS)
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
CONTENT_FILE = Path(__file__).resolve().parent / "growth" / "content" / "pages.json"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
VIDEO_NS = "http://www.google.com/schemas/sitemap-video/1.1"


def enabled(value):
    return value is True or str(value).strip().lower() in {"1", "true", "yes"}


def load_pages():
    document = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    pages = {"/" + page["slug"]: page for page in document["pages"]}
    if set(pages) != set(CONTENT_PATHS):
        raise ValueError("Search content routes do not match the public route allowlist")
    return pages


PAGES = load_pages()


def indexable():
    if not enabled(current_app.config.get("CJ_SEO_INDEXABLE", True)):
        return False
    public_hosts = {"codejet.app", "www.codejet.app"}
    host = request.host.split(":", 1)[0].lower()
    if host in public_hosts:
        return True
    # Front Door uses the Render hostname for its origin Host header. Only use
    # its original public host for SEO when the configured Front Door ID matches.
    # This selects indexing metadata, NOT authentication or authorization.
    expected = str(current_app.config.get("CJ_SEO_FRONTDOOR_ID", "") or
                   current_app.config.get("CJ_ANALYTICS_FRONTDOOR_ID", "")).lower()
    received = request.headers.get("X-Azure-FDID", "").lower()
    original_host = request.headers.get("X-Forwarded-Host", "").lower()
    return (host == "stellar-v2.onrender.com" and bool(expected) and
            hmac.compare_digest(received.encode(), expected.encode()) and original_host in public_hosts)


def campaign_url(path):
    """Carry only short UTM values through public links, never arbitrary URLs."""
    parts = urlsplit(path)
    if parts.scheme or parts.netloc or parts.path not in TRACKED_PAGES or parts.query:
        raise ValueError("Campaign links must use an approved local page")
    values = {}
    for key in UTM_KEYS:
        value = re.sub(r"[\x00-\x1f\x7f]", "", request.args.get(key, "")).strip()[:100]
        if value:
            values[key] = value
    return urlunsplit(("", "", parts.path, urlencode(values), parts.fragment))


def configured_thumbnail():
    value = str(current_app.config.get("CJ_VIDEO_THUMBNAIL_URL", "")).strip()
    if len(value) > 2048 or re.search(r"[\x00-\x1f\x7f]", value):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.fragment:
        return None
    return value


def video_object():
    """Emit schema only with explicitly enabled, valid, original video metadata."""
    config = current_app.config
    if not enabled(config.get("CJ_VIDEO_SCHEMA_ENABLED", False)):
        return None
    raw_date = str(config.get("CJ_VIDEO_UPLOAD_DATE", "")).strip()
    thumbnail = configured_thumbnail()
    try:
        uploaded = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    if uploaded.tzinfo is None or uploaded > datetime.now(timezone.utc):
        return None
    if not thumbnail:
        return None
    video = {
        "@type": "VideoObject", "@id": ORIGIN + "/demo#video",
        "name": "CodeJet retail intelligence demo",
        "description": "See CodeJet's approach to answering retail business questions using existing reports, queries, and business definitions.",
        "thumbnailUrl": [thumbnail], "uploadDate": uploaded.isoformat(), "embedUrl": VIDEO_EMBED,
        "publisher": {"@id": ORIGIN + "/#organization"}, "isPartOf": {"@id": ORIGIN + "/demo#webpage"},
    }
    duration = str(config.get("CJ_VIDEO_DURATION", "")).strip()
    if (re.fullmatch(r"PT(?=\d)(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?", duration) and
            any(float(value) > 0 for value in re.findall(r"\d+(?:\.\d+)?", duration))):
        video["duration"] = duration
    return video


def public_context(path):
    if path == "/":
        title = "CodeJet | Retail Analytics Software & Retail Intelligence"
        description = "Turn your existing retail reports and business definitions into answers to sales, margin, and inventory questions. Watch the CodeJet demo."
        name = "CodeJet retail intelligence platform"
    elif path == "/demo":
        title = "Retail Intelligence Software Demo | CodeJet"
        description = "Watch the CodeJet retail intelligence demo. See an approach to asking business questions using existing reports, queries, and definitions."
        name = "CodeJet retail intelligence demo"
    else:
        page = PAGES[path]
        title, description, name = page["title"], page["description"], page["h1"]
    canonical = ORIGIN + path
    thumbnail = configured_thumbnail() or VIDEO_THUMBNAIL
    organization = {
        "@type": "Organization", "@id": ORIGIN + "/#organization", "name": "CodeJet",
        "legalName": "CodeJET LLC", "url": ORIGIN + "/",
        "logo": ORIGIN + "/static/images/CodeJet_Retail_Intelligence_Platform_RedHeader.png",
        "email": "sales@codejet.app", "telephone": "+1-336-302-7925",
        "description": "A retail intelligence platform built around existing reports, queries, and business definitions.",
    }
    website = {"@type": "WebSite", "@id": ORIGIN + "/#website", "url": ORIGIN + "/",
               "name": "CodeJet", "publisher": {"@id": organization["@id"]}}
    webpage = {
        "@type": "WebPage", "@id": canonical + "#webpage", "url": canonical, "name": name,
        "description": description, "inLanguage": "en-US", "isPartOf": {"@id": website["@id"]},
        "publisher": {"@id": organization["@id"]},
    }
    graph = [organization, website, webpage]
    if path != "/":
        breadcrumb = {
            "@type": "BreadcrumbList", "@id": canonical + "#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "CodeJet", "item": ORIGIN + "/"},
                {"@type": "ListItem", "position": 2, "name": name, "item": canonical},
            ],
        }
        webpage["breadcrumb"] = {"@id": breadcrumb["@id"]}
        graph.append(breadcrumb)
    video = video_object() if path == "/demo" else None
    if video:
        webpage["mainEntity"] = {"@id": video["@id"]}
        graph.append(video)
    verification = str(current_app.config.get("CJ_GOOGLE_SITE_VERIFICATION", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,256}", verification):
        verification = ""
    return {
        "seo": {
            "title": title, "description": description, "canonical": canonical,
            "image": thumbnail if path == "/demo" else SOCIAL_IMAGE,
            "image_alt": "CodeJet retail intelligence demo" if path == "/demo" else "CodeJet retail analytics software",
            "indexable": indexable(), "structured_data": {"@context": "https://schema.org", "@graph": graph},
            "verification": verification,
        },
        "page_path": path, "video_embed": VIDEO_EMBED, "video_thumbnail": thumbnail, "video_id": VIDEO_ID,
    }


def _sitemap():
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("video", VIDEO_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for path in TRACKED_PAGES:
        node = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = ORIGIN + path
        video = video_object() if path == "/demo" else None
        if video:
            entry = ET.SubElement(node, f"{{{VIDEO_NS}}}video")
            for key, value in (("thumbnail_loc", video["thumbnailUrl"][0]), ("title", video["name"]),
                               ("description", video["description"]), ("player_loc", video["embedUrl"]),
                               ("publication_date", video["uploadDate"])):
                ET.SubElement(entry, f"{{{VIDEO_NS}}}{key}").text = value
    return Response(ET.tostring(root, encoding="utf-8", xml_declaration=True), mimetype="application/xml")


def init_seo(app):
    defaults = {
        "CJ_SEO_INDEXABLE": "1", "CJ_SEO_FRONTDOOR_ID": "", "CJ_GOOGLE_SITE_VERIFICATION": "", "CJ_VIDEO_SCHEMA_ENABLED": "0",
        "CJ_VIDEO_UPLOAD_DATE": "", "CJ_VIDEO_THUMBNAIL_URL": VIDEO_THUMBNAIL, "CJ_VIDEO_DURATION": "",
    }
    for key, value in defaults.items():
        app.config.setdefault(key, os.getenv(key, value))
    app.jinja_env.globals["campaign_url"] = campaign_url

    def search_page():
        return render_template("search/page.html", page=PAGES[request.path], **public_context(request.path))

    def canonical_trailing_slash():
        return redirect(campaign_url(request.path.rstrip("/")), code=308)

    for path in CONTENT_PATHS:
        endpoint = path[1:].replace("-", "_")
        app.add_url_rule(path, endpoint, search_page, methods=["GET"])
        app.add_url_rule(path + "/", endpoint + "_slash", canonical_trailing_slash, methods=["GET"])

    @app.get("/robots.txt")
    def robots():
        if not indexable():
            body = "User-agent: *\nDisallow: /\n"
        else:
            # Training and public-search discovery are separate permissions.
            body = ("User-agent: *\nDisallow: /_cj/\nDisallow: /ai\n"
                    "Disallow: /elements\nDisallow: /send_email\nDisallow: /health\nAllow: /\n\n"
                    "User-agent: GPTBot\nDisallow: /\n\n" f"Sitemap: {ORIGIN}/sitemap.xml\n")
        return Response(body, mimetype="text/plain")

    app.add_url_rule("/sitemap.xml", "sitemap", _sitemap, methods=["GET"])

    @app.after_request
    def search_headers(response):
        if request.path in TRACKED_PAGES and any(key in request.args for key in UTM_KEYS):
            # Personalized UTM links must never be served from a shared HTML cache.
            response.headers["Cache-Control"] = "private, no-store"
        if (not indexable() or response.status_code >= 400 or request.path in
                {"/elements", "/health", "/send_email"}):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response
