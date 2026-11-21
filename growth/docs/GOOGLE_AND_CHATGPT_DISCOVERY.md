# CodeJet: Google and ChatGPT discovery

Prepared November 20, 2026. Official sources reviewed on that date. This is the technical companion to the landing pages, content, and campaign assets in this repository.

## The outcome this project is built for

Give retail teams a useful answer to a real software question, then make the CodeJet demo the obvious next action. The primary category is **retail analytics software**; **retail intelligence platform** explains the product. AI is the mechanism, not the entire search strategy.

The product statement to keep consistent is: **CodeJet helps retail teams ask questions of their existing reporting infrastructure, using the business definitions and rules they already rely on.** Review all capability statements against what the current demo actually shows. Do not add customer names, savings estimates, integrations, security certifications, pricing, or case studies without evidence.

### Page responsibilities

| Canonical URL | Searcher's likely question | Page's job | Next action |
| --- | --- | --- | --- |
| `https://codejet.app/retail-analytics-software` | Is this suitable analytics software for a retail team? | Explain fit, the reporting foundation, representative business questions, and the adoption conversation. | Watch the demo. |
| `https://codejet.app/retail-reporting-automation` | How can we answer recurring questions without repeatedly assembling reports? | Explain the workflow and the role of existing reports and definitions. | Watch the demo. |
| `https://codejet.app/retail-data-questions` | What specific questions could my retail team ask? | Give meaningful examples and identify the information each needs. Examples are possibilities, not claims about a visitor's private performance. | Watch the demo. |
| `https://codejet.app/demo` | What does CodeJet actually do? | Let the visitor watch the existing video immediately, with a factual explanation of what it demonstrates. | Discuss an AI partnership. |
| `https://codejet.app/` | Who is CodeJet? | Establish identity and connect the public product pages. | Explore the product or watch the demo. |

Keep these pages distinct. Do not create dozens of near-identical location, industry, or keyword pages that all say the same thing. Add a future page when it answers a different buying question with enough substance to deserve its own URL.

### Keyword-to-page map

These are intent hypotheses to validate, not measured search-volume or price estimates. Use readable variations in context; do not repeat every phrase mechanically.

| Cluster | Representative queries | Primary page |
| --- | --- | --- |
| Product category | retail analytics software; retail intelligence platform; retail business intelligence software | `/retail-analytics-software` |
| Reporting workflow | retail reporting automation; automate retail reports; reduce manual retail reporting | `/retail-reporting-automation` |
| Questions and evaluation | questions to ask retail data; natural-language retail analytics; retail sales margin shrink analysis | `/retail-data-questions` |
| Branded product evidence | CodeJet demo; CodeJet retail analytics video; CodeJet platform demonstration | `/demo` |

Lead with the category buyer's language. Broad “AI tools” traffic may include many unrelated needs; these pages aim at people responsible for retail reporting and decisions. Search Console and the paid search-term report will tell the owner which actual phrasing merits more attention.

## Google organic search

The implementation should serve the important copy in HTML, provide descriptive titles and canonical URLs, connect the pages with normal links, and list only public canonical pages in `/sitemap.xml`. A sitemap is a discovery aid. It does not purchase indexing or ranking. Use accurate significant-change dates if adding `lastmod`; do not stamp every URL with today's date on every request. [Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)

The practical distinction between two jobs matters:

- **A page can be found:** Google can access it and understand what it says.
- **A page earns visits:** its subject and evidence are useful enough to appear for searches a suitable buyer makes.

Publishing resolves the first job only in part. The owner still needs to verify Search Console, inspect the deployed pages, and improve content based on observed queries. Those exact steps are in [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md).

### Google AI Overviews and AI Mode

Google says its normal SEO practices apply. Supporting pages need to be indexed and eligible for snippets. No special AI text file or special schema is required. Content shown in these experiences is included in Search Console's Web performance reporting; meeting eligibility requirements does not guarantee inclusion. [Google AI features guidance](https://developers.google.com/search/docs/appearance/ai-features)

For CodeJet, this means publishing clear explanations of the product, showing representative questions, and distinguishing established capability from what a partnership would configure. An `llms.txt` file is not a prerequisite for this campaign. It is not a substitute for readable pages or legitimate references from elsewhere on the web.

## Make `/demo` a real watch page

Keep the video prominent and playable without a lead form. Google's video guidance calls for a dedicated watch page whose primary purpose is watching that video, an indexable page, and a stable, accessible thumbnail. Embedding the same video on a product page is permissible, but the product page is not automatically a watch page. An indexed page does not guarantee that its video will be indexed. [Google video guidance](https://developers.google.com/search/docs/appearance/video)

For this release, keep `/demo` as the canonical watch page and retain the existing Cloudflare Stream player:

```text
https://customer-0k2chsytrbkmpgjr.cloudflarestream.com/38ccab99e8156adae4abcfbb1d36cc0f/iframe
```

### Real video metadata is an owner-supplied prerequisite

Google's required `VideoObject` properties are `name`, `thumbnailUrl`, and `uploadDate`. The upload date is when the video was first published, not this website release date. Supply it in ISO 8601 with a timezone. `description`, `duration`, and player/media URLs are additional useful properties. `embedUrl` identifies the player; `contentUrl`, if supplied, must identify the actual video bytes. Neither the watch page nor iframe is a `contentUrl`. [Google VideoObject reference](https://developers.google.com/search/docs/appearance/structured-data/video)

Before enabling video-specific markup:

