# Origin

Origin now includes a purpose-built utility for keeping your GitHub Actions artifacts in check. The
`artifact_auditor` module can audit the artifacts created by the workflows that power the GALP
repository and optionally delete anything that no longer needs to live in storage.

## Artifact auditor quick start

### Requirements

- Python 3.10+
- A personal access token (classic) or fine-grained token with the `repo` scope so the script can list
  and delete artifacts
- `httpx` (installed automatically when you install the project's dependencies)

### Environment setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
```

You can store default values for the CLI with environment variables:

- `GITHUB_TOKEN` – required token if you do not pass `--token`
- `GITHUB_OWNER` – defaults to `GALP`
- `GITHUB_REPO` – defaults to `GALP`

### Auditing artifacts

Run the auditor with the owner and repository that hosts your GALP workflows:

```bash
python -m artifact_auditor --owner my-org --repo GALP --older-than 14 --name-contains build
```

The script prints a table containing the artifacts that match your filters followed by an aggregate
summary. Use the filters to narrow the output:

| Option | Description |
| ------ | ----------- |
| `--older-than <days>` | Only include artifacts created at least the specified number of days ago. |
| `--name-contains <text>` | Only include artifacts whose name contains the provided text. |
| `--limit <n>` | Stop after the first `n` matching artifacts. |

### Cleaning up artifacts

After reviewing the audit output you can remove the artifacts directly from the command line:

```bash
python -m artifact_auditor --owner my-org --repo GALP --older-than 30 --delete --apply
```

- `--delete` instructs the tool to stage the selected artifacts for deletion.
- `--apply` tells the tool to perform the deletion. Omit `--apply` to run a dry run; the tool will
  print the IDs it would delete without performing the API calls.

Tip: add `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO` to your shell profile so you can reuse the
command without re-typing the values.

### Testing the script

All of the repository tests—including the artifact auditor unit tests—can be run with `pytest`:

```bash
pytest -q
```

## Backend and PWA

This repository continues to host the Origin backend API (FastAPI) and the minimal PWA. Start the
Docker Compose stack for local development:

```bash
docker compose up --build
```

Refer to the documents in [docs/](docs/) for configuration details, API specifications, and the
original developer guide.
