# CodeJet: retail search to video

Prepared November 20, 2026. This package gives retail teams searching for analytics software a clear path to understand CodeJet, watch its demo, and discuss an AI partnership.

The website work belongs in the existing `jdbroach90/stellar_V2` repository and on **codejet.app**. Use the review branch `feature/retail-search-campaign-20261120`, based on production `master`. A separate domain or GitHub Pages copy would split the product story and attribution.

**Delivery status:** The GitHub connection could read the project but rejected remote branch creation with 403. The download includes the completed local branch as a Git bundle and the full source. Follow [Publish from Windows](docs/PUBLISH_TO_GITHUB.md) to publish the exact branch using your existing local Git authentication. No remote PR or production deployment is claimed.

## What is built

| Component | Delivered behavior |
| --- | --- |
| Product search page | `/retail-analytics-software`: category positioning, specific questions, implementation context, demo CTA, AI partnership CTA. |
| Reporting page | `/retail-reporting-automation`: practical guide to choosing, defining, and evaluating a repeated reporting workflow. |
| Retail questions guide | `/retail-data-questions`: specific questions about sales, gross profit, markdowns, and inventory, with necessary definitions. |
| Watch page | `/demo`: existing Cloudflare video, descriptive visible text, responsive player, ungated viewing, clear next step. Playback stays on the watch page when it ends. |
| Homepage update | Retail analytics positioning, shared search metadata, and links into the three public pages. |
| Search metadata | Unique titles/descriptions, fixed canonical URLs, social cards, Organization/WebSite/WebPage/Breadcrumb JSON-LD, robots and sitemap routes. |
| Video markup | Conditional VideoObject and video sitemap entry, enabled only after the original publication date and thumbnail are verified. |
| Attribution | The existing five UTM fields survive public-page navigation; the existing optional tracker now accepts the three new pages. |
| Google campaign | Three paused responsive search ads, 36 headline assets, 12 descriptions, 28 Exact/Phrase keyword rows, 63 negative-keyword rules, setup files and validator. |
| ChatGPT campaign | Six paused/setup ads, 18 context hints, setup reference CSV and account instructions. Organic crawler/discovery guidance is included separately. |
| Creative | A 1200×1200 PNG and editable SVG at `static/images/campaign/codejet-retail-analytics.*`. |
| Measurement | A local CSV tool that deduplicates exported sessions, separates bot-flagged/unflagged/unknown cohorts, and compares starts, coverage and optional costs. |
| Release tools | Read-only public-site checker, Python/JavaScript tests, GitHub checks, and Windows launch instructions. |

The supplied source content, ad assets and instructions are complete. Account-specific verification, publication, billing, budgets and activation are launch actions, not something the files perform automatically.

## The four channels have different jobs

| Channel | What the package supplies | Next action |
| --- | --- | --- |
| Google organic search | Search-focused HTML, internal links, metadata, sitemap and watch page. | Deploy, verify Search Console, submit sitemap, inspect pages, review real queries. |
| ChatGPT organic discovery | Crawlable factual content, clear company/domain identity, public access for OAI-SearchBot, repeatable prompt checks. | Deploy and verify public crawler access; observe actual citations and referrals. |
| Google paid Search | Keyword/ad/negative CSVs and conservative proposed settings. | Review forecasts and account configuration, import paused assets, choose a total budget, enable only the initial subset. |
| ChatGPT paid ads | Copy, image, intent context and setup reference. | Confirm account availability, use its current native template/UI, configure and review the optional test. |

Ordinary search access and useful content are the foundation for organic discovery. Paying for an ad does not buy an organic answer recommendation. Indexing, citations, viewing and inquiries depend on real demand, access and product fit; the files do not guarantee those outcomes. Official sources and specific platform behavior are documented in [the discovery guide](docs/GOOGLE_AND_CHATGPT_DISCOVERY.md) and [campaign sources](campaigns/SOURCES.md).

## Start here, in this order

