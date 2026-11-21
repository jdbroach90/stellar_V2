# Local campaign traffic report

This tool reads CSV files downloaded from the existing CodeJet analytics dashboard and writes campaign-level summaries. It uses only Python's standard library. It does not connect to the website, Google Ads, ChatGPT, or any other service, and needs no credentials.

## Run it on Windows

Use **PowerShell**, where the prompt starts with `PS`. If you see Python's `>>>` prompt, type `exit()` first.

From your repository folder, run:

```powershell
cd C:\CodeJet\stellar_V2
py -3 growth\tools\summarize_traffic.py "C:\CodeJet\private\codejet-demo-visits.csv" --output-dir "C:\CodeJet\private\weekly-report"
```

Replace the input path with the downloaded dashboard CSV. The tool needs Python 3.10 or newer and no `pip install`. Your Python 3.14 installation is suitable.

To combine overlapping downloads without counting the same session twice:

```powershell
py -3 growth\tools\summarize_traffic.py "C:\CodeJet\private\monday.csv" "C:\CodeJet\private\friday.csv" --output-dir "C:\CodeJet\private\combined-report"
```

Open `report.txt` for a short summary and `traffic_by_campaign.csv` in Excel for campaign comparisons. `summary.json` contains the same aggregate totals for scripts. `spend_summary.csv` has cost calculations when manual spend is supplied; otherwise it contains headers only. Re-running replaces these four report files in the selected output directory. Use a different directory when you want to keep an earlier report.

## Keep exports private

The dashboard export contains IPs and session identifiers. Store it outside the Git repository, as in the examples above, and never put it in `static`, public hosting, or a shared downloads folder. The tool does not copy those columns into its reports or produce an individual-session table.

If `--output-dir` is omitted, output goes to `growth/tools/private_reports/`, which this directory's `.gitignore` excludes. A custom directory inside another part of the repository is **not automatically ignored**. Keep both source exports and local reports out of commits. The tool's tests generate synthetic data in temporary directories; no real traffic fixture is included.

Campaign labels are preserved for grouping. Do not place names, personal emails, or customer identifiers in UTM tags. The tool suppresses obvious email addresses, IP addresses, and UUIDs used as whole labels, but this is not a general anonymization guarantee. Spreadsheet formula prefixes are escaped in output labels.

## What the numbers mean

Each campaign group has four cohort rows:

| Cohort | Meaning |
| --- | --- |
| `all` | Every unique exported session in this group. |
| `probable_bot_flagged` | At least one overlapping export marked the session's `probable_bot` flag true. |
| `unflagged` | The exported flag is false and no overlapping record marked it true. This does not establish a human visitor. |
| `flag_unknown` | No exported record supplied a bot assessment, including older CSVs without that column. |

The `all` row is the total; do not add it to the other three cohorts. A session is a browser-tab analytics session, not a verified person or company.

| Metric | Definition |
| --- | --- |
| `sessions` | Unique `visit_id` values, used in memory only. |
| `demo_sessions` | Sessions with an exported `demo_page_views` count above zero. |
| `video_start_sessions` | Sessions with a reported video-start event. |
| `end_reached_sessions` | Sessions reporting the end; seeking can trigger this without watching the full video. |
| `coverage_50_sessions` | Sessions whose reported played-range coverage reached at least 50%. |
| `coverage_90_sessions` | Sessions whose reported played-range coverage reached at least 90%. |
| `engaged_50_sessions` | Sessions with both a reported start and at least 50% reported coverage. Its `unflagged` cohort is an engagement proxy. |
| `coverage_unknown_sessions` | Sessions with no reported coverage value. Unknown is not zero. |

Coverage is not calculated from `max_position_seconds`, and an end event is not treated as full coverage. Video starts and coverage remain separate signals because events can be blocked, missed, or interrupted. An unflagged engaged session is stronger evidence of interest than a page request, but none of these fields proves a human identity or buying intent.

## Attribution and overlapping exports

Grouping uses `utm_source`, `utm_medium`, `utm_campaign`, and `utm_content`. Missing dimensions become `(not set)`. When all four tags are absent, an available referrer hostname becomes the source with medium `referral`; without one, the source is `(direct or unknown)`. A Google referrer by itself does not identify a paid versus organic visit, so the tool does not guess that distinction.

Overlapping files are deduplicated by `visit_id`. Each session retains the earliest first-seen time, latest last-seen time, maximum reported coverage, and any observed demo/start/end signal. Metrics are not summed across overlapping records. Bot-flagged status wins over unflagged or unknown status.

If attribution differs across exports, the tool prefers explicit UTM data, then the earliest observation, with a deterministic lexical tie-break. It keeps a complete attribution tuple rather than assembling tags from different records. The summary reports the number of sessions with attribution conflicts.

These are observed-session summaries, not a reconstruction of raw events. Maximum coverage across exports is not a union of disjoint played ranges. Observed date bounds do not prove that an export covers an entire calendar window. The dashboard's retention and export limits still apply; this tool cannot recover missing or truncated records. Avoid comparing a seven-day traffic export with a month's spend.

## Add manual spend

Prepare a separate CSV with these columns and one row per campaign/content group. The row below is a **synthetic example**, not a current budget or cost estimate:

```csv
source,medium,campaign,content,spend,currency
google,cpc,codejet_retail_analytics,retail_analytics_demo_v1,25.00,USD
```

Use the exact group labels shown in `traffic_by_campaign.csv`. Empty manual dimensions become `(not set)`. `spend` is the total nonnegative amount for the same reporting time and campaign scope as the traffic. Use one currency per row; the tool does not combine currencies. Consolidate multiple daily spend entries for the same group before importing; duplicate groups are rejected to prevent accidental double counting.

```powershell
py -3 growth\tools\summarize_traffic.py "C:\CodeJet\private\codejet-demo-visits.csv" --spend "C:\CodeJet\private\spend.csv" --output-dir "C:\CodeJet\private\weekly-report"
```

`spend_summary.csv` reports cost per start and cost per session with at least 90% reported coverage, both for all traffic and for the unflagged cohort. Each calculation uses the entire matched campaign group's spend; flagged sessions do not cause spend to be subtracted. This makes the unflagged cost a cautious quality comparison rather than a claim of verified human cost.

A cost is blank when its denominator is zero. An unmatched spend group remains visible with `matched_traffic=false` and blank costs. Groups without supplied spend have no cost estimate. The tool never guesses zero ad spend or a current ad price. It does not verify the supplied spend window, and there is no automated ad-platform import.

## Validate the tool

```powershell
py -3 -m unittest discover -s growth\tools -p "test_*.py" -v
```

Tests cover overlapping exports, attribution conflicts, bot and unknown cohorts, played coverage versus end seeking, manual spend, empty input, private-field exclusion, identifier/formula handling, and preventing an input file from being overwritten. They operate entirely on synthetic rows.
