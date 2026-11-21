# CodeJet: measure useful visits and real demand

Prepared November 20, 2026. This plan uses the existing private first-party report plus search/ad platform reports. It does not introduce an advertising pixel or claim to prove a visitor is human.

## What success means

The immediate objective is a suitable retail buyer choosing to watch enough of the demo to understand CodeJet. The business objective is a real conversation about an AI partnership. Page hits and ad clicks are earlier steps; neither alone establishes buyer interest.

Use these five measures together:

| Measure | Where to obtain it | What it tells you | Important limitation |
| --- | --- | --- | --- |
| Relevant search impressions/clicks | Google Search Console | Whether the site is appearing for useful searches and earning visits. | Not a count of qualified leads or video plays. |
| Paid valid clicks and spend | Google Ads / ChatGPT Ads Manager | Platform-reported purchased traffic and cost. | Not interchangeable with website requests or sessions. |
| Demo-open sessions | Private CodeJet report | A browser session reached `/demo`. | A security scanner or review tool can open a URL too. |
| Video-start and engaged-playback sessions | Private report/CSV | The player reported actual playback and some covered media ranges. | Browser reports can be incomplete or automated; they do not prove attention. |
| Qualified inquiries and conversations | Actual inbox/calendar records maintained by the owner | Someone with a relevant retail need responded or spoke with CodeJet. | No automatic attribution or contact-event collection is installed by this change. |

