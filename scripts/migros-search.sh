#!/bin/bash
# Search Migros products. Usage: migros-search.sh QUERY
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/migros-api.py" search "$@"
