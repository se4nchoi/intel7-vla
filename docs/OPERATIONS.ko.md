# Studio / LeRobot 원클릭 실행

이 폴더는 **현재 Windows PC**의 설치 경로·USB 시리얼·데이터셋을 기준으로 합니다. 최초 사전준비를 마친 뒤에는 프로젝트 루트의 실행 파일 하나만 더블클릭하면 됩니다.

| 사용할 환경 | 더블클릭할 파일 | 완료 후 |
|---|---|---|
| Physical AI Studio | `windows/Start-Studio.cmd` | 기존 Docker 컨테이너를 시작하고 브라우저를 엽니다. |
| WSL LeRobot + Rerun | `windows/Start-LeRobot.cmd` | USB·카메라·ZMQ를 준비한 뒤 Dataset Desk를 엽니다. 녹화는 버튼으로 시작합니다. |
| 저장된 데이터셋만 보기 | `windows/Start-Dataset-Viewer.cmd` | 로봇 전원 없이 Dataset Desk를 엽니다. |

Dataset Desk는 http://localhost:8877 에서 실행합니다. `데이터셋` 탭은 로컬 영상·관절값·에피소드 목록을 표시하고 개별 에피소드 삭제·복원을 지원합니다. `카메라 · 녹화` 탭은 기존 로봇·ZMQ 설정을 사용하며 새 캘리브레이션 설정 화면을 요구하지 않습니다. 시작만으로 추종하거나 녹화하지 않습니다. leLab(:8000)은 별도 앱이며 이 화면에서는 사용하지 않습니다.

## 공통 사전준비 — 처음 한 번

현재 PC에는 아래 구성이 설치돼 있습니다. 다른 PC로 옮기거나 재설치할 때 확인하세요.

1. **WSL2 + Ubuntu-24.04** 설치 및 첫 로그인 완료. Linux 사용자 홈은 현재 `/home/user`입니다.
2. **usbipd-win** 설치. 현재 경로는 `C:\Program Files\usbipd-win\usbipd.exe`입니다.
3. 로봇 두 보드를 Windows에서 한 번 공유(bind). 관리자로 연 PowerShell에서 먼저 `usbipd list`로 BUSID를 확인하고, 해당 보드 각각에 `usbipd bind --busid <BUSID>`를 실행합니다. BUSID는 포트에 따라 달라지므로 예시 값을 그대로 쓰지 마세요.
4. `usbipd-autoattach` 예약 작업 설치. 기존 설치 파일은 `windows/setup/install-usbipd-autoattach.ps1`입니다. **카메라 제외 설정을 유지해야 하므로, 현재 PC에서 설치 파일을 무작정 재실행하지 마세요.** 실제 설치된 `C:\ProgramData\usbipd-autoattach\usbipd-autoattach.ps1`의 `$ExcludeHardwareIds`에 `'32e6:9211'`이 있어야 합니다. 카메라는 Windows에서 촬영하며 WSL에 USB attach하지 않습니다.
5. Ubuntu 사용자의 로봇 직렬 포트 읽기·쓰기 권한. 필요하면 Ubuntu에서 `sudo usermod -aG dialout "$USER"` 실행 후 새 로그인으로 적용합니다. 재로그인이 필요할 때 실행 중인 학습을 먼저 마치세요.
6. **기존 Windows 카메라 브리지** 설치. `windows/camera_server.py`와 `.camera-tools`의 OpenCV·NumPy 의존성이 필요합니다. `physical-ai-camera-bridge` 예약 작업으로 로그인 시 실행됩니다. 브리지는 `http://127.0.0.1:8765/health`에서 상태를 제공합니다. 설치·구조는 `windows/setup/install-camera-bridge.ps1`, `docs/CAMERA-RELAY.ko.md`를 참고하세요.
7. 현재 실행 파일이 사용하는 Python: `%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe`. 이 경로가 없는 다른 PC에서는 Python과 의존성을 별도로 설치하고 `windows/start.ps1`, `windows/start-camera-relay.ps1`의 경로를 변경해야 합니다. Codex 자체가 필요한 구조는 아니지만 현재는 그 번들 Python을 사용합니다.
8. 스크립트가 자기 위치에서 저장소 경로를 계산하므로 저장소는 어느 폴더에 clone해도 됩니다. WSL에서는 같은 폴더를 `/mnt/<드라이브>/...`로 접근합니다. 단, `windows/`의 실행 파일만 다른 곳에 복사하면 작동하지 않습니다. 바로가기는 사용할 수 있습니다.

