from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import sys
from typing import Callable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from .core import Job, classify_category, classify_role, plain_text, score_job, stable_job_id


LEIPZIG_AREA_TOWNS = frozenset({
    "leipzig",
    "markkleeberg",
    "schkeuditz",
    "taucha",
    "markranstädt",
    "zwenkau",
    "böhlen",
    "rötha",
    "großpösna",
    "rackwitz",
    "borsdorf",
    "brandis",
    "machern",
    "naunhof",
    "krostitz",
    "delitzsch",
    "eilenburg",
    "borna",
    "grimma",
    "wurzen",
    "neukieritzsch",
    "pegau",
})


def is_leipzig_area(location: str) -> bool:
    city = location.split(",", 1)[0].strip().casefold()
    return city in LEIPZIG_AREA_TOWNS


def normalize_arbeitnow(raw: dict) -> Job:
    title = str(raw.get("title", "")).strip()
    company = str(raw.get("company_name", "Unknown")).strip()
    location = str(raw.get("location", "Germany")).strip() or "Germany"
    description = plain_text(str(raw.get("description", "")))
    role_type = classify_role(title, description)
    created = raw.get("created_at")
    published_at = ""
    if isinstance(created, (int, float)):
        published_at = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
    job = Job(
        id=stable_job_id(company, title, location),
        title=title,
        company=company,
        location=location,
        url=str(raw.get("url", "")),
        description=description,
        source="arbeitnow",
        role_type=role_type,
        category=classify_category(title, role_type, description),
        remote=bool(raw.get("remote", False)),
        published_at=published_at,
    )
    job.score, job.reasons = score_job(job)
    return job


def _display_location(value: object) -> str:
    return str(value or "").strip().replace("_", " ").title()


def normalize_ba(raw: dict) -> Job:
    title = str(raw.get("titel") or raw.get("stellenangebotsTitel") or "").strip()
    company = str(raw.get("arbeitgeber") or raw.get("firma") or "Unknown").strip()
    place = raw.get("arbeitsort") or {}
    locations = raw.get("stellenlokationen") or []
    if not place and locations and isinstance(locations[0], dict):
        place = locations[0].get("adresse") or {}
    location = ", ".join(
        _display_location(place.get(key)) for key in ("ort", "region", "land") if place.get(key)
    )
    description = plain_text(str(raw.get("beruf") or raw.get("hauptberuf") or ""))
    reference = str(raw.get("refnr") or raw.get("referenznummer") or "").strip()
    role_type = classify_role(title, description)
    job = Job(
        id=stable_job_id(company, title, location), title=title, company=company,
        location=location or "Deutschland",
        url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{reference}",
        description=description, source="bundesagentur", role_type=role_type,
        category=classify_category(title, role_type, description),
        published_at=str(
            raw.get("aktuelleVeroeffentlichungsdatum")
            or raw.get("datumErsteVeroeffentlichung")
            or ""
        ),
    )
    job.score, job.reasons = score_job(job)
    return job


def normalize_remotive(raw: dict) -> Job:
    title = str(raw.get("title", "")).strip()
    company = str(raw.get("company_name", "Unknown")).strip()
    location = str(raw.get("candidate_required_location", "Remote")).strip() or "Remote"
    description = plain_text(str(raw.get("description", "")))
    role_type = classify_role(title, description)
    job = Job(
        id=stable_job_id(company, title, location), title=title, company=company,
        location=location, url=str(raw.get("url", "")), description=description,
        source="remotive", role_type=role_type,
        category=classify_category(title, role_type, description), remote=True,
        published_at=str(raw.get("publication_date", "")),
    )
    job.score, job.reasons = score_job(job)
    return job


class _BAStateParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_state = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "ng-state":
            self.in_state = True

    def handle_data(self, data: str) -> None:
        if self.in_state:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.in_state:
            self.in_state = False


def _parse_ba_search_html(html: str) -> dict:
    parser = _BAStateParser()
    parser.feed(html)
    if not parser.parts:
        raise ValueError("Bundesagentur search page did not contain ng-state data")
    state = json.loads("".join(parser.parts))
    search = state.get("suchergebnis") or {}
    jobs = search.get("ergebnisliste") or []
    if not isinstance(jobs, list):
        raise ValueError("Bundesagentur ng-state search results are invalid")
    return {"stellenangebote": jobs}


def _fetch_json(url: str) -> dict:
    is_ba_page = "www.arbeitsagentur.de/jobsuche/suche" in url
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GermanyCSJobsAgent/0.1; personal-use)",
        "Accept": "text/html" if is_ba_page else "application/json",
    }
    if "rest.arbeitsagentur.de" in url:
        headers["X-API-Key"] = "jobboerse-jobsuche"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        if is_ba_page:
            return _parse_ba_search_html(response.read().decode("utf-8"))
        return json.load(response)


def fetch_all(fetch_json: Callable[[str], dict] = _fetch_json, min_score: int = 55) -> list[Job]:
    candidates: list[Job] = []
    successful_requests = 0
    failures: list[str] = []

    def load(source: str, url: str) -> dict | None:
        nonlocal successful_requests
        try:
            result = fetch_json(url)
        except Exception as error:
            failures.append(f"{source}: {error}")
            return None
        successful_requests += 1
        return result

    arbeitnow = load("arbeitnow", "https://www.arbeitnow.com/api/job-board-api")
    if arbeitnow is not None:
        candidates.extend(normalize_arbeitnow(item) for item in arbeitnow.get("data", []))

    remotive = load("remotive", "https://remotive.com/api/remote-jobs")
    if remotive is not None:
        candidates.extend(normalize_remotive(item) for item in remotive.get("jobs", []))

    technical_queries = (
        "werkstudent informatik",
        "werkstudent software",
        "junior softwareentwickler",
        "berufseinsteiger informatik",
    )
    general_queries = (
        "minijob",
        "teilzeit",
        "studentenjob",
        "aushilfe lager",
        "aushilfe gastronomie",
        "aushilfe restaurant",
    )
    for query in technical_queries + general_queries:
        if query in general_queries:
            location_query = "wo=Leipzig&umkreis=35"
        else:
            location_query = "wo=Deutschland"
        url = (
            "https://www.arbeitsagentur.de/jobsuche/suche?angebotsart=1"
            f"&was={quote_plus(query)}&{location_query}"
        )
        result = load("bundesagentur", url)
        if result is None:
            break
        candidates.extend(normalize_ba(item) for item in result.get("stellenangebote", []))

    for failure in failures:
        print(f"Warning: job source unavailable: {failure}", file=sys.stderr)
    if successful_requests == 0:
        raise RuntimeError("All job sources failed; refusing to publish an empty dashboard")

    best: dict[str, Job] = {}
    for job in candidates:
        if job.category == "other" or job.role_type == "other" or job.score < min_score:
            continue
        if job.category == "part-time" and not is_leipzig_area(job.location):
            continue
        existing = best.get(job.id)
        if existing is None or job.score > existing.score:
            best[job.id] = job
    return sorted(best.values(), key=lambda job: (-job.score, job.title.casefold()))
