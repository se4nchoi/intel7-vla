"""Source, static asset and legacy runtime paths shared across entry points."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = PROJECT_ROOT/'web/dataset-desk'
# Preserve the location consumed by existing Windows launchers and active servers.
RUNTIME_ROOT = Path(os.environ.get('VLA_RUNTIME_DIR', PROJECT_ROOT/'workflows'))
