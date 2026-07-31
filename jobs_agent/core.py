from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re


SENIOR_TERMS = ("senior", "lead ", "principal", "staff ", "manager", "head of", "director")
WERKSTUDENT_TERMS = ("werkstudent", "working student", "student assistant", "studentische hilfskraft")
ENTRY_TERMS = ("junior", "entry level", "entry-level", "graduate", "trainee", "berufseinsteiger")
TECH_TERMS = (
    "software", "developer", "engineer", "data", "python", "java", "javascript",
    "typescript", "cloud", "devops", "security", "cyber", "machine learning", " ai ",
    "frontend", "backend", "full stack", "fullstack", "qa", "test automation",
    "computer science", "informatik", "information technology", "product analyst",
    "business intelligence", "database", "systems administrator", "web development",
)


@dataclass(slots=True)
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    source: str
    role_type: str = "other"
    remote: bool = False
    published_at: str = ""
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    first_seen_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def stable_job_id(company: str, title: str, location: str) -> str:
    key = "|".join(_normalized(v) for v in (company, title, location))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def classify_role(title: str, description: str = "") -> str:
    title_text = _normalized(title)
    if any(term in title_text for term in SENIOR_TERMS):
        return "other"
    if any(term in title_text for term in WERKSTUDENT_TERMS):
        return "werkstudent"
    if any(term in title_text for term in ENTRY_TERMS):
        return "entry-level"
    return "other"


def score_job(job: Job) -> tuple[int, list[str]]:
    title_text = f" {_normalized(job.title)} "
    description_text = f" {_normalized(job.description)} "
    text = f"{title_text} {description_text}"
    location = _normalized(job.location)
    role_type = job.role_type if job.role_type != "other" else classify_role(job.title, job.description)
    score = 0
    reasons: list[str] = []

    if role_type == "werkstudent":
        score += 35
        reasons.append("Werkstudent role")
    elif role_type == "entry-level":
        score += 35
        reasons.append("Entry-level role")

    if any(term in title_text for term in TECH_TERMS):
        score += 40
        reasons.append("Computer-science relevance")
    if any(term in text for term in ("student", "enrolled", "immatrikul", "studium", "university")):
        score += 8
        reasons.append("Student-friendly wording")
    if any(term in location for term in ("germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "cologne", "köln", "frankfurt", "stuttgart", "düsseldorf")):
        score += 7
        reasons.append("Located in Germany")
    if "english" in text or "englisch" in text:
        score += 3
        reasons.append("English mentioned")
    if any(term in _normalized(job.title) for term in SENIOR_TERMS):
        score -= 80
        reasons.append("Senior-level penalty")

    return max(0, min(100, score)), reasons


def plain_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()
