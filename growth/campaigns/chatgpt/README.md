# ChatGPT paid campaign setup

This is an optional campaign prepared for review. It has not been created in Ads Manager. The CSV is explicitly a **setup reference**, not an invented native upload template.

## Prepared settings

| Setting | Proposed choice |
| --- | --- |
| Campaign name | `CodeJet Retail Analytics ChatGPT Pilot` |
| Objective | Clicks |
| Country | United States |
| Budget mode | Campaign-total |
| Proposed total | $350 for a proposed 14-day test |
| Possible later total | Up to $500 only after a separate decision to increase it |
| Bidding | Intelligent bidding |
| Ad format | Single image |
| Initial ad group | `01 Retail Analytics Evaluation` |
| Initial ad | `retail_analytics_demo_v1` |
| Status | Keep draft/paused; no publication or spending performed |

Campaign-total budgeting is selected to control the complete test amount. The budget and dates must be verified in the actual account. The optional test does not need to run at the same time as Google. [Source O3](../SOURCES.md)

### First ad, ready to paste

**Title:** Retail data, answered

**Copy:** Ask sales and margin questions using existing reports. Watch the CodeJet demo.

**Destination:**

`https://codejet.app/retail-analytics-software?utm_source=chatgpt&utm_medium=cpc&utm_campaign=codejet_retail_analytics&utm_content=retail_analytics_demo_v1`

**Image:**

`https://codejet.app/static/images/campaign/codejet-retail-analytics.png`

The image URL is a deployment dependency. Confirm that it returns the public square PNG before uploading. The proposed creative is 1200 × 1200 pixels. Titles are validated to 50 characters and copy to 100; the supplied titles are concise. [Sources O2, O5](../SOURCES.md)

The other five ads and all context hints are in `setup_reference.csv`, `context_hints.json` and `../ad_copy_review.md`. Use the first variant initially; keep alternatives in reserve until there is useful traffic to review.

## Guided setup or native bulk transfer

For this small test, guided creation is the clearest path: enter the prepared campaign, ad group, context hints and creative. Preserve draft/paused state until the landing page and spend settings are reviewed. If first-campaign onboarding does not expose dates or a safe draft state, do not publish merely to reveal those settings; OpenAI's campaign guide warns that publication can allow delivery before scheduling is adjusted. [Sources O1, O3](../SOURCES.md)

For bulk setup, download the **current template from Create > Upload bulk in your own Ads Manager**. Transfer these reference values into that template, preserving its exact headers and required fields. The public docs describe the required structure but do not provide a verified native file schema for this account; this package therefore does not claim that its reference CSV can be uploaded. For later edits, start from an account export containing the correct IDs, rather than replaying creation rows. [Sources O1–O2](../SOURCES.md)

In the native bulk template, start and end dates are interpreted at 00:00 UTC, with an exclusive end date. For a 14-day test, the end date is 14 days after the start date, not the last day at midnight. Account settings and the final preview should be checked together. [Source O2](../SOURCES.md)

## Current bidding, reviewed November 20, 2026

Use **Intelligent bidding** for the initial Clicks test because no measured campaign CPC is available. A later Target CPC is an average-cost aim, not a ceiling on every click. Target CPC became available for new click campaigns on November 9. Since November 18, using legacy maximum-bid API fields to create campaigns or change bid types selects target bidding. Do not rely on older launch-guide wording that treats those fields as a new-campaign hard cap. This package does not call the Ads API or populate legacy bid fields. [Source O4](../SOURCES.md)

## Match the conversation

Context hints describe relevant buying situations; they do not reserve particular questions or behave like Google's exact-match keywords. All three themes focus on evaluating retail analytics or improving reporting, rather than generic enthusiasm about AI. [Sources O5–O6](../SOURCES.md)

Do not assume paid ChatGPT ads can reach every retail executive who uses ChatGPT. Plus, Pro and Business users are not shown these ads under the current guidance. Keep organic discovery as a separate part of the project, with paid delivery treated as a small optional test. [Source O6](../SOURCES.md)

The Clicks objective uses valid-click billing. Site logs and UTM sessions are separate measurements; the presence of a tag is not confirmation that a person watched or that a click was billed. Use the first-party demo/playback report and actual inquiries to judge the visit. No OpenAI Pixel, Conversions API event or conversion-bidding integration is configured by this package. [Sources O3–O4, O6](../SOURCES.md)
