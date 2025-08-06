-- Initial schema generated for Flyway migrations

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    screen_name VARCHAR UNIQUE,
    first_name VARCHAR,
    last_name VARCHAR,
    name VARCHAR,
    initials VARCHAR(3),
    profile_picture VARCHAR,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR UNIQUE,
    reset_token VARCHAR UNIQUE
);

-- Machines table
CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    secret VARCHAR NOT NULL
);

-- Machine claims table
CREATE TABLE IF NOT EXISTS machine_claims (
    machine_id VARCHAR PRIMARY KEY,
    claim_code VARCHAR UNIQUE NOT NULL,
    shared_secret VARCHAR NOT NULL,
    game_title VARCHAR NOT NULL,
    claimed BOOLEAN NOT NULL DEFAULT FALSE,
    user_id INTEGER REFERENCES users(id)
);

-- Scores table
CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    machine_id INTEGER REFERENCES machines(id),
    game VARCHAR,
    value INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- QR codes table
CREATE TABLE IF NOT EXISTS qr_codes (
    id SERIAL PRIMARY KEY,
    url VARCHAR UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_at TIMESTAMPTZ,
    nfc_link VARCHAR,
    user_id INTEGER REFERENCES users(id),
    machine_id INTEGER REFERENCES machines(id)
);

-- Record schema version to skip Python migrations
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
DELETE FROM schema_version;
INSERT INTO schema_version (version) VALUES (8);
