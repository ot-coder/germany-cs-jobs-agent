from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Callable

from .publish import publish_jobs, telegram_message
from .sources import FetchResult, fetch_all
from .store import JobStore
from .web import render_digest, serve


def default_db_path() -> Path:
    return Path(os.environ.get("JOBS_AGENT_DB", Path.cwd() / "data" / "jobs.db"))


def run_fetch(store: JobStore, fetcher: Callable[[], FetchResult] = fetch_all) -> tuple[int, str]:
    result = fetcher()
    new_count = store.upsert(result.jobs)
    return new_count, render_digest(store.list_jobs(limit=10), new_count)


def run_publish(
    fetcher: Callable[[], FetchResult], docs_dir: Path, message_path: Path, site_url: str
) -> int:
    result = fetcher()
    new_jobs = publish_jobs(result.jobs, docs_dir)
    message_path.parent.mkdir(parents=True, exist_ok=True)
    message = telegram_message(
        new_jobs, result.evaluated, result.duplicates_removed, result.passed_threshold, site_url,
    )
    message_path.write_text(message, encoding="utf-8")
    return len(new_jobs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Germany CS Jobs Agent")
    parser.add_argument("--db", type=Path, default=default_db_path())
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("fetch", help="Search sources, store matches, and print a digest")
    subparsers.add_parser("digest", help="Print the current top matches without fetching")
    serve_parser = subparsers.add_parser("serve", help="Run the local dashboard")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)
    publish_parser = subparsers.add_parser("publish", help="Fetch jobs and build the static live dashboard")
    publish_parser.add_argument("--docs", type=Path, default=Path("docs"))
    publish_parser.add_argument("--message", type=Path, default=Path(".out/telegram.txt"))
    publish_parser.add_argument("--site-url", default="https://ot-coder.github.io/germany-cs-jobs-agent/")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = JobStore(args.db)
    if args.command == "fetch":
        _, digest = run_fetch(store)
        print(digest)
    elif args.command == "digest":
        print(render_digest(store.list_jobs(limit=10), 0))
    elif args.command == "serve":
        serve(args.db, args.host, args.port)
    elif args.command == "publish":
        count = run_publish(fetch_all, args.docs, args.message, args.site_url)
        print(f"Published live dashboard with {count} new suitable roles")
    return 0
