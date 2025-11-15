from datetime import datetime, timedelta, timezone

from artifact_auditor.github import Artifact, ArtifactAuditor


class FakeClient:
    def __init__(self, artifacts):
        self._artifacts = artifacts
        self.deleted = []

    def iter_artifacts(self):
        yield from self._artifacts

    def delete_artifact(self, artifact_id: int) -> None:
        self.deleted.append(artifact_id)


def build_artifact(artifact_id: int, *, days_old: int, name: str, expired: bool = False) -> Artifact:
    created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    return Artifact(
        id=artifact_id,
        name=name,
        size_in_bytes=artifact_id * 1024,
        created_at=created_at,
        expires_at=created_at + timedelta(days=30),
        expired=expired,
    )


def test_collect_filters_by_age_and_name():
    artifacts = [
        build_artifact(1, days_old=10, name="galp-build"),
        build_artifact(2, days_old=2, name="galp-build"),
        build_artifact(3, days_old=15, name="docs"),
    ]
    client = FakeClient(artifacts)
    auditor = ArtifactAuditor(client)

    selected = auditor.collect(older_than_days=7, name_contains="galp")

    assert [artifact.id for artifact in selected] == [1]


def test_summary_reports_count_size_and_expired():
    artifacts = [
        build_artifact(1, days_old=30, name="foo", expired=True),
        build_artifact(2, days_old=40, name="bar", expired=False),
    ]
    summary = ArtifactAuditor.summarize(artifacts)

    assert summary["count"] == 2
    assert summary["expired"] == 1
    assert summary["size_in_bytes"] == sum(a.size_in_bytes for a in artifacts)


def test_delete_can_run_dry_run_or_apply():
    artifacts = [
        build_artifact(1, days_old=10, name="one"),
        build_artifact(2, days_old=20, name="two"),
    ]
    client = FakeClient(artifacts)
    auditor = ArtifactAuditor(client)

    dry_run_ids = auditor.delete(artifacts, dry_run=True)
    assert dry_run_ids == [1, 2]
    assert client.deleted == []

    apply_ids = auditor.delete(artifacts, dry_run=False)
    assert apply_ids == [1, 2]
    assert client.deleted == [1, 2]
