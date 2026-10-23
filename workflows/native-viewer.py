"""Connect LeRobot hardware and display live data in the native Rerun application."""
import json
import os
from pathlib import Path
import signal
from threading import Thread
import time
import logging

import rerun as rr
from recorder import Recorder, blueprint

ROOT = Path(__file__).resolve().parent
STATUS = ROOT / 'native-status.json'
STOP = ROOT / 'native-stop.request'


def write_status(app):
    data = {**app.status(), 'native':True, 'pid':os.getpid(), 'updated_at':time.time()}
    temporary = STATUS.with_suffix('.tmp')
    temporary.write_text(json.dumps(data),encoding='utf-8')
    temporary.replace(STATUS)


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    STOP.unlink(missing_ok=True)
    app = Recorder(teleoperate=True)
    write_status(app)
    rr.init('LeRobot live',default_blueprint=blueprint())
    rr.spawn(memory_limit='128MB')
    worker = Thread(target=app.run,daemon=True)
    worker.start()
    def stop(*_):
        if worker.is_alive(): app.commands.put(('shutdown',{}))
        else: app.quit.set()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        while not app.quit.wait(.5):
            write_status(app)
            if STOP.exists():
                STOP.unlink(missing_ok=True)
                stop()
    finally:
        worker.join(timeout=60)
        app.update(state='disconnected')
        write_status(app)
        rr.rerun_shutdown()


if __name__=='__main__': main()
