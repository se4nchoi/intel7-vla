#!/usr/bin/env bash
# Compatibility WSL entry point.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$root/scripts/wsl/start-dataset-ui.sh" "$@"
