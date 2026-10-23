"""Allow direct test execution without installing or changing the LeRobot venv."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
