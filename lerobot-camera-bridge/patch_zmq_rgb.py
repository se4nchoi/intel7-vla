"""Fix v0.6.1 ZMQCamera ignoring its RGB color_mode, preserving the original."""
from pathlib import Path
import lerobot.cameras.zmq.camera_zmq as module

path = Path(module.__file__)
source = path.read_text()
old = '        return frame\n\n    @check_if_not_connected\n    def read('
new = ('        if self.color_mode == ColorMode.RGB:\n'
       '            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)\n'
       '        return frame\n\n    @check_if_not_connected\n    def read(')
if new in source:
    print('ZMQ RGB fix already installed')
elif source.count(old) == 1:
    backup = path.with_suffix('.py.before-rgb-fix')
    if not backup.exists():
        backup.write_text(source)
    path.write_text(source.replace(old, new))
    print('Installed ZMQ RGB fix:', path)
else:
    raise SystemExit('Unsupported source version; no files changed')
