"""Windows entry point; implementation: intel7_vla.platforms.windows.camera_server."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
runpy.run_module('intel7_vla.platforms.windows.camera_server', run_name='__main__')
