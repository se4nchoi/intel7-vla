#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/lerobot"
args=()
if [[ -n "${1:-}" ]]; then args=(--episode "$1"); fi
exec uv run --no-sync python "$root/src/intel7_vla/datasets/replay.py" "${args[@]}"
