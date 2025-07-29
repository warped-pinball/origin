# Developer Guide

This repository contains a FastAPI backend and a Progressive Web App. Both clients share the same JavaScript API package, which is generated from `openapi.json`.
For an overview of upcoming features see the [API specification](API_SPEC.md).

## API Client

The TypeScript SDK is generated with [OpenAPI Generator](https://github.com/OpenAPITools/openapi-generator) by running (see [SDKs](SDKS.md) for details):

```bash
./scripts/generate-sdks.sh
```

The resulting `sdks/typescript/dist/index.js` file is bundled with the web host when you run `npm --prefix web build`. The build script copies the file to `app/static/api.js`.

## API Base URL

The clients read the API base URL from the `PUBLIC_API_URL` environment variable. If the variable is not set the PWA defaults to `https://origin-beta.doze.dev`.

## Running Tests

Install the Python and Node.js dependencies as shown in the main `README.md` and run the following:

```bash
npm --prefix web test --silent
pytest -q
```
