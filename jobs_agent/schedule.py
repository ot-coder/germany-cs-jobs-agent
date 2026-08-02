from __future__ import annotations

from datetime import date, datetime, time, timezone
import os
from zoneinfo import ZoneInfo


def should_run(event_name: str, schedule: str, utc_date: date | None = None) -> bool:
    if event_name == "workflow_dispatch":
        return True
    if event_name != "schedule":
        return False
    parts = schedule.split()
    if len(parts) != 5:
        return False
    try:
        minute = int(parts[0])
        hour = int(parts[1])
    except ValueError:
        return False
    day = utc_date or datetime.now(timezone.utc).date()
    scheduled_utc = datetime.combine(day, time(hour=hour, minute=minute), tzinfo=timezone.utc)
    return scheduled_utc.astimezone(ZoneInfo("Europe/Berlin")).hour == 8


def main() -> int:
    event_name = os.environ.get("EVENT_NAME", "")
    schedule = os.environ.get("EVENT_SCHEDULE", "")
    result = should_run(event_name, schedule)
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"run={'true' if result else 'false'}\n")
    print(f"event={event_name}, schedule={schedule!r}, run={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
