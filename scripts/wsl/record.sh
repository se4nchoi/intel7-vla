#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/lerobot"
GATEWAY=$(python3 /mnt/c/Users/user/rjsxo/workflows/camera_address.py)
CAMERAS="{\"follower_cam\":{\"type\":\"zmq\",\"server_address\":\"$GATEWAY\",\"port\":5555,\"camera_name\":\"follower_cam\",\"width\":640,\"height\":480,\"fps\":30},\"field_cam\":{\"type\":\"zmq\",\"server_address\":\"$GATEWAY\",\"port\":5556,\"camera_name\":\"field_cam\",\"width\":640,\"height\":480,\"fps\":30}}"
export LEROBOT_RERUN_MEMORY_LIMIT=128MB
RESUME=false
if [[ -f "$HOME/.cache/huggingface/lerobot/se4nchoi/messi/meta/info.json" ]]; then RESUME=true; fi
ARGS=(
  --robot.type=so101_follower
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90150163-if00
  --robot.id=follower
  --robot.use_degrees=false
  "--robot.cameras=$CAMERAS"
  --teleop.type=so101_leader
  --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90149145-if00
  --teleop.id=leader
  --teleop.use_degrees=false
  --dataset.repo_id=se4nchoi/messi
  "--dataset.root=$HOME/.cache/huggingface/lerobot/se4nchoi/messi"
  "--dataset.single_task=Pick up the red ball, identify the open lane to the left or right of the pickup location, and roll or shoot the ball between the two cones to score a goal."
  --dataset.no_stamp=true
  --dataset.fps=30
  --dataset.num_episodes=50
  --dataset.episode_time_s=60
  --dataset.reset_time_s=60
  --dataset.push_to_hub=false
  "--resume=$RESUME"
  --display_data=true
  --display_compressed_images=true
  --play_sounds=false
)
if [[ "${1:-}" == "--check" ]]; then
  shift
  uv run --no-sync python /mnt/c/Users/user/rjsxo/lerobot-camera-bridge/preflight.py "${ARGS[@]}" "$@"
else
  exec uv run --no-sync lerobot-record "${ARGS[@]}" "$@"
fi