### 실행할 때마다 연결할 하드웨어

- Leader USB + Follower USB를 PC에 연결합니다.
- 로봇을 사용할 때 두 팔의 모터용 DC 전원·스위치를 켭니다. USB만 연결돼 있어도 직렬 포트는 나타나므로, 준비 완료 메시지가 모터 전원 켜짐까지 의미하지는 않습니다.
- 웹캠을 PC에 연결하고 Windows 카메라 앱·회의 앱 등 카메라를 독점할 수 있는 앱은 닫습니다.
- 현재 보드 식별: Leader `5B90149145`, Follower `5B90150163`. 다른 보드로 바꾸면 `start.ps1`, `prepare-wsl.sh`, `wsl/record.sh`를 수정해야 합니다.

## Studio 전용 사전준비

- **Docker Desktop** 설치, WSL2 Linux 컨테이너 사용, 초기 약관·권한 설정 완료. Docker Desktop 종료 상태라면 실행 스크립트가 시작합니다. 설치 또는 최초 로그인 화면을 대신 처리하지는 않습니다.
- 기존 컨테이너 **`physical-ai-studio-cuda`**가 있어야 합니다. 실행 스크립트는 `docker start`를 사용하며 새 컨테이너를 만들지 않습니다. 기존 카메라·녹화 수정과 저장 볼륨을 보존하기 위한 선택입니다. 컨테이너를 삭제·재생성하면 컨테이너 내부의 별도 패치를 다시 적용해야 할 수 있습니다.
- GPU 학습을 하려면 NVIDIA 드라이버와 Docker/WSL GPU 지원이 준비돼 있어야 합니다. 실행 버튼은 GPU 드라이버를 설치하지 않습니다.
- Studio에서 로봇·캘리브레이션·Environment를 등록해 두어야 합니다. 현재 기존 `test` 환경을 그대로 사용합니다.
- Studio 카메라 주소는 `http://host.docker.internal:8765/camera.mjpg`입니다. 이름 `follower_cam`, 640×480, 30fps 설정을 유지합니다.
- 외부 모델 다운로드·Hub 업로드를 하려면 인터넷 및 Studio의 Hugging Face 토큰 설정이 필요합니다.

### Studio 버튼이 자동으로 하는 일

1. 실행 중인 WSL LeRobot 녹화·제어·학습 프로세스가 있는지 확인합니다.
2. Ubuntu를 시작하고 두 로봇 USB를 연결합니다. 실수로 WSL에 붙은 카메라는 Windows로 돌려놓습니다.
3. Windows 카메라 서버를 확인하고 필요하면 시작합니다. 새 프레임 수신까지 확인합니다.
4. Docker Desktop을 필요하면 시작하고, LeRobot용 ZMQ 전달 서버만 종료합니다.
5. 기존 Studio 컨테이너를 시작하고 HTTP 응답을 기다립니다.
6. 기본 브라우저에 `http://localhost:7860`을 엽니다. 그다음 Studio에서 로봇 Connect·Teleoperate·녹화 등을 선택합니다.

## LeRobot 전용 사전준비

### 현재 작업: messi

- 저장 위치: `/home/user/.cache/huggingface/lerobot/se4nchoi/messi`
- 데이터셋 ID: `se4nchoi/messi`
- 작업: 빨간 공 집기 → 집은 위치를 기준으로 열린 왼쪽/오른쪽 경로 판단 → 두 콘 사이로 굴리거나 슛해서 득점.
- 기록할 task 문장: `Pick up the red ball, identify the open lane to the left or right of the pickup location, and roll or shoot the ball between the two cones to score a goal.`
- 첫 기록 때 생성하며 이후에는 같은 폴더에 이어서 저장합니다. `redball`은 별도 데이터셋으로 유지합니다.

### 카메라 2대 구성

