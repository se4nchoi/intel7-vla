# 팀원 설치·실행 안내

이 안내는 2026-10-23 현재 코드를 기준으로 합니다. 기존 실행 PC의 환경을 그대로 패키징한 설치 프로그램은 아닙니다. 원본 설치 자료는 [Windows 설치 순서](../windows_setup/README_설치순서.md), 일상 운영은 [workflows 안내](../workflows/README.md)를 참고하세요. 원본 자료의 카메라 USB 자동 연결 절차는 현재 Windows 카메라 브리지 구성과 다르므로 아래 안내를 우선합니다.

## 1. 저장소와 필수 프로그램 (Windows)

Windows 11, WSL2 Ubuntu-24.04, Windows Python 3.12 이상, Git, usbipd-win을 준비합니다. GPU 학습에는 NVIDIA 드라이버와 WSL CUDA 지원, 실시간 Rerun 창에는 WSLg가 필요합니다. Docker Desktop은 Studio를 쓸 때 설치합니다.

```powershell
git clone https://github.com/se4nchoi/intel7-vla.git
cd intel7-vla
# 아직 설치하지 않았다면 관리자 PowerShell에서 실행
wsl --install -d Ubuntu-24.04
winget install --id dorssel.usbipd-win -e
```

설치 후 재부팅·Ubuntu 첫 로그인·사용자 생성을 완료하세요. WSL이 이미 있으면 다시 설치하지 않습니다.

## 2. PC별 설정 맞추기

현재 실행 파일에는 다음 값이 들어 있습니다. 실행 전에 자신의 환경에 맞게 수정하고 diff를 확인하세요.

| 항목 | 현재 값 | 주요 확인 파일 |
|---|---|---|
| Windows 프로젝트 경로 | `C:/Users/user/rjsxo` | `src/`, `scripts/`의 실제 구현과 OS 스크립트 |
| WSL 프로젝트 경로 | `/mnt/c/Users/user/rjsxo` | 같은 파일의 Linux 경로 |
| WSL 배포판 | `Ubuntu-24.04` | 실행 ps1, USB 자동 연결 |
| Windows Python | 사용자 홈의 `.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python[w].exe` | `scripts/windows/start.ps1`, `install-camera-bridge.ps1`, `start-field-camera.ps1`, `start-camera-relay.ps1` |
| Leader / Follower 시리얼 | `5B90149145` / `5B90150163` | `scripts/windows/start.ps1`, `scripts/wsl/prepare-wsl.sh`, `src/intel7_vla/recording/recorder.py`, `scripts/wsl/record.sh` 등 |
| 카메라 장치명 | `icspring camera` / `USB HD` | `src/intel7_vla/platforms/windows/camera_server.py`, `scripts/windows/start-field-camera.ps1` |
| 데이터셋 | `se4nchoi/messi` | Dataset Desk에서 변경, CLI는 해당 스크립트 확인 |

Windows Python은 직접 설치한 Python 경로로 바꾸면 됩니다. Codex 설치는 필요하지 않습니다. 경로 변경 대상을 찾는 PowerShell 예시:

```powershell
Get-ChildItem src,scripts -Recurse -File -Include *.ps1,*.sh,*.py |
  Select-String -Pattern 'Users[/\\]user|codex-runtimes|5B90149145|5B90150163'
```

일괄 치환으로 전체 스크립트를 다시 저장하면 셸 줄바꿈·인코딩이 바뀔 수 있으므로 편집기에서 대상 값을 수정하세요. `.sh`는 LF 줄바꿈을 유지합니다. 루트 실행 파일만 다른 폴더에 복사하면 동작하지 않습니다.

## 3. Windows 카메라 의존성

프로젝트 루트에서 **실제로 실행 스크립트에 지정한 Windows Python**으로 설치합니다. 아래 `python`이 그 실행 파일인지 먼저 확인하세요.

```powershell
python -m pip install --target .camera-tools opencv-python numpy pyzmq comtypes pygrabber
python -c "import sys; sys.path.insert(0, '.camera-tools'); import cv2, zmq, comtypes; from pygrabber.dshow_graph import FilterGraph; print(FilterGraph().get_input_devices())"
```

표시되는 장치명으로 카메라 설정을 맞춥니다. 현재 주 카메라는 `icspring camera`, 보조는 `USB HD`입니다. 현재 녹화 코드는 두 카메라를 요구합니다.

`physical-ai-camera-bridge-share/install.ps1`은 별도 단일 카메라 수업 배포용입니다. 프로젝트용 브리지와 같은 8765 포트·예약 작업명을 쓰므로 둘을 동시에 설치·실행하지 마세요.

## 4. WSL LeRobot 환경 (Ubuntu)

```bash
sudo apt update
sudo apt install -y git curl ffmpeg build-essential cmake pkg-config python3-dev libevdev-dev v4l-utils usbutils
sudo usermod -aG dialout,video,plugdev "$USER"
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
cd ~
git clone https://github.com/huggingface/lerobot.git
cd ~/lerobot
git checkout 7e241bd630a3719a56157a497ce5d08f244784f1
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[core_scripts,training,feetech,smolvla]"
uv pip install evdev pyzmq==27.2.0 rerun-sdk==0.33.1 av==15.1.0
uv tool install git+https://github.com/huggingface/leLab.git
```

기존 `~/lerobot`이 있으면 clone·checkout을 바로 반복하지 말고 기존 변경과 환경을 먼저 확인하세요. `leLab`은 Dataset Desk가 가져오는 `episode_media.py` 때문에 필요합니다. 현재 설치 명령은 최신 leLab을 받으므로 향후 API 변경 시 같은 버전 보장이 없습니다. 그 밖의 전이 의존성도 완전히 잠근 lockfile은 제공하지 않습니다.

