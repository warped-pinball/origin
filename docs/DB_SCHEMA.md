# Database Schema

## machine_claims

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| machine_id | VARCHAR | True | False |  | False |
| claim_code | VARCHAR | False | True |  | False |
| shared_secret | VARCHAR | False | False |  | False |
| game_title | VARCHAR | False | False |  | False |
| claimed | BOOLEAN | False | False |  | False |
| user_id | INTEGER | False | True |  | False |

## machines

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| name | VARCHAR | False | True |  | True |
| secret | VARCHAR | False | False |  | False |

## schema_version

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| version | INTEGER | False | False |  | False |

## scores

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| user_id | INTEGER | False | True |  | False |
| machine_id | INTEGER | False | True |  | False |
| game | VARCHAR | False | True |  | False |
| value | INTEGER | False | True |  | False |
| created_at | DATETIME | False | True | CURRENT_TIMESTAMP | False |

## users

| Column | Type | Primary Key | Nullable | Default | Unique |
| --- | --- | --- | --- | --- | --- |
| id | INTEGER | True | False |  | False |
| phone | VARCHAR | False | False |  | True |
| hashed_password | VARCHAR | False | False |  | False |
| screen_name | VARCHAR | False | True |  | False |
| first_name | VARCHAR | False | True |  | False |
| last_name | VARCHAR | False | True |  | False |
| name | VARCHAR | False | True |  | False |
| initials | VARCHAR(3) | False | True |  | False |
| profile_picture | VARCHAR | False | True |  | False |
| is_verified | BOOLEAN | False | True | '0' | False |
| verification_token | VARCHAR(255) | False | True |  | False |
| reset_token | VARCHAR(255) | False | True |  | False |

