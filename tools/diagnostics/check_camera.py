"""Camera-only WSL test. Does not open robot serial ports."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys
import time

import cv2
import numpy as np
from lerobot.cameras.zmq import ZMQCamera, ZMQCameraConfig

parser = argparse.ArgumentParser()
parser.add_argument('--view', action='store_true')
parser.add_argument('--seconds', type=float, default=5)
parser.add_argument('--camera-name',default='follower_cam')
parser.add_argument('--port',type=int,default=5555)
args = parser.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from intel7_vla.common.camera_address import camera_host
gateway = camera_host()
root = Path(__file__).resolve().parent

# Verify the actual driver's JPEG decode returns RGB, independent of the scene.
red_bgr = np.zeros((32, 32, 3), dtype=np.uint8)
red_bgr[:, :, 2] = 255
_, jpeg = cv2.imencode('.jpg', red_bgr)
payload = json.dumps({'images': {'follower_cam': base64.b64encode(jpeg).decode()}})
class FakeSocket:
    def recv_string(self):
        return payload
probe = ZMQCamera(ZMQCameraConfig(server_address=gateway, camera_name='follower_cam'))
probe._connected, probe.context, probe.socket = True, object(), FakeSocket()
rgb = probe._read_from_hardware()
assert rgb[:, :, 0].mean() > 250 and rgb[:, :, 2].mean() < 5, 'RGB conversion failed'
print('RGB decode check passed', flush=True)

camera = ZMQCamera(ZMQCameraConfig(server_address=gateway, camera_name=args.camera_name,port=args.port,
                                  width=640, height=480, fps=30))
try:
    camera.connect()
    if args.view:
        import rerun as rr
        rr.init('Windows webcam -> WSL LeRobot')
        rr.spawn(memory_limit='128MB')
    start = time.monotonic()
    count = 0
    while time.monotonic() - start < args.seconds:
        frame = camera.async_read(timeout_ms=3000)
        assert frame.shape == (480, 640, 3), frame.shape
        if args.view:
            rr.set_time('frame', sequence=count)
            rr.log('follower_cam', rr.Image(frame))
        count += 1
    elapsed = time.monotonic() - start
    cv2.imwrite(str(root / (args.camera_name+'-check.jpg')), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    result = {'frames': count, 'seconds': round(elapsed, 2), 'fps': round(count / elapsed, 2),
              'shape': list(frame.shape), 'gateway': gateway, 'rgb_test': 'passed','camera':args.camera_name}
    (root / 'check-result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
finally:
    camera.disconnect()
