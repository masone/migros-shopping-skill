#!/bin/bash
# Add product to online basket. Usage: migros-add.sh PRODUCT_ID [QUANTITY]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/migros-api.py" add "$@"
