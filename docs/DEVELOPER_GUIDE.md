# Developer Guide

This repository contains a FastAPI backend and a Cordova mobile app. Both clients share the same JavaScript API package, which is generated from `openapi.json`.

## API Client

The TypeScript SDK is generated with [Fern](https://buildwithfern.com) by running:

```bash
./scripts/generate-sdks.sh
```

The resulting `sdks/typescript/index.js` file is bundled with both the web host and the mobile app when you run `npm --prefix shared build`. The build script copies the file to `app/static/api.js` and `mobile/www/api.js`.

## API Base URL

The clients read the API base URL from the `PUBLIC_API_URL` environment variable. When building the Cordova app, `mobile/scripts/build-pages.js` injects this value into the HTML templates. If the variable is not set, the value from `mobile/api-base.js` is used instead. Edit that file to change the default (`https://origin-beta.doze.dev`).

## Running Tests

Install the Python and Node.js dependencies as shown in the main `README.md` and run the following:

```bash
npm --prefix shared test --silent
npm --prefix mobile test --silent
pytest -q
```
