"""Compatibility launcher for tests/check_training_jobs.py."""
from pathlib import Path
import runpy
import sys
path = Path(__file__).resolve().parents[1]/'tests'
sys.path.insert(0, str(path))
runpy.run_path(str(path/'check_training_jobs.py'), run_name='__main__')
