# Brasaland Website

Public corporate website built with Next.js + TypeScript.

## Routes

- `/`: corporate home page migrated from milestone 1, including all sections and bilingual language toggle.

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

- `NEXT_PUBLIC_TRACKER_API_BASE_URL`: base URL for tracker API integrations.

## Build

```bash
npm run build
npm run start
```
