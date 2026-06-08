# Carpeta `apps`

Esta carpeta contiene **todas las aplicaciones del monorepo** relacionadas con la compañía para el proyecto transversal de AI Engineering (por ejemplo: aplicaciones web, APIs, dashboards internos, portales de clientes, etc.).

Cada subcarpeta dentro de `uis/` debe corresponder a **una aplicación concreta** (por ejemplo `web-portal`, `admin-api`, `backoffice-dashboard`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar en un único monorepo todas las aplicaciones que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) las aplicaciones que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlas en desarrollo, pruebas y producción.

## Aplicaciones en esta carpeta

- `website`: Sitio corporativo público (Next.js + TypeScript) con el contenido del milestone 1 migrado a `/`.
- `backoffice`: Aplicación interna de dashboard (Next.js + TypeScript) con integración de salidas de lógica de negocio del milestone 2.
