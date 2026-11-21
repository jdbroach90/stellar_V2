# Campaign sources and verification

Reviewed **November 20, 2026**, using the project's America/New_York date. Settings and schemas should be checked against the live account at launch. Budgets, keyword choices, reserve order and manual review thresholds are proposals authored for this project, not published market benchmarks.

## Google

| ID | Official source | Applied to this package |
| --- | --- | --- |
| G1 | [Google Ads Editor CSV file columns](https://support.google.com/google-ads/editor/answer/57747?hl=en) | English headers, numbered headline/description fields, status values, daily-budget aliases, update matching |
| G2 | [Import a CSV file](https://support.google.com/google-ads/editor/answer/30564?hl=en) | Import preview and proposed-change review |
| G3 | [Export ads as responsive search ads](https://support.google.com/google-ads/editor/answer/7023600?hl=en) | Documented Responsive search ads > Make multiple changes paste context |
| G4 | [Change keyword match types](https://support.google.com/google-ads/editor/answer/47635?hl=en) | Exact, Phrase, Negative phrase and Negative exact values |
| G5 | [About responsive search ads](https://support.google.com/google-ads/answer/7684791?hl=en) | Asset counts and 30/90/15-character limits; assets can be rearranged |
| G6 | [Campaign total budget FAQs](https://support.google.com/google-ads/answer/15137812?hl=en) | Search campaign-total budgeting for a defined flight; no recurring daily budget substitution |
| G7 | [Google Ads Editor version 2.12](https://support.google.com/google-ads/editor/answer/16924635?hl=en) | Introduction of Search campaign-total support in the Editor interface |
| G8 | [Prevent clicks outside targeted locations](https://support.google.com/google-ads/answer/9376662?hl=en) | Presence-based location setting |
| G9 | [About Maximize clicks bidding](https://support.google.com/google-ads/answer/6268626?hl=en) | Click-oriented bidding and optional maximum CPC bid limit; bid-adjustment caveat |
| G10 | [About keyword matching options](https://support.google.com/google-ads/answer/7478529?hl=en) | Meaning-based Exact/Phrase matching and overlap |
| G11 | [About invalid traffic](https://support.google.com/google-ads/answer/11182074?hl=en) | Detected invalid traffic filtering; billing and on-site activity remain different measurements |
| G12 | [About negative keywords](https://support.google.com/google-ads/answer/2453972?hl=en) | Negative phrase/exact behavior and variant limitations |
| G13 | [Download a search terms report](https://support.google.com/google-ads/editor/answer/9003338?hl=en) | Reviewing actual queries before changing keyword coverage |
| G14 | [Change status with Make multiple changes](https://support.google.com/google-ads/editor/answer/71857?hl=en) | Negative items cannot be paused; omit their Status field |

### Google schema decision

Only documented column names are emitted. The RSA file is imported in the typed Responsive search ads view, so it does not need an unverified `Ad type` field. Negatives use explicit documented types at the ad-group level, which avoids guessing a combined campaign-negative type. The same 21 rules are intentionally repeated across three ad groups.

Campaign-total budget support is documented in both the budget FAQ and Editor release notes, while their bulk-support descriptions differ. The package therefore leaves all budget and bid fields out of CSV and instructs the operator to use the live campaign settings. The campaign must remain paused throughout preparation.

## ChatGPT

| ID | Official source | Applied to this package |
| --- | --- | --- |
| O1 | [Launch campaigns](https://help.openai.com/en/articles/20001209-launch-campaigns) | Guided setup; obtain the actual bulk template in Ads Manager |
| O2 | [Bulk upload campaign schema checklist](https://help.openai.com/en/articles/20001218-bulk-upload-campaign-schema-checklist) | Native template preservation, creative limits, image requirements, IDs and UTC end-date semantics |
| O3 | [Creating campaigns for ChatGPT Ads](https://help.openai.com/en/articles/20001210-creating-campaigns-for-chatgpt-ads) | Clicks objective, campaign-total budget and first-campaign publication caveat |
| O4 | [Bidding strategies and pricing](https://help.openai.com/en/articles/20001634-bidding-strategies-and-how-pricing-works-in-chatgpt-ads) | Intelligent bidding, November 9 Target CPC availability and November 18 legacy API-field behavior |
| O5 | [Creating ads for ChatGPT Ads](https://help.openai.com/en/articles/20001212-creating-ads-for-chatgpt-ads) | Specific benefit copy, relevant landing page, static UTMs and crawler access |
| O6 | [Ads in ChatGPT: The basics](https://help.openai.com/en/articles/20001207-ads-in-chatgpt-the-basics) | Context hints are not exact keywords; audience and measurement distinctions |
| O7 | [Ads Manager availability](https://help.openai.com/en/articles/20001245-ads-manager-availability) | United States self-service availability, subject to the actual account's readiness |

### ChatGPT schema and bidding decisions

The public sources identify the native template and required structure but do not expose a verified static schema suitable for this account. `setup_reference.csv` is therefore labeled as reference in the filename, every row and its instructions. No fabricated upload compatibility is claimed.

The newer bidding guide O4 supersedes older maximum-bid wording in O1 and O6 for new campaigns. The package proposes Intelligent bidding, leaves numeric Target CPC unset, and does not call legacy API fields. No current auction price is inferred from historical examples or platform recommendations.

## Product

| ID | Source | Use |
| --- | --- | --- |
| P1 | [CodeJet's current website](https://codejet.app/) and the user's product description | Retail positioning; existing reporting context and business definitions; plain-English questions; implementation involves approved sources and a business blueprint |

No independent performance study, customer endorsement, quantified savings, universal integration guarantee or measured campaign result is claimed. The ad language is newly authored for CodeJet using its supplied positioning.

## What has and has not been checked

Local validation covers the source structure, all copy lengths, duplicate IDs, paused statuses, static URL/UTM structure, positive-negative conflicts and deterministic CSV export. The asset files have **not** been submitted to a live account. Production availability, account-specific import acceptance, current forecasts, identity/billing setup and final campaign activation remain separate launch checks.