1. Look up the original publication date in the source video records. Do not infer it from the mailer date or today's deployment.
2. Open the thumbnail URL without signing in. Verify that it is a real frame for this video, returns an image successfully, and is allowed by the hosting account's restrictions.
3. Check the duration against the player or original file before adding it.
4. Use the configuration documented in the repository's `.env.example`; leave unknown optional values unset. Required values must be real before video markup is enabled.
5. Run Google's [Rich Results Test](https://search.google.com/test/rich-results) against the deployed watch page. Then use Search Console URL Inspection to check the rendered video and thumbnail.

The readable watch page can launch before every video enhancement is configured. Do not ship guessed metadata to make a validation warning disappear. A transcript may be added after someone transcribes and checks the actual recording. A marketing summary must be labeled as a summary, not presented as a transcript or timed chapter list.

## ChatGPT organic discovery

There are separate OpenAI agents for separate purposes:

| Agent | Purpose | CodeJet access decision |
| --- | --- | --- |
| `OAI-SearchBot` | Discovers material for ChatGPT search results. | Allow public product pages, the watch page, and necessary public assets. |
| `GPTBot` | Crawls material that may be used for model training. | This release disallows training crawling. It is a separate content-use choice; training access is not required to allow search access. |
| `OAI-AdsBot` | Validates pages submitted as ChatGPT ad destinations. | Allow submitted public landing pages and their required public resources when using ads. |
| `ChatGPT-User` | Fetches for certain user-initiated actions; it is not the automatic search crawler. | Keep public pages usable. Do not treat its presence or robots behavior as search inclusion. |

Use OpenAI's current agent documentation and published address lists, not a permanent list of IPs copied from a few recent visits. Robots controls for search and training are independent. [OpenAI crawler documentation](https://developers.openai.com/api/docs/bots)

Current authoritative IP-list locations:

- Search: <https://openai.com/searchbot.json>
- Ads: <https://openai.com/adsbot.json>
- User-initiated fetches: <https://openai.com/chatgpt-user.json>
- Training, only if the owner elects to allow it: <https://openai.com/gptbot.json>

These are inputs for validating a crawler identity, not instructions to bypass every website control. Review them when configuring access and when investigating a genuine access problem.

The same public pages supply the factual material a search answer might cite. State the company identity consistently, answer the buying question directly, and make limitations clear. Seek legitimate mentions from partners or publications that have actually evaluated the product. Do not buy automated backlinks or publish invented reviews. Access and useful content improve the opportunity to be discovered; they do not guarantee a recommendation, citation, or a particular answer.

## Azure Front Door: public discovery, protected application

**Preserve the existing `/ai` IP restriction and the `/_cj/analytics` report protections.** Search and advertising crawlers do not need application access, visitor data, report credentials, SMTP credentials, or a bypass around the private analytics origin check.

Inspect the existing policy before adding any exception. Azure custom rules evaluate lower numerical priorities first; actions other than Log stop evaluation. An overbroad Allow can therefore bypass later controls. Prefer fixing the specific false positive. If a crawler exception is necessary, constrain it to the relevant public host, public paths/resources, suitable methods, and validated crawler source. [Microsoft custom-rule documentation](https://learn.microsoft.com/en-us/azure/web-application-firewall/afds/waf-front-door-custom-rules)

Use this access boundary when reviewing the policy:

| Resource | Expected visitor behavior | Crawler change permitted by this project |
| --- | --- | --- |
| Homepage, three search pages, `/demo` | Public GET/HEAD | Make accessible without a login or JavaScript challenge that prevents reading. |
| `/robots.txt`, `/sitemap.xml`, public CSS/JS/images | Public GET/HEAD | Allow retrieval needed to discover and render public content. |
| Cloudflare Stream iframe, thumbnail, media | Public video hosting according to existing account settings | Check that video-host rules do not block required retrieval. |
| `/ai` and protected application/API paths | Existing restricted policy | None. |
| `/_cj/analytics` and report download | Existing authentication and origin checks | None. |
| `/_cj/analytics/visit` and `/event` | Existing validated browser collection | Preserve origin/FDID/token checks, rate limits, and no-store behavior. No crawler Allow exception is needed. |
| Contact-form POST | Existing validation, reCAPTCHA, SMTP | None. Do not allow bots to bypass submission protection. |

Do not identify a trusted bot by User-Agent alone: anyone can send that header. Google documents source validation using its published ranges or a reverse lookup followed by a matching forward lookup. [Google request verification](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests)

Robots rules guide cooperating crawlers; they are not authentication. Similarly, `noindex` is a publishing directive, not a substitute for access control.

### Additional requirement if running ChatGPT ads

OpenAI requires `OAI-AdsBot` for ad landing-page validation and recommends `OAI-SearchBot` too. Check each host in the redirect chain and hosts serving required assets. A permissive robots rule alone does not fix a CDN/WAF rejection. Validate identity through the provider's published information and relevant infrastructure signals. [OpenAI advertiser crawler guidance](https://help.openai.com/en/articles/20001243-advertiser-guidance-for-allowing-openai-web-crawlers)

This is an ad-review requirement, not a paid route into organic answers. The campaign assets are drafts; ad account setup, spend, verification, and activation are separate owner actions.

## What this release deliberately leaves to real evidence

- Actual keyword volume, competition, and click prices require account/tool data; none is fabricated here.
- Video upload date, verified duration, transcript, and chapter timestamps require the actual video record.
- Search Console verification requires the token issued to the owner's account.
- Public partner/customer claims require the customer's permission and a factual record.
- Rankings, search indexing, rich results, and AI recommendations remain outside CodeJet's control.

For release steps, use [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md). For what to count after launch, use [MEASUREMENT.md](MEASUREMENT.md).
