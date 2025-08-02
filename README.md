# Origin

This repository contains the Origin backend API built with FastAPI and a simple Progressive Web App (PWA). Additional documentation lives in the [docs](docs/) folder. Start with the [Developer Guide](docs/DEVELOPER_GUIDE.md) and the [API specification](docs/API_SPEC.md).

## Backend

### Development

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000` and the WebSocket at `ws://localhost:8001`.

### Configuration

By default the application connects to the Postgres instance defined in
`docker-compose.yml`. The connection URL can be overridden with the
`DATABASE_URL` environment variable or by setting `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_HOST` and `POSTGRES_DB`.

Additional settings control SMS delivery and machine claims:

- `RSA_PRIVATE_KEY`: PEM encoded RSA key used to sign machine claim handshakes.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`: enable
  transactional SMS for account verification and password resets.

The service listens on port `8000` for HTTP and `8001` for WebSocket traffic.
Ensure both ports are reachable or forwarded by your reverse proxy.

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for details on generating the
RSA key pair and obtaining SMS API credentials.

### Database Migrations

Schema changes live in `app/migrations` as numbered SQL files. On startup the service runs any pending migrations automatically. Add a new numbered SQL file alongside the code that requires it.

## Progressive Web App

The web host serves a minimal PWA that implements the same login and signup flow as the old Cordova application. Users can install the app to their home screen when prompted by their browser. A minimal hand-written service worker handles installation without any caching yet.

## API Client

Clients can generate an API client on the fly using
[openapi-client-axios](https://github.com/anttiviljami/openapi-client-axios).
The OpenAPI specification is served dynamically at `/openapi.json` and the
API base URL comes from the `PUBLIC_API_URL` environment variable.

## Continuous Integration

Pull requests run backend tests. Docker images are built for releases and
attached as artifacts.

## Testing

Install dependencies and run the backend test suite:

```bash
pip install -r requirements.txt -r requirements-test.txt
pytest -q
```
