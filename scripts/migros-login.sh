#!/bin/bash
# Login to Migros and cache tokens (mobile + web session)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/migros-api.py" login
