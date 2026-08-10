# Germany Student Jobs Agent

A dependency-free Python agent that searches Germany for both **computer-science opportunities** and **general part-time/minijob work**, removes duplicates, publishes a switchable live dashboard, and sends dependable daily Telegram updates.

## Live dashboard

**https://ot-coder.github.io/germany-cs-jobs-agent/**

The dashboard refreshes automatically from public internet job sources every day at approximately **08:00 Europe/Berlin**. Use its category switch to move between **CS & Tech** and **Part-time & Minijob** listings. Saved, applied, and dismissed states stay private in your browser's local storage; they are not committed to GitHub.

## What it does

- Searches public endpoints from:
  - Bundesagentur für Arbeit Jobsuche
  - Arbeitnow
  - Remotive (remote roles)
- Uses Germany-focused technical searches plus general queries such as `minijob`, `teilzeit`, `studentenjob`, `aushilfe lager`, and `aushilfe gastronomie`.
- Separates technical roles from nontechnical part-time work such as warehouse, restaurant, retail, delivery, and similar jobs whenever the title signals part-time, minijob, student job, or temporary-help work.
- Rejects senior roles and unrelated full-time nontechnical roles.
- Scores matches by student fit, category relevance, German location, and English-language wording.
- Deduplicates jobs across sources.
- Publishes `docs/index.html` and `docs/jobs.json` to GitHub Pages.
- Sends new matches through Telegram and a daily completion heartbeat when no new jobs are found.

## Cloud automation

`.github/workflows/refresh-jobs.yml` runs on GitHub Actions:

1. Selects the 08:00 Europe/Berlin run across daylight-saving changes.
2. Runs the behavior tests.
3. Fetches current jobs from the internet.
4. Compares them with the previously published dataset.
5. Sends a Telegram digest for new jobs or a completion heartbeat when there are none.
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
- CS scoring remains strict, while the separate general category requires a part-time, minijob, Werkstudent, student-job, or temporary-help signal.
- The public repository contains job listings only—not Telegram credentials or personal application statuses.
