#!/usr/bin/env python3
"""Dedicated scheduler process for DEV-53 (not inside FastAPI).

Sleeps until the next America/Bogota 02:00, then runs ``nightly_export.py``.
Cron equivalent: ``0 2 * * *`` with ``TZ=America/Bogota``.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"
for _path in (str(API_ROOT), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from job_runner.schedule import seconds_until_next_run  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("nightly_scheduler")

SCRIPT = Path(__file__).resolve().parent / "nightly_export.py"


def main() -> int:
    logger.info(
        "Nightly scheduler started (cron 0 2 * * * America/Bogota). "
        "Script=%s",
        SCRIPT,
    )
    while True:
        wait_s = seconds_until_next_run()
        logger.info("Sleeping %.0f seconds until next Bogota 02:00 run", wait_s)
        time.sleep(wait_s)
        logger.info("Firing nightly_export.py")
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=False,
        )
        if completed.returncode != 0:
            logger.error(
                "nightly_export exited with code %s", completed.returncode
            )
        # Avoid tight loop if the clock hasn't advanced past the slot.
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
