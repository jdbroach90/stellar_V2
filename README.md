# CodeJet public website

Flask website for [CodeJet](https://codejet.app), a retail intelligence platform. The public product pages lead to the existing Cloudflare demo and the existing contact form.

## Retail search and video campaign

**Start with [growth/README.md](growth/README.md)** for the completed Google and ChatGPT campaign package, website changes, paused ad assets, measurement tools, and launch order.

The production line identified for this project is **`master`**. GitHub's default `main` is not the deployment branch. Changes in the review branch do not publish the website; merging to the Render-linked branch can deploy it.

## Local development

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app server run --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000/retail-analytics-software` or `/demo`. These are shell commands; exit Python's `>>>` prompt before running them. Use Ctrl+C to stop the local server.

On Linux/macOS use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`, and `.venv/bin/python -m flask --app server run`. The optional `npm run dev` command is an adapter for the managed Linux preview environment; production remains Flask/Gunicorn via `Procfile`.

The public pages render without production secrets. Contact delivery and protected analytics need the existing server configuration. `.env.example` documents configuration names; never commit a populated `.env` or a traffic database.

## Checks

```text
python -m unittest discover -s tests -v
node --test tests/test_analytics_client.js
python -m unittest discover -s growth/tools -p "test_*.py" -v
python growth/campaigns/build_campaign_assets.py --check
python scripts/check_search.py --local
```

Use the virtual environment's Python executable where necessary. The GitHub workflow runs these checks without production credentials. Contact tests mock mail delivery; the checks do not send email, activate advertising, or submit forms.

After an intentional deployment, run:

```text
python scripts/check_search.py --base-url https://codejet.app
```

This performs public read-only GETs. See [the launch guide](growth/docs/LAUNCH_GUIDE.md) for Front Door, Search Console, video metadata, and release verification.

## Existing operations

- [Front Door configuration](FRONT_DOOR_SETUP.md)
- [Private first-party analytics setup](DEMO_ANALYTICS_SETUP.md)
- [Current release and discovery instructions](growth/docs/LAUNCH_GUIDE.md)

The search release retains the existing contact protections and analytics authentication, origin checks, database, and privacy signals. `/ai` remains subject to its separate WAF restriction. Robots rules are discovery guidance, not an access-control mechanism.
