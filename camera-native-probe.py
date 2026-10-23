"""Compatibility launcher for tools/diagnostics/camera-native-probe.py."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[0]/'tools/diagnostics/camera-native-probe.py'), run_name='__main__')
