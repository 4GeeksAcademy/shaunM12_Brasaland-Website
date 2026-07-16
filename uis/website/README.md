# Brasaland Website

Public corporate website (Next.js + TypeScript).

> Parent index: [../README.md](../README.md)

## Routes

- `/` — corporate home (Milestone 1 content, bilingual language toggle)

## Development

```bash
cp ../../.env.example ../../.env   # once, repo root
cd uis/website
npm install
npm run dev
```

Env: `NEXT_PUBLIC_TRACKER_API_BASE_URL` (tracker API base, if used).

## Build

```bash
npm run build && npm run start
```