프로젝트 경로를 실제 clone 위치로 바꾼 뒤 [LeRobot 패치](../patches/README.md)를 적용합니다. dialout 등 그룹 변경은 새 로그인으로 적용하며, 실행 중인 학습·녹화를 마친 뒤 WSL을 재시작하세요.

## 5. USB와 캘리브레이션

두 로봇의 모터 전원과 USB를 연결합니다. 관리자 PowerShell에서 실제 BUSID를 확인하고 로봇 보드만 공유합니다.

```powershell
usbipd list
usbipd bind --busid <Leader-BUSID>
usbipd bind --busid <Follower-BUSID>
usbipd attach --wsl Ubuntu-24.04 --busid <Leader-BUSID>
usbipd attach --wsl Ubuntu-24.04 --busid <Follower-BUSID>
```

카메라는 WSL에 attach하지 않습니다. 다른 보드라면 Ubuntu의 `ls -l /dev/serial/by-id/` 결과를 이용해 코드의 포트를 맞추세요. 자동 연결은 필수가 아니며 위 수동 연결로 시작할 수 있습니다.

기존 `usbipd-autoattach` 작업을 사용한다면 설치된 `C:/ProgramData/usbipd-autoattach/usbipd-autoattach.ps1`의 카메라 제외 목록을 확인하세요. 현재 icSpring VID:PID `32e6:9211`은 제외되어야 합니다. 기존 `windows_setup/install-usbipd-autoattach.ps1`은 카메라도 자동 연결하는 과거 구성이므로 현재 환경에서 무작정 재실행하지 마세요.

각 실물 팔에 맞는 LeRobot `follower` / `leader` 캘리브레이션이 필요합니다. 기존 Studio 보정을 옮길 때는 `windows_setup/studio_export_calibration.py`의 사용법을 확인하세요. 다른 실물 팔에는 저장소의 예시 보정을 복사해서 사용하지 마세요. 관절 단위는 기존 데이터와 맞추기 위해 `use_degrees=false`입니다.

## 6. 카메라 브리지와 실행

먼저 수정한 Python 경로로 주 카메라 서버를 별도 PowerShell 창에서 실행해 확인합니다.

```powershell
python camera-bridge/server.py
# 다른 창에서 상태 확인
Invoke-RestMethod http://127.0.0.1:8765/health
```

`camera-bridge/install.ps1`은 기존 USB 자동 연결 작업이 있는 PC에서 카메라 제외와 로그인 예약 작업을 설정하는 관리자용 스크립트입니다. 새 PC에는 그 작업이 없을 수 있으므로 바로 실행하지 말고 위 수동 서버로 확인하세요. 로그인 작업을 사용할 경우 스크립트의 Python 경로도 수정해야 합니다.

서버 실행 상태에서 `Start-LeRobot.cmd`를 실행합니다. 보조 카메라와 ZMQ relay를 준비하고 UART 모터 응답을 확인합니다. 주·보조 카메라 상태는 8765/8766 `/health`로 확인합니다. 실패하면 `workflows/launcher.log`, `workflows/dataset-ui.log`, `camera-bridge/bridge.log`를 확인하세요.

Dataset Desk에서 데이터셋 ID와 작업 설명을 확인한 뒤 연결·녹화를 시작합니다. 처음 빈 데이터셋은 첫 저장 후 목록에 나타납니다. Hub에 자동 업로드하지 않습니다.

## 7. Studio를 사용할 때 (선택)

Docker Desktop WSL integration에서 Ubuntu-24.04를 활성화합니다. Studio 설치 원리는 [기존 설치 자료 7번](../windows_setup/README_설치순서.md)을 참고하되, 현재 코드 기준 소스 커밋은 `9fd6fbea534bfcfcb9747f8902f7e85a37bedc73`입니다. 개발 이미지 태그는 향후 없어질 수 있으며 컨테이너 이미지 자체는 이 저장소에 포함하지 않습니다.

실제 WSL override 스냅샷은 `patches/studio-docker-compose.override.yaml`입니다. 장치 매핑을 검토해 Studio의 `application/docker/docker-compose.override.yaml`로 복사합니다. 기존 컨테이너 이름 `physical-ai-studio-cuda`가 준비되어야 `Start-Studio.cmd`가 동작합니다. 실행 파일은 컨테이너를 새로 만들지 않습니다.

Studio IP camera URL은 `http://host.docker.internal:8765/camera.mjpg`입니다. RGB 녹화에서 `gray12le`/HEVC 깊이 인코더 오류가 나면 `recording-encoder-fix/README.md`를 읽고 해당 버전용 패치를 적용하세요. 컨테이너 재생성 시 재적용이 필요할 수 있습니다. 같은 로봇을 LeRobot과 동시에 제어하지 마세요.

## 8. 하드웨어 없는 검사

```bash
cd ~/lerobot
.venv/bin/python /mnt/c/Users/<사용자>/<저장소폴더>/workflows/check_dataset_ui.py
```

이 검사는 임시 데이터셋만 사용하여 저장·이어 저장·버리기와 영상 디코딩을 확인합니다. 실제 모터·카메라 연결 또는 학습 성능을 검증하지는 않습니다.

코드 정리 이후 실제 구현·호환 경로·런타임 데이터 경계는 [구조 안내](ARCHITECTURE.ko.md)를 참고하세요. 기존 실행 명령은 호환 진입점으로 유지됩니다.
