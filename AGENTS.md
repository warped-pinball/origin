# Agent Guidelines for The Box

## General Workflow
- Read this file before making changes. If additional AGENTS.md files are added in subdirectories, follow the most specific one for files you touch.
- Follow existing project documentation in README.md and TOURNAMENTS.md.

## Code Style
- Use Python 3.10+ features already in the codebase, but avoid introducing new dependencies without approval.
- Maintain consistent formatting with existing files; prefer PEP 8 and black-style formatting.
- Do not wrap imports in try/except blocks.
- Practice DRY (do not repeat yourself) principals whenever possible

## Testing
- Always run `pytest` before commiting code
- If pytest results in warnings resolve them or surface them to the user
- Document the commands run and results in your final response.

## Pull Requests
- Summarize changes clearly and concisely in the PR body.
- List any new or updated tests in the PR description.

## Documentation
- Update README.md or relevant docs when behavior or setup steps change.
- Update AGENTS.md with:
  - high level guidence
  - tasks that should be done as a part of most development
  - any thing that can cause an agent to get confused or off track when working with this repository

