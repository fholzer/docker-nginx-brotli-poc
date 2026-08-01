#!/usr/bin/env python3
"""
Create or update a GitHub PR to add missing nginx versions to versions.txt.

Reads the JSON output from checkNginxVersions.py and either:
- Creates a new PR with a branch `update-nginx-versions-YYYY-MM-DD`
- Updates an existing PR from github-actions[bot]

Usage:
    python3 updateVersionsPr.py \
        --result /tmp/versions-result.json \
        --base-branch main \
        --pr-number "123" \
        --title-prefix "ci: add missing nginx versions"
"""

import argparse
import datetime
import json
import os
import subprocess
import sys


def run_command(cmd: list[str], capture: bool = True) -> tuple[str, str, int]:
    """Run a shell command and return (stdout, stderr, returncode).

    Raises subprocess.CalledProcessError with error details on non-zero exit codes.
    """
    result = subprocess.run(
        cmd, capture_output=capture, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        if result.stdout:
            print(f"stdout: {result.stdout}", file=sys.stderr)
        if result.stderr:
            print(f"stderr: {result.stderr}", file=sys.stderr)
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    return result.stdout.strip(), result.stderr.strip(), 0


def get_current_date() -> str:
    """Get current date as YYYY-MM-DD."""
    return datetime.date.today().isoformat()


def get_all_versions_in_title(missing: dict[str, list[str]]) -> list[str]:
    """Get all missing versions formatted for PR title."""
    versions: list[str] = []
    for category in ["stable", "mainline"]:
        for v in missing.get(category, []):
            versions.append(f"v{v}")
    return versions


def read_versions_file(filepath: str) -> list[str]:
    """Read versions from file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()
        return [line.strip() for line in raw_lines if line.strip()]
    except FileNotFoundError:
        return []


def write_versions_file(filepath: str, versions: list[str]) -> None:
    """Write versions to file, sorted descending."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(f"{v}\n" for v in versions)


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse version string to tuple for sorting."""
    parts = version_str.strip().split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def create_pr(
    result_file: str, base_branch: str, title_prefix: str
) -> None:
    """Create a new PR with missing versions."""
    # Read result data
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    missing = data.get("missing", {})
    release_dates = data.get("release_dates", {})

    all_missing_versions: list[str] = []
    for category in ["stable", "mainline"]:
        all_missing_versions.extend(missing.get(category, []))

    if not all_missing_versions:
        print("No missing versions to add.")
        return

    # Generate branch name
    date_str = get_current_date()
    branch_name = f"update-nginx-versions-{date_str}"

    # Read existing versions
    existing_versions = read_versions_file("versions.txt")

    # Merge and deduplicate
    existing_set = set(existing_versions)
    all_versions = list(existing_set)
    for v in all_missing_versions:
        if v not in existing_set:
            all_versions.append(v)

    # Sort descending
    all_versions.sort(key=parse_version, reverse=True)

    # Create and checkout branch
    run_command(["git", "checkout", base_branch])
    run_command(["git", "checkout", "-b", branch_name])

    # Update versions.txt
    write_versions_file("versions.txt", all_versions)

    # Commit
    run_command(["git", "add", "versions.txt"])
    run_command(
        [
            "git",
            "commit",
            "-m",
            f"ci: add missing nginx versions {', '.join(f'v{v}' for v in all_missing_versions)}",
        ]
    )

    # Push
    run_command(["git", "push", "origin", branch_name])

    # Build PR title
    title_versions = get_all_versions_in_title(missing)
    pr_title = f"{title_prefix} {', '.join(title_versions)}"

    # Build PR body
    pr_body = build_pr_body(missing, release_dates, is_update=False)

    # Create PR
    repo = os.environ.get("GITHUB_REPOSITORY", "fholzer/docker-nginx-brotli-poc")

    stdout, stderr, rc = run_command(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch,
            "--title",
            pr_title,
            "--body",
            pr_body,
            "--repo",
            repo,
        ]
    )

    if rc != 0:
        print(f"Error creating PR: {stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"PR created: {stdout}")


def update_pr(
    pr_number: str, result_file: str, base_branch: str, title_prefix: str
) -> None:
    """Update an existing PR with new missing versions."""
    # Read result data
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    missing = data.get("missing", {})
    release_dates = data.get("release_dates", {})

    all_missing_versions: list[str] = []
    for category in ["stable", "mainline"]:
        all_missing_versions.extend(missing.get(category, []))

    if not all_missing_versions:
        print("No new missing versions to add.")
        return

    # Get the branch from the existing PR
    stdout, stderr, rc = run_command(
        [
            "gh",
            "pr",
            "view",
            pr_number,
            "--json headRefName",
            "--jq",
            ".headRefName",
        ]
    )

    if rc != 0:
        print(f"Error getting PR branch: {stderr}", file=sys.stderr)
        sys.exit(1)

    branch_name = stdout.strip()
    if not branch_name:
        print("Error: could not determine PR branch name", file=sys.stderr)
        sys.exit(1)

    # Checkout and pull branch
    run_command(["git", "checkout", branch_name])
    run_command(["git", "pull", "origin", branch_name])

    # Read existing versions
    existing_versions = read_versions_file("versions.txt")
    existing_set = set(existing_versions)

    # Add missing versions
    all_versions = list(existing_set)
    for v in all_missing_versions:
        if v not in existing_set:
            all_versions.append(v)

    # Sort descending
    all_versions.sort(key=parse_version, reverse=True)

    # Update versions.txt
    write_versions_file("versions.txt", all_versions)

    # Amend commit
    run_command(["git", "add", "versions.txt"])
    run_command(
        [
            "git",
            "commit",
            "--amend",
            "--no-edit",
        ]
    )

    # Force push
    run_command(["git", "push", "origin", branch_name, "--force"])

    # Build updated PR title with all versions
    title_versions = get_all_versions_in_title(missing)
    pr_title = f"{title_prefix} {', '.join(title_versions)}"

    # Build PR body
    pr_body = build_pr_body(missing, release_dates, is_update=True)

    # Update PR title and body
    repo = os.environ.get("GITHUB_REPOSITORY", "fholzer/docker-nginx-brotli-poc")

    run_command(
        [
            "gh",
            "pr",
            "edit",
            pr_number,
            "--title",
            pr_title,
            "--body",
            pr_body,
            "--repo",
            repo,
        ]
    )

    print(f"PR #{pr_number} updated.")


def build_pr_body(
    missing: dict[str, list[str]],
    release_dates: dict[str, str],
    is_update: bool = False,
) -> str:
    """Build the PR body text."""
    lines: list[str] = []

    if is_update:
        lines.append("## Update: New nginx versions detected")
        lines.append("")
        lines.append(
            "The daily version check detected additional nginx releases since the last update."
        )
        lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(
        "The following nginx versions have been released but are not yet included in this repository:"
    )
    lines.append("")

    # Stable versions
    stable = missing.get("stable", [])
    if stable:
        lines.append("### Stable")
        lines.append("")
        for v in stable:
            date = release_dates.get(v, "unknown")
            lines.append(f"- `v{v}` (released: {date})")
        lines.append("")

    # Mainline versions
    mainline = missing.get("mainline", [])
    if mainline:
        lines.append("### Mainline")
        lines.append("")
        for v in mainline:
            date = release_dates.get(v, "unknown")
            lines.append(f"- `v{v}` (released: {date})")
        lines.append("")

    lines.append("## Changes")
    lines.append("- Updated `versions.txt` with missing versions")
    lines.append("")
    lines.append(
        "This PR was auto-generated by the [version check workflow](https://github.com/"
        + os.environ.get("GITHUB_REPOSITORY", "fholzer/docker-nginx-brotli-poc")
        + "/actions/workflows/check-versions.yml)."
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or update a PR for missing nginx versions"
    )
    parser.add_argument(
        "--result",
        type=str,
        required=True,
        help="Path to JSON result file from checkNginxVersions.py",
    )
    parser.add_argument(
        "--base-branch",
        type=str,
        default="main",
        help="Base branch for PR, default: main",
    )
    parser.add_argument(
        "--pr-number",
        type=str,
        default="",
        help="Existing PR number to update (empty for new PR)",
    )
    parser.add_argument(
        "--title-prefix",
        type=str,
        default="ci: add missing nginx versions",
        help="PR title prefix",
    )
    args = parser.parse_args()

    if args.pr_number:
        update_pr(args.pr_number, args.result, args.base_branch, args.title_prefix)
    else:
        create_pr(args.result, args.base_branch, args.title_prefix)


if __name__ == "__main__":
    main()