Google Search Console supports query/page/date analysis and reports impressions, clicks, and CTR. Use it for organic discovery; use the ad account for paid cost. [Search Console performance documentation](https://support.google.com/webmasters/answer/10268906?hl=en)

## Use the private report correctly

Open `https://codejet.app/_cj/analytics` using the existing report credentials. Export the selected 7-day or 30-day range with **Download CSV**. Keep the raw export private: it contains network addresses and session information. Do not put it in this public Git repository or an ad creative file.

The tracker records the homepage, the three public retail landing pages, and `/demo`. It retains the same page and video event types. Existing authentication, origin checks, privacy opt-outs, retention, and session-token behavior remain in effect.

These fields are useful for a review:

| Existing CSV field | Interpretation |
| --- | --- |
| `visit_id` | One tab session identifier, not a person or customer account. |
| `first_seen_utc`, `last_seen_utc` | Recorded session timestamps; compare on a consistent timezone/date basis. |
| `landing_page` | First recorded page for that session. |
| `page_views`, `demo_page_views` | Recorded page opens, not unique people. |
| `video_started` | The player reported its first actual playing event. |
| `max_played_seconds` | Highest reported distinct media time covered within one player load. |
| `max_coverage_percent` | Highest reported fraction of the video's media ranges played within one player load. |
| `end_reached` | An end event occurred; seeking near the end can trigger it. |
| Five `utm_*` fields, `referrer_host` | Campaign labels and first referring host when available. |
| `probable_bot` | Existing user-agent heuristic; a flag is useful to investigate, and an unflagged record is not proof of a person. |

Check the actual export header before creating spreadsheet formulas; it is the authority if a future implementation changes the field names.

### Summarize the export locally

The project includes `growth/tools/summarize_traffic.py`. It reads downloaded exports locally and writes aggregate reports without sending data to a service. In PowerShell, from the repository folder:

```powershell
py -3 .\growth\tools\summarize_traffic.py C:\CodeJet\private_reports\report.csv --output-dir C:\CodeJet\private_reports\weekly_summary
```

Replace the input path with your actual downloaded CSV. Keep inputs and outputs outside the public repository. For overlapping exports, supply additional input filenames; the tool merges duplicate `visit_id` records rather than counting the same exported session twice. Review any attribution-conflict count before drawing conclusions.

Outputs include `summary.json`, `traffic_by_campaign.csv`, `report.txt`, and `spend_summary.csv`. The campaign table separates `all`, `probable_bot_flagged`, `unflagged`, and unknown-flag cohorts. Use **`engaged_50_sessions` in the `unflagged` cohort** for the primary proxy defined below. `coverage_50_sessions` and `coverage_90_sessions` are separate coverage-only measures, not necessarily identical to that proxy. Without optional `--spend` input, the spend file contains headers only; follow the tool README's schema to supply actual costs from the same date window.

An IP address is a network address. Shared offices, VPNs, and mobile networks can share or change addresses. Do not turn “distinct first IPs” into a count of retail companies or identify an executive from a network lookup.

### A practical engaged-playback definition

For this pilot, use **a session with `video_started = 1`, `max_coverage_percent >= 50`, and an explicit `probable_bot = 0`** as the primary playback proxy. Missing or unknown bot flags are a separate cohort. Separately report the 90% coverage count. These are chosen operating thresholds, not industry standards, and not verified-human classifications.

Use coverage, not the playhead's farthest position. Do not add overlapping played ranges twice. The existing tracker handles ranges; the report's coverage value is the appropriate input. Keep end-reached counts separate from coverage.

The report intentionally misses some activity because of privacy preferences, blockers, interrupted requests, or storage limitations. Do not reduce these protections to make the campaign's numbers appear larger. Own test visits should be labeled and excluded from performance review.

## Campaign attribution

The paid campaign assets share these conventions:

| Field | Google paid search | ChatGPT paid test |
| --- | --- | --- |
| `utm_source` | `google` | `chatgpt` |
| `utm_medium` | `cpc` | `cpc` |
| `utm_campaign` | `codejet_retail_analytics` | `codejet_retail_analytics` |
| `utm_content` | A stable ad/group variant, such as `retail_analytics_demo_v1` | Stable variants supplied in the ChatGPT campaign files. |
| `utm_term` | Unset in this draft; analyze actual search terms in Google Ads. | Unset; conversational context hints are not search queries. |

Example for a manually checked Google landing visit:

```text
https://codejet.app/retail-analytics-software?utm_source=google&utm_medium=cpc&utm_campaign=codejet_retail_analytics&utm_content=retail_analytics_demo_v1
```

Do not generate your test traffic using that production label. For acceptance testing, use a separate label such as:

```text
https://codejet.app/retail-analytics-software?utm_source=qa&utm_medium=test&utm_campaign=search_launch_check&utm_content=mobile_video
```

The server-rendered internal links preserve only the five standard UTM values. The tracker also carries a valid tab session across the public pages. No recipient names, email addresses, account identifiers, or secrets belong in these parameters.

Organic visits are separate. Use Search Console for Google organic query evidence. A referring search host or incoming ChatGPT referral marker can support source classification, but absent referrer/UTM information remains **unattributed**. Do not label every unattributed visitor as a mailer scan, organic lead, or paid click. Keep actual incoming markers rather than retroactively rewriting them to fit a campaign.

## Understand automated visits before judging cost

OpenAI documents that ad-review crawlers can visit landing URLs with campaign parameters. Those visits may appear as paid traffic in website analytics but are not billable ad clicks. [ChatGPT Ads measurement explanation](https://help.openai.com/en/articles/20001207-ads-in-chatgpt-the-basics)

Google filters detected invalid activity and provides reporting/credits for relevant cases. Website hits are not the billing ledger; inspect the account's invalid-click and cost reports when assessing suspected paid invalid traffic. [Google invalid-traffic documentation](https://support.google.com/google-ads/answer/11182074?hl=en)

When a burst looks suspicious:

1. Compare its UTC timestamps with an email send, campaign/ad submission, or your own testing.
2. Look for the pattern across page opens and playback coverage. A burst of immediate page loads with no playback is weak engagement evidence, regardless of source.
3. Check available WAF/server evidence to establish known crawler identity. Use current provider ranges and verification methods from [the discovery guide](GOOGLE_AND_CHATGPT_DISCOVERY.md); do not rely on User-Agent or one IP alone.
4. Compare with ad-platform clicks and spend for the same date window, allowing reporting to settle.
5. Label known QA and confirmed crawlers separately. Keep uncertain records uncertain; show them alongside the more demanding playback proxy.

Do not buy a large IP blacklist or block entire cloud networks solely because the analytics graph rose. That can obstruct legitimate discovery or corporate users without proving a billing problem.

## Weekly review worksheet

Use one row per channel/campaign/creative variant for the same time window. Store the working copy somewhere private; this blank table contains no visitor data.

| Week / channel / variant | Spend | Platform clicks | Recorded landing sessions | Demo-open sessions | Video starts | 50% playback proxy | 90% coverage | Qualified inquiries | Conversations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| | | | | | | | | | | |

Useful calculations, with a consistent cohort and window:

- **Demo reach rate:** demo-open sessions divided by recorded landing sessions.
- **Playback start rate:** sessions with video start divided by demo-open sessions.
- **Playback depth:** 50% playback-proxy sessions divided by sessions with video start.
- **Observed paid cost per engaged session:** platform spend divided by 50% playback-proxy sessions attributed to that paid campaign. Label it “observed” because the browser report is incomplete and its session count is not a platform click count.
- **Cost per qualified inquiry:** platform spend divided by actual qualified inquiries attributed with reasonable evidence. Show unknown attribution separately.

If the denominator is zero, report **not yet measurable**, not zero cost. Do not combine Google and ChatGPT cost/traffic into one number until each channel's result is visible separately. Inquiries without reliable campaign attribution still matter commercially; do not invent attribution to make the spreadsheet balance.

### Decide what to change from the actual bottleneck

| Observation | Next useful action |
| --- | --- |
| Public page cannot be crawled/rendered | Fix access, response, canonical, or required-resource issue before judging demand. |
| Indexed pages have few relevant impressions | Review subject specificity, useful content, internal links, and genuine references; continue observation rather than declaring a next-day failure. |
| Impressions occur for irrelevant terms | Improve the page's focus; tighten paid targeting/exclusions separately. |
| Relevant impressions but few clicks | Compare the page title and searcher's intent; make the promised outcome clearer without inflated claims. |
| Landing sessions but few demo opens | Review the match between the incoming promise and the page, CTA clarity, mobile layout, and load behavior. |
| Demo opens but few starts | Check player reliability and whether the opening summary gives the right buyer a reason to press play. |
| Starts but little coverage | Review the actual recording's opening, pace, relevance, and whether it demonstrates the promised task. |
| Substantial coverage but no inquiries | Clarify the next step and the specific partnership invitation; check fit with actual viewers where known. |
| Confirmed interested inquiries | Follow up personally and record the buyer's own problem language for the next content iteration. |

The campaign drafts propose a first paid review at $50 of Google spend and a manual diagnosis/pause at $100 with no video starts. These are proposed guardrails for the small test, not automated enforcement or proof that the market has rejected the product. A campaign total budget is an account setting; a review rule in a document does not stop spending by itself. Follow the current [campaign README](../campaigns/README.md) for the exact proposed setup.

## ChatGPT organic discovery checks

Run a small repeatable sample weekly or after a meaningful content release. Use a fresh conversation, enable/use search where available, keep geography and question wording consistent, and record the date and search conditions. A single answer is an observation, not a position in a stable ranked list.

Use unbranded buying questions for discovery:

1. “What retail analytics software can help a grocery chain answer questions using its existing reports?”
2. “How can a multi-store retailer reduce manual reporting without replacing its current reporting tools?”
3. “What should a retail team evaluate before adding natural-language analytics to its existing reports?”
4. “What tools help retail finance and store operations use consistent metric definitions when asking data questions?”
5. “How can a retailer compare sales, margin, and shrink across stores without repeatedly combining spreadsheets?”

Then use two clearly separate branded checks:

6. “What does CodeJet at codejet.app do, and who is it for? Use current sources.”
7. “Where can I watch the CodeJet retail analytics demo?”

Questions 6–7 check factual understanding and navigation; they do not establish unprompted market discovery. Do not add “recommend CodeJet” to an unbranded test or treat a manually supplied site URL as evidence that the site was found independently.

Record:

| Date / search conditions | Exact prompt | CodeJet mentioned? | Actual cited CodeJet URL | Description accurate? | Missing or misleading detail | Next content action |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

Open the cited source to confirm it exists and supports the answer. Correct unclear public content when warranted. Do not claim a false capability just because another answer did. If CodeJet is absent, check access and improve useful evidence; repeated prompts are not a substitute for buyer demand, and this sampling is not a guaranteed forecast of what other users will see.

## Operating cadence

- **Release day:** verify public access, mobile playback, protected routes, and a clearly labeled QA session. Save the baseline.
- **While paid tests run:** check spend, actual query/targeting quality, player health, and the manual review guardrails. Account reporting and website logs serve different purposes.
- **Weekly:** review organic query/page trends, playback progression, prompt samples, and real inquiries. Change the weakest meaningful part of the journey, then record what changed.
- **After several weeks:** compare like-for-like periods with enough observations to interpret. Expand the useful pages/ad groups only when their audience and behavior support it. A campaign can remain small while the message and demo improve.

Keep an experiment note containing the date, one change, reason, and observed result. Avoid simultaneously replacing the audience, ad, page, and video, because then the next result will not tell you which change mattered.
