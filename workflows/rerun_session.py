"""Compatibility entry point; implementation: intel7_vla.recording.rerun_session."""
import importlib
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
if __name__ == '__main__':
    runpy.run_module('intel7_vla.recording.rerun_session', run_name='__main__')
else:
    sys.modules[__name__] = importlib.import_module('intel7_vla.recording.rerun_session')
