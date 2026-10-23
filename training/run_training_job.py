"""Dataset Desk job supervisor entry point (WSL)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'src'))
from intel7_vla.training.runner import run_job

if __name__ == '__main__':
    run_job(sys.argv[1])
