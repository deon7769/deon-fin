# PostgreSQL foundation

This is the optional PostgreSQL foundation for the multi-family cutover. It can
be started and bootstrapped before the application moves off SQLite.

This slice does not cut the app over to PostgreSQL. The web app and regular CLI
commands keep using SQLite while the active `DATABASE_URL` remains:

```text
DATABASE_URL=sqlite:///data/financas.db
```

It also does not replace the current Basic Auth gate or cut the whole app over
to PostgreSQL yet. The app now exposes the first HTTP login/session foundation
on `/api/auth/login`, `/api/auth/me`, and `/api/auth/logout` when
`DATABASE_URL` points to PostgreSQL and `AUTH_PEPPER` is configured.
User-facing family switching is still a later cutover step.

## Start local PostgreSQL

The Compose file includes an optional `postgres` service under the `postgres`
profile. Start only that service with:

```bash
docker compose --profile postgres up -d postgres
```

`POSTGRES_PASSWORD` is intentionally blank in `.env.example`. Copy or update
your real `.env` and set a real password before starting the profile:

```text
POSTGRES_DB=deon_fin
POSTGRES_USER=deon_fin
POSTGRES_PASSWORD=<real-password>
```

The local Compose service is attached to the internal Compose network and does
not currently publish port `5432` to the host.

Use the Compose service hostname from inside Compose:

```text
postgresql://deon_fin:<real-password>@postgres:5432/deon_fin
```

Use a host DSN only when PostgreSQL is reachable from the host, for example
after adding a temporary port mapping, SSH tunnel, or other explicit exposure:

```text
postgresql://deon_fin:<real-password>@localhost:5432/deon_fin
```

## Point one command at PostgreSQL

Keep `.env` on SQLite until the cutover is intentional. To point a single
host-side command at PostgreSQL, override `DATABASE_URL` only in that shell.
This example assumes the database is reachable from the host on
`localhost:5432`:

```powershell
$env:DATABASE_URL = "postgresql://deon_fin:<real-password>@localhost:5432/deon_fin"
python -m src.cli bootstrap-auth --email admin@example.com --display-name Admin
Remove-Item Env:\DATABASE_URL
```

If the database is only reachable on the Compose network, run the command from a
Compose service and use the `postgres` hostname:

```bash
docker compose --profile postgres run --rm \
  -e DATABASE_URL="postgresql://deon_fin:<real-password>@postgres:5432/deon_fin" \
  financas-agent \
  python -m src.cli bootstrap-auth --email admin@example.com --display-name Admin
```

The bootstrap command prompts for the initial admin password and confirmation.

## Bootstrap behavior

Run:

```bash
python -m src.cli bootstrap-auth --email admin@example.com --display-name Admin
```

With `DATABASE_URL` pointed at PostgreSQL, this command:

- runs the PostgreSQL Alembic migrations first;
- hashes the provided password with Argon2id;
- creates or updates the active admin user for the normalized email;
- creates or updates the default family;
- creates or updates the admin's active owner membership;
- creates or updates the first financial person linked to that user.

The command is idempotent for the configured admin email and family slug: running
it again updates those foundation records instead of creating duplicates.

## HTTP login/session foundation

The session endpoints use the PostgreSQL auth tables created in this foundation:

- `POST /api/auth/login`: validates the email/password pair, records login
  attempts, applies the basic account/IP lockout rules, creates a server-side
  session, and returns a `deon_session` HttpOnly cookie.
- `GET /api/auth/me`: reads the `deon_session` cookie and returns the active
  user/family context for valid, non-expired sessions.
- `POST /api/auth/logout`: revokes the current server-side session and clears
  the cookie.

Set `AUTH_PEPPER` before enabling these endpoints outside tests. Raw session
tokens, emails, IP addresses, and user agents are stored only as peppered
SHA-256 HMAC hashes in the auth tables.

Basic Auth still protects the rest of the app while `APP_PASSWORD` is set; only
`/api/auth/*` and `/api/health` bypass that legacy gate.

## SQLite migration dry run

Run the dry run against the legacy SQLite file:

```bash
python -m src.cli pg-migration-dry-run --sqlite-path data/financas.db
```

The dry run opens SQLite read-only, prints the default family name, prints row
counts for legacy tables, and shows the PostgreSQL target table mapping where a
table name changes. It does not connect to PostgreSQL and writes nowhere.

The report also includes a "Tabelas sem destino nesta fundacao" section when
ignored legacy tables exist:

- `savings_goals_import_state`: import marker state that must be reconciled
  manually in the complete migration.
- `quote_cache`: rebuildable quote cache that should be regenerated in
  PostgreSQL rather than copied as authoritative data.

Save this ignored-table section with the rest of the dry-run output. Nonzero
counts are not a blocker for this foundation slice, but they matter during later
migration reconciliation so operators can explain which data was intentionally
not copied.

## Production safety checklist

Before any production cutover work:

1. Back up `data/financas.db` and record where the backup artifact lives.
2. Set a production-grade `POSTGRES_PASSWORD` in the real `.env`.
3. Start PostgreSQL with `docker compose --profile postgres up -d postgres`.
4. Run and save `python -m src.cli pg-migration-dry-run --sqlite-path data/financas.db`.
5. Point only the bootstrap command at PostgreSQL and run
   `python -m src.cli bootstrap-auth --email admin@example.com --display-name Admin`.
6. Keep the SQLite backup and original SQLite database as rollback artifacts
   until the full cutover and smoke tests have passed.

Do not treat this foundation as the application cutover. The application remains
SQLite-backed until `DATABASE_URL` is changed as part of a later, explicit
multi-family migration step.
