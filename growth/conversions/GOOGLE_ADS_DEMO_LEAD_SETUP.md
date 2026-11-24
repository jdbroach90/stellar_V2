# CodeJet — Google Ads conversion only after deliberate demo engagement + inquiry

## What the website now does

1. An actual click on the **large Play button** requests a short-lived first-party watch token. Page loading, autoplay, and emailed-link scans cannot obtain this through normal page behavior.
2. The Cloudflare Stream player reports `played` time ranges. Skipping forward does **not** count the skipped section. Only after **at least 50% unique playable coverage** and at least **25 seconds elapsed since the click** will the browser request a qualification token from the website.
3. A qualified token is **signed server-side**, tied to a short-lived HttpOnly first-party session cookie, and expires after 30 minutes. It contains a random per-watch identifier, not visitor contact details.
4. The form works even without a video watch. After a valid reCAPTCHA and successful **SMTP acceptance**, the website returns a confirmation page.
5. Confirmation emits `codejet_inquiry_accepted` for **any** accepted inquiry, but additionally emits **`codejet_demo_engaged_lead` ONLY** if the visitor watched and successfully submitted. That event includes a non-identifying `transaction_id` for conversion deduplication.
6. A rejected reCAPTCHA, invalid form, failed SMTP send, page view, click, seek to the end, or short playback **must not** emit `codejet_demo_engaged_lead`.

**Limits:** These checks substantially reduce accidental or automated conversions, but client-reported playback cannot prove human attention and sophisticated automation can simulate interactions. Google Ads invalid-click filters, reCAPTCHA, lead review, and measured business results are still important.

## Production configuration

This patch leaves the existing Google Tag Manager code `GTM-TQ6SDXNL` and all SMTP credentials alone.

- Preferred: in **Render → website service → Environment**, add `CJ_DEMO_ENGAGEMENT_SECRET` with a strong 32+ character random value, e.g. generate locally with `py -3 -c "import secrets; print(secrets.token_urlsafe(48))"`. Copy the secret into Render, **not into GitHub or this chat**. Your user-facing form and Google tag still work if you omit it, provided the existing **32+ character `CJ_ANALYTICS_ORIGIN_KEY`** from the working first-party analytics setup is still configured. The fallback key is cryptographically domain-separated.
- If neither secret exists, the ordinary form **still works**, but the stricter qualified event intentionally fails closed. The server logs a configuration warning on a watch-start request.
- Keep existing `cj_email`, `cj_password`, `RECAPTCHA_SECRET_KEY`, and `CJ_CONTACT_RECIPIENT` intact. If `sales@codejet.app` does not forward to your inbox, retain `CJ_CONTACT_RECIPIENT=jbroach@codejet.app` internally. The public website may still display `sales@codejet.app`.
- `CJ_GOOGLE_TAG_ENABLED=0` is an emergency off switch for the public Google tag if measurement needs to be halted.

## Create one manual Ads conversion — do not use page views

**Do not start the Search pilot yet.** In the new Google Ads account, create a **manual Website conversion action** for a submitted lead, ideally titled `CodeJet — Demo Watched 50% + Inquiry`.

- Category: **Submit lead form**.
- Count: **One**.
- Initially **Secondary** (or a separate campaign-specific goal) while testing; **Primary** only after reliable verification.
- Do not use **Page views**, the old `#contact` URL, or automatic form detection as the primary lead conversion. Inspect any existing `Submit lead form (Website)` conversion to ensure it is not matching every submit or success URL by itself.
- Obtain the **Conversion ID** (`AW-` plus digits) and **Conversion Label** from Google Ads → Goals → Conversions → conversion action → Tag setup → Use Google Tag Manager.

### Configure the GTM container

Open <https://tagmanager.google.com/> and select container **`GTM-TQ6SDXNL`** (or the actual container that Tag Assistant reports on codejet.app).

1. **Triggers → New → Custom Event**. Name `CodeJet — Qualified Demo Lead`, set event name **`codejet_demo_engaged_lead`**, and fire on **All Custom Events** (an exact name, no regex wildcard).
2. **Variables → New → Data Layer Variable**. Name `CodeJet Transaction ID`; data layer variable name: **`transaction_id`**; Data Layer Version 2.
3. **Tags → New → Google Ads Conversion Tracking**. Supply the new manual Conversion ID and Conversion Label. Set the **Transaction ID** field to `{{CodeJet Transaction ID}}`. Assign only the `CodeJet — Qualified Demo Lead` trigger.
4. Set up a **Conversion Linker** tag on all public pages if GTM doesn't already have one. Check it is not duplicated.
5. **Preview** the container. Then publish the GTM workspace only after both positive and negative tests below pass.

If the supplied Google Ads tag ID can't be opened in Tag Manager, do **not** guess a conversion label. Retrieve the Google Ads Conversion ID and Label and configure an alternative direct-event integration separately; installing another tag at random could double-count leads.

## Verification before enabling Google Ads

In a fresh browser session on `https://codejet.app/demo`:

**Negative case:** Without watching the demo, submit a test inquiry. Gmail should accept it. In Tag Assistant the page should show `codejet_inquiry_accepted`, **not** `codejet_demo_engaged_lead`, and the Google Ads conversion tag should not fire.

**Positive case:** Return to `/demo` in a new browser session. **Click the large Play button**, let at least half the video *actually play* (for an ~81-second demo, over 40.5 seconds of distinct playback), then submit a test inquiry. The confirmation should emit `codejet_demo_engaged_lead` once with a non-PII `transaction_id`. The Google Ads conversion tag should fire **once**.

**Seek test:** Click Play and drag directly to the end. Submit the inquiry: **no** `codejet_demo_engaged_lead`.

**Failure case:** Form errors, blocked reCAPTCHA or failed SMTP should never emit an Ads lead event.

**Refresh test:** If someone reloads a successful POST response, the `transaction_id` remains derived from the same watch token. Configure this field in the Ads conversion tag for deduplication. This does not prevent duplicate inquiry emails; avoid duplicate manual submits during testing.

A successful *Gmail SMTP acceptance* is not a guarantee the email arrived in your inbox; verify the actual lead delivery too. Google Ads also needs time to record conversions, which aren't necessarily visible immediately.

## Audience and reporting

Canada can be added in Google Ads Editor alongside the U.S. under **Locations**, ideally with **Presence** targeting. Monitor the two countries separately. If the test budget is small, consider separate tests rather than spreading clicks across too many audiences. Advertising measurement and consent requirements vary by jurisdiction; review them before activating Canadian traffic.

For the first campaign, keep **Search only**, **search partners off**, **Display off**, **AI Max off**, six exact-match keywords, and paused ads until your measured lead funnel passes the tests. Google's recorded ads clicks are not equivalent to verified people, and video coverage alone is not a conversion.

## Official references

- Google Tag Manager: <https://support.google.com/tagmanager/answer/7679219> (Custom Event trigger)
- Google Ads conversion tag: <https://support.google.com/tagmanager/answer/6105160> (Conversion ID, label, and transaction ID)
- Cloudflare Stream player API: <https://developers.cloudflare.com/stream/viewing-videos/using-the-stream-player/using-the-player-api/> (`played` TimeRanges and events)
