#!/usr/bin/env bash
# setup-wsl.sh — Ubuntu 24.04 (WSL2) 안에서 로봇 실습 준비 (한 번만)
#   실행:  sudo bash setup-wsl.sh
#   하는 일: 필수 패키지 설치 · 시리얼/카메라 권한 그룹 · udev 규칙 · 커널 모듈 확인
set -euo pipefail

if [[ $EUID -ne 0 ]]; then echo "sudo bash $0 으로 실행하세요"; exit 1; fi
TARGET_USER="${SUDO_USER:-$(getent passwd 1000 | cut -d: -f1)}"

echo "[1/4] 패키지 설치 (git, ffmpeg, 빌드 도구, 카메라/USB 진단 도구)"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git curl ffmpeg build-essential cmake pkg-config python3-dev \
    libevdev-dev v4l-utils usbutils tree

echo "[2/4] $TARGET_USER 를 dialout(시리얼) · video(카메라) · plugdev 그룹에 추가"
usermod -aG dialout,video,plugdev "$TARGET_USER"

echo "[3/4] udev 규칙 — SO-101 모터보드(1a86 계열)와 카메라를 누구나 읽고 쓰게"
cat > /etc/udev/rules.d/99-so101-cameras.rules <<'EOF'
# SO-ARM101 motor bus boards (CH343 1a86:55d3, CH340 1a86:7523, CH9102 1a86:55d4)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666"
# USB cameras (UVC)
SUBSYSTEM=="video4linux", MODE="0666"
EOF
udevadm control --reload-rules
udevadm trigger

echo "[4/4] 커널 모듈 확인 (cdc_acm = /dev/ttyACM*, uvcvideo = /dev/video*)"
modprobe -a cdc_acm uvcvideo || true
lsmod | grep -E '^(cdc_acm|uvcvideo|vhci_hcd)' || true

echo
echo "완료. 그룹 적용을 위해 Windows PowerShell 에서:  wsl --shutdown  후 Ubuntu 다시 열기"
