"""Import Bright Data LinkedIn sample CSVs into per-company snapshot JSON files.

Usage (from backend/):
    python scripts/import_samples.py

Reads:
    C:/Users/User/Downloads/Linkedin job listings information.csv

Writes:
    backend/snapshots/<company-slug>.json   (one per target company)

Each snapshot matches the format produced by /scraper/refresh + consumed by
app.services.scraper_cache.load_snapshot().
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

# Make sure we can import from the app package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.scraper_cache import save_snapshot


JOBS_CSV = Path("C:/Users/User/Downloads/Linkedin job listings information.csv")

TARGET_COMPANIES = [
    "NVIDIA",
    "Affirm",
    "Walmart",
    "Marriott International",
    "Amazon",
    "Anthropic",      # bold play — Claude's own company
    "Deloitte",       # backup hero
    "Roche",          # backup
    "Micron Technology",  # backup
]


def main() -> None:
    if not JOBS_CSV.is_file():
        print(f"ERROR: jobs CSV not found at {JOBS_CSV}")
        sys.exit(1)

    targets_lower = {c.lower(): c for c in TARGET_COMPANIES}
    grouped: dict[str, list[dict]] = {c: [] for c in TARGET_COMPANIES}

    with JOBS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("company_name") or "").strip()
            if not name:
                continue
            target = targets_lower.get(name.lower())
            if not target:
                continue
            # Keep only the fields our parser cares about, plus a few demo-useful extras
            grouped[target].append({
                "job_title": row.get("job_title", ""),
                "company_name": name,
                "job_location": row.get("job_location", ""),
                "job_seniority_level": row.get("job_seniority_level", ""),
                "job_function": row.get("job_function", ""),
                "job_industries": row.get("job_industries", ""),
                "job_employment_type": row.get("job_employment_type", ""),
                "job_posted_time": row.get("job_posted_time", ""),
                "job_num_applicants": row.get("job_num_applicants", ""),
                "url": row.get("url", ""),
            })

    print(f"Read CSV. Grouped jobs per company:")
    for c, recs in grouped.items():
        print(f"  {c:30}  {len(recs)} records")

    written = 0
    for company, records in grouped.items():
        if not records:
            print(f"  SKIP {company}: 0 records in sample")
            continue
        # Fake the original scrape latency (typical Bright Data Web Scraper API
        # job takes 30-120s for LinkedIn jobs). Use a realistic value per record.
        fake_latency_ms = max(15000, len(records) * 2500)
        save_snapshot(company, records, fake_latency_ms)
        written += 1
        print(f"  WROTE {company}: {len(records)} records ({fake_latency_ms}ms reported)")

    print(f"\nDone. {written} snapshots written to backend/snapshots/")


if __name__ == "__main__":
    main()
