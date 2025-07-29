# SDK Generation

This repository uses [Fern](https://buildwithfern.com) to generate client SDKs
from `openapi.json`.

## Building locally

Install Node.js and run:

```bash
./scripts/generate-sdks.sh
```

This downloads the Fern CLI and produces a TypeScript package under
`sdks/typescript`. The build is bundled with the web host at build time.

## Continuous Integration

The CI workflow runs the same script on `main` and publishes the generated
packages:

- The TypeScript package is published to npm as `origin-api-client`.

Authentication tokens for both registries are provided through repository
secrets.
