# Deon Fin multi-family Postgres and auth foundation design

Date: 2026-06-27
Repository: `deon7769/deon-fin`
Scope: foundation only, before product workflows and login polish

## Context

`deon-fin` is currently a single-family finance app. The backend is FastAPI,
the frontend is Next.js, and the database is SQLite through `src/storage/db.py`.
Authentication is a global Basic Auth password configured by
`APP_USER`/`APP_PASSWORD`. Existing data tables such as `accounts`,
`transactions`, `pluggy_items`, `tags`, `budget_buckets`, `profile`,
`portfolio_assets`, and audit/rule tables do not carry a tenant boundary.

The existing database ADR already points to "SQLite now, PostgreSQL as target".
The user now wants the system prepared for real users and families, with
separate financial data per family, while keeping third-party login such as
Google out of the first slice.

This design therefore treats authentication as a supporting layer and makes
`family_id` the main data boundary.

## Problem

A prettier login screen on top of the current Basic Auth would not create a
multi-family system. The app needs a data model where:

- a user can log in;
- a user can belong to one or more families;
- a family owns financial data;
- financial people in a family can exist without login accounts;
- Pluggy connections, accounts, transactions, tags, buckets, rules, goals, and
  portfolio data cannot leak across families;
- account ownership and transfers between family accounts can be represented.

The foundation must be ready for migration to PostgreSQL and for a future
Google/OIDC identity provider, without taking a hard dependency on those login
providers now.

## Recommended approach

Use self-hosted PostgreSQL plus first-party auth inside the FastAPI app.

PostgreSQL becomes the operational database for the multi-family cutover.
FastAPI owns login, session creation, current user lookup, current family
selection, and authorization checks. The schema keeps a `user_identities` table
so Google or another OIDC provider can be added later by linking external
identities to existing users.

This is preferred over Supabase self-hosted for now because the app already has
its own FastAPI API and repository layer. It is preferred over Keycloak or
authentik because those are good SSO systems but add unnecessary operational
weight before the family data boundary is solved.

## Non-goals

This foundation does not include:

- public signup;
- invite-by-email flows;
- Google login;
- MFA;
- billing or plans;
- per-screen permission rules beyond family membership and role;
- row-level-security policies as the primary enforcement mechanism;
- UI redesign beyond what is needed later for login and family selection.

The first implementation should be a closed system where an admin seed or CLI
creates the first user and family.

## Architecture

The domain boundary is:

```text
users
  -> family_members
    -> families
      -> provider_connections
        -> accounts
          -> transactions
```

The household/financial boundary is separate from login:

```text
families
  -> family_people
    -> account_people
      -> accounts
```

`users` are identities that can authenticate. `family_people` are people or
entities represented in the financial model. A family person may be linked to a
user, but does not have to be. This supports spouses, children, cardholders,
business entities, and future manual ownership mapping without forcing every
financial person to have login credentials.

Every repository and API route that reads or writes financial data must receive
a `current_family_id`. Queries must filter by that family explicitly, even when
also filtering by account, transaction, tag, or goal id.

## Target infrastructure

Add a PostgreSQL service to the self-hosted deployment:

- `postgres` Docker Compose service with a named volume;
- `DATABASE_URL=postgresql://...` as the application connection string;
- host-level and deploy-level backup using `pg_dump`;
- restore documentation before production cutover;
- migration script that copies SQLite data into PostgreSQL;
- dry-run mode that reports counts and integrity checks before writing;
- SQLite file retained as a read-only rollback artifact after cutover.

Schema migrations for PostgreSQL should use a versioned migration tool such as
Alembic. The existing SQLite migration runner can stay for the legacy database
until the cutover script has migrated production data.

## Core schema

Primary ids in PostgreSQL should be UUIDs for new multi-family tables. Imported
legacy transaction ids may stay as deterministic text where that preserves
deduplication. JSON payloads from providers should use `jsonb`.

### users

Minimum fields:

- `id uuid primary key`
- `email citext unique not null`
- `password_hash text`
- `display_name text`
- `status text not null`
- `password_changed_at timestamptz`
- `last_login_at timestamptz`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

`status` starts with `active`, `disabled`, and `pending`.

### user_identities

Minimum fields:

- `id uuid primary key`
- `user_id uuid not null references users(id)`
- `provider text not null`
- `provider_subject text`
- `provider_email citext`
- `metadata_json jsonb`
- `created_at timestamptz not null`
- unique `(provider, provider_subject)` when `provider_subject` is present

