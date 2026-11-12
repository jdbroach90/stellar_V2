# CodeJet demo analytics — morning setup

Prepared November 12, 2026 for `jdbroach90/stellar_V2`.
Base reviewed: `730d80f162758c9e038855dd4b7a9c4795067ea7`.

## What this adds

The existing Flask site serves `/demo`, which embeds Cloudflare Stream video
`38ccab99e8156adae4abcfbb1d36cc0f`. This change uses that same player's API.
Its one-second redirect to `https://codejet.app/#contact` remains intact.

| Report field | Meaning |
| --- | --- |
| Public IP | First and latest observed public network address per tab session |
| First/last seen | Server timestamps in UTC |
| Page opens | Homepage and demo-page views recorded by the browser |
| Video started | First actual `playing` event from the player |
| Max coverage | Maximum fraction of distinct media ranges reported played within one player load |
| End reached | Video reached its end, including when someone seeks forward |
| Campaign/source | Five standard UTM labels, plus referring hostname |
| Possible bot | Simple browser user-agent heuristic, not reliable bot detection |

An IP is not a verified person or company. Offices, VPNs, and mobile networks can
share addresses. Sessions use a signed token in a browser tab's `sessionStorage`;
different tabs, blocked storage, or network changes affect counts. Browser events
can be blocked, interrupted, or forged. This is marketing telemetry, not audit
evidence. No external IP-lookup service is used.

Tracking is **disabled by default**. There are no new Python dependencies.
This branch does not provision services, change Azure/Render settings, send
emails, or deploy the website.

## 1. Apply the patch to a review branch locally

Extract `CodeJet_Demo_Analytics.zip` outside your repository. The connected GitHub
app could read this public repository but was denied permission to publish a branch,
so the tested changes are supplied as a patch. The patch contains all implementation,
test, and documentation changes; it does not contain credentials or visitor data.

On your Windows machine, first confirm the checkout is clean:

```powershell
Set-Location C:\CodeJet\stellar_V2
git status --short
git fetch origin
```

If `git status --short` prints changes, preserve that work before continuing.
Do not discard or overwrite it. Then create a local review branch and apply:

```powershell
git switch -c feature/demo-visit-analytics-20261112
if ($LASTEXITCODE -ne 0) { throw "Could not create review branch." }

$patchPath = "C:\Users\<your-user>\Downloads\CodeJet_Demo_Analytics\CodeJet_Demo_Analytics.patch"
git apply --check $patchPath
if ($LASTEXITCODE -ne 0) { throw "Patch does not apply cleanly. Stop and review the differences." }
git apply $patchPath
if ($LASTEXITCODE -ne 0) { throw "Patch application failed." }
git diff --stat
git status --short
```

Replace `$patchPath` with the actual extracted file path. If the branch name already
exists, inspect it before choosing another name. The patch was built against the base
commit listed above; `git apply --check` protects against incompatible local versions.
Review and test, then commit/push through your own GitHub access and merge into the
branch Render actually deploys (the repository default is `main`).
Keep tracking disabled while configuring storage and the Front Door rule.

Validation:

```powershell
python -m unittest discover -s tests -v
node --test tests/test_analytics_client.js
```

Node is only a test tool. Render still starts the app with `gunicorn server:app`.

## 2. Attach a persistent Render disk

In the existing `stellar_V2` Render web service, attach a persistent disk at:

```text
/var/data
```

The database path is:

```text
/var/data/codejet-demo-analytics.sqlite3
```

**The directory must actually be a Render persistent disk. Setting an environment
variable or creating a folder does not make it persistent.** Render's ordinary
filesystem is erased on redeploy/restart.

A disk requires a paid service and has a hosting cost. It limits the service to one
instance and prevents zero-downtime deployments. This implementation suits a small,
single-instance mailer campaign. For multiple service instances or zero-downtime
deploys, move analytics storage to a managed database first. Multiple Gunicorn
workers on this one service are supported with SQLite WAL and a busy timeout.

