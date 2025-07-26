# Origin

Backend service for tracking pinball scores using FastAPI.

## Development

```bash
docker compose up --build
```

API will be available at `http://localhost:8000`.

### Configuration

By default the application connects to a Postgres instance running in the
`db` service from `docker-compose.yml`. The connection URL can be overridden via
the `DATABASE_URL` environment variable or by setting the individual variables
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_DB`. These
are combined at startup if `DATABASE_URL` is not provided.

## Database Migrations

Schema changes are tracked in the `app/migrations` folder as numbered SQL files
(e.g. `001.sql`). When the application starts it runs `run_migrations()` which
executes any files with a higher version than the one recorded in the
`schema_version` table. New environments automatically apply all pending
migrations on first run.

To create a migration, add a new numbered SQL file and commit it with the code
that requires it.
