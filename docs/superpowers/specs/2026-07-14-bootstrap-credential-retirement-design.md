# Bootstrap Credential Retirement Design

## Goal

Remove the obsolete plaintext bootstrap credential from the VPS after the
owner password has been changed, without changing authentication behavior,
environment variables, database records, or deploy configuration.

## Context

The VPS still contains `data/secrets/initial-auth-owner.txt`, created on
2026-07-02 with mode `0600`. The user confirmed that the owner password used by
the session login has already been changed.

The current application does not reference that file. Session-login passwords
are passed to the authentication code, hashed with the existing password
helper, and persisted only as a password hash in PostgreSQL. The similarly
named environment values have different responsibilities:

- `APP_PASSWORD` belongs to the legacy Basic Auth fallback.
- `POSTGRES_PASSWORD` authenticates the PostgreSQL service.
- No environment key stores the current session-login password.

The file is therefore a stale operational artifact, not a runtime dependency
or a recovery source for the active password.

## Decision

Retire only `data/secrets/initial-auth-owner.txt` from the live VPS. Keep the
`data/secrets/` directory and its established `0700` privacy boundary.

The metadata-only probe confirmed these required invariants:

- `data/secrets/`: real directory, not a symlink, mode `0700`, owner `ubuntu:ubuntu`.
- `data/secrets/initial-auth-owner.txt`: when present, regular non-symlink file, mode `0600`, owner `ubuntu:ubuntu`.
- Any canonical-path, type, mode, or ownership mismatch stops the procedure without deleting anything.

Do not add automatic deletion to the application or deploy script. Bootstrap
credential handling is an operator action, and coupling account updates to a
host filesystem path would make authentication depend on deployment layout.

The removal is a normal unlink of the exact path. The procedure does not claim
forensic secure erasure on SSD or virtualized storage. The security improvement
is that the obsolete plaintext credential is no longer addressable through the
live filesystem.

## Operational Flow

1. Confirm the VPS checkout is `/opt/projetos/financas-agent` and record the
   current branch and commit.
2. Inspect only metadata for the target file; never print or copy its contents.
3. Require the exact target to be a regular file below `data/secrets/`.
4. Remove only `data/secrets/initial-auth-owner.txt` with elevated host access.
5. Verify the file is absent and `data/secrets/` remains mode `0700`.
6. Verify the public login boundary and `/api/health` still respond normally.
7. Verify Git state is unchanged apart from the two already-known untracked
   paths: `.cursor/` and `docs/repasse-2026-07-07.md`.

No application restart or deploy is required because no running component
reads the file.

## Failure Handling

- If the target is missing before removal, treat the retirement as already
  complete and continue with verification.
- If the target is not a regular file, has a different resolved parent, or the
  parent is not `data/secrets/`, stop without deleting anything.
- If permission or ownership checks fail, stop and report the actual metadata;
  do not widen the directory mode.
- If public health changes after removal, investigate the live service. Do not
  restore the obsolete plaintext credential as a rollback mechanism.

## Validation

The code baseline must remain green before the operational change:

- Backend: `499 passed`, with environment-dependent tests skipped as expected.
- Frontend: `152 passed`.

After removal, validate:

- Both `test ! -e` and `test ! -L` hold for the exact
  `data/secrets/initial-auth-owner.txt` target.
- `stat` reports mode `0700` and owner `ubuntu:ubuntu` for `data/secrets/`.
- `https://fin.deonlab.tech/api/health` returns `{"status":"ok"}`.
- The public root continues to redirect unauthenticated users to `/login`.
- The active branch remains aligned with the GitHub `deon` branch.

## Rollback

There is no plaintext-file rollback. If the owner later loses access, use the
documented account recovery or an explicit administrative password reset that
creates a new password hash. Do not recreate the retired credential from logs,
shell history, backups, or copied files.

## Out of Scope

- Changing the owner password, email, sessions, or PostgreSQL data.
- Changing `.env`, `APP_PASSWORD`, `AUTH_PEPPER`, or database credentials.
- Automatically deleting future bootstrap output.
- Modifying backup retention or private-file permissions.
- Addressing dependency audit warnings or migrations executed per request.
