# Vector Pinball Hub

This repository contains the "Vector Hub" application, a Dockerized service designed to act as a central hub for Warped Pinball "Vector" boards. It receives game state updates via UDP, stores them in a PostgreSQL database, and provides a Web API/UI for leaderboards and active game monitoring.

## Architecture

The system consists of:
1.  **Vector Hub App**: A Python (FastAPI) application.
    -   **UDP Listener (Port 5000)**: Receives real-time game data (ball, player, score, time) from pinball boards.
    -   **Web API (Port 8000)**: Serves data to the frontend UI.
2.  **PostgreSQL Database**: Stores persistent data about machines, games, and scores.

### Database Schema (ER Diagram)

```mermaid
erDiagram
    MACHINES {
        int id PK
        string name
        string ip_address
        timestamp last_seen
    }
    PLAYERS {
        int id PK
        string initials
        string screen_name
        string first_name
        string last_name
        string email
        string phone_number
    }
    GAMES {
        int id PK
        int machine_id FK
        timestamp start_time
        timestamp end_time
        boolean is_active
    }
    GAME_PLAYERS {
        int id PK
        int game_id FK
        int player_id FK
        int player_number
    }
    GAME_STATES {
        int id PK
        int game_id FK
        timestamp timestamp
        int seconds_elapsed
        int ball
        int player_up
        json scores
    }

    MACHINES ||--o{ GAMES : hosts
    PLAYERS ||--o{ GAME_PLAYERS : plays
    GAMES ||--o{ GAME_PLAYERS : includes
    GAMES ||--o{ GAME_STATES : logs
```

## Docker Usage

### Prerequisites
- Docker
- Docker Compose

### Running with Docker Compose (Recommended)

The easiest way to run the hub and the database together is using Docker Compose.

1.  **Start the services**:
    ```bash
    docker-compose up --build
    ```
    This command will:
    -   Build the `app` image from the `Dockerfile`.
    -   Start a `postgres` container (`db`).
    -   Start the `app` container, linked to the database.

2.  **Access the Application**:
    -   **Web API**: [http://localhost:8000](http://localhost:8000)
    -   **UDP Listener**: `localhost:5000` (UDP)

3.  **Stop the services**:
    ```bash
    docker-compose down
    ```

### Building the Docker Image Manually

If you want to build the image without Compose:

```bash
docker build -t vector-hub .
```

### Running the Container Manually

To run the container standalone (requires a running database):

```bash
docker run -p 8000:8000 -p 5000:5000/udp \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  vector-hub
```

## Configuration

The application is configured via environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | Connection string for PostgreSQL | `postgresql://vector_user:vector_password@localhost:5432/vector_db` |

## CI/CD

A GitHub Actions workflow (`.github/workflows/publish.yml`) is configured to automatically build and publish the Docker image to GitHub Container Registry (GHCR) on every push to the `main` branch.