| 역할 / 데이터셋 키 | Windows 장치 | MJPEG 미리보기 | WSL ZMQ 포트 |
|---|---|---|---|
| 그리퍼 / `follower_cam` | `icspring camera`, `32e6:9211` | `http://127.0.0.1:8765/camera.mjpg` | 5555 |
| 골대·필드 / `field_cam` | `USB CAMERA`, `1224:2a25` | `http://127.0.0.1:8766/camera.mjpg` | 5556 |

두 카메라는 모두 Windows에 남깁니다. 웹캠을 WSL에 USB attach하지 마세요. 촬영 프로세스는 DirectShow 장치 이름으로 번호를 다시 찾으므로 두 장치를 꽂는 순서가 바뀌어도 역할을 유지합니다. 같은 이름의 카메라가 여러 대이면 임의 선택하지 않고 오류를 냅니다. Windows `.camera-tools`에는 OpenCV·NumPy 외에 `pygrabber`, `comtypes`가 필요합니다.

`windows/Start-LeRobot.cmd`는 기존 그리퍼 브리지와 새 필드 브리지, ZMQ 전달 프로세스 2개를 준비합니다. Field 브리지 실행 파일은 `windows/start-field-camera.ps1`이며 로그인 예약 작업에 자동 등록되지는 않습니다. LeRobot 실행 시 시작하고 카메라 분리 시 재연결을 시도합니다. 카메라를 사용하는 다른 앱을 닫으세요.

Dataset Desk는 두 라이브 영상을 함께 보여주고, Rerun도 두 영상 패널을 표시합니다. 새 데이터셋에는 `observation.images.follower_cam`과 `observation.images.field_cam`을 각각 640×480·30fps 설정으로 저장합니다. 카메라의 실제 프레임 속도는 드라이버·조명·USB 환경에 따라 다를 수 있습니다. 각 프레임은 제어 루프에서 읽은 두 카메라의 최신 영상이며 하드웨어 동기 촬영은 아닙니다.

기존 1카메라 `redball`은 계속 재생할 수 있습니다. 카메라 수가 다른 기존 데이터셋에는 그대로 이어 쓰지 마세요. `messi`는 비어 있는 상태에서 2카메라 기록을 시작하도록 설정했습니다. Studio에서 필드 카메라를 추가할 때는 IP 카메라 URL `http://host.docker.internal:8766/camera.mjpg`를 사용하며 필드 브리지를 먼저 실행해야 합니다.

### 설치와 연결

- Ubuntu `~/lerobot`의 LeRobot 0.6.1 및 `.venv`, 로봇 SDK·OpenCV·pyzmq·rerun-sdk가 필요합니다.
- `uv tool install git+https://github.com/huggingface/leLab.git` 설치가 필요합니다. Dataset Desk는 설치된 leLab의 읽기 전용 `episode_media.py`를 불러와 v3 데이터셋의 영상 구간을 해석합니다. 실행·녹화는 기존 `~/lerobot/.venv` 환경을 사용합니다. leLab을 지우면 이 미디어 모듈도 없어지므로 뷰어가 시작하지 않습니다.
- 기본 Rerun 프로그램을 띄울 WSLg가 필요합니다. 현재 WSL에서는 CPU 렌더링 경고가 발생합니다. 표시 메모리는 128MB로 제한합니다.
- Windows `.camera-tools`에도 pyzmq가 필요합니다.
- 기본 저장 위치 `/home/user/.cache/huggingface/lerobot/se4nchoi/messi`와 캘리브레이션 ID `follower`, `leader`가 필요합니다. 카메라 이름은 `follower_cam`, 640×480, 30fps입니다.
- 관절 단위를 기존 Studio 데이터와 맞추기 위해 양쪽 `use_degrees=false`를 유지합니다.
- 추종은 LeRobot 기본값을 사용합니다. 별도의 `max_relative_target` 제한은 제거했습니다. 시작 전 두 팔 자세를 비슷하게 맞추세요.
- 카메라만 교재의 V4L2 대신 Windows MJPEG → ZMQ를 사용합니다. NAT에서는 가상 게이트웨이, mirrored에서는 127.0.0.1을 자동 선택합니다.
- GPU 학습·Hub 업로드는 별도 설정과 Ubuntu 인증이 필요합니다. 이 버튼은 학습이나 Hub 업로드를 시작하지 않습니다.

### 실행과 유지

