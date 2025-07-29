# API Roadmap and Specification

This document outlines a high-level plan for the Origin API. It covers core features, suggested endpoints, database structure and authentication considerations.
For project structure details see the [Developer Guide](DEVELOPER_GUIDE.md) and
the [SDK documentation](SDKS.md).

## 1. Overview

The service allows arcade owners to manage machines and events while letting players track scores and achievements. Physical devices inside pinball machines will report scores directly to the API. Both the website and mobile clients will use the same endpoints.

Key goals:

- **Scalable user management** for thousands of daily active users.
- **Flexible machine registration** so new games can be added easily.
- **Real‑time and historical leaderboards** to power score displays.
- **Event and tournament tools** for arcade owners.
- **Self‑contained sign‑up and login** with optional two‑factor verification. Email is primarily used for account recovery.

## 2. Core Features

1. **User Accounts**
   - Register with email, password and optional phone number.
   - Unique display name ("screen name") that can be changed later.
   - Password reset via email link.
   - Two‑factor options: email verification codes or time‑based one‑time passwords (TOTP) to avoid SMS costs.

2. **Machine Management**
   - Owners register machines and receive a secret token for the physical device.
   - Devices authenticate with this token when posting scores.
   - Owners can view active devices and revoke/renew tokens.

3. **Scores and Leaderboards**
   - Submit scores with user ID, machine ID and game name.
   - Live leaderboard endpoints for real‑time scoreboards.
   - Historical queries by day/week/month/all‑time.

4. **Events and Tournaments**
   - Create tournaments that pair players and assign games.
   - Notify players of upcoming events through the app.
   - Record results to influence leaderboards and achievements.

5. **Analytics for Arcades**
   - Reports on machine popularity, peak hours and user attendance.
   - Optional integration with foot traffic counters or check‑ins.

6. **In‑App Purchases and Cosmetics**
   - Track virtual goods linked to a user profile.
   - Webhooks or background jobs for payment processor events.

## 3. Suggested Database Schema

The current models in `app/models.py` include `User`, `Machine` and `Score` tables【F:app/models.py†L1-L30】. Future tables to consider:

- `Tournament` – stores event details (name, start/end time, rules).
- `TournamentEntry` – links users to tournaments and tracks progress.
- `Arcade` – represents a physical location with address and owner.
- `MachineStatus` – periodic updates from devices (e.g., busy, available).
- `Achievement` and `UserAchievement` – unlockable badges and progress.
- `CosmeticItem` and `UserInventory` – purchased customizations.

When designing new tables, omit `created_at` and `updated_at` fields in the base tables. Instead, maintain a corresponding `<table>_history` table recording every change with a `history_id` primary key and `valid_from`/`valid_to` timestamps. These history tables enable "as of" queries for any point in time.

## 4. Authentication Flow

1. **Sign‑Up**
   - User provides email, password and optional phone number.
   - Service sends a verification code to the email address (link or numeric code).
   - Upon verification the account becomes active.
   - Optionally allow enabling a TOTP app (e.g., Google Authenticator) for 2FA.

2. **Login**
   - Users authenticate with email and password (username not required for login).
   - If 2FA is enabled, the API requests the second factor after verifying the password.
   - JWT access tokens (as implemented in `app/auth.py`) continue to secure API calls.

3. **Password and Email Changes**
   - Require current password to change to a new one.
   - When changing email, send a confirmation link to the new address.

## 5. REST Endpoints (Proposed)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/users/` | Create user account. |
| `POST` | `/auth/token` | Obtain JWT access token. |
| `GET` | `/users/me` | Retrieve current user profile. |
| `POST` | `/machines/` | Register a machine (owner only). |
| `POST` | `/scores/` | Submit a score. |
| `GET` | `/scores/top/{game}` | Top scores for a game. |
| `GET` | `/scores/user/{user_id}` | Scores for a user. |
| `POST` | `/tournaments/` | Create tournament. |
| `POST` | `/tournaments/{id}/join` | Join tournament. |
| `GET` | `/tournaments/{id}/leaderboard` | View tournament standings. |
| `GET` | `/arcades/nearby` | List arcades by location. |
| `POST` | `/cosmetics/purchase` | Purchase cosmetic item. |

Background workers or scheduled tasks can handle leaderboard calculations, tournament matchmaking and analytics aggregation.

## 6. Automation and Scaling Considerations

- **Queue system**: Use a message broker (e.g., RabbitMQ or Redis) for tasks like score processing, email notifications and analytics computation.
- **Caching**: Cache frequent leaderboard queries to reduce database load.
- **Database migrations**: Schema changes are stored as numbered SQL files in
  `app/migrations`. The application executes any pending files on startup so all
  environments upgrade in lockstep.
- **Sharding/Replication**: Plan for read replicas once traffic grows; keep writes centralized initially.
- **API versioning**: Prefix routes with `/v1/` (e.g., `/v1/scores/`) so future versions can coexist.

## 7. Email Delivery and Password Reset

To avoid running a full mail server in each environment, configure the application to use an SMTP relay service such as Mailgun or SendGrid. These services offer free tiers and allow sending from your own domain. Store the SMTP host, port, username and password in environment variables in `docker-compose.yml` so containers can send verification and password reset messages without rebuilding the image.

## 8. Docker Build and Deployment

Build the container image with `docker build -t pinball-api:$VERSION .` and publish it to a private registry.

1. **GitHub Container Registry (GHCR)** – create a personal access token with the `write:packages` scope and authenticate using `docker login ghcr.io`. Push images as `ghcr.io/<owner>/pinball-api:$VERSION`. GHCR supports private repositories and works seamlessly with GitHub Actions.


## 9. Next Steps

1. Finalize authentication method (email codes vs TOTP) and implement verification endpoints.
2. Expand the database with tournament and arcade tables.
3. Add endpoints for event creation and user participation.
4. Build analytics workers for reporting to arcade owners.
5. Draft detailed API documentation using OpenAPI/Swagger (FastAPI provides this automatically).

This roadmap should provide a solid foundation for building out the full pinball tracking platform while keeping the design flexible for future growth.

