"""Report active LeRobot work without inspecting unrelated command arguments."""
from pathlib import Path
import os

tokens = ('lerobot-record', 'lerobot-teleoperate', 'lerobot-rollout', 'lerobot-train',
          'lerobot_record.py', 'lerobot_teleoperate.py', 'lerobot_rollout.py', 'lerobot_train.py',
          'lerobot.scripts.lerobot_record', 'lerobot.scripts.lerobot_teleoperate',
          'lerobot.scripts.lerobot_rollout', 'lerobot.scripts.lerobot_train',
          'train_bf16.py', 'run_training_job.py', 'intel7_vla.training.bf16')
for item in Path('/proc').iterdir():
    if not item.name.isdigit() or int(item.name) == os.getpid():
        continue
    try:
        parts = (item / 'cmdline').read_bytes().decode(errors='replace').split('\0')
    except (PermissionError, FileNotFoundError, ProcessLookupError):
        continue
    for part in parts:
        name = Path(part).name
        if name in tokens or part in tokens:
            print(f'PID {item.name}: {name}')
            break
