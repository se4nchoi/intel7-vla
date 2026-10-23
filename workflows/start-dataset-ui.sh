#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/lerobot"
exec .venv/bin/python /mnt/c/Users/user/rjsxo/workflows/dataset_ui.py >> /mnt/c/Users/user/rjsxo/workflows/dataset-ui.log 2>&1
