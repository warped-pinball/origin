# SDK Generation

This repository uses [OpenAPI Generator](https://github.com/OpenAPITools/openapi-generator)
to generate client SDKs from `openapi.json`.
The generated JavaScript client is copied to `app/static/api.js` via the
[`web` build script](../web/scripts/build.js) discussed in the
[Developer Guide](DEVELOPER_GUIDE.md).

## Building locally

Install Node.js and run:

```bash
./scripts/generate-sdks.sh
```

This downloads the OpenAPI Generator CLI and produces a TypeScript package under
`sdks/typescript/dist`. The build is bundled with the web host at build time.

## Continuous Integration

The CI workflow runs the same script on `main` and bundles the generated
clients with the web host. The TypeScript package is no longer published
to npm.

For a list of planned endpoints see the [API specification](API_SPEC.md).