Do not put the database in `static`, commit it, or use the ordinary app directory
for production data. Initialization runs at runtime, after the disk is mounted.

## 3. Generate two different secrets locally

```powershell
py -c "import secrets; print('CJ_ANALYTICS_ADMIN_TOKEN=' + secrets.token_urlsafe(32)); print('CJ_ANALYTICS_ORIGIN_KEY=' + secrets.token_urlsafe(32))"
```

Keep these in your password manager and service configuration:

- `CJ_ANALYTICS_ADMIN_TOKEN` is the private report password and signs temporary
  visit tokens. Rotating it also invalidates current visit tokens.
- `CJ_ANALYTICS_ORIGIN_KEY` authenticates requests forwarded by Front Door.
  It is separate from the report password and never appears in browser code.

Use freshly generated values, not placeholders. Keep secrets out of source
control, QR codes, URLs, screenshots, and support logs.

## 4. Configure the existing Front Door marketing route

In the existing `codejet-frontdoor` profile, associate a rule set with the marketing
route that forwards to `stellar-v2.onrender.com`:

1. Match **URL path begins with `/_cj/`**.
2. Add **Modify request header**: name `X-CodeJet-Origin-Key`, action **Overwrite**,
   value equal to your generated `CJ_ANALYTICS_ORIGIN_KEY`.
3. Disable caching for `/_cj/*`, preserving the existing origin group and
   HTTPS-only forwarding. The app also sends `Cache-Control: private, no-store`.
4. Associate the rule set with that route and allow it to propagate.
5. Copy the profile's **Front Door ID**, a GUID, for the Render variable below.
   This is not the endpoint hostname or subscription ID.

Use a **request** header, never a response header. Use **Overwrite**, not Append.
Never return the origin secret to visitors.

The collector lives at `/_cj/analytics/...`, outside the existing `/api` protection.
Do not remove `/api` or `/ai` WAF protections for this feature. If WAF blocks a
legitimate analytics request, inspect that specific rule.

Render's origin remains public. `X-Azure-FDID` alone cannot authenticate it because
a direct caller could supply that header. This module requires both the origin
secret and expected FDID before accepting `X-Azure-SocketIP`. It ignores arbitrary
`X-Forwarded-For`, `X-Azure-ClientIP`, and browser-supplied JSON IP values.
This protects the analytics routes; it does not make the entire Render origin private.

## 5. Set Render variables and deploy the reviewed code

Preserve all existing SMTP/contact-form settings. Add:

```dotenv
CJ_ANALYTICS_ENABLED=1
CJ_ANALYTICS_DB_PATH=/var/data/codejet-demo-analytics.sqlite3
CJ_ANALYTICS_ADMIN_TOKEN=<your-first-random-secret>
CJ_ANALYTICS_ORIGIN_KEY=<your-second-random-secret>
CJ_ANALYTICS_FRONTDOOR_ID=<your-front-door-profile-guid>
CJ_ANALYTICS_ALLOWED_ORIGINS=https://codejet.app,https://www.codejet.app
CJ_ANALYTICS_IP_MODE=frontdoor
CJ_ANALYTICS_LOCAL_DEV=0
CJ_ANALYTICS_RETENTION_DAYS=30
```

Deploy the reviewed commit through the existing Render workflow. No reCAPTCHA,
SMTP, DNS, video URL, or video-hosting changes are required. A tracking or storage
failure returns an analytics error; it does not prevent the video or contact form
from working.

The homepage and demo include a small `/demo-privacy` link when tracking is enabled.
Review that disclosure with the change. It describes this tracker, not a complete
website privacy policy.

## 6. Open the private report

```text
https://codejet.app/_cj/analytics
```

Your browser prompts for:

```text
Username: codejet
Password: your CJ_ANALYTICS_ADMIN_TOKEN value
```

Use HTTPS. A private browser window avoids retaining Basic-auth credentials in your
usual browser session; close the window afterward.

Use the 7-day/30-day links and **Download CSV** button. Direct CSV:

```text
https://codejet.app/_cj/analytics/report.csv?days=30
```

