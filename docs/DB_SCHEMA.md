# Database Schema

## locations

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| user_id | INTEGER | False | False |  | False |
| name | VARCHAR | False | False |  | False |
| address | VARCHAR | False | True |  | False |
| website | VARCHAR | False | True |  | False |
| hours | VARCHAR | False | True |  | False |

## machine_challenges

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| challenge | VARCHAR | True | False |  | False |
| machine_id | VARCHAR | False | False |  | False |
| issued_at | TIMESTAMP | False | False | CURRENT_TIMESTAMP | False |

## machine_game_states

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| machine_id | VARCHAR | False | False |  | False |
| created_at | TIMESTAMP | False | False | CURRENT_TIMESTAMP | False |
| time_ms | INTEGER | False | False |  | False |
| ball_in_play | INTEGER | False | False |  | False |
| scores | JSON | False | False |  | False |
| player_up | INTEGER | False | True |  | False |
| players_total | INTEGER | False | True |  | False |
| game_active | BOOLEAN | False | True |  | False |

## machines

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | VARCHAR | True | False |  | False |
| game_title | VARCHAR | False | False |  | False |
| shared_secret | VARCHAR | False | False |  | False |
| user_id | INTEGER | False | True |  | False |
| location_id | INTEGER | False | True |  | False |
| claim_code | VARCHAR | False | True |  | True |

## qr_codes

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| url | VARCHAR | False | False |  | True |
| created_at | TIMESTAMP | False | False | CURRENT_TIMESTAMP | False |
| generated_at | TIMESTAMP | False | True |  | False |
| nfc_link | VARCHAR | False | True |  | False |
| user_id | INTEGER | False | True |  | False |
| machine_id | VARCHAR | False | True |  | False |

## scores

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| user_id | INTEGER | False | True |  | False |
| machine_id | VARCHAR | False | True |  | False |
| game | VARCHAR | False | True |  | False |
| value | INTEGER | False | True |  | False |
| created_at | TIMESTAMP | False | False | CURRENT_TIMESTAMP | False |

## users

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| email | VARCHAR(255) | False | False |  | False |
| hashed_password | VARCHAR | False | False |  | False |
| screen_name | VARCHAR | False | True |  | True |
| first_name | VARCHAR | False | True |  | False |
| last_name | VARCHAR | False | True |  | False |
| name | VARCHAR | False | True |  | False |
| initials | VARCHAR(3) | False | True |  | False |
| profile_picture | VARCHAR | False | True |  | False |
| is_verified | BOOLEAN | False | True | FALSE | False |
| verification_token | VARCHAR | False | True |  | True |
| reset_token | VARCHAR | False | True |  | True |