1. 두 팔 DC 전원·USB와 카메라를 연결하고 시작 자세를 비슷하게 맞춥니다.
2. `windows/Start-LeRobot.cmd` 더블클릭: WSL·USB·카메라·ZMQ·기존 데이터셋 설정을 자동 준비합니다. 위치 명령을 보내지 않는 실제 UART ping으로 두 팔 12개 모터 응답을 확인하며, 무응답이면 녹화를 시작하지 않습니다.
3. Dataset Desk 웹 화면이 열립니다. 에피소드 목록을 선택하면 저장 영상을 재생하고 6개 관절값 그래프를 확인할 수 있습니다. 재생·프레임 이동·속도 변경·Rerun 열기를 지원합니다. 브라우저가 MP4 코덱을 지원하지 않으면 서버 프레임 재생으로 전환합니다.
4. `카메라 · 녹화`에서 데이터셋 ID·작업 설명을 확인하고 `로봇 연결 + Rerun`을 누릅니다. 두 팔·ZMQ 카메라가 연결되고 기본 Rerun이 별도 창에 열립니다. 연결 단계에서는 현재 Follower 자세를 유지하며 Leader 추종·데이터셋 기록은 시작하지 않습니다. 자세를 맞추고 주변을 비우세요.
5. `녹화 시작`을 누르면 Leader 추종과 데이터셋 기록이 함께 시작됩니다. 추가 속도 제한이나 시작 보간은 없습니다. 기본 최대 60초 또는 `중지 · 저장` 버튼으로 한 에피소드를 저장하고 추종을 멈춥니다. 저장 후 장치 연결과 실시간 영상은 유지됩니다. `추종 켜기 (저장 안 함)`은 녹화 없이 추종을 별도로 켭니다.
6. 저장할 때 Parquet writer도 닫으므로 에피소드를 바로 조회할 수 있습니다. 목록 새로고침을 누르세요. `이번 녹화 버리기`는 현재 버퍼만 버립니다. 기존 에피소드는 삭제하지 않습니다. `연결 해제`는 녹화 중이면 저장 후 장치를 해제합니다. 브라우저를 닫아도 서버·연결은 유지되므로 종료 전 이 버튼을 사용하세요.
7. 다른 작업은 연결 해제 후 `owner/new_task`와 작업 설명을 입력하고 다시 연결합니다. 새 데이터셋은 첫 녹화에 생성되며 기존 데이터셋이면 이어서 추가합니다. 저장은 `~/.cache/huggingface/lerobot/<owner>/<task>`이며 Hub에 자동 업로드하지 않습니다.

`카메라 · 녹화` 탭 맨 아래의 **SESSION LOG**는 페이지를 연 이후의 연결·추종·녹화·저장 상태와 오류, 주기적인 FPS/프레임 진행 상황을 CLI 형태로 표시합니다. 로컬 시각과 로그 수준을 붙이며 최근 600줄을 유지합니다. Auto-scroll을 끄면 이전 줄을 읽을 수 있고, Copy는 표시된 로그를 복사합니다. Clear view는 화면 로그만 비우며 데이터셋을 삭제하지 않습니다. 이 패널은 세션 이벤트 로그이며 Python/인코더의 전체 stdout·stderr 출력은 `runtime/dataset-ui.log`에서 확인합니다. 페이지를 새로고침하면 패널의 이전 로그는 초기화되지만 로봇 세션은 유지됩니다.

새 저장 위치를 빈 폴더로 미리 만들어도 녹화를 시작할 수 있습니다. LeRobot 생성 API에 맞춰 빈 디렉터리만 다시 생성하며, `meta/info.json` 없이 파일이 들어 있는 폴더는 덮어쓰지 않고 오류를 표시합니다.

Rerun 표시는 별도 스레드와 최신 프레임 1개 큐를 사용합니다. 뷰어가 느리거나 표시가 밀려도 로봇 제어·녹화·중지 명령을 기다리게 하지 않습니다. 표시용으로 오래된 프레임을 버릴 수 있으며 데이터셋 프레임은 별도로 제어 루프에서 저장합니다.

### 예전 표준 CLI를 수동 실행할 때의 키 조작

키는 **자동으로 열린 Ubuntu 창에 포커스**가 있어야 인식됩니다. Rerun 창은 시각화용입니다.

