# `apps` Folder

This folder contains **all the applications of the monorepo** related to the company for the cross-functional AI Engineering project (for example: web applications, APIs, internal dashboards, customer portals, etc.).

Each subfolder inside `uis/` must correspond to **one specific application** (for example: `web-portal`, `admin-api`, `backoffice-dashboard`) and include its own technical and functional documentation.

- **Main purpose**: to centralize in a single monorepo all the applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them in development, testing, and production environments.

## Applications in this folder

- `website`: Public corporate site (Next.js + TypeScript) with milestone 1 content migrated to `/`.
- `backoffice`: Internal dashboard app (Next.js + TypeScript) integrating milestone 2 business logic outputs.
