#!/bin/sh
set -e

cd /app/uis/website
./node_modules/.bin/next dev --webpack -p 3000 &
WEBSITE_PID=$!

cd /app/uis/backoffice
./node_modules/.bin/next dev --webpack -p 3001 &
BACKOFFICE_PID=$!

cleanup() {
  kill "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null || true
}

trap cleanup INT TERM
wait "$WEBSITE_PID" "$BACKOFFICE_PID"
