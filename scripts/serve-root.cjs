const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const host = "0.0.0.0";
const port = 3000;
const rootDir = path.resolve(__dirname, "..");
const pidFile = "/tmp/brasaland-server.pid";

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".txt": "text/plain; charset=utf-8"
};

function safeResolve(requestUrlPath) {
  const rawPath = decodeURIComponent(requestUrlPath.split("?")[0]);
  const normalized = path.normalize(rawPath).replace(/^([.][.][/\\])+/, "");
  let resolved = path.join(rootDir, normalized);

  if (resolved.endsWith(path.sep)) {
    resolved = path.join(resolved, "index.html");
  }

  if (path.extname(resolved) === "") {
    resolved = path.join(resolved, "index.html");
  }

  return resolved;
}

function exists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

const server = http.createServer((req, res) => {
  const requestedPath = req.url === "/" ? "/index.html" : req.url || "/index.html";
  const filePath = safeResolve(requestedPath);

  if (!filePath.startsWith(rootDir)) {
    res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Forbidden");
    return;
  }

  if (!exists(filePath)) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Not Found");
    return;
  }

  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    "Content-Type": mimeTypes[ext] || "application/octet-stream"
  });
  fs.createReadStream(filePath).pipe(res);
});

server.listen(port, host, () => {
  fs.writeFileSync(pidFile, String(process.pid));
  console.log(`Serving project root at http://${host}:${port}`);
});

function shutdown() {
  try {
    if (fs.existsSync(pidFile)) {
      fs.unlinkSync(pidFile);
    }
  } catch {
    // Ignore cleanup errors.
  }

  server.close(() => {
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
