"""Public discovery, attribution, and proxy regression checks. No external I/O."""
from html.parser import HTMLParser
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import server
from codejet_seo import CONTENT_PATHS, ORIGIN, TRACKED_PAGES, VIDEO_THUMBNAIL


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.ld = []
        self.in_ld = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_ld = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_ld = False

    def handle_data(self, data):
        if self.in_ld:
            self.ld.append(json.loads(data))

    def matching(self, tag, **attrs):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in attrs.items())]


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.config = patch.dict(server.app.config, TESTING=True, CJ_SEO_INDEXABLE="1",
                                 CJ_ANALYTICS_ENABLED=False, CJ_VIDEO_SCHEMA_ENABLED="0",
                                 CJ_GOOGLE_SITE_VERIFICATION="", CJ_VIDEO_UPLOAD_DATE="",
                                 CJ_VIDEO_THUMBNAIL_URL=VIDEO_THUMBNAIL,
                                 CJ_SEO_FRONTDOOR_ID="", CJ_ANALYTICS_FRONTDOOR_ID="")
        self.config.start()
        self.addCleanup(self.config.stop)
        self.client = server.app.test_client()

    def get(self, path, **kwargs):
        return self.client.get(path, base_url=ORIGIN, **kwargs)

    def test_public_pages_have_one_h1_unique_canonical_and_parseable_schema(self):
        descriptions = set()
        for path in TRACKED_PAGES:
            with self.subTest(path=path):
                response = self.get(path)
                self.assertEqual(response.status_code, 200)
                doc = Document(response.get_data(as_text=True))
                self.assertEqual(len(doc.matching("h1")), 1)
                self.assertEqual(doc.matching("link", rel="canonical"), [{"rel": "canonical", "href": ORIGIN + path}])
                self.assertIn("index, follow", doc.matching("meta", name="robots")[0]["content"])
                descriptions.add(doc.matching("meta", name="description")[0]["content"])
                self.assertEqual(doc.ld[0]["@context"], "https://schema.org")
                self.assertNotIn("noindex", response.headers.get("X-Robots-Tag", ""))
        self.assertEqual(len(descriptions), len(TRACKED_PAGES))

    def test_campaign_links_preserve_only_approved_parameters_without_changing_canonical(self):
        response = self.get("/retail-analytics-software?utm_source=google&utm_campaign=codejet_retail_analytics&utm_content=a%26b&email=private%40example.com&next=https://bad.example")
        doc = Document(response.get_data(as_text=True))
        demo_links = [a["href"] for a in doc.matching("a") if a.get("href", "").startswith("/demo")]
        self.assertGreater(len(demo_links), 2)
        for link in demo_links:
            self.assertEqual(parse_qs(urlsplit(link).query), {
                "utm_source": ["google"], "utm_campaign": ["codejet_retail_analytics"], "utm_content": ["a&b"]})
        self.assertNotIn("private@example", response.get_data(as_text=True))
        self.assertEqual(doc.matching("link", rel="canonical")[0]["href"], ORIGIN + "/retail-analytics-software")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_demo_requires_click_to_play_with_sound_and_contact_form_is_on_the_page(self):
        response = self.get('/demo?utm_source=google&utm_medium=cpc&utm_campaign=retail_analytics')
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        doc = Document(body)
        players = doc.matching('iframe', id='stream-player')
        self.assertEqual(len(players), 1)
        options = parse_qs(urlsplit(players[0]['src']).query)
        self.assertEqual(options['autoplay'], ['false'])
        self.assertEqual(options['muted'], ['false'])
        self.assertEqual(options['startTime'], ['0'])
        self.assertEqual(options.get('loop'), None)
        self.assertEqual(len(doc.matching('button', id='demo-play')), 1)
        self.assertIn('Play the 80-second demo with sound', body)
        self.assertIn('mailto:sales@codejet.app', body)
        self.assertNotIn('jbroach@codejet.app', body)
        self.assertEqual(len(doc.matching('div', id='demo-video-ended')), 1)
        self.assertEqual(len(doc.matching('aside', id='demo-contact')), 1)
        forms = doc.matching('form', id='codejet-demo-form')
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]['action'], '/send_email')
        self.assertEqual(forms[0]['method'], 'post')
        self.assertIn('grecaptcha', body)
        self.assertNotIn('href="/#contact"', body)
        self.assertIn('name="utm_source" value="google"', body)
        self.assertIn('name="utm_campaign" value="retail_analytics"', body)

    def test_host_header_cannot_change_canonical_or_index_a_preview(self):
        response = self.client.get("/demo", base_url="https://preview.invalid")
        doc = Document(response.get_data(as_text=True))
        self.assertEqual(doc.matching("link", rel="canonical")[0]["href"], ORIGIN + "/demo")
        self.assertIn("noindex", response.headers["X-Robots-Tag"])
        self.assertEqual(self.client.get("/robots.txt", base_url="https://stellar-v2.onrender.com").data,
                         b"User-agent: *\nDisallow: /\n")

    def test_frontdoor_origin_host_preserves_public_indexing_only_for_expected_proxy(self):
        server.app.config["CJ_ANALYTICS_FRONTDOOR_ID"] = "ef992e31-a324-4134-8c86-a607f2159845"
        headers = {"X-Azure-FDID": server.app.config["CJ_ANALYTICS_FRONTDOOR_ID"], "X-Forwarded-Host": "codejet.app"}
        response = self.client.get("/retail-analytics-software", base_url="https://stellar-v2.onrender.com", headers=headers)
        self.assertNotIn("noindex", response.headers.get("X-Robots-Tag", ""))
        for bad in ({**headers, "X-Azure-FDID": "wrong"}, {"X-Forwarded-Host": "codejet.app"},
                    {**headers, "X-Forwarded-Host": "codejet.app,evil.example"}):
            response = self.client.get("/robots.txt", base_url="https://stellar-v2.onrender.com", headers=bad)
            self.assertEqual(response.data, b"User-agent: *\nDisallow: /\n")

    def test_robots_keeps_search_and_ads_public_and_training_private(self):
        parser = RobotFileParser()
        parser.parse(self.get("/robots.txt").get_data(as_text=True).splitlines())
        for crawler in ("Googlebot", "OAI-SearchBot", "OAI-AdsBot"):
            self.assertTrue(parser.can_fetch(crawler, ORIGIN + "/demo"))
            self.assertTrue(parser.can_fetch(crawler, ORIGIN + CONTENT_PATHS[0]))
            self.assertFalse(parser.can_fetch(crawler, ORIGIN + "/ai"))
            self.assertFalse(parser.can_fetch(crawler, ORIGIN + "/_cj/analytics"))
        self.assertFalse(parser.can_fetch("GPTBot", ORIGIN + "/demo"))

    def test_sitemap_lists_only_public_canonical_pages(self):
        root = ET.fromstring(self.get("/sitemap.xml").data)
        self.assertEqual({node.text for node in root.findall("{*}url/{*}loc")}, {ORIGIN + p for p in TRACKED_PAGES})
        self.assertEqual(root.findall(".//{http://www.google.com/schemas/sitemap-video/1.1}video"), [])

    def test_video_metadata_is_absent_without_real_required_values(self):
        server.app.config["CJ_VIDEO_SCHEMA_ENABLED"] = "1"
        for date, thumbnail in (("", VIDEO_THUMBNAIL), ("2026-11-20", VIDEO_THUMBNAIL),
                                ("2999-01-01T00:00:00Z", VIDEO_THUMBNAIL),
                                ("2026-01-01T00:00:00Z", "https://[broken")):
            server.app.config.update(CJ_VIDEO_UPLOAD_DATE=date, CJ_VIDEO_THUMBNAIL_URL=thumbnail)
            response = self.get("/demo")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("VideoObject", [v["@type"] for v in Document(response.get_data(as_text=True)).ld[0]["@graph"]])
            self.assertEqual(self.get("/sitemap.xml").status_code, 200)

    def test_verified_video_config_drives_schema_sitemap_and_visible_thumbnail(self):
        # Synthetic configuration, not an assertion of the real recording's date.
        server.app.config.update(CJ_VIDEO_SCHEMA_ENABLED="1", CJ_VIDEO_UPLOAD_DATE="2020-01-01T12:00:00Z",
                                 CJ_VIDEO_THUMBNAIL_URL="https://codejet.app/verified-thumbnail.jpg", CJ_VIDEO_DURATION="PT2M")
        doc = Document(self.get("/demo").get_data(as_text=True))
        video = next(v for v in doc.ld[0]["@graph"] if v["@type"] == "VideoObject")
        self.assertEqual(video["duration"], "PT2M")
        self.assertNotIn("contentUrl", video)
        self.assertEqual(doc.matching("meta", property="og:image")[0]["content"], video["thumbnailUrl"][0])
        iframe = doc.matching("iframe")[0]
        self.assertEqual(parse_qs(urlsplit(iframe["src"]).query)["poster"], video["thumbnailUrl"])
        root = ET.fromstring(self.get("/sitemap.xml").data)
        self.assertEqual(len(root.findall(".//{http://www.google.com/schemas/sitemap-video/1.1}video")), 1)

    def test_unknown_and_nonsearch_pages_stay_noindex(self):
        for path in ("/not-a-real-page", "/elements", "/health", "/_cj/analytics", "/demo-privacy"):
            response = self.get(path)
            self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""))

    def test_tracking_is_optional_and_uses_each_public_page_path(self):
        for path in CONTENT_PATHS:
            self.assertNotIn(b"data-cj-analytics", self.get(path).data)
        server.app.config["CJ_ANALYTICS_ENABLED"] = True
        for path in CONTENT_PATHS:
            self.assertIn(('data-cj-page="' + path + '"').encode(), self.get(path).data)

    def test_slash_redirect_preserves_campaign_and_cannot_redirect_offsite(self):
        response = self.get(CONTENT_PATHS[0] + "/?utm_source=chatgpt&next=https://bad.example")
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.location, CONTENT_PATHS[0] + "?utm_source=chatgpt")

    def test_verification_token_is_optional_and_rejects_markup(self):
        server.app.config["CJ_GOOGLE_SITE_VERIFICATION"] = '"><script>alert(1)</script>'
        self.assertNotIn(b'google-site-verification', self.get("/").data)
        server.app.config["CJ_GOOGLE_SITE_VERIFICATION"] = "valid_test_token-123"
        self.assertIn(b'content="valid_test_token-123"', self.get("/").data)


if __name__ == "__main__":
    unittest.main()
