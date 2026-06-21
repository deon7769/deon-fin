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

## Checks

```bash
npm test -- --run
npm run typecheck
npm run lint
npm run build
```
