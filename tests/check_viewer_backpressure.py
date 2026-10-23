"""A stalled viewer must not stall observations or shutdown commands."""
import _bootstrap  # repository source path, no environment mutation
from threading import Event,Thread
import time
from unittest.mock import patch
from intel7_vla.recording.recorder import Recorder

blocked=Event()
entered=Event()
def slow_log(*args,**kwargs):
    entered.set()
    blocked.wait(5)

with patch('intel7_vla.recording.recorder.rr.send_blueprint'),patch('intel7_vla.recording.recorder.rr.set_time'),patch('intel7_vla.recording.recorder.rr.log',slow_log):
    app=Recorder(demo=True)
    worker=Thread(target=app.run)
    worker.start()
    try:
        assert entered.wait(2), 'Viewer did not enter the simulated stall'
        time.sleep(.5)
        assert app.status()['fps']>25,app.status()
        started=time.monotonic()
        app.commands.put(('shutdown',{}))
        worker.join(1)
        assert not worker.is_alive(), 'Viewer stall prevented shutdown'
        print(f'PASS: viewer blocked; control {app.status()["fps"]:.1f}Hz; shutdown {time.monotonic()-started:.3f}s; queue bounded at one frame')
    finally:
        blocked.set()
        app.quit.set()
        worker.join(2)
