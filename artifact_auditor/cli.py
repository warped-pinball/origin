"""Command line interface for auditing GitHub Actions artifacts."""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Iterable

from .github import ArtifactAuditor, GithubArtifactClient


def human_size(num_bytes: int) -> str:
    suffixes = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for suffix in suffixes:
        if value < 1024 or suffix == suffixes[-1]:
            return f"{value:.2f} {suffix}"
        value /= 1024
    return f"{value:.2f} TB"


def format_rows(artifacts: Iterable) -> str:
    rows = ["ID      Created (UTC)        Size      Expired  Name", "------  -------------------  --------  -------  ----"]
    for artifact in artifacts:
        rows.append(
            f"{artifact.id:<6}  {artifact.created_at.strftime('%Y-%m-%d %H:%M'):>19}  "
            f"{human_size(artifact.size_in_bytes):>8}  {str(artifact.expired):>7}  {artifact.name}"
        )
    return "\n".join(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and clean up GitHub Actions artifacts. "
            "Provide --delete to remove artifacts after reviewing the audit output."
        )
    )
    parser.add_argument("--owner", default=os.getenv("GITHUB_OWNER", "GALP"), help="Repository owner")
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPO", "GALP"),
        help="Repository name that contains the workflow artifacts",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        required=os.getenv("GITHUB_TOKEN") is None,
        help="GitHub token with the repo scope (can also be provided via GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=None,
        help="Only include artifacts created at least N days ago",
    )
    parser.add_argument(
        "--name-contains",
        default=None,
        help="Only include artifacts whose name contains the provided fragment",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of artifacts returned (after filtering)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the selected artifacts after auditing them",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="When used with --delete, perform the deletion instead of a dry run",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    with GithubArtifactClient(args.token, args.owner, args.repo) as client:
        auditor = ArtifactAuditor(client)
        artifacts = auditor.collect(
            older_than_days=args.older_than,
            name_contains=args.name_contains,
            limit=args.limit,
            reference=datetime.now(timezone.utc),
        )
        summary = ArtifactAuditor.summarize(artifacts)

    if not artifacts:
        print("No artifacts matched the provided filters.")
        return 0

    print(format_rows(artifacts))
    print("\nSummary:")
    print(
        f"Total: {summary['count']} artifacts, "
        f"Expired: {summary['expired']}, "
        f"Combined size: {human_size(summary['size_in_bytes'])}"
    )

    if args.delete:
        with GithubArtifactClient(args.token, args.owner, args.repo) as client:
            auditor = ArtifactAuditor(client)
            deleted_ids = auditor.delete(artifacts, dry_run=not args.apply)
        action = "Deleted" if args.apply else "Dry run (not deleted)"
        print(f"{action} artifact IDs: {', '.join(str(i) for i in deleted_ids)}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
