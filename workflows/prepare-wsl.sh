#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/lerobot"
uv run --no-sync python -c 'import lerobot, cv2, zmq, rerun; from lerobot.cameras.zmq import ZMQCamera'
for serial in 5B90149145 5B90150163; do
  device="/dev/serial/by-id/usb-1a86_USB_Single_Serial_${serial}-if00"
  [[ -r "$device" && -w "$device" ]] || { echo "Serial port missing or permission denied: $device (check USB and dialout group)"; exit 1; }
done
uv run --no-sync python /mnt/c/Users/user/rjsxo/lerobot-camera-bridge/patch_zmq_rgb.py
uv run --no-sync python /mnt/c/Users/user/rjsxo/workflows/patch_rerun_images.py
uv run --no-sync python /mnt/c/Users/user/rjsxo/lerobot-camera-bridge/check_camera.py --seconds 2
uv run --no-sync python /mnt/c/Users/user/rjsxo/lerobot-camera-bridge/check_camera.py --seconds 2 --camera-name field_cam --port 5556
bash /mnt/c/Users/user/rjsxo/lerobot-camera-bridge/record.sh --check
echo 'WSL configuration ready. Connecting robots for native Rerun.'
