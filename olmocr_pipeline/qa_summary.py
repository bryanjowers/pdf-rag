#!/usr/bin/env python3
"""
qa_summary.py — Generate simple run summaries and diffs.
"""

import json
import time
from pathlib import Path
from bs4 import BeautifulSoup
from difflib import unified_diff

def summarize_output(pdf_path: Path, html_path: Path, start_time: float) -> dict:
    """Basic summary: runtime, file stats, detected tables."""
    runtime = round(time.time() - start_time, 2)
    html = html_path.read_text(encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")
    tables = len(soup.find_all("table"))
    words = len(soup.get_text().split())

    summary = {
        "pdf_name": pdf_path.name,
        "pages": "unknown (OCR placeholder)",
        "tables_detected": tables,
        "word_count": words,
        "runtime_sec": runtime,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return summary


def diff_outputs(new_html: Path, old_html: Path) -> dict:
    """Simple HTML diff summary."""
    new_text = new_html.read_text(encoding="utf-8").splitlines()
    old_text = old_html.read_text(encoding="utf-8").splitlines()

    diff = list(unified_diff(old_text, new_text, lineterm=""))
    added = [line for line in diff if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in diff if line.startswith("-") and not line.startswith("---")]

    diff_summary = {
        "baseline": old_html.name,
        "new_run": new_html.name,
        "added_lines": len(added),
        "removed_lines": len(removed),
        "diff_score": round(1 - (len(diff) / max(len(new_text), 1)), 3)
    }
    return diff_summary
