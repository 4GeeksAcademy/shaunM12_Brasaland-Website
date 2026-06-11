import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const incidentApiOrigin =
  process.env.INCIDENTS_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

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
        destination: `${incidentApiOrigin}/api/incidents/:path*`,
      },
    ];
  },
};

export default nextConfig;
