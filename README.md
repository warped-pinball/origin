# Origin

This repository contains the Origin backend API built with FastAPI and a simple Progressive Web App (PWA). Additional documentation lives in the [docs](docs/) folder. Start with the [Developer Guide](docs/DEVELOPER_GUIDE.md) and the [API specification](docs/API_SPEC.md).

## Backend

### Development

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Configuration

By default the application connects to the Postgres instance defined in
`docker-compose.yml`. The connection URL can be overridden with the
`DATABASE_URL` environment variable or by setting `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_HOST` and `POSTGRES_DB`.

Additional settings control email delivery and machine claims:

- `RSA_PRIVATE_KEY`: PEM encoded RSA key used to sign machine claim handshakes.
- `BREVO_API_KEY`: enables transactional email when set to a Brevo API key.
- `BREVO_SENDER_EMAIL` / `BREVO_SENDER_NAME`: optional email sender overrides.

The service listens on port `8000` for both HTTP and WebSocket traffic. Ensure
this port is reachable or forwarded by your reverse proxy.

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for details on generating the
RSA key pair and obtaining an email API key.

### Database Migrations

Schema changes live in `app/migrations` as numbered SQL files. On startup the service runs any pending migrations automatically. Add a new numbered SQL file alongside the code that requires it.

## Progressive Web App

The web host serves a minimal PWA that implements the same login and signup flow as the old Cordova application. Users can install the app to their home screen when prompted by their browser.
The JavaScript client used by the PWA lives in the `web` directory and is
copied to `app/static/api.js` when you run `npm --prefix web build`. The build
script also generates a Workbox-powered service worker for offline support.

## SDK Generation

API clients are generated from `openapi.json` using
[OpenAPI Generator](https://github.com/OpenAPITools/openapi-generator). Running
`./scripts/generate-sdks.sh` produces a TypeScript SDK in
`sdks/typescript/dist`. The web host consumes this build. The API base URL
comes from the `PUBLIC_API_URL` environment variable.
See `docs/SDKS.md` for details.

## Continuous Integration

Pull requests run backend and SDK tests. On `main` the workflow
also executes `scripts/generate-sdks.sh` and bundles the resulting
client with the web host. Docker images are built for releases and
attached as artifacts.

## Testing

Install dependencies and run the backend and SDK test suites:

```bash
pip install -r requirements.txt -r requirements-test.txt
npm --prefix web ci && npm --prefix web test --silent
pytest -q
```
