"""Local-only DirectShow to MJPEG bridge for Physical AI Studio."""
import sys
from pathlib import Path

from intel7_vla.paths import PROJECT_ROOT, RUNTIME_ROOT
sys.path.insert(0, str(PROJECT_ROOT / '.camera-tools'))
import cv2
import comtypes
from pygrabber.dshow_graph import FilterGraph
import argparse
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = RUNTIME_ROOT
parser = argparse.ArgumentParser()
parser.add_argument('--camera-name', default='icspring camera')
parser.add_argument('--name', default='follower_cam')
parser.add_argument('--port', type=int, default=8765)
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler(ROOT / ('bridge.log' if args.port==8765 else 'field-bridge.log'), encoding='utf-8')],force=True)
condition = threading.Condition()
jpeg = None
sequence = 0
last_frame_at = 0.0


def capture():
    global jpeg, sequence, last_frame_at
    while True:
        cap = None
        try:
            # DirectShow enumeration matches OpenCV CAP_DSHOW indices. Resolve
            # by device name each reopen, never assume USB enumeration order.
            logging.info('Enumerating DirectShow cameras for %s',args.camera_name)
            comtypes.CoInitialize()
            try:
                names = FilterGraph().get_input_devices()
            finally:
                comtypes.CoUninitialize()
            matches = [i for i,name in enumerate(names) if name.casefold()==args.camera_name.casefold()]
            if len(matches)!=1:
                raise RuntimeError(f'Expected one {args.camera_name!r}; DirectShow devices: {names}')
            index = matches[0]
            logging.info('Opening %s at index %s (devices=%s)',args.camera_name,index,names)
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                logging.warning('Camera unavailable; retrying')
                time.sleep(3)
                continue
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            logging.info('%s: %s, index %s, connected at %sx%s',args.name,args.camera_name,index,
                         cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            failures = 0
            while failures < 5:
                ok, frame = cap.read()
                if not ok:
                    failures += 1
                    time.sleep(.1)
                    continue
                failures = 0
                ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                if ok:
                    with condition:
                        jpeg = encoded.tobytes()
                        sequence += 1
                        last_frame_at = time.monotonic()
                        condition.notify_all()
        except Exception:
            logging.exception('Capture failed; reconnecting')
        finally:
            if cap is not None: cap.release()
        time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/health':
            with condition:
                fresh = time.monotonic() - last_frame_at < 3
                data = json.dumps({'ok': fresh, 'frames': sequence,'camera':args.name,'device':args.camera_name}).encode()
            self.send_response(200 if fresh else 503)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == '/frame.jpg':
            with condition: data = jpeg
            if data is None: self.send_error(503); return
            self.send_response(200)
            self.send_header('Content-Type','image/jpeg')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(data);return
        if self.path != '/camera.mjpg':
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        previous = -1
        try:
            while True:
                with condition:
                    ready = condition.wait_for(
                        lambda: sequence != previous and jpeg is not None, timeout=5)
                    if not ready or time.monotonic() - last_frame_at > 3:
                        return
                    data, previous = jpeg, sequence
                self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '
                                 + str(len(data)).encode() + b'\r\n\r\n' + data + b'\r\n')
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.daemon_threads = True
    threading.Thread(target=capture, daemon=True).start()
    logging.info('Bridge listening on http://127.0.0.1:%s/camera.mjpg',args.port)
    server.serve_forever()
