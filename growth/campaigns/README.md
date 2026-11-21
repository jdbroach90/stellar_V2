# CodeJet paid discovery campaign

These assets connect retail software searches and relevant ChatGPT conversations to the CodeJet product page and its ungated video. Everything is prepared locally and paused. No campaign has been created in an ad account, and no spending is scheduled.

## Start with one test

The proposed first test is **Google Search, $400 total over 21 days**, starting with the six Exact keywords in **01 Retail Analytics Software**. The other two ad groups and all Phrase keywords are reserves. A narrow first test makes it easier to see whether the category, message and video fit together before expanding the audience.

The optional ChatGPT test is **$350 total over 14 days**. A later increase toward $500 is a separate decision. Run it after the Google test has established that the destination and playback tracking work. These are proposed risk budgets, not cost forecasts or commitments.

| Asset | Use |
| --- | --- |
| `campaigns.json` | Authoritative copy, keywords, exclusions, settings and UTM conventions |
| `build_campaign_assets.py` | Rebuild and validate the files without accessing any account |
| `ad_copy_review.md` | Read every ad and its character count before import |
| `google/ad_groups.csv` | Three paused Google ad groups |
| `google/responsive_search_ads.csv` | Three paused responsive search ads, one per theme |
| `google/keywords.csv` | 28 paused rows: 14 terms supplied in Exact and Phrase |
| `google/negative_keywords.csv` | 21 focused exclusions repeated across the three groups, 63 rows |
| `google/settings.json` | Manual setup reference; deliberately not a budget import |
| `google/README.md` | Correct Editor import context and launch settings |
| `chatgpt/setup_reference.csv` | Six paste-ready ads; **not a native ChatGPT import file** |
| `chatgpt/context_hints.json` | Three intent groups with six context hints each |
| `chatgpt/settings.json` | Optional Clicks campaign and campaign-total budget proposal |
| `chatgpt/README.md` | Guided setup and transfer into the actual account template |
| `KEYWORD_STRATEGY.md` | Buying intent, exclusions and expansion decisions |
| `SOURCES.md` | Official documentation and dated implementation decisions |
| `validation_report.json` | Local checks and the account/production checks still outstanding |

## Where the clicks go

Every paid ad lands on:

`https://codejet.app/retail-analytics-software`

The primary action on that page leads to `/demo`, with campaign tags preserved. This gives a visitor enough context to recognize a retail analytics product and choose the video without submitting a form.

All destination links include:

| Parameter | Value |
| --- | --- |
| `utm_source` | `google` or `chatgpt` |
| `utm_medium` | `cpc` |
| `utm_campaign` | `codejet_retail_analytics` |
| `utm_content` | Stable ad ID, such as `retail_analytics_demo_v1` |

The ad group and variant are recoverable from the content ID. Keyword and search-query detail belongs in the Google Ads search terms report; the package does not invent that detail in a static `utm_term`.

## Rebuild or check

Open **PowerShell** in the repository folder. Use the `PS ...>` prompt, not Python's `>>>` prompt.

```powershell
py -3 .\growth\campaigns\build_campaign_assets.py --check
```

After editing `campaigns.json`, regenerate the derived files:

```powershell
py -3 .\growth\campaigns\build_campaign_assets.py
```

On macOS or Linux, use `python3 growth/campaigns/build_campaign_assets.py --check` from the repository root. There are no third-party package requirements.

The validator checks copy lengths, unique IDs, positive/negative keyword conflicts, status values, destinations, UTM values, CSV parsing and stale generated files. It deliberately does not claim that an account accepted an import or that an unpublished URL is reachable. Running the builder cannot launch or alter a campaign.

## Before choosing to spend

1. Publish the product page and confirm that its main action opens the real video on desktop and mobile. Check that campaign tags survive the transition.
2. Open the tagged link from `ad_copy_review.md` directly, play the video and confirm that the first-party analytics records the expected page, source and playback. Exclude that deliberate test from performance reviews.
3. For Google, obtain current United States keyword forecasts in your account and choose an affordable maximum CPC bid limit. This package contains no search-volume, auction-price or lead-volume estimates.
4. For ChatGPT, confirm that the public square image URL returns an actual PNG and that the current account template and paused/draft controls match the documented workflow.
5. Confirm the total budget, dates, country and selected initial ad group in the account. Only the reviewed subset should be enabled.

## Decide from engagement

Keep separate counts for platform-reported paid clicks, site browser sessions, demo opens, video starts, extensive playback and actual retail inquiries. A raw request or unique IP is not a buyer count. Google filters detected invalid traffic for billing, but that does not prevent every automated visit from appearing on the website. [Sources G11 and O6](SOURCES.md)

Use the proposed $50 spend point for a manual search-term and playback review. If spend reaches $100 without a video start, pause and investigate the query mix, landing page and player before spending the remainder. These are operating guardrails for this pilot, not statistically established success thresholds. When video starts occur but inquiries do not, inspect the message and next step before buying more visits.

This package uses existing first-party measurements. It does not install an advertising pixel, configure an ad-account conversion action or automatically upload conversions. Do not select conversion bidding on the assumption that those integrations exist.
