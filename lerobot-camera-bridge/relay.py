"""Forward the existing localhost MJPEG bridge to LeRobot's ZMQ camera."""
import argparse
import base64
import json
import logging
from pathlib import Path
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / '.camera-tools'))
import zmq


def frames(response):
    while True:
        line = response.readline(4096)
        if not line:
            raise EOFError('Camera stream closed')
        if line.strip() != b'--frame':
            continue
        headers = {}
        while True:
            line = response.readline(4096)
            if not line:
                raise EOFError('Incomplete MJPEG headers')
            if line == b'\r\n':
                break
            key, value = line.decode('ascii').split(':', 1)
            headers[key.lower()] = value.strip()
        length = int(headers['content-length'])
        if not 0 < length < 10_000_000:
            raise ValueError('Invalid JPEG length')
        data = bytearray()
        while len(data) < length:
            chunk = response.read(length - len(data))
            if not chunk:
                raise EOFError('Incomplete JPEG')
            data.extend(chunk)
        yield data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', required=True, help='Windows WSL virtual adapter IPv4')
    parser.add_argument('--port', type=int, default=5555)
    parser.add_argument('--camera-name', default='follower_cam')
    parser.add_argument('--source', default='http://127.0.0.1:8765/camera.mjpg')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    logging.basicConfig(filename=root / 'relay.log', level=logging.INFO,
                        format='%(asctime)s %(message)s')
    with zmq.Context() as context:
        with context.socket(zmq.PUB) as publisher:
            publisher.setsockopt(zmq.SNDHWM, 1)
            publisher.setsockopt(zmq.LINGER, 0)
            publisher.bind(f'tcp://{args.bind}:{args.port}')
            logging.info('Listening on %s:%s', args.bind, args.port)
            while True:
                try:
                    with urllib.request.urlopen(args.source, timeout=5) as response:
                        logging.info('Connected to existing Windows camera bridge')
                        for jpeg in frames(response):
                            message = {'timestamps': {args.camera_name: time.time()},
                                       'images': {args.camera_name: base64.b64encode(jpeg).decode('ascii')}}
                            publisher.send_string(json.dumps(message), zmq.NOBLOCK)
                except (OSError, ValueError, EOFError, zmq.Again):
                    logging.exception('Stream interrupted; reconnecting')
                    time.sleep(2)


if __name__ == '__main__':
    main()
