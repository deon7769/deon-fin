# Static Reference Data Boundary Design

## Goal

Restore normal Git operation for the VPS operator while keeping financial data,
secrets, and backups private to the non-root application user.

## Problem

The VPS hardening intentionally sets `data/` directories to `0700` and files
below them to `0600`, owned by the container UID/GID. That boundary is correct
for runtime financial data, but `data/country_ratings.json` is a versioned,
non-sensitive reference asset. Because Git must inspect every tracked path,
`git status` as the SSH user reports `Permission denied` for that file.

The same placement also makes the investment map depend on the host volume for
static application data. The Docker image copies `src/`, but it does not copy
`data/`; the ratings file reaches the container only because production mounts
the private host directory at `/app/data`.

## Decision

Move the versioned ratings dataset from `data/country_ratings.json` to
`src/agent/portfolio/country_ratings.json`, beside its Python loader. Change the
loader to resolve the JSON with `Path(__file__).with_suffix(".json")`.

This creates two explicit boundaries:

- `data/` contains only ignored runtime state and remains private at
  `0700`/`0600`.
- `src/agent/portfolio/` contains the code and immutable reference data shipped
  in the application image.

No ACL, shared host group, or permanent permission widening will be introduced.

## Components and Data Flow

1. `src/agent/portfolio/country_ratings.py` resolves the adjacent JSON asset.
2. `load_country_ratings()` continues to read and cache the dataset once per
   process; its public API and response payloads do not change.
3. `Dockerfile` already copies the complete `src/` directory, so the JSON asset
   is included without another image layer or Compose volume.
4. The portfolio router continues to consume the loader through the existing
   module interface.

Missing or malformed reference data remains a startup/request failure at the
loader boundary. Silent fallback is deliberately out of scope because a map
served with incomplete sovereign ratings would be misleading.

## File Changes

- Move `data/country_ratings.json` to
  `src/agent/portfolio/country_ratings.json` without changing its contents.
- Update `DATA_PATH` in `src/agent/portfolio/country_ratings.py`.
- Add a regression contract in `tests/test_country_ratings.py` proving that the
  dataset is adjacent to the loader and readable.
- Update the F4 investment specs that still name the old `data/` path.

The deploy permission script, Compose labels, database files, backups, secrets,
portfolio API schema, and ratings values are unchanged.

## Test Strategy

Implementation follows TDD:

1. Add a test asserting that `DATA_PATH` equals the loader path with a `.json`
   suffix and that the file is readable.
2. Run the focused test and observe RED against the current `data/` location.
3. Move the JSON and update the loader.
4. Run the country-ratings tests, then the complete backend suite.
5. Run frontend Vitest, typecheck, lint, and build because the map consumes the
   same API contract.
6. Confirm the Docker image contains
   `/app/src/agent/portfolio/country_ratings.json`.

## VPS Rollout

The active checkout cannot fast-forward normally while the old tracked file is
inside an unreadable directory. The rollout therefore uses a one-time, narrow
migration:

1. Verify the target commit contains the new `src/agent/portfolio` JSON blob.
2. Remove only the old static `data/country_ratings.json` as root.
3. Temporarily set `data/` to execute-only traversal for non-owners (`0711`) so
   Git can confirm the tracked path is absent without listing or reading private
   files.
4. Fast-forward the checkout as the normal SSH/Git user, never as root.
5. Restore `data/` to `0700` in a guaranteed cleanup step, including on a failed
   fast-forward.
6. Run `scripts/vps_deploy.sh`, which reasserts ownership and all private modes,
   executes tests, rebuilds the image, restarts the service, and performs smoke
   checks.

After deployment, `git status --short --branch` as the SSH user must complete
without permission warnings, `git ls-files data` must return no paths, and the
public health endpoint and investment map API must remain healthy.

## Rollback

Revert the implementation commit, temporarily make `data/` traversable for the
Git operation, and restore the tracked JSON from Git. Run the deploy script and
verify `data/` returns to `0700` with files at `0600`.

Rollback does not modify the SQLite database or its backups.

## Out of Scope

- Changing runtime data ownership or privacy modes.
- Repairing the unrelated OpenClaw watchdog failure.
- Consolidating the long-running feature branch into `main`.
- Pruning merged branches or deciding the destination of the untracked handoff
  document.
