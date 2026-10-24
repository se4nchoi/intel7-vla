"""Local-only DirectShow to MJPEG bridge for Physical AI Studio."""
import sys
from pathlib import Path


import cv2
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler(ROOT / 'bridge.log', encoding='utf-8')])
condition = threading.Condition()
jpeg = None
sequence = 0
last_frame_at = 0.0


def capture():
    global jpeg, sequence, last_frame_at
    while True:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        try:
            if not cap.isOpened():
                logging.warning('Camera unavailable; retrying')
                time.sleep(3)
                continue
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            logging.info('DirectShow camera connected at %sx%s',
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
            cap.release()
        time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/health':
            with condition:
                fresh = time.monotonic() - last_frame_at < 3
                data = json.dumps({'ok': fresh, 'frames': sequence}).encode()
            self.send_response(200 if fresh else 503)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
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
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    server.daemon_threads = True
    threading.Thread(target=capture, daemon=True).start()
    logging.info('Bridge listening on http://127.0.0.1:8765/camera.mjpg')
    server.serve_forever()
