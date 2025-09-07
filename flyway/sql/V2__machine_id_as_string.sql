-- Change machine-related IDs to VARCHAR to support UUIDs

-- Machines table
ALTER TABLE machines RENAME TO machines_old;
CREATE TABLE machines (
    id VARCHAR PRIMARY KEY,
    game_title VARCHAR NOT NULL,
    shared_secret VARCHAR NOT NULL,
    user_id INTEGER REFERENCES users(id),
    location_id INTEGER REFERENCES locations(id)
);
INSERT INTO machines (id, game_title, shared_secret, user_id, location_id)
    SELECT CAST(id AS VARCHAR), game_title, shared_secret, user_id, location_id FROM machines_old;
DROP TABLE machines_old;

-- Scores table
ALTER TABLE scores RENAME TO scores_old;
CREATE TABLE scores (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    machine_id VARCHAR REFERENCES machines(id),
    game VARCHAR,
    value INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO scores (id, user_id, machine_id, game, value, created_at)
    SELECT id, user_id, CAST(machine_id AS VARCHAR), game, value, created_at FROM scores_old;
DROP TABLE scores_old;

-- QR codes table
ALTER TABLE qr_codes RENAME TO qr_codes_old;
CREATE TABLE qr_codes (
    id SERIAL PRIMARY KEY,
    url VARCHAR UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_at TIMESTAMPTZ,
    nfc_link VARCHAR,
    user_id INTEGER REFERENCES users(id),
    machine_id VARCHAR REFERENCES machines(id)
);
INSERT INTO qr_codes (id, url, created_at, generated_at, nfc_link, user_id, machine_id)
    SELECT id, url, created_at, generated_at, nfc_link, user_id, CAST(machine_id AS VARCHAR) FROM qr_codes_old;
DROP TABLE qr_codes_old;
