#!/usr/bin/env bash
# Same transactional deployment engine, dry-run unless --apply is explicit.
set -euo pipefail
script_dir="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
exec python3 "$script_dir/deployment.py" deploy "$@"
