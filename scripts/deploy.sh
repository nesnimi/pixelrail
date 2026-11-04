#!/usr/bin/env bash
# --apply switches the PixelRail process after IPC readiness; --no-start is offline.
set -euo pipefail
script_dir="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
exec python3 "$script_dir/deployment.py" deploy "$@"
