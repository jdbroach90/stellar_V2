## Why

CodeJet needs a clear route from searches for retail analytics software to its video and a relevant AI partnership conversation. The existing demo page offers little searchable context, and traffic counts alone do not distinguish viewing engagement from automated requests.

## Changes

- Add three distinct server-rendered pages for retail analytics software, reporting automation, and specific retail data questions.
- Reframe the homepage around retail analytics and connect the new pages through internal links.
- Build a responsive, descriptive watch page around the existing Cloudflare recording, with an explicit partnership action and replay after playback ends.
- Add fixed canonicals, social metadata, honest JSON-LD, robots and sitemap routes, with video-specific metadata gated on verified original publication information.
- Preserve UTM attribution into the demo and extend the existing page allowlist without changing analytics authorization, privacy controls, storage or video-event restrictions.
- Handle the existing Front Door origin hostname when selecting public indexing metadata; this is separate from authentication.
- Include paused Google assets, clearly labeled ChatGPT setup references, creative, source validators, an offline aggregate traffic tool and launch instructions.

## Validation

- 52 Python website/analytics/contact tests passed locally.
- 23 JavaScript tracker tests passed.
- 14 offline summary tests passed with synthetic data.
- Generated campaign files matched their editable source and passed limits/status/UTM checks.
- Local public release checker passed, with an expected warning because optional VideoObject is not enabled yet.
- Desktop and 390-pixel layouts were inspected. The demo CTA preserved UTMs, and the Cloudflare video played.

## Release notes

The PR targets **master**, the identified Render production branch. Merging can trigger deployment. Keep existing SMTP, reCAPTCHA, analytics secrets, the persistent database/disk and WAF protections.

The owner must provide the real original video publication timestamp before enabling optional VideoObject. Search Console verification and current ad-account setup are separate launch steps. No ad campaign was activated, money spent, conversion pixel installed, or contact email sent by this change.

After deployment, run `python scripts/check_search.py --base-url https://codejet.app` and follow `growth/docs/LAUNCH_GUIDE.md`.
