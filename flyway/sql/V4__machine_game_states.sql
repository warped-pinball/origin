CREATE TABLE IF NOT EXISTS machine_game_states (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_ms INTEGER NOT NULL,
    ball_in_play INTEGER NOT NULL,
    scores JSON NOT NULL,
    player_up INTEGER,
    players_total INTEGER
);

CREATE INDEX IF NOT EXISTS idx_machine_game_states_machine_id
    ON machine_game_states(machine_id);
