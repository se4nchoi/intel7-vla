"""WSL entry point; implementation: intel7_vla.training.bf16."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
runpy.run_module('intel7_vla.training.bf16', run_name='__main__')
