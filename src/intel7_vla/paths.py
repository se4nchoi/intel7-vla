"""Source, static asset and runtime paths shared across entry points."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = PROJECT_ROOT/'web/dataset-desk'
# Logs, status files and stop requests shared by Windows launchers and WSL servers (gitignored).
RUNTIME_ROOT = Path(os.environ.get('VLA_RUNTIME_DIR', PROJECT_ROOT/'runtime'))
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
