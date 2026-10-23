#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/lerobot"
args=()
if [[ -n "${1:-}" ]]; then args=(--episode "$1"); fi
exec uv run --no-sync python /mnt/c/Users/user/rjsxo/workflows/view_episodes.py "${args[@]}"
