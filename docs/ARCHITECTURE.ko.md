# 코드 구조와 실행 경계

최상위 폴더는 **어느 쪽에서 실행되는지**로 나눕니다. Windows에서 실행하는 파일은 `windows/`, Ubuntu(WSL)에서 실행하는 파일은 `wsl/`에 있습니다. 실제 Python 구현은 `src/intel7_vla/`에 있고, 두 폴더의 Python 파일은 이 패키지를 불러오는 얇은 진입점입니다.

```text
intel7-vla/
  windows/                       Windows에서 실행
    Start-LeRobot.cmd 등          더블클릭 실행 파일
    start.ps1                     USB·카메라·ZMQ·Studio/LeRobot 준비
    open-dataset-ui.ps1           WSL Dataset Desk 시작 후 브라우저 열기
    start-camera-relay.ps1        ZMQ relay 2개 시작 (5555 / 5556)
    start-field-camera.ps1        필드 카메라 MJPEG 브리지 (8766)
    camera_server.py, relay.py    DirectShow 브리지·ZMQ relay 진입점
    setup/                        카메라 브리지·usbipd 자동 연결 설치, .wslconfig 예시
  wsl/                           Ubuntu(WSL)에서 실행
    dataset_desk.py               Dataset Desk 웹 서버
    record.sh, record-standard.sh 우리 설정의 lerobot-record
    prepare-wsl.sh                패치·카메라·녹화 설정 사전 검사
    train.py, run_training_job.py, train_bf16.py   학습 CLI·작업 감독·BF16 실행
    view-episodes.sh, start-*.sh  에피소드 Rerun 재생, 서버 시작
    setup/setup-wsl.sh            Ubuntu 최초 준비
  src/intel7_vla/
    paths.py                      프로젝트·정적 파일·runtime 경로
    common/camera_address.py      WSL에서 Windows 카메라 주소 확인
    recording/                    로봇·녹화 루프와 Rerun 스트림
    datasets/                     에피소드 삭제·복원과 재생
    training/                     파라미터 검증·진행률·작업 관리·독립 실행·BF16·CLI
    web/server.py                 HTTP API와 녹화·학습 명령 조정
    platforms/windows/            DirectShow 서버·ZMQ relay 구현
  web/dataset-desk/              HTML·CSS·JavaScript 화면 원본
  tools/
    diagnostics/                  카메라·모터·프로세스·녹화 설정 수동 진단
    patches/                      LeRobot 0.6.1 패치와 적용 스크립트
    maintenance/                  일회성 유지보수
  tests/                         하드웨어 없는 회귀 검사와 수동 검사
  config/calibration-examples/   현재 장치의 참고 보정값
  studio/                        1일차 Physical AI Studio 자료
  docs/                          설치·운영·명령어·학습·카메라·구조 안내
  runtime/                       로그·상태 파일·잠금 (Git 제외, 자동 생성)
```

## 의존 방향

- 웹 서버와 CLI는 같은 `training.jobs.TrainingManager`를 사용합니다.
- 학습 시작·상태 조회는 녹화 루프와 별도입니다. 학습 프로세스는 웹 서버와 독립 실행됩니다.
- `training.runner`만 시연을 고정 복사하고, 설치된 외부 `~/lerobot`의 학습 코드를 호출합니다.
- Windows 전용 DirectShow 의존성은 `platforms/windows`에 두며 WSL 서버에서 import하지 않습니다.
- 정적 HTML/CSS/JavaScript에는 Python·직렬 포트·학습 프로세스 로직이 없습니다.
- 외부 LeRobot 소스·가상환경은 저장소에 복사하지 않습니다. 필요한 패치는 `tools/patches/`에서 관리합니다.

## 경로 계산

스크립트는 저장소 경로를 하드코딩하지 않고 자기 위치에서 계산합니다.

- WSL 셸 스크립트: `root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`
- Windows PowerShell: `$root`에서 `/mnt/<드라이브>/...` 형태의 `$wslRoot`를 만들어 WSL 명령에 전달
- Python: `intel7_vla.paths.PROJECT_ROOT`

PC마다 다른 값(USB 시리얼, 카메라 장치명, Windows Python 경로, WSL 배포판 이름)은 아직 스크립트에 들어 있습니다. 목록은 [설치 안내](SETUP.ko.md)의 "PC별 설정 맞추기"를 참고하세요.

## 런타임 위치

| 데이터 | 위치 |
|---|---|
| 실제 녹화 데이터 | WSL `~/.cache/huggingface/lerobot/<owner>/<task>` |
| 학습 복사본·모델·로그 | WSL `~/vla-training/runs/<학습ID>/` |
| 실행 상태·로그·종료 요청·카메라 로그 | 저장소 `runtime/` (Git 제외) |

`paths.py`의 `RUNTIME_ROOT`는 기본적으로 `runtime/`이며, `VLA_RUNTIME_DIR`로 다른 위치를 지정할 수 있습니다.

## 기본 진입점

Ubuntu:

```bash
cd /mnt/c/Users/<사용자>/intel7-vla
~/lerobot/.venv/bin/python wsl/dataset_desk.py
# 서버가 이미 실행 중이면 중복 실행하지 마세요.

~/lerobot/.venv/bin/python wsl/train.py --help
~/lerobot/.venv/bin/python wsl/train.py --repo se4nchoi/messi --steps 20000 --batch-size 4
```

학습 CLI는 웹과 같은 기본 10,000스텝·중복 차단·스냅샷 검증을 사용합니다.

Windows의 실제 준비 로직은 `windows/start.ps1`입니다. 설치 스크립트·모터 진단·패치 도구는 자동 실행하지 않습니다.

## 검사 실행

Ubuntu (실제 장치를 사용하지 않는 검사):

```bash
cd /mnt/c/Users/<사용자>/intel7-vla
~/lerobot/.venv/bin/python tests/check_training_jobs.py
~/lerobot/.venv/bin/python tests/check_dataset_ui.py
~/lerobot/.venv/bin/python tests/check_episode_edit.py
~/lerobot/.venv/bin/python tests/check_viewer_backpressure.py
~/lerobot/.venv/bin/python tests/check_rerun_reconnect.py
```

Windows PowerShell:

```powershell
node tests/check_training_ui.cjs
node tests/check_ui_controls.cjs
```

`tests/check_live_recording.py`는 실제 카메라를 읽는 수동 검사입니다. `tools/diagnostics/check_motors.py`는 UART 포트를 여는 수동 진단입니다. 이 둘은 일반 회귀 검사에 포함하지 않습니다.
