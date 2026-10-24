# WSL LeRobot 카메라 연결

**현재 권장 실행 방법:** 프로젝트 루트의 `windows/Start-LeRobot.cmd` 또는 `windows/Start-Studio.cmd`를 더블클릭합니다. 사전준비와 자동 전환 설명은 [원클릭 실행 안내](OPERATIONS.ko.md)를 참고하세요. 아래는 카메라 구조와 개별 명령 설명입니다.

현재 PC 전용 설정. 2026-10-23 LeRobot 0.6.1에서 검증.

웹캠 → Windows DirectShow 브리지(기존 127.0.0.1:8765) → Windows ZMQ 전달 서버(WSL 가상 어댑터:5555) → Ubuntu LeRobot → Rerun.

카메라는 Windows에 남기고, 로봇 USB 두 개만 usbipd로 WSL에 연결합니다. 카메라를 WSL에 attach하지 마세요. Docker는 이 영상 경로에 필요하지 않습니다.

## 1. Windows PowerShell

기존 카메라 브리지는 로그인 시 자동 실행됩니다. 추가 전달 서버는 아래 명령으로 시작합니다. 현재는 실행해 두었습니다. 재부팅하거나 WSL 네트워크 주소가 바뀌면 다시 실행하세요. 이전 주소에 남은 relay.py 프로세스는 종료한 뒤 다시 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File <저장소>\windows\start-camera-relay.ps1
```

전달 서버는 WSL 가상 어댑터 주소에만 바인딩합니다. 종료하려면 해당 포트의 프로세스 ID를 확인하고 그 프로세스만 종료합니다.

```powershell
Get-NetTCPConnection -LocalPort 5555 -State Listen | Select-Object LocalAddress,OwningProcess
```

## 2. Ubuntu: 카메라만 보기

로봇 직렬 포트를 열거나 모터를 움직이지 않습니다. 30초 뒤 수신이 끝납니다. Rerun 창은 닫아도 됩니다.

```bash
cd ~/lerobot
uv run --no-sync python /mnt/c/Users/<사용자>/intel7-vla/tools/diagnostics/check_camera.py --view --seconds 30
```

10초 시험: 316프레임, 640×480×3, 약 31.54fps. RGB 채널 검사를 통과했고 저장 프레임에 타일링이 없었습니다. 녹화 전체 속도는 로봇 통신·저장 부하에 따라 달라집니다. WSL Rerun은 현재 CPU 렌더링을 사용하며 표시 메모리는 128MB로 제한했습니다.

## 3. Ubuntu: 로봇 녹화

먼저 Studio의 Teleoperate와 두 로봇 Connect를 끄고 해당 화면을 닫아 직렬 포트를 해제합니다. 실행 중인 학습이 있다면 컨테이너를 중지하지 마세요. Leader/Follower DC 전원을 켜고 두 팔을 비슷한 시작 자세에 놓은 뒤 실행합니다. 이 단계부터 Follower가 Leader를 따라 움직입니다.

```bash
# 설정과 메타데이터만 확인. 하드웨어 연결·데이터 변경 없음.
bash /mnt/c/Users/<사용자>/intel7-vla/wsl/record.sh --check

# 기존 20개 에피소드에 30초 에피소드 1개를 이어 녹화. Hub 업로드 없음.
bash /mnt/c/Users/<사용자>/intel7-vla/wsl/record.sh
```

추가 수집량을 바꾸려면:

```bash
bash /mnt/c/Users/<사용자>/intel7-vla/wsl/record.sh --dataset.num_episodes=20 --dataset.episode_time_s=30
```

기존 데이터셋: `/home/user/.cache/huggingface/lerobot/se4nchoi/redball`, 카메라 `follower_cam`, 640×480, 30fps, 작업 `pick red ball`. 교재의 카메라 이름이나 예시 USB 시리얼을 그대로 쓰면 맞지 않습니다.

Follower: `5B90150163`, Leader: `5B90149145`. 캘리브레이션 ID는 각각 `follower`, `leader`입니다.

Studio SO101 드라이버는 몸통 관절을 [-100,100]으로 정규화합니다. 현재 LeRobot은 기본값이 각도 단위이므로 스크립트에서 양쪽 모두 `use_degrees=false`로 지정했습니다. 기존 데이터와 섞을 때 유지해야 합니다. `robot_type` 문자열만 수정하는 것으로 단위까지 맞춰지지는 않습니다.

## 적용 파일

- Windows: `relay.py`, `start.ps1`, `.camera-tools/pyzmq` 추가. 기존 DirectShow 서버는 유지.
- Ubuntu: venv에 `pyzmq` 설치. `src/lerobot/cameras/zmq/camera_zmq.py`의 JPEG 디코딩 뒤 RGB 변환 추가. 원본은 옆의 `.py.before-rgb-fix` 파일에 보관.
- `patch_zmq_rgb.py`: 해당 버전에 한해 재적용 가능한 수정 스크립트.
- Docker 컨테이너와 기존 데이터셋은 이 작업에서 변경하지 않았습니다.

LeRobot 재설치나 git 업데이트로 RGB 수정이 사라지면 소스를 확인하고 이 버전용 수정의 재적용 여부를 판단해야 합니다.
