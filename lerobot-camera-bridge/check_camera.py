"""Compatibility launcher for tools/diagnostics/check_camera.py."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'tools/diagnostics/check_camera.py'), run_name='__main__')
