const fs = require("node:fs");

const pidFile = "/tmp/brasaland-server.pid";

try {
  if (!fs.existsSync(pidFile)) {
    console.log("No running server found");
    process.exit(0);
  }

  const pidValue = fs.readFileSync(pidFile, "utf8").trim();
  const pid = Number(pidValue);

  if (!Number.isInteger(pid) || pid <= 0) {
    fs.unlinkSync(pidFile);
    console.log("Removed invalid PID file");
    process.exit(0);
  }

  try {
    process.kill(pid, "SIGTERM");
    console.log(`Stopped server process ${pid}`);
  } catch {
    console.log("Server process was not running");
  }

  fs.unlinkSync(pidFile);
  process.exit(0);
} catch (error) {
  console.error("serve:stop failed", error);
  process.exit(1);
}
