#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

cd "$FRONTEND_DIR"

echo "Running mocked admin Playwright coverage..."
npx playwright test tests/e2e/admin.spec.ts

if [[ "${PURECORTEX_RUN_LIVE_ADMIN_E2E:-0}" == "1" ]]; then
  echo "Running live admin Playwright smoke coverage..."
  npx playwright test tests/e2e/admin.live.spec.ts
else
  echo "Skipping live admin Playwright smoke coverage."
  echo "Set PURECORTEX_RUN_LIVE_ADMIN_E2E=1 to include the live admin test."
fi
