#!/usr/bin/env bash
# Restore the original install chain. Backups and user data are retained.
set -euo pipefail
script_dir="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
exec python3 "$script_dir/deployment.py" uninstall "$@"
