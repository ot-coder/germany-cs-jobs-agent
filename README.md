# Germany CS Jobs Agent

A dependency-free Python agent that searches for **Werkstudent** and **entry-level tech roles in Germany**, ranks them for a computer-science student, removes duplicates, publishes a live dashboard, and sends Telegram updates when new matches appear.

## Live dashboard

**https://ot-coder.github.io/germany-cs-jobs-agent/**

The dashboard refreshes automatically from public internet job sources every day at **08:00 Europe/Berlin**. Saved, applied, and dismissed states stay private in your browser's local storage; they are not committed to GitHub.

## What it does

- Searches public endpoints from:
  - Bundesagentur für Arbeit Jobsuche
  - Arbeitnow
  - Remotive (remote roles)
- Uses Germany-focused searches including `werkstudent informatik`, `werkstudent software`, `junior softwareentwickler`, and `berufseinsteiger informatik`.
- Rejects senior and non-technical roles.
- Scores matches by student fit, CS relevance, German location, and English-language wording.
- Deduplicates jobs across sources.
- Publishes `docs/index.html` and `docs/jobs.json` to GitHub Pages.
- Sends a Telegram digest only when newly discovered jobs exist.

## Cloud automation

`.github/workflows/refresh-jobs.yml` runs on GitHub Actions:

1. Selects the 08:00 Europe/Berlin run across daylight-saving changes.
2. Runs the behavior tests.
3. Fetches current jobs from the internet.
4. Compares them with the previously published dataset.
5. Sends a Telegram message if new jobs were found.
6. Commits refreshed data and deploys GitHub Pages.

Telegram delivery uses encrypted GitHub Actions secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Run locally

Requires Python 3.11 or newer; there are no third-party dependencies.

```bash
# Search now and print the top 10
python3 -m jobs_agent fetch

# Start the local SQLite-backed dashboard
python3 -m jobs_agent serve
# Open http://127.0.0.1:8787

# Build the static GitHub Pages dashboard
python3 -m jobs_agent publish \
  --docs docs \
  --message .out/telegram.txt \
  --site-url https://ot-coder.github.io/germany-cs-jobs-agent/

# Run tests
python3 -m unittest discover -s tests -v
```

## Project structure

```text
jobs_agent/core.py       classification and scoring
jobs_agent/sources.py    live source adapters and network fetches
jobs_agent/store.py      local SQLite persistence
jobs_agent/web.py        local dashboard and Markdown digest
jobs_agent/publish.py    static GitHub Pages dashboard export
jobs_agent/telegram.py   Telegram Bot API notifications
jobs_agent/cli.py        fetch, digest, serve, and publish commands
docs/                    generated live dashboard and job dataset
tests/                   behavior tests
```

## Notes

- Job availability changes continuously; always verify each posting on its source page.
- The agent uses public endpoints and identifies itself with a user-agent. Request volume is deliberately modest.
- Scoring is intentionally strict: titles must indicate both junior/student level and technical relevance, reducing marketing, legal, and operations false positives.
- The public repository contains job listings only—not Telegram credentials or personal application statuses.
