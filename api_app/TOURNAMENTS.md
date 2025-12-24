# Tournaments

This guide captures the current tournament setup workflow, how scoring templates are used, and how tournament leaderboards surface in the UI.

## Admin workflow

1. **Pick a tournament type** (`GET /api/v1/tournaments/types`)
   - Each type hard-codes the scoring profile and machine mode pairing (for example, `limbo` → `limbo` profile + `pin-golf` mode).
   - The admin UI surfaces these types in a dropdown with names and descriptions.
2. **(Optional) Extend catalog** (`POST /api/v1/tournaments/profiles` + `POST /api/v1/tournaments/modes`)
   - New scoring profiles and modes can be added and wired into `TOURNAMENT_TYPES` to produce more presets.
3. **Create tournaments** (`POST /api/v1/tournaments`)
   - Supply a `tournament_type`, slug, description, time window, display window, and optional machine/player scopes. Leaving players blank means “all players.”
   - Tournaments start active by default; they can be edited (`PATCH /api/v1/tournaments/{id}`) or deleted (`DELETE /api/v1/tournaments/{id}`).
4. **Review configuration** (`GET /api/v1/tournaments`)
   - Fetch tournaments, their resolved scoring profile + machine mode, and assigned machines/players.

## Leaderboard behavior

- The big screen shows tournaments while they are active (once `start_time` arrives) and until `display_until` is reached. Tournaments with no dates stay visible while flagged `is_active`.
- Standings are rebuilt server-side by executing each tournament's scoped scoring template against:
  - Only the tournament's machines (if provided)
  - Only the invited players (if provided)
  - Game state timestamps between `start_time` and `end_time` (when set)
- Each scoring template must emit `player_id` and `score` columns; the service joins player metadata and returns the top 10 rows using the profile's sort direction.

## Seeded examples

The seed data registers two scoring profiles:
- **High score** (`high-score`): `MAX(score)` wins
- **Limbo** (`limbo`): `MIN(score)` wins

A demo tournament (`limbo-weekend`) is created with a `display_until` value a few hours past its end time to showcase the post-event display window.

## Frontend notes

- Big screen (`/big-screen`) consumes `tournaments` from the leaderboard summary endpoint and renders each alongside the game leaderboards.
- The admin **Tournaments** tab now uses tournament types, chip-style selectors for machines/players (empty = all), and inline edit/delete controls.
