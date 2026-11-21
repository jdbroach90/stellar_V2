# CodeJet search campaign: launch guide

Prepared November 20, 2026. Use this guide with the code in this branch and [growth/README.md](../README.md). The deliverable prepares the website and campaign assets; creating a draft does not activate advertising or verify a search account.

## 1. Review the project in the existing repository

The website is `jdbroach90/stellar_V2`. This release belongs on a review branch based on **`master`**, the production line identified for this project. The repository also has `main`; do not assume the default GitHub branch is the Render deployment branch.

Before merge, the owner should check Render's service Settings and confirm the linked branch is still `master`. Render deploy behavior follows the service's linked branch and auto-deploy configuration. Its Deploys screen shows the active release. [Render deployment documentation](https://render.com/docs/deploys)

Review these groups of changes:

| Group | What to check |
| --- | --- |
| Public pages | The three retail pages describe the current product accurately and lead to `/demo`. |
| Demo | The existing Cloudflare video is playable; surrounding text accurately describes it. |
| Discovery | Public canonical URLs, titles, descriptions, robots rules, and sitemap are correct for `https://codejet.app`. |
| Tracking | Existing events work on the new public pages; the same five UTM fields survive internal navigation. |
| Security | Protected application and analytics paths, credentials, origin checks, contact validation, and persistent storage are preserved. |
| Campaign assets | Copy and targeting are drafts; campaign activation requires account configuration and a chosen spend limit. |

This release must not restore the visible Privacy & Analytics footer links the owner previously removed. The existing `/demo-privacy` disclosure and tracking behavior remain. The older `DEMO_ANALYTICS_SETUP.md` contains a historical statement that those footer links are shown; this guide supersedes that display statement only. Keep the underlying privacy and analytics protections.

The redesigned demo stays on the watch page when playback ends, so a visitor can replay it, read the explanation, or choose **Discuss an AI partnership**. It replaces the old automatic one-second redirect. End/coverage telemetry still records playback; the older setup guide's redirect description no longer applies.

## 2. Preview locally on Windows

Use **PowerShell**, whose prompt begins with `PS`. If you see `>>>`, you are inside Python; type `exit()` first. Commands below are PowerShell commands.

In the existing checkout:

```powershell
Set-Location C:\CodeJet\stellar_V2
git status --short
git fetch origin
```

If the status lists work in progress, preserve it before switching branches. Do not run a cleanup/reset command to make these instructions succeed. Once the checkout is clean and the review branch is available on GitHub:

```powershell
git switch --track origin/feature/retail-search-campaign-20261120
```

If that local branch already exists, use `git switch feature/retail-search-campaign-20261120` and inspect its status. Do not overwrite it. If working from a downloaded project archive instead, open PowerShell in its extracted repository folder and continue with the environment setup.

Create an isolated Python environment, install the existing requirements, and run the local site:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app server run --host 127.0.0.1 --port 5000
```

Open these browser URLs:

```text
http://127.0.0.1:5000/retail-analytics-software
http://127.0.0.1:5000/retail-reporting-automation
http://127.0.0.1:5000/retail-data-questions
http://127.0.0.1:5000/demo
```

Stop the local server with **Ctrl+C**. This local preview does not deploy the site. Do not copy production passwords into screenshots or a committed `.env` file. Without production credentials, preview the public pages and video; the production contact form and protected analytics need their existing server configuration.

Run the repository checks from a second PowerShell window or after stopping the preview:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/test_analytics_client.js
```

Node is used for the browser-tracker tests; it is not a new production requirement. Check the pull request's test result as well. A local environment missing Node cannot run the JavaScript test command.

## 3. Complete real video metadata

The public pages can launch while optional enhancements remain unset. For video-specific structured data, follow [the metadata checklist](GOOGLE_AND_CHATGPT_DISCOVERY.md#real-video-metadata-is-an-owner-supplied-prerequisite) and `.env.example`. Obtain the real original publication date and verify the current public thumbnail; do not enter the website deployment date as a substitute.

The new configuration is:

| Variable | Release behavior / owner action |
| --- | --- |
| `CJ_SEO_INDEXABLE` | Defaults to `1` for the public production host. Direct preview/origin requests remain `noindex`; use `0` for an intentionally nonpublic preview configuration. |
| `CJ_SEO_FRONTDOOR_ID` | Optional SEO-specific expected Front Door profile GUID; otherwise the existing `CJ_ANALYTICS_FRONTDOOR_ID` is used. Required through one of those variables for recognizing the public host behind the configured Render origin. This is not an analytics password or origin secret. |
| `CJ_GOOGLE_SITE_VERIFICATION` | Optional actual verification token, only if choosing Google's HTML-tag method for a URL-prefix property. Leave unset for the DNS Domain-property method below. |
| `CJ_VIDEO_SCHEMA_ENABLED` | Defaults to `0`. Enable with `1` only after real required metadata is configured. |
| `CJ_VIDEO_UPLOAD_DATE` | Actual original publication timestamp with timezone, in ISO 8601. No default date is invented. |
| `CJ_VIDEO_THUMBNAIL_URL` | Defaults to the project's current public Cloudflare video thumbnail. Recheck access when enabling video markup. |
| `CJ_VIDEO_DURATION` | Optional verified ISO 8601 duration. Leave unset until checked against the recording. |

Video-specific JSON-LD and the video sitemap entry are conditional on enabled, valid required metadata. The ordinary public sitemap and page metadata do not depend on inventing those missing values. Preserve all existing environment values when adding these fields in Render.

Do not add a transcript, runtime claim, or video chapters until checked against the recording. Keep the current video ID and player unless intentionally releasing a replacement. If replacing the video later, update the visible summary, metadata, thumbnail, and analytics video identifier together.

## 4. Merge and deploy through the existing Render service

After reviewing the pull request and passing checks:

1. Confirm the PR base is `master` and review the final diff.
2. Merge through GitHub. This is the production release action when Render auto-deploys `master`.
3. In Render, open the existing service's Deploys screen and confirm the deployed commit matches the merge.
4. Preserve the existing SMTP/reCAPTCHA variables and analytics environment values. Do not regenerate existing analytics secrets as part of SEO deployment.
5. Preserve the actual persistent disk at `/var/data` and the existing database path. Do not replace, clear, download into the repository, or commit the analytics database.
6. Confirm `/health` is healthy before considering the deployment complete.

This project does not require changing nameservers, MX records, Azure origins, or the Cloudflare video-hosting account. Search Console DNS verification later adds its own record without replacing existing records.

## 5. Check the live public routes and existing protections

Check the final public host, not only the Render origin. In PowerShell:

```powershell
$publicBase = 'https://codejet.app'
$publicPaths = @(
  '/health',
  '/retail-analytics-software',
  '/retail-reporting-automation',
  '/retail-data-questions',
  '/demo',
  '/robots.txt',
  '/sitemap.xml'
)
foreach ($publicPath in $publicPaths) {
  $response = Invoke-WebRequest ($publicBase + $publicPath) -UseBasicParsing
  Write-Output ($response.StatusCode.ToString() + ' ' + $publicPath)
}
```

Each should return the intended public resource successfully. Open the HTML pages on a phone as well. Confirm:

- Titles and canonical URLs refer to the production site, not localhost, Render, an Azure endpoint, or a GitHub preview.
- Public search pages have no accidental `noindex`, authentication wall, or interstitial challenge.
- The demo player loads and plays; the video is easy to find above the supporting explanation.
- The thumbnail, stylesheet, script, and player resources load without a sign-in requirement.
- The contact action reaches the existing contact section. Any real submission used for acceptance testing should be identifiable as a test.
- `/robots.txt` and `/sitemap.xml` contain the intended public URLs and do not expose private report data.
- A logged-out request to the private report does not reveal analytics. The direct Render analytics origin does not bypass the existing authentication/origin controls.
- `/ai` remains restricted according to the current WAF allowlist when tested from outside the permitted network.
- The privacy disclosure remains available without restoring its removed footer links.

### Azure Front Door checks

Use [the public-versus-protected access table](GOOGLE_AND_CHATGPT_DISCOVERY.md#azure-front-door-public-discovery-protected-application) to inspect the current policy. Do not add an unqualified Allow for all traffic claiming to be a search bot. Preserve the existing `/_cj/` request-header overwrite and no-cache behavior, expected Front Door ID, `/ai` restriction, and contact protection. Fix specific blocked public paths/resources only after checking WAF logs.

The existing Front Door setup sends `stellar-v2.onrender.com` as the origin Host. Front Door supplies the original public hostname in `X-Forwarded-Host` and overwrites a client-supplied value. The SEO implementation recognizes that public hostname only for the expected origin host and matching configured Front Door ID. Confirm the actual deployed `https://codejet.app/robots.txt` allows public crawling and the public HTML says `index, follow`; a healthy Render page alone does not confirm this. [Microsoft forwarded-header documentation](https://learn.microsoft.com/azure/frontdoor/front-door-http-headers-protocol)

That host selection is only a publishing decision. It does not authenticate requests or replace the analytics origin secret, token, or IP checks. Direct requests to the Render hostname remain excluded from indexing by default.

Do not cache personalized analytics responses. If public-page caching is configured later, verify campaign query parameters do not cause one visitor's attributed links to be served to another; bypass query-bearing HTML or use a cache key that preserves their variation.

## 6. Verify Google Search Console and submit the sitemap

Use the Google account that should own CodeJet's search property.

1. Open [Google Search Console](https://search.google.com/search-console/).
2. Select the existing verified `codejet.app` Domain property if there is one. Otherwise add that Domain property.
3. Copy the DNS verification record issued in that account's verification screen and add it exactly as directed at the authoritative DNS provider. Keep other verification and email records intact.
4. Return to Search Console and verify. Keep the record after successful verification.

No usable verification code can be invented in this repository. Domain verification requires the real account-issued record; DNS changes can take time to become visible. [Google ownership verification](https://support.google.com/webmasters/answer/9008080?hl=en)

After verification:

1. Submit `https://codejet.app/sitemap.xml` in **Sitemaps**.
2. Inspect the three retail pages and `/demo` individually with **URL Inspection**. Run a live test when diagnosing access or rendering.
3. Review the rendered HTML, canonical choice, indexing eligibility, and required resources. Request indexing for the new/updated public pages if the tool permits it.
4. Check `/demo` with [Rich Results Test](https://search.google.com/test/rich-results) after enabling real video metadata. Correct material errors; do not invent facts to clear optional-property notices.
5. Revisit Search Console's page/video indexing reports after Google has had time to process the site. Submission is not confirmation of indexing.

Record the deployment date and baseline data in [MEASUREMENT.md](MEASUREMENT.md). The recommended review schedule is a working cadence, not a ranking or lead-volume forecast.

## 7. Check ChatGPT organic access

Read the deployed robots rules and the OpenAI access section in [GOOGLE_AND_CHATGPT_DISCOVERY.md](GOOGLE_AND_CHATGPT_DISCOVERY.md). Confirm `OAI-SearchBot` can retrieve the public pages and required resources under the current CDN/WAF policy. Keep the training-crawler decision separate.

Run the small prompt-check routine in [MEASUREMENT.md](MEASUREMENT.md#chatgpt-organic-discovery-checks) after release and periodically thereafter. Capture actual cited URLs and factual accuracy. Do not describe one favorable answer as a stable ranking or assume repeated self-searches create demand.

## 8. Configure paid tests separately

The assets in `growth/campaigns/` are a separate way to buy controlled traffic while organic visibility develops. Import/review the Google assets or recreate the ChatGPT drafts in the relevant advertiser account. Keep them paused until all of these concrete fields are chosen and checked:

- Billing account, service availability, geography, language, campaign dates, and explicit spend limit.
- Intended landing URL, UTM labels, mobile experience, and video playback.
- Targeting/exclusions, ad copy, and current account-specific budget/bidding controls.
- Current landing-page access for the ad platform's review crawler.
- The measurement plan and how actual inquiries will be recorded.

The existing first-party tracker does not install a Google or OpenAI conversion pixel and does not upload conversions to an ad platform. Do not select conversion-optimized bidding on the assumption that this repository has already connected one.

Search-engine submission and campaign activation are distinct actions. No paid campaign is needed to make the public content eligible for organic discovery. No ad campaign promises only human visits.

## 9. First review and rollback

Review technical access soon after deployment. Review paid traffic/search terms frequently while a paid test is active; review organic query and page patterns weekly. Use [MEASUREMENT.md](MEASUREMENT.md) for the decision logic.

If a release breaks public pages, playback, analytics protection, or the contact flow, revert the release through a normal reviewed Git commit/PR to `master`, or use the existing Render rollback process while accounting for auto-deploy behavior. Preserve the persistent database and production secrets. Do not force-push, delete the database, or disable WAF protections to make a deployment appear healthy.

## Release record to fill in

| Item | Owner's record |
| --- | --- |
| Reviewed PR / merged commit | |
| Render deployed commit / time | |
| Live public-route check | |
| Mobile video/playback check | |
| Protected-path check | |
| Video metadata values verified | |
| Search Console property / sitemap submission date | |
| Baseline date range saved | |
| Paid campaign status and approved limit, if used | |
