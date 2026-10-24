"""Preserve camera frames on the Rerun timeline instead of logging them as static."""
from pathlib import Path
import lerobot.utils.rerun_visualization as module

path = Path(module.__file__)
source = path.read_text()
old = 'rr.log(key, entity=img_entity, static=True)'
new = 'rr.log(key, img_entity)'
if old in source:
    backup = path.with_suffix('.py.before-live-images')
    if not backup.exists(): backup.write_text(source)
    path.write_text(source.replace(old,new))
    print('Rerun image frames now use the live timeline')
elif new in source:
    print('Rerun image timeline fix already installed')
else:
    raise SystemExit('Unknown Rerun image logging source; no changes made')
