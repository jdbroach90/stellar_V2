# CodeJet marketing site: Render behind Azure Front Door

This plan fronts the Flask marketing/contact site only, **not** the future CodeJet Platform API.

## Before touching DNS

1. In Render, ensure the `stellar_V2` web service has the environment variables `RECAPTCHA_SECRET_KEY`, `cj_email`, and `cj_password` with their existing live values. Do not commit `.env`. An email test succeeding confirms the mail path, but `/health` is independent of SMTP.
2. Deploy the `server.py` and `templates/email_failure.html` changes. Verify `https://<exact-service>.onrender.com/health` replies HTTP **200** and `ok` to GET and HEAD.
3. In Render's service **Settings > Health Checks**, use path `/health` if configuring an HTTP health check. Keep the Render `onrender.com` hostname enabled for Front Door's origin.

## Azure Front Door Standard/Premium

1. Create an Azure Front Door **Standard or Premium** profile and endpoint. Choose **Premium** if you want Microsoft-managed WAF rule sets or plan to add future Azure private-link origins; **Standard** is enough for a basic public Render site with custom WAF rules. Do **not** create Front Door (classic).
2. Create origin group `codejet-site-og`, with **Custom** origin `codejet-render` and **origin hostname** set to the EXACT host from the Render web service's `*.onrender.com` URL (no scheme/path). Set **Origin host header** to the SAME `*.onrender.com` hostname. Use HTTPS port 443 and enabled origin. Keep the origin public; Render doesn't support Azure Front Door Premium Private Link as a private origin.
3. Origin group health probe: **HTTPS**; **HEAD**; path `/health`; e.g. 60 seconds interval. Front Door requires HTTP **200** for health. `GET /health` also returns 200.
4. Create route `codejet-site-route`: match `/*`, connect it to `codejet-site-og`; enable HTTPS redirect; forward to origin using **HTTPS only**; enable link to default `*.azurefd.net` endpoint; **do not cache** the dynamic Flask site or `/send_email` POST. Keep compression optional.
5. First test `https://<your-endpoint>.azurefd.net/`, `/demo`, `/health` **before DNS cutover**. Do not submit the form using the Azure-managed domain; Google reCAPTCHA may not recognize that hostname.
6. Add `www.codejet.app` as a custom Front Door domain, verify via Azure-provided `_dnsauth` TXT record, associate the domain with the route, and enable managed HTTPS certificate. Change the `www` CNAME to the EXACT Front Door endpoint only after tests and certificate readiness.
7. `codejet.app` is a DNS zone apex. Use Azure DNS alias record or a third-party provider's supported CNAME flattening / ALIAS / ANAME capability to point the apex at the Front Door endpoint; do not add an ordinary apex CNAME. Validate apex via its Azure-provided TXT record and associate it with the route. Verify `https://codejet.app/health`, homepage, demo, and one real contact submission.
8. Attach a WAF policy/security policy to both custom domains. **Standard supports custom rules only**; **Premium also supports Microsoft-managed rule sets**. Start the policy in **Detection** mode, review false positives, then switch to **Prevention** after validating legitimate traffic. Consider a rate-limit custom rule for the contact endpoint after testing.

## Important limitations / security

- Azure Front Door does **not** make Render's public `onrender.com` endpoint private. Anybody knowing that URL may bypass Front Door WAF until separately restricted by an origin-level control. Do not disable the Render subdomain while using it as an origin.
- Do not change nameservers, erase MX/TXT email DNS records, or replace existing root DNS until the Front Door endpoint, domain validation, and certificates are ready.
- Old credentials accidentally committed to Git history should be rotated. Removing `.env` from the present branch does not erase past exposures.
- The `/health` probe tests Flask availability only; it intentionally makes no outbound SMTP/Google calls, so a temporary email provider failure doesn't mark the entire site unhealthy.

## Smoke tests (PowerShell)

```powershell
$origin = 'https://<your-exact-service>.onrender.com'
(Invoke-WebRequest "$origin/health").StatusCode
(Invoke-WebRequest "$origin/health" -Method Head).StatusCode

$frontdoor = 'https://<your-endpoint>.azurefd.net'
(Invoke-WebRequest "$frontdoor/health").StatusCode
(Invoke-WebRequest "$frontdoor/demo").StatusCode

(Invoke-WebRequest 'https://codejet.app/health').StatusCode
```
