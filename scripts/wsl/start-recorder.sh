#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/lerobot"
exec uv run --no-sync python /mnt/c/Users/user/rjsxo/workflows/native-viewer.py >> /mnt/c/Users/user/rjsxo/workflows/recorder.log 2>&1
