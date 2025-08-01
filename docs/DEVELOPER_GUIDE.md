# Developer Guide

This repository contains a FastAPI backend and a Progressive Web App. Clients share a JavaScript API generated at runtime from the dynamic OpenAPI schema. For an overview of upcoming features see the [API specification](API_SPEC.md).

## API Client

The web client builds its SDK at runtime using [openapi-client-axios](https://github.com/anttiviljami/openapi-client-axios). The wrapper lives in `app/static/js/api.js` and fetches `/openapi.json` directly. The service worker is a simple static file located in `app/static/js`.

## API Base URL

The clients read the API base URL from the `PUBLIC_API_URL` environment variable. If the variable is not set the PWA defaults to `https://origin-beta.doze.dev`.

## Running Tests

Install the Python dependencies as shown in the main `README.md` and run the following:

```bash
pytest -q
```
