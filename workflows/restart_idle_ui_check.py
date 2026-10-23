"""Compatibility launcher for tools/maintenance/restart_idle_ui_check.py."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'tools/maintenance/restart_idle_ui_check.py'), run_name='__main__')
