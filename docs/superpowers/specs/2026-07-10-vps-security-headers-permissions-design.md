# VPS Security Headers and File Permissions Design

## Goal

Harden the public Deon Fin deployment without changing authentication behavior,
backup scheduling, backup encryption, or financial data.

## Scope

This slice changes two boundaries only:

1. Traefik response headers for `https://fin.deonlab.tech`.
2. File permissions for the existing `.env`, SQLite data, secrets, and local
   backup files on the VPS.

The existing VPS backup script remains the owner of backup orchestration. This
slice only ensures that files it creates are private to the application owner.

## Design decisions

### Edge headers in Traefik

The headers belong in the Traefik middleware, not FastAPI. Traefik owns TLS and
therefore can apply HSTS correctly before the request reaches the container. A
single `financas-security` middleware will be added to the existing router
chain after `tailscale-only@docker`.

The middleware will emit:

- HSTS for 180 days (`stsSeconds=15552000`), without `includeSubDomains` and
  without preload. Other Deon Lab subdomains are deliberately out of scope.
- `X-Content-Type-Options: nosniff`.
- frame denial and `frame-ancestors 'none'`.
- `Referrer-Policy: strict-origin-when-cross-origin`.
- `Permissions-Policy` denying geolocation, camera, microphone, payment, and
  USB APIs.
- A restrictive CSP that permits the static Next application, inline runtime
  bootstrap required by the static export, the Pluggy Connect widget, and
  Carto map tiles:

  ```text
  default-src 'self'; base-uri 'self'; object-src 'none';
  frame-ancestors 'none'; form-action 'self';
  script-src 'self' 'unsafe-inline' https://cdn.pluggy.ai;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https://*.basemaps.cartocdn.com;
  font-src 'self' data:; connect-src 'self' https://*.pluggy.ai;
  frame-src https://*.pluggy.ai
  ```

`unsafe-inline` is limited to scripts and styles because the statically
exported Next application requires inline bootstrap/style content. The policy
does not allow arbitrary third-party origins.

### Private files on the VPS

`scripts/vps_deploy.sh` will set `umask 077` and enforce permissions after it
repairs ownership and creates the pre-deploy backup. The target modes are:

| Path | Mode |
| --- | --- |
| `.env`, `data/financas.db`, WAL/SHM and regular files below `data/` | `0600` |
| `data/`, `data/backups/`, `data/backups/env/`, `data/secrets/` | `0700` |

The existing `APP_UID` / `APP_GID` ownership mechanism remains unchanged, so
the non-root container user retains access. The deploy stops on a permission
failure rather than starting with a weakened mode.

## Out of scope

- Encrypting backups or introducing a new backup key.
- Changing the user-owned VPS backup script or its destination.
- Database migration, classification changes, navigation changes, and
  dependency upgrades.
- Trusting `X-Forwarded-For`; proxy-IP configuration is a separate decision.

## Validation

Tests are written before production changes:

1. A Compose test asserts the router middleware chain and every security header
   label, including the CSP allow-list.
2. The deploy-script test asserts `umask 077` and the exact permission
   enforcement for `.env`, data, backups, and secrets.
3. The existing backend/frontend suites remain green.
4. After deploy, an unauthenticated HTTPS `HEAD /` confirms the headers at the
   public Traefik boundary; the existing auth redirect (`303 /login`) remains
   expected.
5. `stat` confirms that the target files are `0600` and directories are `0700`.

## Rollback

If CSP blocks Pluggy Connect or the investment map, remove only the
`financas-security` middleware from the router chain and redeploy. The
