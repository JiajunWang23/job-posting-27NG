#!/usr/bin/env python3
"""Sync the Jiajun Google Sheet tab into this repository."""

from __future__ import annotations

import csv
import subprocess
import sys
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SHEET_ID = "1-h9XMUpQfxNLSY5u0y20ZVJmoy6iKo098XVjcrqg9NA"
GID = "1733775388"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
TIMEZONE = ZoneInfo("America/Chicago")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_rows() -> list[dict[str, str]]:
    with urllib.request.urlopen(CSV_URL, timeout=30) as response:
        raw = response.read().decode("utf-8-sig")
    return list(csv.DictReader(raw.splitlines()))


def clean_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    clean: list[dict[str, str]] = []
    for row in rows:
        clean.append(
            {
                "No.": row.get("No.", "").strip(),
                "Company": row.get("Campany", row.get("Company", "")).strip(),
                "Applied Date": row.get("Date", "").strip(),
                "Status": row.get("Status", "").strip(),
                "Position": row.get("position", "").strip(),
                "Link": row.get("link", "").strip(),
                "OA": row.get("OA", "").strip(),
                "VO": row.get("VO", "").strip(),
            }
        )
    return clean


def md_escape(value: str) -> str:
    value = (value or "").replace("\n", " ").strip().replace("|", r"\|")
    return value if value else "-"


def link_cell(url: str) -> str:
    if not url or url.upper() == "N/A":
        return "-"
    return f"[link]({url})"


def build_markdown(rows: list[dict[str, str]]) -> str:
    status_counts = Counter(row["Status"] or "blank" for row in rows)
    date_counts = Counter(row["Applied Date"] for row in rows)
    active_notes = [row for row in rows if row["OA"] or row["VO"]]
    latest_date = max((row["Applied Date"] for row in rows if row["Applied Date"]), default="-")

    lines: list[str] = [
        "# job posting 27NG",
        "",
        "Source: Jiajun tab from the shared Google Sheet",
        f"Updated: {datetime.now(TIMEZONE).date().isoformat()}",
        "",
        "## Summary",
        "",
        f"- Total postings: {len(rows)}",
        "- Status: " + ", ".join(f"{key}: {value}" for key, value in sorted(status_counts.items())),
        f"- OA missing / not recorded: {sum(1 for row in rows if not row['OA'])}",
        f"- VO missing / not recorded: {sum(1 for row in rows if not row['VO'])}",
        f"- Most recent application date: {latest_date}",
        "",
        "## Follow-up Queue",
        "",
    ]

    if active_notes:
        lines.extend(
            [
                "| Company | Position | Applied Date | OA | VO | Link |",
                "|---|---|---:|---|---|---|",
            ]
        )
        for row in active_notes:
            lines.append(
                f"| {md_escape(row['Company'])} | {md_escape(row['Position'])} | "
                f"{md_escape(row['Applied Date'])} | {md_escape(row['OA'])} | "
                f"{md_escape(row['VO'])} | {link_cell(row['Link'])} |"
            )
    else:
        lines.append("- No OA/VO follow-up notes recorded yet.")

    lines.extend(
        [
            "",
            "## Applications",
            "",
            "| No. | Company | Applied Date | Status | Position | OA | VO | Link |",
            "|---:|---|---:|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {md_escape(row['No.'])} | {md_escape(row['Company'])} | "
            f"{md_escape(row['Applied Date'])} | {md_escape(row['Status'])} | "
            f"{md_escape(row['Position'])} | {md_escape(row['OA'])} | "
            f"{md_escape(row['VO'])} | {link_cell(row['Link'])} |"
        )

    lines.extend(["", "## Daily Count", "", "| Date | Count |", "|---:|---:|"])
    for date, count in sorted(date_counts.items()):
        lines.append(f"| {md_escape(date)} | {count} |")
    lines.append("")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_git(args: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main() -> int:
    root = repo_root()
    rows = clean_rows(read_rows())
    if not rows:
        print("No rows found in the Jiajun sheet tab.", file=sys.stderr)
        return 1

    (root / "README.md").write_text(build_markdown(rows), encoding="utf-8")
    write_csv(root / "data" / "job-posting-27NG.csv", rows)

    run_git(["add", "README.md", "data/job-posting-27NG.csv", "scripts/sync_job_posting.py"], root)
    diff = run_git(["diff", "--cached", "--quiet"], root, check=False)
    if diff.returncode == 0:
        print("No changes to commit.")
        return 0

    run_git(["commit", "-m", "Update job posting 27NG"], root)
    run_git(["push"], root)
    print("Synced job posting 27NG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
