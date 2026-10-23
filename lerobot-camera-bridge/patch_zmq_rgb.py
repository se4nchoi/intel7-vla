"""Compatibility launcher for tools/patches/patch_zmq_rgb.py."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'tools/patches/patch_zmq_rgb.py'), run_name='__main__')
