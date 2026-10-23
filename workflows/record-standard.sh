#!/usr/bin/env bash
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/lerobot" || exit 1
echo 'LeRobot textbook workflow: recording + leader following + native Rerun.'
echo '60s episode / 60s reset / up to 50 NEW episodes. Saved automatically.'
echo 'Keep this Ubuntu window focused for keys: Right/n = next; Left/r = redo; Esc/q = save and quit.'
echo 'Follower moves with Leader during recording AND reset. Close after normal shutdown.'
bash /mnt/c/Users/user/rjsxo/lerobot-camera-bridge/record.sh 2>&1 | tee -a /mnt/c/Users/user/rjsxo/workflows/standard-record.log
result=${PIPESTATUS[0]}
echo "LeRobot session ended (exit $result)."
read -r -p 'Press Enter to close...' _ || true
exit "$result"