- 오른쪽 화살표 또는 `n`: 현재 단계를 조기 종료하고 다음 단계로 진행. 녹화 에피소드는 저장합니다.
- 왼쪽 화살표 또는 `r`: 현재 에피소드를 버리고 재녹화합니다.
- Esc 또는 `q`: 현재 에피소드를 저장하고 세션을 종료합니다.

Rerun의 .rrd 저장 버튼은 시각화 로그 저장이며 LeRobot 데이터셋 저장과 별개입니다. 교재도 Rerun 버튼으로 데이터셋 녹화를 제어하지 않습니다.

### 저장된 에피소드 보기

프로젝트 루트의 **`windows/Start-Dataset-Viewer.cmd`**를 더블클릭하면 에피소드 목록을 웹에서 선택할 수 있습니다. `windows/View-Episodes.cmd`는 이전 방식으로 최근 에피소드를 바로 Rerun에 여는 실행 파일입니다. 웹 화면의 `Rerun에서 보기` 버튼은 선택한 에피소드를 엽니다. 현재 기본 녹화 데이터셋은 `se4nchoi/messi`입니다. 첫 에피소드를 저장하면 목록에 나타납니다. 기존 `redball`도 계속 조회할 수 있습니다.

Rerun 왼쪽 Sources에서 `se4nchoi/redball/episode_24` 같은 저장 에피소드 소스를 선택하고 하단 시간축으로 재생·탐색합니다. 라이브 영상은 `recording` 소스를 선택하고 시간축을 최신 시점으로 이동합니다.

녹화가 진행 중인 Parquet 파일은 아직 footer가 없어 표준 뷰어가 읽지 못할 수 있습니다. 이 실행 파일은 닫힌 데이터 파일과 메타데이터의 별도 스냅샷을 사용하며 원본을 변경하지 않습니다. 현재 세션의 최신 에피소드는 Ubuntu에서 `q`로 저장·종료한 뒤 볼 수 있습니다. `view_episodes.py`의 `--root`, `--repo-id`로 다른 데이터셋도 지정할 수 있습니다.

### 현재 PC용 수정

- Windows 브리지 카메라: 카메라 USB는 Windows에 남기며 로봇 두 개만 WSL에 붙입니다.
- `patch_zmq_rgb.py`: 설치된 0.6.1의 ZMQ JPEG 디코딩 결과를 RGB로 맞춥니다.
- `patch_rerun_images.py`: 이미지 로그의 `static=True`를 제거해 영상 프레임이 Rerun 시간축에 남도록 합니다. 원본은 `.py.before-live-images`로 보관합니다.
- 새로 만든 별도 연결 루프·웹 서버·메뉴는 CMD 실행 경로에서 사용하지 않습니다.

## 모드 전환과 오류

- 두 버튼을 동시에 누르지 마세요. 준비 중 중복 실행은 잠금으로 차단합니다.
- 학습·녹화·제어가 실행 중이면 해당 프로그램에서 정상 종료한 뒤 전환합니다. 학습을 강제로 끊거나 로봇 프로세스를 강제 종료하지 않습니다.
- 두 모드 모두 같은 Windows 카메라 서버를 재사용합니다. Studio 모드에서는 ZMQ 서버가 필요 없어 종료하고, LeRobot 모드에서만 추가 실행합니다.
- 오류가 나면 창이 닫히지 않고 `FAILED` 이유를 보여줍니다. `runtime/launcher.log`에 같은 메시지가 저장됩니다. 최근 성공 모드와 시간은 `runtime/last-run.json`에 기록됩니다.
- USB 누락: 케이블을 확인하고 다시 실행. `usbipd list`의 **Attached**는 USB 연결 상태이며 DC 모터 전원 상태가 아닙니다.
- `not shared`: 안내된 BUSID를 관리자 PowerShell에서 bind한 뒤 다시 실행합니다. 첫 USB 공유에는 관리자 권한이 필요합니다.
- 카메라 대기 시간 초과: 웹캠 연결·다른 카메라 앱·`runtime/bridge.log` 확인. 카메라를 WSL에 자동 attach하는 설정이 남아 있지 않은지 확인합니다.
- ZMQ 수신 실패: `runtime/relay.log` 및 Windows 방화벽 확인. 현재 WSL 가상 어댑터의 TCP 5555 통신이 가능해야 합니다. 스크립트는 방화벽을 끄지 않습니다.
- Studio API가 응답하지 않아 작업 상태를 확인할 수 없으면 자동 종료하지 않습니다. 작업 상태를 직접 확인한 후 컨테이너를 정상 종료하고 다시 실행합니다.
- 준비 완료는 환경·영상·USB 확인이며 실제 모터 통신이나 GPU 학습 성공을 보장하는 검사는 아닙니다.

