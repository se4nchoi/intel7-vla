# Windows 11 실습 환경 — 설치 순서 · 명령어 모음

강의실 PC 기준: Core Ultra 7 265K · RAM 16GB · RTX 3050 6GB · Windows 11 Pro/Education
대상 버전 (2026.10 확인): Physical AI Studio v0.3.0 (Docker 이미지 `:main` = 0.3.0-dev-7b099fe1) · LeRobot v0.6.1 · usbipd-win 5.3.0 · WSL 3.0.3 · Docker Desktop 4.96

> **어디서 실행하나** — 각 블록 제목에 표시
> - **PowerShell (관리자)**: 시작 → PowerShell 우클릭 → 관리자로 실행
> - **PowerShell**: 일반 PowerShell
> - **Ubuntu**: 시작 메뉴의 Ubuntu 24.04 (또는 PowerShell 에서 `wsl`)

---

## 0. 수업 전 확인 (PowerShell)

```powershell
nvidia-smi                                                      # NVIDIA 드라이버 (CUDA Toolkit 설치 불필요)
(Get-CimInstance Win32_OperatingSystem).Caption                 # Windows 11 Pro / Education
(Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled # True = BIOS 가상화 켜짐
[int]((Get-PSDrive C).Free/1GB)                                 # 디스크 여유 50GB 이상 권장
```

- 이미지 다운로드 6.4GB(디스크 18.8GB), LeRobot 가상환경 7.8GB
- 설치 프로그램은 **하나씩** — 동시에 돌리면 `오류 1618`

## 1. WSL2 + Ubuntu 24.04 (PowerShell 관리자)

```powershell
wsl --install -d Ubuntu-24.04
# 처음이면 '가상 머신 플랫폼' 설치 후 재부팅 요청 → 재부팅 → 같은 명령 다시
# 사용자 이름 / 비밀번호 만들기 (비밀번호는 입력해도 안 보임 = 정상)
wsl -l -v                       # Ubuntu-24.04  VERSION 2
```

## 2. WSL 기본 설정 (PowerShell)

```powershell
wsl --set-default Ubuntu-24.04  # Docker 를 먼저 깔면 docker-desktop 이 기본이 되어 버림
notepad $env:USERPROFILE\.wslconfig
```

`.wslconfig` 내용 (RAM 16GB PC):

```ini
[wsl2]
memory=10GB
swap=12GB
```

```powershell
wsl --shutdown                  # 적용
```

실측 (테스트 PC, memory=10GB): Studio ACT 훈련 RAM 최고 7.6GB + 스왑 1.7GB · LeRobot ACT/SmolVLA 4.3~4.6GB · 메모리 부족(OOM) 없음

## 3. Ubuntu 준비 (Ubuntu)

```bash
sudo bash /mnt/c/Users/<사용자>/Documents/VLA수업/windows_setup/setup-wsl.sh
```

스크립트가 하는 일 (직접 쳐도 됨):

