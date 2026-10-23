#!/usr/bin/env bash
# Compatibility entry point for the WSL recording CLI.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$root/scripts/wsl/record.sh" "$@"
