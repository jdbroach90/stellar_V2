# CodeJet search content

Prepared November 20, 2026 (America/New_York).

## Purpose and page ownership

`pages.json` is the editable content source for three public, server-rendered pages. Each has one buyer intent and points to `/demo` as its primary next step. These pages belong on the existing `https://codejet.app` domain. Publishing duplicate copies on GitHub Pages or another domain would split the content and require a separate canonical strategy.

| Route | Reader's need | Main job of the page |
| --- | --- | --- |
| `/retail-analytics-software` | Evaluate a retail analytics product | Define CodeJet, explain fit, and offer a video and a scoped partnership conversation. |
| `/retail-reporting-automation` | Reduce recurring reporting work | Show how to select and evaluate a useful workflow before expanding it. |
| `/retail-data-questions` | Ask more useful questions of retail data | Give specific examples and explain metric, scope, period, comparison, and evidence. |

The commercial page owns the main product phrase. The guides answer narrower questions and link back to it. This is an editorial choice, not a claim that a particular keyword will rank or convert.

## JSON rendering contract

The root object has `version`, `canonical_origin`, `primary_cta`, and `pages`.

Each page has `slug` without a leading slash; `title`; `description`; `eyebrow`; `h1`; `lead`; `sections`; `questions_heading`; `questions_intro`; `questions`; `faqs`; `related_links`; and primary/secondary CTA objects. Every CTA/link object uses `label` and `href`. Sections use `heading`, `paragraphs`, and optional `bullets`. FAQs use `question` and `answer`.

Render all substantive text as ordinary HTML. Render the `questions_intro` visibly so examples are not mistaken for customer results, confirmed product integrations, or questions demonstrated in the current video. Put the primary CTA near the lead and again after the content. Secondary CTAs use the existing `/#contact` form. Do not hide the answer text behind a lead form.

The content deliberately avoids video duration, a fabricated transcript, customer names or logos, financial savings, pricing, a free trial, benchmark performance, and guaranteed integration. A future case study should be a separate evidence-backed addition, with customer permission and a clear measurement basis.

## Product claim basis

The user-provided campaign context and the current [CodeJet homepage](https://codejet.app/) describe existing reports, queries, business definitions, approved data, controlled retrieval, role-aware access, and summary/table/chart/PowerPoint/PDF outputs. These are product descriptions, not independently audited performance claims. The draft frames implementation around an agreed question, source access, definitions, validation, and scope. It does not promise compatibility with a named system or a zero-effort deployment.

The existing site's sample result is not treated as a customer case study. The new questions are original examples, with no real retailer's private data or performance assertions.

## Google organic search and AI discovery

Google says ordinary SEO practices apply to AI Overviews and AI Mode. Pages need to be indexed and eligible to show a snippet; special AI text files and special schema are not required. Useful text, crawlable internal links, and structured data that agrees with visible content are the practical foundations. Eligibility does not guarantee indexing or inclusion. [Source: Google Search Central, AI features and your website](https://developers.google.com/search/docs/appearance/ai-features).

Implementation implications: give each page its own title, description, canonical URL, H1, and links from the site. Keep the substantive text in the HTML response. Publish distinct helpful content and validate the rendered pages in Search Console. Do not create many near-identical industry or city pages, or present `llms.txt` as a requirement for ranking.

## The video destination

Google's video guidance calls for an indexable watch page, a prominent embedded video, and a valid thumbnail at a stable URL. The watch page being indexed does not by itself ensure the video is indexed. Google can discover ordinary iframes, and video discovery should not depend on an interaction that inserts the player. Metadata should accurately describe the actual video. [Source: Google Search Central, Video SEO best practices](https://developers.google.com/search/docs/appearance/video).

Implementation implications: retain `/demo` as the dedicated watch page. Keep its player prominent and preserve existing analytics. Add truthful introductory text, a clear next action, and confirmed video metadata. Obtain the real upload date, duration, and transcript before adding those fields or publishing a transcript. The content pack does not assert that the video answers every example question.

## ChatGPT search discovery

OpenAI distinguishes `OAI-SearchBot` for search from `GPTBot` for potential training use. Those controls are independent. Its crawler documentation recommends allowing `OAI-SearchBot` and its published IP ranges when seeking search visibility. `ChatGPT-User` serves user-initiated access and is not the control for search inclusion. [Source: OpenAI, Overview of OpenAI Crawlers](https://developers.openai.com/api/docs/bots).

Implementation implications: make the same public product and guide pages accessible to search crawlers through both robots rules and the actual CDN/WAF. Maintain existing protection for private/admin endpoints. Evaluate training preferences separately; do not weaken authentication or `/ai` access rules for discoverability. Clear factual pages give search systems something useful to retrieve, but do not guarantee a citation, recommendation, or visit. No paid placement or automated ChatGPT submission is created by these content files.

## Content maintenance

Use real prospect language and Search Console queries to decide what deserves a new page. Expand only when the new material answers a distinct question. Add verified implementation details, a truthful demo transcript, or an approved case study when those become available. Recheck product descriptions whenever capabilities change. Keep a human review step for metric definitions and claims before publication.

For evaluation, distinguish a landing-page request, an intentional video play, sustained viewing, and a qualified inquiry. Link scanners and previews can make traffic counts misleading; content quality should be judged with the full visitor path and sales conversations. Measurement implementation belongs to the site's analytics code, not these copy files.
