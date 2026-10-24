#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/lerobot"
mkdir -p "$root/runtime"
export PYTHONPATH="$root/src"
exec uv run --no-sync python -m intel7_vla.recording.native_viewer >> "$root/runtime/recorder.log" 2>&1
