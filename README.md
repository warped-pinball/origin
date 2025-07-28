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

## Shared JavaScript Client

API calls used by both the web UI and the mobile app live under `shared/`.
Run `node shared/scripts/build.js` to generate `api.js` and copy it into the
correct locations. The script also respects the `PUBLIC_API_URL` environment
variable so both clients use the same API base URL. See
`docs/JS_CLIENT.md` for details.

## Continuous Integration

Pull requests run both backend and mobile tests. Building the backend Docker image and Android APK happens when changes land on `main` or a release is published. Check the workflow runs for downloadable artifacts.
