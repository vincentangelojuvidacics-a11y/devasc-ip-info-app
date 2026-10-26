"""
exporter.py - Save lookup results to a file so technicians can attach
them to tickets or reports.

Supported formats: JSON (full data) and CSV (one row per lookup).
Files are written to the ./reports folder with a timestamped name.
"""

import csv
import json
import os
from datetime import datetime

REPORT_DIR = "reports"


def _path(extension):
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(REPORT_DIR, f"ip_report_{stamp}.{extension}")


def export_json(records):
    """records: list of dicts. Returns the file path written."""
    path = _path("json")
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(records),
        "results": records,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def export_csv(records):
    """records: list of dicts (may have different keys). Returns the file path."""
    path = _path("csv")
    fieldnames = []
    for rec in records:  # union of all keys, keeping first-seen order
        for key in rec:
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    return path
