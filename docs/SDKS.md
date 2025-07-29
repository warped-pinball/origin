# SDK Generation

This repository uses [Fern](https://buildwithfern.com) to generate client SDKs
from `openapi.json`.

## Building locally

Install Node.js and run:

```bash
./scripts/generate-sdks.sh
```

This downloads the Fern CLI and produces TypeScript and Python packages under
`sdks/`. The TypeScript build is bundled with the web host at build time.

## Continuous Integration

The CI workflow runs the same script on `main` and publishes the generated
packages:

- The TypeScript package is published to npm as `origin-api-client`.
- The Python package is published to PyPI as `origin-sdk`.

Authentication tokens for both registries are provided through repository
secrets.
