#!/usr/bin/env python3
"""Build paused CodeJet campaign files. No network, account access or spending.

Run from any directory:
    python growth/campaigns/build_campaign_assets.py
    python growth/campaigns/build_campaign_assets.py --check

The Google files use documented Ads Editor column names. Import responsive
search ads in the Responsive search ads context. ChatGPT exports are reference
files, not a claimed native import template.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "campaigns.json"
SLUG = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def clean_text(value: str, label: str, limit: int | None = None) -> None:
    require(isinstance(value, str) and bool(value.strip()), f"{label}: text is empty")
    require(value == value.strip(), f"{label}: surrounding whitespace")
    require(not any(ord(c) < 32 for c in value), f"{label}: control character")
    require(not value.startswith(("=", "+", "@", "\t", "\r")), f"{label}: unsafe CSV prefix")
    if limit is not None:
        require(len(value) <= limit, f"{label}: {len(value)} characters exceeds {limit}")


def tagged_url(config: dict, source: str, content: str) -> str:
    return config["site_origin"] + config["landing_path"] + "?" + urlencode({
        "utm_source": source,
        "utm_medium": config["utm_medium"],
        "utm_campaign": config["utm_campaign"],
        "utm_content": content,
    })


def validate_url(config: dict, source: str, content: str) -> None:
    url = tagged_url(config, source, content)
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.netloc == "codejet.app", "Unexpected destination domain")
    require(parsed.path == "/retail-analytics-software", "Unexpected paid landing path")
    require(parse_qs(parsed.query) == {
        "utm_source": [source],
        "utm_medium": ["cpc"],
        "utm_campaign": ["codejet_retail_analytics"],
        "utm_content": [content],
    }, f"Inconsistent UTMs: {url}")


def negative_conflicts(term: str, negative: dict) -> bool:
    text = term.casefold().split()
    bad = negative["term"].casefold().split()
    if negative["match_type"] == "Negative exact":
        return text == bad
    return any(text[i:i + len(bad)] == bad for i in range(len(text) - len(bad) + 1))


def validate(config: dict) -> dict:
    require(config["schema_version"] == 1, "Unsupported source schema")
    require(config["site_origin"] == "https://codejet.app", "Unexpected site origin")
    require(config["utm_medium"] == "cpc", "Paid medium must be cpc")
    require(config["utm_campaign"] == "codejet_retail_analytics", "Unexpected campaign UTM")
    require(config["measurement"]["ad_platform_conversion_integration"] is False,
            "This package does not install ad-platform conversion tracking")
    require(config["state"] == "prepared_locally_not_created_in_ad_accounts",
            "Source must accurately describe its local preparation state")
    for path_name in ("landing_path", "demo_path", "image_path"):
        path = config[path_name]
        require(path.startswith("/") and "?" not in path and "#" not in path and ".." not in path,
                f"Invalid {path_name}")

    counts = {"google_ad_groups": 0, "google_rsa_ads": 0, "google_keyword_rows": 0,
              "google_unique_keyword_terms": 0, "google_unique_negative_terms": 0,
              "google_negative_rows": 0, "chatgpt_ad_groups": 0, "chatgpt_ads": 0,
              "chatgpt_context_hints": 0}
    for platform in ("google", "chatgpt"):
        campaign = config[platform]
        require(campaign["status"] == "Paused", f"{platform}: campaign must remain Paused")
        budget = campaign["budget"]
        require(budget["type"] == "campaign_total", f"{platform}: only campaign-total planning is allowed")
        require(budget["currency"] == "USD", f"{platform}: expected USD")
        require(budget["recurring"] is False and budget["automatic_budget_increase"] is False,
                f"{platform}: no recurring spending or automatic increases")
        require(budget["start_date"] is None and budget["end_date"] is None,
                f"{platform}: account launch dates must be selected during launch review")
        require(budget["proposed_total"] > 0, f"{platform}: invalid proposed budget")
        require(len({g["id"] for g in campaign["ad_groups"]}) == len(campaign["ad_groups"]),
                f"{platform}: duplicate ad group id")
        require(len({g["name"] for g in campaign["ad_groups"]}) == len(campaign["ad_groups"]),
                f"{platform}: duplicate ad group name")
        ad_ids = set()
        for group in campaign["ad_groups"]:
            require(group["status"] == "Paused", f"{platform}/{group['id']}: group must remain Paused")
            require(SLUG.fullmatch(group["id"]) is not None, "Invalid group id")
            clean_text(group["name"], "Ad group name")
            ads = [group["ad"]] if platform == "google" else group["ads"]
            for ad in ads:
                require(ad["status"] == "Paused", f"{ad['id']}: ad must remain Paused")
                require(SLUG.fullmatch(ad["id"]) is not None, "Invalid ad id")
                require(ad["id"] not in ad_ids, f"{platform}: duplicate ad id")
                ad_ids.add(ad["id"])
                validate_url(config, platform, ad["id"])
                if platform == "google":
                    require(3 <= len(ad["headlines"]) <= 15, f"{ad['id']}: need 3–15 headlines")
                    require(2 <= len(ad["descriptions"]) <= 4, f"{ad['id']}: need 2–4 descriptions")
                    require(len({h.casefold() for h in ad["headlines"]}) == len(ad["headlines"]),
                            f"{ad['id']}: duplicate headline")
                    for i, headline in enumerate(ad["headlines"], 1):
                        clean_text(headline, f"{ad['id']} headline {i}", 30)
                    for i, description in enumerate(ad["descriptions"], 1):
                        clean_text(description, f"{ad['id']} description {i}", 90)
                    clean_text(ad["path_1"], f"{ad['id']} path 1", 15)
                    clean_text(ad["path_2"], f"{ad['id']} path 2", 15)
                    counts["google_rsa_ads"] += 1
                else:
                    clean_text(ad["title"], f"{ad['id']} title", 50)
                    clean_text(ad["copy"], f"{ad['id']} copy", 100)
                    counts["chatgpt_ads"] += 1
            if platform == "google":
                counts["google_ad_groups"] += 1
                counts["google_unique_keyword_terms"] += len(group["keywords"])
                counts["google_keyword_rows"] += len(group["keywords"]) * len(campaign["keyword_match_types"])
                require(len(set(group["keywords"])) == len(group["keywords"]), "Duplicate keyword")
                for keyword in group["keywords"]:
                    clean_text(keyword, "Keyword")
                    require(not any(negative_conflicts(keyword, n) for n in campaign["negative_keywords"]),
                            f"Negative blocks positive keyword: {keyword}")
            else:
                counts["chatgpt_ad_groups"] += 1
                require(group["context_hints"], f"{group['id']}: missing context hints")
                require(len(set(group["context_hints"])) == len(group["context_hints"]), "Duplicate hint")
                for hint in group["context_hints"]:
                    clean_text(hint, "Context hint")
                counts["chatgpt_context_hints"] += len(group["context_hints"])
        initial = campaign["recommended_first_activation"]
        groups_by_id = {g["id"]: g for g in campaign["ad_groups"]}
        require(initial["ad_group_id"] in groups_by_id, "Initial group does not exist")
        initial_group = groups_by_id[initial["ad_group_id"]]
        initial_ads = [initial_group["ad"]] if platform == "google" else initial_group["ads"]
        require(initial["ad_id"] in {ad["id"] for ad in initial_ads}, "Initial ad is in the wrong group")

    google = config["google"]
    require(google["keyword_match_types"] == ["Exact", "Phrase"], "No broad-match default")
    require(google["budget"]["proposed_total"] == 400, "Google total must remain the proposed $400")
    require(3 <= google["budget"]["proposed_duration_days"] <= 90,
            "Google campaign-total planning requires a 3–90 day flight")
    require(google["bidding"]["maximum_cpc_bid_limit"] is None, "Do not invent a numeric market CPC")
    require(not google["search_partners"] and not google["display_expansion"], "Search-only test required")
    negatives = google["negative_keywords"]
    require(len({(n['term'], n['match_type']) for n in negatives}) == len(negatives), "Duplicate negative")
    for negative in negatives:
        clean_text(negative["term"], "Negative keyword")
        require(negative["match_type"] in {"Negative phrase", "Negative exact"}, "Unreviewed negative type")
        require(negative["term"].casefold() not in {x.casefold() for x in google["terms_not_blanket_excluded"]},
                "A blanket negative contradicts the stated exclusions policy")
    counts["google_unique_negative_terms"] = len(negatives)
    counts["google_negative_rows"] = len(negatives) * len(google["ad_groups"])
    chatgpt = config["chatgpt"]
    require(chatgpt["format"] == "setup_reference_not_native_import_schema", "Do not claim an unverified import schema")
    require(chatgpt["budget"]["proposed_total"] == 350, "ChatGPT proposed test total must remain $350")
    require(chatgpt["bidding"]["proposed_strategy"] == "Intelligent bidding", "Unreviewed ChatGPT bidding strategy")
    require(chatgpt["bidding"]["target_cpc"] is None, "No measured ChatGPT CPC is available")
    return counts


def csv_bytes(columns: list[str], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\r\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    text = stream.getvalue()
    # UTF-8 BOM makes the text safe to open in Windows Excel before Editor paste.
    encoded = text.encode("utf-8-sig")
    require(len(list(csv.DictReader(io.StringIO(encoded.decode("utf-8-sig"))))) == len(rows),
            "CSV round trip lost rows")
    forbidden = {"Budget", "Daily budget", "Campaign budget", "Campaign daily budget", "Max CPC"}
    require(not forbidden.intersection(columns), "Native CSV must never set budget or CPC fields")
    return encoded


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_review(config: dict) -> bytes:
    lines = [
        "# CodeJet ad copy review", "",
        "Generated from `campaigns.json`. All campaigns, ad groups and ads are prepared as paused.",
        "No ad account has been changed. Keywords and bids are buying hypotheses, not forecasts.", "",
        "## Google Search", "",
        "One responsive search ad per theme keeps this first test small. Google can assemble headlines",
        "and descriptions in different combinations. The first recommended activation is the exact-match",
        "keywords and ad in **01 Retail Analytics Software**. Other themes remain reserve.", "",
    ]
    for group in config["google"]["ad_groups"]:
        ad = group["ad"]
        lines.extend([f"### {group['name']}", "", f"Phase: **{group['phase']}**. {group['intent']}", "",
                      f"Ad ID: `{ad['id']}`", "",
                      f"Landing URL: {tagged_url(config, 'google', ad['id'])}", "",
                      f"Display path: `{ad['path_1']}/{ad['path_2']}`", "",
                      "| Headline | Characters / 30 |", "| --- | ---: |"])
        lines.extend(f"| {s} | {len(s)} |" for s in ad["headlines"])
        lines.extend(["", "| Description | Characters / 90 |", "| --- | ---: |"])
        lines.extend(f"| {s} | {len(s)} |" for s in ad["descriptions"])
        lines.extend(["", "Keywords, each supplied as a separate Exact and Phrase row:", ""])
        lines.extend(f"- {s}" for s in group["keywords"])
        lines.append("")
    lines.extend(["## ChatGPT ads", "",
                  "Reference content for guided setup or transfer into the current account template.",
                  "The main brand image is shared. Each creative has its own stable UTM content value.", ""])
    for group in config["chatgpt"]["ad_groups"]:
        lines.extend([f"### {group['name']}", "", f"Phase: **{group['phase']}**.", ""])
        for ad in group["ads"]:
            lines.extend([f"#### {ad['id']}", "", f"**{ad['title']}**", "", ad["copy"], "",
                          f"Title: {len(ad['title'])}/50. Copy: {len(ad['copy'])}/100.", "",
                          f"Landing URL: {tagged_url(config, 'chatgpt', ad['id'])}", ""])
        lines.extend(["Context hints:", ""])
        lines.extend(f"- {s}" for s in group["context_hints"])
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def generate(config: dict, source_bytes: bytes) -> dict[str, bytes]:
    counts = validate(config)
    google = config["google"]
    campaign_name = google["campaign_name"]
    groups, ads, keywords, negatives = [], [], [], []
    max_headlines = max(len(g["ad"]["headlines"]) for g in google["ad_groups"])
    ad_columns = ["Campaign", "Campaign status", "Ad group", "Ad group status", "Status"]
    ad_columns += [f"Headline {i}" for i in range(1, max_headlines + 1)]
    ad_columns += [f"Description {i}" for i in range(1, 5)]
    ad_columns += ["Path 1", "Path 2", "Final URL"]
    for group in google["ad_groups"]:
        base = {"Campaign": campaign_name, "Campaign status": "Paused", "Ad group": group["name"],
                "Ad group status": "Paused"}
        groups.append(base.copy())
        ad = group["ad"]
        row = {**base, "Status": "Paused", "Path 1": ad["path_1"], "Path 2": ad["path_2"],
               "Final URL": tagged_url(config, "google", ad["id"])}
        row.update({f"Headline {i}": s for i, s in enumerate(ad["headlines"], 1)})
        row.update({f"Description {i}": s for i, s in enumerate(ad["descriptions"], 1)})
        ads.append(row)
        for keyword in group["keywords"]:
            for match_type in google["keyword_match_types"]:
                keywords.append({**base, "Keyword": keyword, "Criterion type": match_type, "Status": "Paused"})
        for negative in google["negative_keywords"]:
            # Negatives are exclusion rules, not paused traffic-producing entities.
            negatives.append({"Campaign": campaign_name, "Ad group": group["name"],
                              "Keyword": negative["term"], "Criterion type": negative["match_type"]})

    chatgpt = config["chatgpt"]
    chat_rows, hints = [], []
    for group in chatgpt["ad_groups"]:
        hints.append({"ad_group_name": group["name"], "context_hints": group["context_hints"]})
        for ad in group["ads"]:
            chat_rows.append({
                "reference_format": "NOT A NATIVE CHATGPT IMPORT FILE",
                "campaign_name": chatgpt["campaign_name"],
                "ad_group_name": group["name"], "phase": group["phase"],
                "ad_id": ad["id"], "status": "Paused", "title": ad["title"], "copy": ad["copy"],
                "landing_url": tagged_url(config, "chatgpt", ad["id"]),
                "image_url": config["site_origin"] + config["image_path"],
                "context_hints_json": json.dumps(group["context_hints"], ensure_ascii=False),
            })
    google_settings = {k: v for k, v in google.items() if k not in ("ad_groups", "negative_keywords")}
    google_settings.update({"format": "manual_setup_reference_not_import_schema", "account_created": False,
                            "base_landing_url": config["site_origin"] + config["landing_path"],
                            "base_demo_url": config["site_origin"] + config["demo_path"]})
    chat_settings = {k: v for k, v in chatgpt.items() if k != "ad_groups"}
    chat_settings.update({"account_created": False, "image_url": config["site_origin"] + config["image_path"],
                          "image_publication_status": config["image_publication_status"]})
    files = {
        "google/ad_groups.csv": csv_bytes(["Campaign", "Campaign status", "Ad group", "Ad group status"], groups),
        "google/responsive_search_ads.csv": csv_bytes(ad_columns, ads),
        "google/keywords.csv": csv_bytes(["Campaign", "Campaign status", "Ad group", "Ad group status",
                                           "Keyword", "Criterion type", "Status"], keywords),
        "google/negative_keywords.csv": csv_bytes(["Campaign", "Ad group", "Keyword", "Criterion type"], negatives),
        "google/settings.json": json_bytes(google_settings),
        "chatgpt/setup_reference.csv": csv_bytes(list(chat_rows[0]), chat_rows),
        "chatgpt/context_hints.json": json_bytes({"format": "reference_not_native_import", "ad_groups": hints}),
        "chatgpt/settings.json": json_bytes(chat_settings),
        "ad_copy_review.md": build_review(config),
        "validation_report.json": json_bytes({
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "reviewed_on": config["reviewed_on"],
            "counts": counts,
            "checks": ["character_limits", "paused_statuses", "no_budget_or_bid_fields_in_import_csv",
                       "consistent_destinations_and_utms", "unique_ids", "negative_positive_conflicts",
                       "no_blanket_free_or_existing_system_negatives", "csv_round_trip"],
            "native_google_import_executed": False,
            "native_chatgpt_schema_verified": False,
            "production_landing_and_image_reachability_verified": False,
            "note": "Local content validation only. Review actual imports and production URLs before activation."
        }),
    }
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="validate source and fail if generated files are missing or stale")
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="output root, default: this script's directory")
    args = parser.parse_args()
    try:
        source_bytes = SOURCE.read_bytes()
        config = json.loads(source_bytes)
        files = generate(config, source_bytes)
        output = args.output_dir.resolve()
        stale = []
        for relative, contents in files.items():
            target = output / relative
            if args.check:
                if not target.is_file() or target.read_bytes() != contents:
                    stale.append(relative)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(contents)
        if stale:
            print("Missing or stale generated files: " + ", ".join(stale), file=sys.stderr)
            print("Run the builder without --check, then review the generated diff.", file=sys.stderr)
            return 1
        report = json.loads(files["validation_report.json"])
        print(("Validated" if args.check else "Built") + f" {len(files)} files under {output}")
        print(json.dumps(report["counts"], sort_keys=True))
        print("No account was accessed, no campaign was launched, and no money was spent.")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Campaign build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