Programmatic clients can send `Authorization: Bearer <admin token>`. Do not put the
token in a query string. Campaign strings are escaped against spreadsheet formula
execution. The HTML table shows at most 500 sessions; CSV/summary include at most
10,000. Shorten the date window if needed. All data is limited to retention.
Per-event IPs are stored in the protected database; the session report displays
the first and latest.

## 7. Verify with your own phone

1. Check `/health` returns `ok`.
2. Open the homepage and demo on cellular data, then start playback.
3. Pause partway through. Check the report for your session/IP and playback coverage.
4. Resume to the end and confirm the existing contact-section redirect.
5. In a fresh tab, seek near the end: the report should show **End reached** with
   only actual reported coverage, not an invented 100% watched.
6. Confirm a logged-out report request is rejected.
7. Confirm direct `https://stellar-v2.onrender.com/_cj/analytics` is rejected.
8. After a later controlled redeploy, confirm the test row survives. This validates
   the deployed persistent-disk setup.

Test visits are real records, recognizable by time/IP. No test visits are added
automatically. GPC/DNT intentionally suppress tracking; blockers or network failures
can also prevent events.

| Status | What to check |
| --- | --- |
| 401 on report | Username/password or Bearer token |
| 401 on collection | Expired token; browser renews once |
| 403 | Front Door header rule, secret/FDID, allowed Origin |
| 404 | Disabled tracker, missing deployment, or wrong path |
| 429 | 120 accepted tracking writes per observed IP/minute; wait a minute |
| 503 | Disk mount/permissions or missing/invalid tracker configuration |

A privacy opt-out may return 204 without a token. A valid event also returns 204.
Never dump configured secrets or all request headers for troubleshooting.

## Your already-printed QR code

If the QR points to the homepage or `/demo`, it keeps working unchanged. Recording
starts after deployment; this code cannot reconstruct earlier video plays.

Without a unique campaign marker in that printed link, visits are **unattributed**.
Do not count every new visitor as a mailer response. For future mailers:

```text
https://codejet.app/demo?utm_source=direct_mail&utm_medium=qr&utm_campaign=retail_nov_2026
```

The same UTM fields work on the homepage and carry into the demo in that valid tab
session. Avoid recipient names/emails in URLs. This change does not try to identify
individual recipients from IP addresses.

## Retention and rollback

Old events and visits are pruned during collection or private report access.
Visit metadata has an absolute age limit as well as an inactivity limit, so
continued activity does not retain its original IP indefinitely. To prune manually
in the Render service's runtime Shell:

```bash
python -m flask --app server analytics-prune
```

No scheduled job is included. Without traffic or report access, run that command
to remove aged records. CSV exports and hosting backups are separate copies with
separate retention.

To disable, set `CJ_ANALYTICS_ENABLED=0` and redeploy. The collector/report return
404 and new pages omit the script. The database remains: disabling is not deletion.
Export anything needed before disabling.

## Local development only

```dotenv
CJ_ANALYTICS_ENABLED=1
CJ_ANALYTICS_IP_MODE=direct
CJ_ANALYTICS_LOCAL_DEV=1
CJ_ANALYTICS_ALLOWED_ORIGINS=http://127.0.0.1:5000
CJ_ANALYTICS_DB_PATH=<absolute-local-path-outside-static>
CJ_ANALYTICS_ADMIN_TOKEN=<random-secret-at-least-32-characters>
```

Direct mode only accepts loopback. Never use it behind Render or another proxy.

## Primary technical references

- [Cloudflare player API](https://developers.cloudflare.com/stream/viewing-videos/using-the-stream-player/using-the-player-api/)
- [Front Door socket/client IP headers](https://learn.microsoft.com/en-us/azure/frontdoor/front-door-http-headers-protocol)
- [Front Door request-header and caching actions](https://learn.microsoft.com/en-us/azure/frontdoor/front-door-rules-engine-actions)
- [Render disk persistence and operational limits](https://render.com/docs/disks)
