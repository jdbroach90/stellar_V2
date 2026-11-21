# Implementation and verification record

Prepared November 20, 2026 for the `feature/retail-search-campaign-20261120` review branch, based on production commit `ffcf5b4e87d0e3c88393b8190e8e59ed89282925`.

## Implemented behavior

- Three substantive server-rendered retail pages and a redesigned watch page use the existing Flask application and Cloudflare video ID.
- The homepage leads with retail analytics and links the new pages into the site.
- Shared metadata uses fixed `https://codejet.app` canonicals, even when campaign parameters or an unrelated Host are supplied.
- Public discovery works through the known Front Door origin-host setup. Expected FDID plus one known forwarded public host controls indexing metadata only. Existing analytics authentication and origin proof remain unchanged.
- UTM links carry only the five known fields; query-bearing public HTML is private/no-store to avoid sharing a visitor's tagged links from a common cache. Existing Front Door cache policy must still honor that behavior.
- The tracker accepts the three new public page paths. Existing video event types, session tokens, data retention, privacy controls, IP-source policy, and protected report behavior are preserved.
- Playback ends on the watch page, with replay and explicit partnership links available, instead of automatically navigating away.
- Real video metadata is optional and gated. Invalid dates or malformed thumbnail configuration omit VideoObject safely. A valid thumbnail override updates the visible poster, preview and social metadata together.
- Google campaign files are generated from one editable JSON source. ChatGPT copy/settings are reference assets because the account's exact bulk template must be obtained in its UI.
- No ad pixel, automatic bid controller, campaign activation, contact-conversion upload, transcript, or invented keyword forecast is included.

## Local verification completed

| Check | Result |
| --- | --- |
| Python website, analytics and contact tests | 52 passed; mail delivery and verification services mocked |
| JavaScript tracker tests | 23 passed |
| Offline traffic-summary tests | 14 passed; synthetic data only |
| Campaign generated-file validation | 10 generated files matched source; copy lengths, status, URL and exclusion checks passed |
| Local public-site release checker | Five HTML pages, robots, sitemap and PNG passed; expected warning for disabled optional VideoObject |
| Required-video-schema negative check | Correctly failed while original upload metadata was absent |
| Source formatting | `git diff --check` passed |
| Browser review | Desktop and 390-pixel embedded viewport layouts inspected; landing CTA opened `/demo` with campaign tags intact; actual Cloudflare playback started and paused |
| Creative | PNG visually inspected; 1200×1200; editable vector source included |

The 89 Python/JavaScript tests run without production credentials. The intentional analytics storage-failure regression can print an ERROR log while the test itself passes; it tests containment of a storage failure.

## Launch checks still required

These local results do not establish that the unpublished branch is live, indexed, cited, accepted by an ad account, or receiving buyers. After review and deployment, run the public URL checker, inspect the player and attribution on the actual public host, verify Search Console ownership, submit the sitemap, and review current ad-account forecasts/settings before activation.

The original recording publication date remains owner-supplied. Add it only after verification, then enable and check VideoObject if desired. No production settings, private analytics records, databases, mail logs, contact lists, or WAF rules were changed by this build.

## Editing and rollback

Edit `growth/content/pages.json` for page copy and `growth/campaigns/campaigns.json` for paid copy/settings. Regenerate paid exports after source edits; the validator detects stale generated files. Re-run the relevant checks when editing templates, routes, attribution, or campaign assets.

Keep deployment in the existing `master` → Render workflow. If a release needs reversal, use a reviewed revert or the existing Render rollback process while preserving the persistent disk and secrets. The read-only tools and creative files can also be used independently of campaign activation.

## GitHub delivery status

The connected GitHub integration rejected branch creation with HTTP403, Resource not accessible by integration. The completed local branch is delivered in a Git bundle with full source and a Windows publishing helper. No remote branch, pull request, remote CI result or production deployment is claimed. The publishing helper uses the owner's existing local Git authentication and refuses a different existing branch rather than force-pushing it. The PowerShell helper was reviewed but was not executed on Windows in this environment.
