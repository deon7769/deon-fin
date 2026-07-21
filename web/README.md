# deon-fin web

Next.js frontend for the new deon-fin UI.

## Development

Run the API from the repository root:

```bash
python -m src.cli serve
```

Run the frontend:

```bash
cd web
npm install
npm run dev
```

The app opens at `http://localhost:3000` and reads the API base URL from `NEXT_PUBLIC_API_URL`.

The session login UI is controlled by `NEXT_PUBLIC_AUTH_ENABLED`. Keep it unset or `false`
while the production app still uses the legacy Basic Auth gate. Set it to `true` only when the
PostgreSQL auth/session cutover is being tested with backend `AUTH_SESSION_ENABLED=true`.

## Production

`next build` exports static files to `web/out`. The project Dockerfile copies that export to
`/app/web_dist`, and FastAPI serves it at `/` with the API under `/api`. The legacy Pluggy UI remains
available at `/legacy`.

Because this is a static export, `NEXT_PUBLIC_AUTH_ENABLED` is baked into the generated frontend at
build time.

## Checks

```bash
npm test -- --run
npm run typecheck
npm run lint
npm run build
```