1. **Review the pages and demo.** Use [the launch guide](docs/LAUNCH_GUIDE.md#2-preview-locally-on-windows) to preview from PowerShell. Product claims deliberately avoid unverified savings, testimonials, performance promises, and connector guarantees.
2. **Review the GitHub changes.** The PR targets `master`; merging can trigger the existing Render deployment. Check the changed files, tests and intended production branch first.
3. **Add real video metadata when available.** Find the original publication timestamp in the video owner's records. Set the `.env.example` fields in Render when verified. The ordinary pages and demo can launch without optional VideoObject markup.
4. **Verify the deployed site.** Run `python scripts/check_search.py --base-url https://codejet.app`, inspect the live video and check Front Door. The checker reports missing optional video markup as a warning; `--require-video-schema` makes it a release requirement when you are ready.
5. **Connect organic discovery.** Follow the Search Console/sitemap steps and public-crawler checks in the launch guide. Keep `/ai` and analytics protection in place.
6. **Run one small paid test if desired.** The proposed first test is Google Search, **$400 total over 21 days**. Start only the Retail Analytics Software group and its six Exact keywords. The optional ChatGPT proposal is **$350 total over 14 days** after the destination and measurement have been checked. These figures are proposals, not account commitments or price forecasts.
7. **Review video engagement and inquiries.** Download the real dashboard CSV into a private local folder, run the summary tool, and compare the campaign's source/content labels. Record actual retail inquiries separately.

## Files to use

- **Website content:** [content/pages.json](content/pages.json) and [content/CONTENT_NOTES.md](content/CONTENT_NOTES.md).
- **External distribution copy:** [content/DISTRIBUTION_PACK.md](content/DISTRIBUTION_PACK.md), with consistent descriptions, video listing copy and tagged links. No posting is automated.
- **Organic implementation:** [docs/GOOGLE_AND_CHATGPT_DISCOVERY.md](docs/GOOGLE_AND_CHATGPT_DISCOVERY.md).
- **Release/account steps:** [docs/LAUNCH_GUIDE.md](docs/LAUNCH_GUIDE.md).
- **Google/ChatGPT ads:** [campaigns/README.md](campaigns/README.md), [campaigns/ad_copy_review.md](campaigns/ad_copy_review.md), and the `google/` and `chatgpt/` folders.
- **Campaign review:** [docs/MEASUREMENT.md](docs/MEASUREMENT.md) and [tools/README.md](tools/README.md).

Google CSVs use the documented Editor contexts in their README. The ChatGPT CSV is explicitly a **reference**, not a fabricated native import template. Download the actual template from the account when using bulk upload.

## Windows commands you will use

From PowerShell in `C:\CodeJet\stellar_V2`:

```powershell
# Check that generated ad files still match their editable source.
py -3 growth\campaigns\build_campaign_assets.py --check

# Regenerate only after intentionally editing campaigns.json.
py -3 growth\campaigns\build_campaign_assets.py

# Check published public pages after deployment.
py -3 scripts\check_search.py --base-url https://codejet.app

# Summarize a private analytics export; this tool makes no network calls.
py -3 growth\tools\summarize_traffic.py "C:\CodeJet\private\codejet-demo-visits.csv" --output-dir "C:\CodeJet\private\weekly-report"
```

The paid-asset builder and traffic tool use Python's standard library. The website and `--local` release check use the repository's existing requirements. Run tests with the virtual environment Python shown in the launch guide.

## How to judge the first month

First verify that an appropriate query reaches the correct page, that the video starts, and that the tags appear in your own reporting. Then inspect whether relevant visitors watch a meaningful portion and contact you. A bot-unflagged start with at least 50% reported played coverage is a useful engagement proxy; it is not a verified human buyer.

The paid setup uses manual spend reviews at $50 and a pause-and-diagnose point at $100 with no video start. Those are operating choices for this test, not evidence that a product or market succeeds or fails at those amounts. Review the search terms that are actually available, the landing message and the video opening before broadening keywords or increasing budget.

Organic discovery should be evaluated through crawl/indexing status, relevant impressions, search queries, clicks, citations and referrals over time. The suggested first-month review cadence is in [MEASUREMENT.md](docs/MEASUREMENT.md). If a useful query emerges, deepen the relevant page with an accurate worked example or a verified product recording instead of publishing near-identical pages.

## Configuration and data boundaries

No customer/contact list, email-sending log, production credential, private analytics export or database belongs in this public repository. The release adds no ad conversion pixel and does not upload conversions. Existing first-party collection remains optional and honors its existing privacy signals.

The default robots policy permits public search/ad crawling and disallows GPTBot training. These are independent choices; the discovery guide explains them. Preview/Render hosts are noindex unless a recognized public host arrives through the configured Front Door route. The FDID host check selects SEO metadata only; it does not replace authentication.

Use the root `.env.example` as a list of names, retaining your existing production settings. `CJ_SEO_FRONTDOOR_ID` can remain empty when the existing `CJ_ANALYTICS_FRONTDOOR_ID` identifies the same route. The original publication date is intentionally blank. No verification code, original video date, traffic number or keyword forecast is invented.