```bash
sudo apt update
sudo apt install -y git curl ffmpeg build-essential cmake pkg-config python3-dev libevdev-dev v4l-utils usbutils tree
sudo usermod -aG dialout,video,plugdev $USER
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666"' | sudo tee /etc/udev/rules.d/99-so101-cameras.rules
echo 'SUBSYSTEM=="video4linux", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-so101-cameras.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

그다음 PowerShell 에서 `wsl --shutdown` → Ubuntu 다시 열기 (그룹 적용)

## 4. Docker Desktop (PowerShell 관리자)

```powershell
winget install --id Docker.DockerDesktop -e
# 로그아웃 또는 재부팅 → Docker Desktop 실행 → 약관 Accept → 로그인은 Skip
```

Docker Desktop 설정:
- Settings → General → **Use the WSL 2 based engine** ✔, **Start Docker Desktop when you sign in** ✔
- Settings → Resources → WSL integration → **Ubuntu-24.04 켜기 → Apply & restart** (토글만 켜면 적용 안 됨)

확인 (Ubuntu):

```bash
docker version
docker run --rm --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark
```

## 5. usbipd-win (PowerShell 관리자)

```powershell
winget install --id dorssel.usbipd-win -e
# PowerShell 새로 열기
usbipd list
```

수동 연결 (원리 확인용 — 자동 연결을 쓰면 칠 일 없음):

```powershell
usbipd bind --busid 2-1                         # 관리자, 한 번 (영구)
usbipd attach --wsl Ubuntu-24.04 --busid 2-1    # 매번 (재부팅·재연결 시 풀림)
usbipd detach --busid 2-1
```

> `usbipd bind --auto-attach` 는 없는 옵션 (5.3.0). `--auto-attach` 는 attach 전용이고 창을 닫으면 끝난다.

## 6. USB 자동 연결 (PowerShell 관리자, 로봇 2대·카메라 꽂은 상태에서)

```powershell
cd $env:USERPROFILE\Documents\VLA수업\windows_setup
powershell -ExecutionPolicy Bypass -File .\install-usbipd-autoattach.ps1
usbipd list                     # 로봇·카메라 STATE = Attached
```

- 로그온할 때마다 작업 스케줄러 `usbipd-autoattach` 가 2초마다 확인 → 뺐다 꽂아도, 다른 포트여도, 재부팅해도 자동 연결
- 실측 (테스트 PC): 연결이 끊긴 뒤 1.7초 만에 재연결 · `wsl --shutdown` 뒤 8초 만에 Ubuntu·USB·Docker·Studio 자동 복구 · 작업 재시작 5초
- 로그: `%LOCALAPPDATA%\usbipd-autoattach\autoattach.log`
- 새 카메라 모델을 쓰게 되면 꽂은 뒤 같은 명령 한 번 더 / 제거: `... -Uninstall`
- 재부팅 없이 점검: PowerShell 에서 `wsl --shutdown` → 10초 뒤 `powershell -ExecutionPolicy Bypass -File .\check-after-reboot.ps1`

장치 확인 (Ubuntu):

```bash
lsusb
ls -l /dev/serial/by-id/ /dev/ttyACM* /dev/video*
v4l2-ctl --list-devices
```

## 7. Physical AI Studio (Ubuntu — 반드시 홈(~)에서)

```bash
cd ~
git clone https://github.com/open-edge-platform/physical-ai-studio.git
cd ~/physical-ai-studio/application/docker
mkdir -p ~/.cache/huggingface/lerobot/calibration
bash ./setup-devices.sh --cuda
# (선택) 수업 자료와 같은 빌드로 고정 — 개발 태그는 몇 주 뒤 GHCR 에서 지워지므로 docker save 백업 권장
# sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=0.3.0-dev-7b099fe1/' .env
cp /mnt/c/Users/<사용자>/Documents/VLA수업/windows_setup/docker-compose.override.yaml .   # USB 핫플러그
docker compose pull             # 6.4GB, 실측 8분 — 미리
docker compose up -d
docker compose ps               # Up (healthy)
```

브라우저: <http://localhost:7860>

확인:

```bash
docker exec physical-ai-studio-cuda python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
docker exec physical-ai-studio-cuda sh -c 'ls -l /dev/ttyACM* /dev/video*'
```

운영:

```bash
docker compose stop             # 멈추기 (LeRobot 훈련 전)
docker compose up -d            # 다시 켜기
docker restart physical-ai-studio-cuda
git pull && docker compose pull && docker compose up -d --force-recreate   # 업데이트
docker save ghcr.io/open-edge-platform/physical-ai-studio-cuda:main | gzip > /mnt/c/Users/<사용자>/Downloads/studio.tar.gz   # 탐색기로 USB 에 복사
gunzip -c /mnt/c/Users/<사용자>/Downloads/studio.tar.gz | docker load   # 다른 PC 에서
```

> **절대 금지**: `docker compose down -v` (볼륨 = 데이터셋·모델·DB 삭제)

## 8. LeRobot (Ubuntu — 2강)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
cd ~ && git clone https://github.com/huggingface/lerobot.git
cd lerobot && git checkout v0.6.1
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[core_scripts,training,feetech,smolvla]"
uv pip install evdev
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Studio 자산 가져오기:

```bash
python3 /mnt/c/Users/<사용자>/Documents/VLA수업/windows_setup/studio_export_calibration.py <프로젝트이름>
docker exec physical-ai-studio-cuda ls /app/storage/datasets
mkdir -p ~/.cache/huggingface/lerobot/intel
docker cp physical-ai-studio-cuda:/app/storage/datasets/<UUID> ~/.cache/huggingface/lerobot/intel/redball
```

로봇 작업 시 주의 (v0.6.1 소스로 확인):

- `lerobot-find-port`: 케이블을 **뺀 상태에서** 2~3초 기다렸다 ENTER → 포트 이름이 나온 뒤 다시 꽂기 (꽂고 ENTER 하면 "No difference was found")
- `lerobot-calibrate`: 같은 id 파일이 있으면 ENTER = 기존 파일 사용 / `c` = 새로 캘리브레이션 (이식한 파일 덮어씀)
- `lerobot-rollout`: Ctrl+C 하면 팔이 약 3초간 시작 자세로 돌아간 뒤 토크 해제 → 손 넣지 말기 · 제자리 정지는 `--return_to_initial_position=false`
- 훈련 VRAM·RAM (테스트 PC 실측, 카메라 2대 640×480): LeRobot ACT 배치 8 = GPU 5.0GB / 배치 4 = 3.2GB · SmolVLA 배치 8 = 3.7GB · WSL 10GB 에서 RAM 최고 4.3~4.6GB
- Studio (배치 8, BF16): ACT = GPU 3.2GB · SmolVLA = 4.8GB · '≥ 3GB VRAM' 표시는 최소 권장일 뿐 제한 아님
- Studio 와 동시에 훈련 금지 — LeRobot 훈련 전 `cd ~/physical-ai-studio/application/docker && docker compose stop`

## 문제 해결

| 증상 | 해결 |
|---|---|
| `failed to connect to the docker API (npipe)` (PowerShell) | Docker Desktop 실행 → 하단 'Engine running' |
| `The command 'docker' could not be found in this WSL 2 distro` | WSL integration → Ubuntu-24.04 → Apply & restart (또는 Docker Desktop 꺼짐) |
| `WARN The "HOME" variable is not set` | PowerShell 에서 compose 실행함 → Ubuntu 에서 |
| `./setup-devices.sh` 반응 없음 | PowerShell 은 .sh 실행 불가 → Ubuntu 에서 `bash ./setup-devices.sh --cuda` |
| `$'\r': command not found` | Windows 에서 받은 파일(CRLF) → Ubuntu 안에서 git clone |
| Studio 훈련이 시작 후 10여 분 GPU 0% | 정상 — 매 훈련마다 데이터셋 통계 계산 (에피소드당 12~15초) |
| `Output directory ... already exists` (lerobot-train) | `--output_dir` 이름 바꾸기 |
| `There is no WSL 2 distribution running` | Ubuntu 꺼짐 → 자동 연결 작업 확인 (로그) |
| `Permission denied: /dev/ttyACM0` | dialout 그룹 → `wsl --shutdown` 후 다시 |
| Studio 에 로봇·카메라 안 보임 | override(/dev 공유) 확인 · `docker restart physical-ai-studio-cuda` |
| 카메라 `failed to set fps` | 640×480 · MJPG · `"backend": "V4L2"` · 카메라를 서로 다른 USB 포트에 |
| `CUDA out of memory` | Studio 와 LeRobot 동시 훈련 금지 · batch 절반 |
| 설치 오류 1618 | 다른 설치가 끝난 뒤 다시 |
