"""Start local training using the same job manager as Dataset Desk."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from intel7_vla.training.cli import main

if __name__=='__main__':
    main()
