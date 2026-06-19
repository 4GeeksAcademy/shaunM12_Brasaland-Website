import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const apiOrigin =
  process.env.BACKOFFICE_API_PROXY_TARGET ??
  process.env.INCIDENTS_API_PROXY_TARGET ??
  "http://127.0.0.1:8000";

const nextConfig = {
  experimental: {
    externalDir: true,
  },
  turbopack: {
    root: path.resolve(__dirname, "../.."),
  },
  async rewrites() {
    return [
      {
        source: "/api/incidents/:path*",
        destination: `${apiOrigin}/api/incidents/:path*`,
      },
      {
        source: "/api/suppliers/:path*",
        destination: `${apiOrigin}/api/suppliers/:path*`,
      },
      // Same-origin proxy for auth so the HttpOnly refresh cookie is first-party.
      {
        source: "/auth/:path*",
        destination: `${apiOrigin}/auth/:path*`,
      },
      {
        source: "/users",
        destination: `${apiOrigin}/users`,
      },
      {
        source: "/users/:path*",
        destination: `${apiOrigin}/users/:path*`,
      },
    ];
  },
};

export default nextConfig;