For first-party password login, create one `provider='local'` identity. Future
Google login adds `provider='google'` with the Google subject.

### families

Minimum fields:

- `id uuid primary key`
- `name text not null`
- `slug text unique not null`
- `status text not null`
- `default_currency text not null default 'BRL'`
- `timezone text not null default 'America/Sao_Paulo'`
- `created_by_user_id uuid references users(id)`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

`status` starts with `active`, `disabled`, and `archived`.

### family_members

Minimum fields:

- `family_id uuid not null references families(id)`
- `user_id uuid not null references users(id)`
- `role text not null`
- `status text not null`
- `joined_at timestamptz`
- `invited_by_user_id uuid references users(id)`
- primary key `(family_id, user_id)`

`role` starts with `owner`, `admin`, `member`, and `viewer`. The first slice only
needs owner/admin/member checks. Fine-grained feature permissions are out of
scope.

### family_people

Minimum fields:

- `id uuid primary key`
- `family_id uuid not null references families(id)`
- `linked_user_id uuid references users(id)`
- `display_name text not null`
- `legal_name text`
- `document_hash text`
- `document_last4 text`
- `aliases_json jsonb`
- `status text not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Do not store raw CPF/CNPJ by default. If document matching is needed, store a
hash with a server-side pepper and optionally the last four digits for display.

## Authentication and session foundation

Password login must be protected against brute force from the first
implementation.

### Password storage

- Use Argon2id for `password_hash` when available.
- Bcrypt is acceptable only as a fallback.
- Never store plaintext or reversible passwords.
- Do not log submitted passwords.

### sessions

Minimum fields:

- `id uuid primary key`
- `user_id uuid not null references users(id)`
- `active_family_id uuid references families(id)`
- `token_hash text unique not null`
- `csrf_token_hash text`
- `created_at timestamptz not null`
- `last_seen_at timestamptz not null`
- `expires_at timestamptz not null`
- `rotated_at timestamptz`
- `revoked_at timestamptz`
- `ip_hash text`
- `user_agent_hash text`

The browser receives only a random session token in a `HttpOnly`, `Secure`,
`SameSite=Lax` cookie. The database stores only the token hash. Session tokens
are regenerated on login and after privilege-sensitive changes. Logout revokes
the session row.

Mutating requests must enforce same-origin checks with strict `Origin` and
`Referer` validation, in addition to the `SameSite=Lax` session cookie. Requests
with missing or foreign origins are rejected for unsafe methods. A separate CSRF
token can be added later, but is not part of the first foundation slice.

### login_attempts

Minimum fields:

- `id uuid primary key`
- `user_id uuid references users(id)`
- `normalized_email_hash text`
- `ip_hash text`
- `user_agent_hash text`
- `success boolean not null`
- `failure_reason text`
- `created_at timestamptz not null`

Store email and IP hashes with a server-side pepper. This keeps enough data for
abuse prevention without making the audit table a sensitive directory of login
targets.

### user_security_state

Minimum fields:

- `user_id uuid primary key references users(id)`
- `failed_login_count integer not null default 0`
- `last_failed_login_at timestamptz`
- `locked_until timestamptz`
- `password_reset_required boolean not null default false`
- `updated_at timestamptz not null`

### Brute-force policy

The first implementation must enforce all of these:

- normalize emails before lookup;
- return the same generic error for unknown email and wrong password;
- record every attempt in `login_attempts`;
- limit repeated failures by normalized email/user;
- limit repeated failures by IP hash;
- temporarily lock an account after repeated failures;
- use exponential or step-up lockouts, capped at 24 hours;
- return HTTP `429` for rate-limited login attempts;
- reset user failure counters after a successful login;
- keep IP-based abuse counters independent from successful login reset;
- include tests for unknown-user attempts, wrong-password attempts, lockout,
  cooldown expiry, and successful reset.

Initial thresholds:

- per account/email: 5 failed attempts in 15 minutes locks for 15 minutes;
- repeated lockouts increase to 1 hour, then 24 hours;
- per IP: 20 failed attempts in 15 minutes returns `429`;
- per IP: 100 failed attempts in 24 hours returns `429` until the window clears.

These numbers are conservative enough for a private finance app and can be
configurable by environment variables later.

## Provider connections

Replace `pluggy_items` as the conceptual owner of external connections.

### provider_connections

Minimum fields:

- `id uuid primary key`
- `family_id uuid not null references families(id)`
- `provider text not null`
- `external_item_id text`
- `connector_id integer`
- `connector_name text`
- `status text`
- `client_user_id text`
- `owner_person_id uuid references family_people(id)`
- `last_synced_at timestamptz`
- `consent_expires_at timestamptz`
- `metadata_json jsonb`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- unique `(family_id, provider, external_item_id)` when `external_item_id` is present

For Pluggy, `provider='pluggy'`, `external_item_id` is the Pluggy item id, and
`client_user_id` should be stable per family/person, for example
`family:{family_id}:person:{person_id}`. This prevents one global app user from
owning every bank connection.

## Accounts and account ownership

### accounts

Minimum fields:

- `id uuid primary key`
- `family_id uuid not null references families(id)`
- `connection_id uuid references provider_connections(id)`
- `source text not null`
- `external_account_id text`
- `institution text`
- `name text`
- `type text`
- `subtype text`
- `currency text not null default 'BRL'`
- `last4 text`
- `status text`
- `metadata_json jsonb`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- unique `(family_id, source, external_account_id)` when `external_account_id` is present

`source` starts with `pluggy`, `ofx`, `csv`, and `manual`.

### account_people

Minimum fields:

- `account_id uuid not null references accounts(id)`
- `person_id uuid not null references family_people(id)`
- `relationship text not null`
- `source text not null`
- `confidence real`
- `created_at timestamptz not null`
- primary key `(account_id, person_id, relationship)`

`relationship` starts with `owner`, `holder`, `cardholder`, and `authorized`.
This supports joint accounts, additional cards, spouse accounts, and future
manual correction.

### account_balances

Keep the current concept, but ensure every account belongs to a family through
`accounts.family_id`.

Minimum additional expectation:

- all balance queries join or filter through `accounts.family_id`;
- no balance endpoint accepts only `account_id` without checking membership.

## Transactions and internal links

### transactions

Minimum fields:

- `id text primary key`
- `family_id uuid not null references families(id)`
- `account_id uuid not null references accounts(id)`
- `connection_id uuid references provider_connections(id)`
- `external_id text`
- `posted_at date not null`
- `reference_month text not null`
- `amount numeric(14,2) not null`
- `currency text not null default 'BRL'`
- `description text not null`
- `raw_description text`
- `category text`
- `category_source text`
- `tag_id uuid`
- `bucket_id uuid`
- `savings_goal_id uuid`
- `hidden boolean not null default false`
- `note text`
- `counterparty_name text`
- `counterparty_document_hash text`
- `merchant_key text`
- `source text not null`
- `metadata_json jsonb`
- `created_at timestamptz not null`
- unique `(family_id, source, external_id)` when `external_id` is present

The existing sign conventions and helper functions remain the source of truth
for financial meaning. The migration should not reinterpret historical amounts.

### transaction_links

Minimum fields:

- `id uuid primary key`
- `family_id uuid not null references families(id)`
- `source_transaction_id text not null references transactions(id)`
- `target_transaction_id text not null references transactions(id)`
- `link_type text not null`
- `confidence real`
- `source text not null`
- `metadata_json jsonb`
- `created_at timestamptz not null`

`link_type` starts with `internal_transfer`, `card_payment`, `refund`,
`duplicate_candidate`, and `manual_match`.

This table is the foundation for understanding connections between family
accounts without deleting either side of a movement. A PIX between two family
accounts remains two transactions linked as an internal transfer. A payment from
checking to credit card remains two transactions linked as a card payment.

## Existing domain tables

Every table that contains family-owned financial configuration or financial
records must carry `family_id` directly, unless it belongs to a parent row that
already enforces the family boundary and every access path checks that parent.

Add `family_id` directly to:

- `family_profiles`, replacing the single-row `profile` concept;
- `tags`;
- `budget_buckets`;
- `bucket_rules`;
- `tag_rules`;
- `savings_goals`;
- `portfolio_assets`;
- `portfolio_transactions`;
- `allocation_targets`;
- `investment_profile`;
- `asset_questions` if customized per family;
- `asset_answers`;
- `classification_audit_log`;
- `movement_total_settings`.

Tables tied to accounts, such as `account_total_settings`, may keep account ids
as their direct foreign key, but every repository must verify the account is in
the current family.

## Authorization rules

The request context exposes:

- `current_user`;
- `current_family`;
- `current_member_role`;
- `current_session`.

Rules:

- unauthenticated requests receive `401`;
- authenticated users outside a family receive `403`;
- login rate limiting receives `429`;
- disabled users or disabled families receive `403`;
- every financial query filters by `current_family.id`;
- ids supplied by the client are never trusted as authorization by themselves;
- owner/admin can manage members later, but the first slice only needs enough
  role checks to protect family data and admin-only bootstrap actions.

## Migration design

The migration creates one default family from existing production data:

- family name: `Familia Principal`;
- first user: admin user created from environment or CLI input;
- first family member: owner;
- first family person: primary financial person linked to that user.

Migration order:

1. Create PostgreSQL schema.
2. Create admin user, default family, owner membership, and primary person.
3. Copy `pluggy_items` into `provider_connections`.
4. Copy `accounts`, attach `family_id`, and map Pluggy item ids to
   `connection_id`.
5. Copy `account_balances`.
6. Copy `transactions`, attach `family_id` and `connection_id` when possible.
7. Copy tags, buckets, bucket rules, tag rules, profile data, savings goals,
   portfolio assets, portfolio transactions, settings, and audit logs.
8. Build indexes and constraints after bulk copy where practical.
9. Run count checks and family-isolation checks.
10. Keep the SQLite file as a read-only rollback artifact.

The migration script must support:

- dry-run mode;
- target database safety check to avoid overwriting non-empty production data;
- row counts by table before and after;
- sample transaction/account integrity checks;
- rollback instructions based on restoring the previous app version and SQLite
  artifact.

## Indexing and constraints

Minimum indexes:

- `family_members(user_id, family_id)`;
- `provider_connections(family_id, provider, external_item_id)`;
- `accounts(family_id, source, external_account_id)`;
- `accounts(family_id, connection_id)`;
- `transactions(family_id, account_id, posted_at desc)`;
- `transactions(family_id, reference_month)`;
- `transactions(family_id, tag_id)`;
- `transactions(family_id, bucket_id)`;
- `transactions(family_id, merchant_key)`;
- `transaction_links(family_id, source_transaction_id)`;
- `transaction_links(family_id, target_transaction_id)`;
- `login_attempts(normalized_email_hash, created_at desc)`;
- `login_attempts(ip_hash, created_at desc)`;
- `sessions(token_hash)`;
- `sessions(user_id, revoked_at, expires_at)`.

Use foreign keys for family-owned relationships wherever PostgreSQL can enforce
them. Where a child row has both `family_id` and a parent id, repositories must
still verify both values match to prevent cross-family references.

## Testing strategy

Minimum tests before the foundation is considered implemented:

- login succeeds with correct password and creates a secure session;
- wrong password is logged and does not reveal whether the email exists;
- repeated wrong password locks the user temporarily;
- repeated attempts from one IP receive `429`;
- successful login resets user failure counters;
- disabled user cannot log in;
- disabled family cannot be selected;
- a user cannot read another family's accounts, transactions, tags, buckets,
  goals, or portfolio data;
- repository methods require explicit `family_id`;
- migration dry-run reports counts without writing;
- SQLite to PostgreSQL migration preserves transaction counts and account counts;
- Pluggy item ids map to provider connections;
- internal transfer link table can store a pair of same-family transactions and
  rejects cross-family links.

## Acceptance criteria

The foundation is ready when:

- PostgreSQL schema exists with users, families, members, people, sessions,
  provider connections, account ownership, transactions, and transaction links;
- every financial table is family-scoped directly or through a checked parent;
- Basic Auth is no longer the primary app protection in the multi-family mode;
- first-party login uses secure password hashing and HttpOnly cookie sessions;
- brute-force controls are implemented and tested;
- the app can create or seed the first admin/family without public signup;
- the SQLite production data can be migrated into one default family;
- tests prove family isolation at API and repository boundaries;
- deployment has a backup and restore procedure for PostgreSQL.

## Deferred work

After this foundation:

1. Build the login UI and family switcher.
2. Add member invitation flows.
3. Add Google login by linking `user_identities.provider='google'`.
4. Add MFA if the app becomes broadly exposed.
5. Consider PostgreSQL RLS as an additional defense layer after repository
   isolation is stable.
