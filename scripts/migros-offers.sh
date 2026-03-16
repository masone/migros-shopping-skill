#!/bin/bash
# Show current offers/promotions
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/migros-api.py" offers
