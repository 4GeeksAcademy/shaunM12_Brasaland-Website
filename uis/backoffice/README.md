# Brasaland Backoffice

Internal app built with Next.js + TypeScript.

## Routes

- `/`: basic backoffice dashboard entry view.

## Integration with Milestone 2

Business logic is imported from the original monorepo module in [src](../../src), without copying code.
The dashboard renders computed outputs (reports, filters, searches) in the interface.

## Development

```bash
npm install
npm run dev
```

Create a local environment file before running:

```bash
cp .env.example .env.local
```

Available variable:

- `NEXT_PUBLIC_TRACKER_API_BASE_URL`: base URL for tracker API requests.

## Build

```bash
npm run build
npm run start
```
