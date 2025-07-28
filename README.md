# Origin

This repository contains the Origin backend API built with FastAPI and the Cordova-based mobile application.

## Backend

### Development

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Configuration

By default the application connects to the Postgres instance defined in `docker-compose.yml`. The connection URL can be overridden with the `DATABASE_URL` environment variable or by setting `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` and `POSTGRES_DB`.

### Database Migrations

Schema changes live in `app/migrations` as numbered SQL files. On startup the service runs any pending migrations automatically. Add a new numbered SQL file alongside the code that requires it.

## Mobile App

The `mobile` folder contains a minimal Cordova application demonstrating NFC, barcode scanning and deep-link handling.

### Setup

```bash
git clone <repo>
cd mobile
npm ci
cordova platform add android ios
```

Pages in `www/` are generated from templates using `npm run build:pages`. This runs automatically during `npm run prepare`.

### Running

```bash
cordova emulate android   # or ios
```

Tag an NFC tag, scan a QR code or open a deep link to see the URL logged on the page.

When running on a real device the app writes a log to `Download/origin-log.txt` which
records signup and login attempts.

### Signing

The workflow generates a debug keystore for Android so the APK is installable without secrets. Edit `build.json` if you wish to use your own signing credentials. For iOS create a `build.json` with your Apple developer team ID and provisioning profile as shown in the comments of the file.

### Screenshots

Screenshots are produced automatically by the **Update Mobile Screenshots** workflow and uploaded as artifacts. They are not committed to the repository.

## SDK Generation

API clients are generated from `openapi.json` using
[Fern](https://buildwithfern.com). Running
`./scripts/generate-sdks.sh` produces TypeScript and Python SDKs in
`sdks/typescript` and `sdks/python` respectively. The web host and Cordova
app consume the TypeScript build. The API base URL continues to come from the
`PUBLIC_API_URL` environment variable or `mobile/api-base.js`.
See `docs/SDKS.md` for details.

## Continuous Integration

Pull requests run backend, mobile and SDK tests. On `main` the workflow
also executes `scripts/generate-sdks.sh` and publishes the resulting
packages to npm and PyPI using repository secrets for authentication.
Docker images and Android APKs are still built for releases and attached as
artifacts.
