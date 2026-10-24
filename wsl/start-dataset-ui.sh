#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HOME/lerobot"
export PATH="$HOME/lerobot/.venv/bin:$HOME/.local/bin:$PATH"
mkdir -p "$root/runtime"
exec .venv/bin/python "$root/wsl/dataset_desk.py" >> "$root/runtime/dataset-ui.log" 2>&1
