# Google Search setup

## Proposed campaign

| Setting | Prepared choice |
| --- | --- |
| Campaign | `CodeJet Retail Analytics Search Pilot` |
| Campaign type | Search |
| Network | Google Search only; Search partners and Display expansion off |
| Country and language | United States, English |
| Location option | People in or regularly in the targeted location |
| Budget | **$400 campaign total**, proposed 21-day flight |
| Dates | Select during launch review; no dates are scheduled in these files |
| Bidding | Maximize clicks; choose a numeric CPC bid limit using current account forecasts |
| Initial group | `01 Retail Analytics Software` |
| Initial keyword set | Six Exact keywords in that group |
| Reserve | Phrase keywords, Reporting Automation group and Retail BI group |
| Status | Campaign, ad groups, ads and positive keywords all Paused |

The location setting narrows delivery to people Google considers present in the target area. It is not proof of a person's location. A CPC bid limit is a bid control; account bid adjustments can apply on top of it. [Sources G8–G9](../SOURCES.md)

## Create the paused campaign shell

Use a current Google Ads Editor version. Campaign-total support for Search was introduced in Editor 2.12; use the current campaign form instead of inventing bulk budget columns. [Source G7](../SOURCES.md)

Create a **new Search campaign** named exactly as above, set its status to **Paused**, and configure its campaign-total budget and selected dates in the campaign settings. If your account or installed Editor cannot expose campaign-total mode, leave the campaign unposted and resolve that setting in the current Google Ads interface. Do not substitute an ordinary daily budget.

**Never put `400` in an Editor `Budget`, `Campaign budget` or `Daily budget` CSV field.** Those documented headers refer to a daily budget. The asset files omit all budget and bid columns intentionally. Google supports campaign-total budgets for scheduled Search flights; the current budget FAQ and Editor release notes describe different stages of bulk support, so this package uses the interface for the budget. [Sources G1, G6–G7](../SOURCES.md)

Check the account for a campaign with the same name before importing. If that name already exists, change it in `../campaigns.json` and rebuild. Editor can interpret a matching object as an update rather than a new object. [Source G1](../SOURCES.md)

## Import the prepared assets

The files use Google's documented English column names. They are prepared for Ads Editor, not the Google Ads web interface's unrelated bulk-upload schemas. [Sources G1–G4](../SOURCES.md)

1. Use **Account > Import > From file** for `ad_groups.csv`, then `keywords.csv`. Review the proposed changes after each import. All supplied positive entities should be Paused.
2. For `responsive_search_ads.csv`, select **Ads > Responsive search ads > Make multiple changes**. Open the CSV in Excel, copy the complete table including headers, paste it, and indicate that the data contains campaign and ad group columns. Map the numbered headlines/descriptions and final URL, process, then review. The typed context selects RSA; the file does not invent an undocumented `Ad type` header.
3. Import `negative_keywords.csv` with **Account > Import > From file**. Confirm all 63 rows appear under **Keywords, Negative**, with the intended ad group and Negative phrase or Negative exact type. They are exclusion rules and cannot be paused. There is deliberately no `Status` column in this file.
4. Review all changes before posting. Confirm three ad groups, three RSAs, 28 positive keyword rows and 63 negative rows. The first group has 12 positive rows, of which six are Exact and six Phrase. There should be no budget change from these CSVs.

When saving the setup to the account, preserve the Paused status at all four positive levels. Preparing or posting paused assets is separate from enabling delivery. This package has not performed either account action.

## Initial activation

After the production page, playback, budget and current auction forecasts have been reviewed, enable only the first campaign's initial group, its RSA and its six Exact keywords. Leave its Phrase rows and both reserve groups paused. Keep text customization, final URL expansion and automatic keyword broadening off for this initial creative test, where those controls are available.

Exact matching can include searches with the same intent; it is not literal string matching. Review actual search terms. Consider Phrase expansion or the reporting group if the exact set delivers too little traffic, while retaining the same total budget. [Sources G10, G13](../SOURCES.md)

The three supplied RSAs each contain 12 headlines and four descriptions, validated against 30- and 90-character limits. Paths are no longer than 15 characters. Copy works as individual assets because Google may rearrange combinations. [Source G5](../SOURCES.md)

## First review

At the proposed $50 spend checkpoint, inspect actual search terms, paid clicks, landing sessions, demo opens and playback. Investigate irrelevant queries with narrow negatives. Check Google's invalid-click reporting separately from the site's raw page traffic. Do not classify every repeated IP as fraud or every tagged visit as a paid human. [Sources G11–G13](../SOURCES.md)

If the $100 diagnostic threshold is reached without any video start, pause the pilot and inspect tracking, mobile playback, the ad-to-page message and query relevance. The threshold limits diagnostic spend; it does not establish that the market has rejected CodeJet.
