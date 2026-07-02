# Brasaland Website

Public corporate website built with Next.js + TypeScript.

## Routes

- `/`: corporate home page migrated from milestone 1, including all sections and bilingual language toggle.

## Development

```bash
cd /workspaces/shaunM12_Brasaland-Website
cp .env.example .env   # once (root env source of truth)
cd uis/website
npm install
npm run dev
```

Available variable:

- `NEXT_PUBLIC_TRACKER_API_BASE_URL`: base URL for tracker API integrations.

## Build

```bash
npm run build
npm run start
```
