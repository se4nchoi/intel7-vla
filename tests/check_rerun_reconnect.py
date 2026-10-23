"""Close a real disposable headless viewer and verify a fresh stream works."""
import _bootstrap  # repository source path, no environment mutation
from pathlib import Path
import socket
import subprocess
import sys
import time
import rerun as rr
from intel7_vla.recording.rerun_session import fresh_stream

with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
viewer=subprocess.Popen([str(Path(sys.executable).parent/'rerun'),'--serve-grpc',
    '--port',str(port),'--memory-limit','64MB'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.1):break
        except OSError:time.sleep(.05)
    first=fresh_stream()
    rr.connect_grpc(f'rerun+http://127.0.0.1:{port}/proxy',recording=first)
    first.log('test',rr.Scalars(1));first.flush(timeout_sec=3)
    viewer.terminate();viewer.wait(10)
    try:first.log('test',rr.Scalars(2));first.flush(timeout_sec=2)
    except RuntimeError:pass
    second=fresh_stream()
    # A file sink verifies delivery without depending on a GUI or any hardware.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmp:
        output=Path(tmp)/'reconnected.rrd'
        rr.save(str(output),recording=second)
        second.log('test',rr.Scalars(3));second.flush(timeout_sec=3);second.disconnect()
        assert output.stat().st_size>100
    print('PASS: closed viewer replaced by a new recording stream; messages delivered')
finally:
    if viewer.poll() is None:viewer.terminate();viewer.wait(10)
