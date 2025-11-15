"""GitHub Actions artifact utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator, List, Optional

import httpx


ISO_Z_SUFFIX = "Z"


def _parse_iso8601(value: str) -> datetime:
    if not value:
        raise ValueError("Missing timestamp value")
    if value.endswith(ISO_Z_SUFFIX):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


@dataclass
class Artifact:
    """Representation of a GitHub Actions artifact."""

    id: int
    name: str
    size_in_bytes: int
    created_at: datetime
    expires_at: Optional[datetime]
    expired: bool

    @classmethod
    def from_api(cls, payload: dict) -> "Artifact":
        return cls(
            id=payload["id"],
            name=payload["name"],
            size_in_bytes=payload["size_in_bytes"],
            created_at=_parse_iso8601(payload["created_at"]),
            expires_at=_parse_iso8601(payload["expires_at"]) if payload.get("expires_at") else None,
            expired=payload.get("expired", False),
        )

    def is_older_than(self, days: Optional[int], reference: Optional[datetime] = None) -> bool:
        if days is None:
            return True
        reference = reference or datetime.now(timezone.utc)
        return self.created_at <= reference - timedelta(days=days)

    def matches_name(self, name_contains: Optional[str]) -> bool:
        if not name_contains:
            return True
        return name_contains.lower() in self.name.lower()


class GithubArtifactClient:
    """Thin wrapper around the GitHub REST API."""

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        *,
        per_page: int = 100,
        base_url: str = "https://api.github.com",
        timeout: float = 10.0,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.per_page = per_page
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "artifact-auditor",
            },
        )

    def __enter__(self) -> "GithubArtifactClient":  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - convenience
        self.close()

    def close(self) -> None:
        self._client.close()

    def iter_artifacts(self) -> Iterator[Artifact]:
        page = 1
        while True:
            response = self._client.get(
                f"/repos/{self.owner}/{self.repo}/actions/artifacts",
                params={"per_page": self.per_page, "page": page},
            )
            response.raise_for_status()
            payload = response.json()
            artifacts = payload.get("artifacts", [])
            if not artifacts:
                break
            for artifact in artifacts:
                yield Artifact.from_api(artifact)
            if len(artifacts) < self.per_page:
                break
            page += 1

    def delete_artifact(self, artifact_id: int) -> None:
        response = self._client.delete(
            f"/repos/{self.owner}/{self.repo}/actions/artifacts/{artifact_id}"
        )
        response.raise_for_status()


class ArtifactAuditor:
    """Provides filtering, reporting, and deletion helpers."""

    def __init__(self, client: GithubArtifactClient) -> None:
        self._client = client

    def collect(
        self,
        *,
        older_than_days: Optional[int] = None,
        name_contains: Optional[str] = None,
        limit: Optional[int] = None,
        reference: Optional[datetime] = None,
    ) -> List[Artifact]:
        selected: List[Artifact] = []
        reference = reference or datetime.now(timezone.utc)
        for artifact in self._client.iter_artifacts():
            if not artifact.is_older_than(older_than_days, reference=reference):
                continue
            if not artifact.matches_name(name_contains):
                continue
            selected.append(artifact)
            if limit and len(selected) >= limit:
                break
        return selected

    @staticmethod
    def summarize(artifacts: Iterable[Artifact]) -> dict:
        artifacts = list(artifacts)
        total_size = sum(item.size_in_bytes for item in artifacts)
        expired = sum(1 for item in artifacts if item.expired)
        return {
            "count": len(artifacts),
            "expired": expired,
            "size_in_bytes": total_size,
        }

    def delete(self, artifacts: Iterable[Artifact], *, dry_run: bool = True) -> List[int]:
        deleted: List[int] = []
        for artifact in artifacts:
            if dry_run:
                deleted.append(artifact.id)
                continue
            self._client.delete_artifact(artifact.id)
            deleted.append(artifact.id)
        return deleted
