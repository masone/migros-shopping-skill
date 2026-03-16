#!/bin/bash
# Show online basket contents
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/migros-api.py" cart
