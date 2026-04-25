#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl -sS -X POST "${BASE_URL}/api/v1/normalize/base" \
  -H "accept: application/json"
