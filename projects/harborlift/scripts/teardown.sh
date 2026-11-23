#!/usr/bin/env bash
# Removes only this lab's compose project, never other demos.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose down -v