### WSL이 출력 없이 오류 코드 1로 끝날 때

2026-10-23에 배포판은 Running이지만 `/bin/echo`까지 실행되지 않는 상태가 발생했습니다. 메모리 여유와 진행 중인 학습·녹화 부재를 확인한 뒤 WSL 가상 머신을 재시작해 복구했습니다. 이 경우 LeRobot 설치나 카메라 설정을 다시 할 필요는 없습니다.

1. Ubuntu/VS Code에서 작업을 저장하고 학습·녹화·제어를 정상 종료합니다. Docker 작업도 확인합니다.
2. Windows PowerShell에서 `wsl --shutdown`을 실행합니다. 모든 WSL 배포판과 그 안의 프로그램이 종료됩니다.
3. `windows/Start-LeRobot.cmd` 또는 `windows/Start-Studio.cmd`를 다시 실행합니다. USB와 카메라 경로는 실행 파일이 다시 준비합니다.

스크립트는 작업 상태를 확인할 수 없는 WSL을 자동으로 강제 재시작하지 않습니다. 오류 코드·실패 단계·복구 안내를 로그와 화면에 표시합니다.

관리·검증용으로 브라우저를 열지 않고 같은 준비를 수행하려면 아래 명령을 사용합니다. LeRobot의 `-Headless`는 사전 설정·카메라 준비만 검사하고 녹화 세션이나 모터 추종을 시작하지 않습니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\start.ps1 -Mode Studio -Headless
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\start.ps1 -Mode LeRobot -Headless
```

## 구조와 변경 범위

```text
Studio:  webcam -> Windows MJPEG :8765 -> Docker Studio -> browser
LeRobot: webcam -> Windows MJPEG :8765 -> Windows ZMQ :5555 -> WSL LeRobot -> native Rerun
Robots:  USB -> usbipd -> WSL serial devices -> selected application
```

`windows/`의 CMD 파일과 `start.ps1`이 실행 진입점입니다. 기존 컨테이너·데이터·캘리브레이션은 새로 만들거나 지우지 않습니다. 프로그램 종료 후에도 공용 카메라 서버와 USB 자동연결 작업은 유지됩니다. 자세한 카메라 구성은 `docs/CAMERA-RELAY.ko.md`를 참고하세요.

### 실행 파일 구성

- `start.ps1`: 공통 준비와 Studio/LeRobot 선택 실행.
- `record-standard.sh`: 교재의 표준 녹화 명령 자동 실행. Ubuntu 창은 키 입력과 오류 확인용입니다.
- `wsl/record.sh`: 현재 USB 시리얼·캘리브레이션·카메라·데이터셋을 반영한 실제 `lerobot-record` 명령.
- `camera_address.py`: NAT/mirrored 주소 선택.
- `recorder.py`: Dataset Desk의 로봇·카메라 연결과 녹화 루프. `native-viewer.py`는 이전 실험용 코드입니다.

### 저장된 에피소드 삭제

1. 녹화 중이면 먼저 **중지 · 저장**을 누르고, **연결 해제**가 끝날 때까지 기다립니다.
2. **데이터셋** 탭에서 데이터셋과 에피소드를 선택합니다.
3. **선택 에피소드 삭제**를 누르고 확인합니다. 영상 정리가 끝날 때까지 기다리세요.
4. 남은 에피소드 번호는 0부터 다시 정렬됩니다. 영상 구간과 관절값·메타데이터도 함께 정리하므로 이후 학습에서도 삭제한 에피소드가 제외됩니다.
5. 실수했다면 **최근 삭제 복원**을 누릅니다. 삭제 후 새 녹화나 외부 수정이 있었다면 덮어쓰기를 막기 위해 복원하지 않습니다.

원본 전체는 WSL의 `~/.cache/huggingface/lerobot/.dataset-desk-history/<고유 ID>/original`에 보관합니다. 백업은 자동 삭제하지 않으므로 디스크 공간을 사용합니다. 마지막 에피소드를 삭제해도 데이터셋 이름과 카메라 설정은 남아 새 녹화를 이어갈 수 있습니다. 데이터셋 전체 삭제 버튼은 제공하지 않습니다. Hub에 이미 올린 사본은 변경하지 않습니다.

### 현재 통신 검사 결과

2026-10-23에 Leader가 모두 무응답인 상태가 발생했고, USB-C 재연결 후 잠시 두 팔 12개 모터가 응답해 표준 녹화가 시작됐으나 에피소드 저장 전에 Leader 통신이 다시 끊겼습니다. **자동 attach를 잠시 중단하고 Windows COM11에서 직접 검사해도 Leader 6개가 모두 무응답**이었습니다. Follower는 정상 응답했습니다. 따라서 이 증상은 WSL/Rerun 설정만으로 설명되지 않습니다. Leader의 USB와 DC를 모두 빼 완전히 껐다가 다시 연결하고 UART 배선·전원 상태를 점검해야 합니다. USB Attached만으로 모터 응답까지 보장되지는 않습니다. 자동 attach 작업은 검사 후 복원했습니다.

표준 녹화 로그는 `runtime/standard-record.log`에 남습니다. Ubuntu 창에서 정상 종료한 뒤 확인하세요. 키 조작은 Ubuntu 창에 포커스가 필요하며, 별도 명령어 입력은 필요하지 않습니다.

Leader의 USB와 DC를 모두 빼 10초 뒤 다시 연결한 후, Windows COM11 직접 검사에서 **25초 동안 관절 위치 읽기 4,620회, 오류 0회**를 확인했습니다. USB만 다시 꽂았을 때 잠깐 복구됐다가 끊기는 경우에는 완전 전원 재인가와 연속 읽기 검사로 안정성을 확인하세요. `check-leader-windows.py`는 위치·토크 명령을 보내지 않는 검사 도구입니다.

같은 전원 재인가 후 WSL에서도 **25초 동안 두 팔 관절 읽기 744회가 연속 성공**했습니다. 표준 녹화의 첫 60초에서 영상 1,781프레임을 수집하고 통신 단절 없이 재배치 단계로 넘어가는 것까지 확인했습니다.

이후 자동 저장으로 **총 에피소드 21 → 22, 총 프레임 16,001 → 17,782**가 되었고, 에피소드 22(0부터 세는 번호)의 다음 녹화가 계속 진행되는 것을 확인했습니다. 이 기록은 테스트 모의 데이터가 아니라 실제 두 팔·카메라로 수집한 데이터입니다.

Rerun 창을 닫은 뒤 재연결할 때는 새 RecordingStream을 생성해 이전 gRPC 연결을 교체합니다. `gRPC connection severed`가 남은 화면은 새로고침한 뒤 **로봇 연결 + Rerun**을 다시 누르세요. 이 버튼만으로 녹화·추종을 시작하지 않습니다.

## 학습 탭

상단 **학습** 탭에서 데이터셋·스텝·배치·학습률·warmup·검증 비율·저장 간격을 설정하고 로컬 WSL GPU 학습을 시작할 수 있습니다. 진행률, 학습·검증 loss 그래프, 실행 기록, 체크포인트, 로그가 5초마다 갱신됩니다. 기존 CLI 학습 기록도 표시합니다.

새 학습 시작 전 녹화·저장·추종을 멈춰 주세요. 데이터 복사·검증 중에는 새 녹화·편집을 차단하며, 준비가 끝나면 원본에 추가 수집할 수 있습니다. 한 번에 한 학습만 실행하며 Hub 업로드는 하지 않습니다. 자세한 동작·검사는 [학습 안내](TRAINING.ko.md)를 참고하세요.

## 코드 구조

실제 구현과 수정 위치는 [코드 구조 안내](ARCHITECTURE.ko.md)를 참고하세요. 웹 화면 원본은 `web/dataset-desk/`, Python 구현은 `src/intel7_vla/`, OS 실행 스크립트는 `windows/`와 `wsl/`, 검사는 `tests/`에서 관리합니다.
