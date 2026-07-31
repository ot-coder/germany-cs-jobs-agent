from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Callable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from .core import Job, classify_role, plain_text, score_job, stable_job_id


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
        remote=bool(raw.get("remote", False)),
        published_at=published_at,
    )
    job.score, job.reasons = score_job(job)
    return job


def normalize_ba(raw: dict) -> Job:
    title = str(raw.get("titel", "")).strip()
    company = str(raw.get("arbeitgeber", "Unknown")).strip()
    place = raw.get("arbeitsort") or {}
    location = ", ".join(str(place.get(key, "")).strip() for key in ("ort", "region", "land") if place.get(key))
    description = plain_text(str(raw.get("beruf", "")))
    reference = str(raw.get("refnr", "")).strip()
    role_type = classify_role(title, description)
    job = Job(
        id=stable_job_id(company, title, location), title=title, company=company,
        location=location or "Deutschland",
        url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{reference}",
        description=description, source="bundesagentur", role_type=role_type,
        published_at=str(raw.get("aktuelleVeroeffentlichungsdatum", "")),
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
        source="remotive", role_type=role_type, remote=True,
        published_at=str(raw.get("publication_date", "")),
    )
    job.score, job.reasons = score_job(job)
    return job


def _fetch_json(url: str) -> dict:
    headers = {"User-Agent": "GermanyCSJobsAgent/0.1 (+local personal-use app)"}
    if "arbeitsagentur.de" in url:
        headers["X-API-Key"] = "jobboerse-jobsuche"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_all(fetch_json: Callable[[str], dict] = _fetch_json, min_score: int = 55) -> list[Job]:
    arbeitnow = fetch_json("https://www.arbeitnow.com/api/job-board-api")
    remotive = fetch_json("https://remotive.com/api/remote-jobs")
    candidates = [normalize_arbeitnow(item) for item in arbeitnow.get("data", [])]
    candidates.extend(normalize_remotive(item) for item in remotive.get("jobs", []))
    for query in ("werkstudent informatik", "werkstudent software", "junior softwareentwickler", "berufseinsteiger informatik"):
        url = (
            "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
            f"?was={quote_plus(query)}&wo=Deutschland&page=1&size=50"
        )
        result = fetch_json(url)
        candidates.extend(normalize_ba(item) for item in result.get("stellenangebote", []))

    best: dict[str, Job] = {}
    for job in candidates:
        if job.role_type == "other" or job.score < min_score:
            continue
        existing = best.get(job.id)
        if existing is None or job.score > existing.score:
            best[job.id] = job
    return sorted(best.values(), key=lambda job: (-job.score, job.title.casefold()))
