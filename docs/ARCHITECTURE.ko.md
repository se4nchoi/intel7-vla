# 코드 구조와 실행 경계

실제 구현은 `src/intel7_vla/`에 모았습니다. `workflows/`와 기존 카메라·학습 폴더의 실행 파일은 예전 호출을 유지하기 위한 얇은 호환 진입점입니다. 기능을 수정할 때는 아래 원본을 수정하세요.

```text
src/intel7_vla/
  paths.py                      프로젝트·정적 파일·기존 런타임 경로
  common/camera_address.py      WSL에서 Windows 카메라 주소 확인
  recording/                    로봇·녹화 루프와 Rerun 스트림
  datasets/                     에피소드 삭제·복원과 재생
  training/
    options.py                  기본값·파라미터 검증
    progress.py                 로그와 정확한 스텝·loss 해석
    jobs.py                     실행 목록·중복 차단·상태·체크포인트
    runner.py                   스냅샷 복사·검증·독립 학습 프로세스
    bf16.py                     설치된 LeRobot의 BF16 실행 어댑터
    cli.py                      웹과 같은 실행 관리자를 사용하는 CLI
  web/server.py                 HTTP API와 녹화·학습 명령 조정
  platforms/windows/           DirectShow 서버·ZMQ relay
web/dataset-desk/
  index.html                    화면 구조
  assets/desk.css, desk.js      데이터 조회·녹화 화면
  assets/training.css, .js      학습 설정·상태·로그 화면
scripts/windows/                Windows 시작·카메라·relay·설치 PowerShell
scripts/wsl/                    WSL 웹 서버·녹화·학습 시작
training/                       기존 학습 명령의 호환 진입점과 운영 기록
workflows/                      기존 경로 호환 진입점·운영 문서
config/calibration-examples/    현재 장치의 참고 보정값
tools/                         진단·패치·유지보수 (자동 실행하지 않음)
tests/                          하드웨어 없는 검사와 별도 수동 진단
```

## 의존 방향

- 웹 서버와 CLI는 같은 `training.jobs.TrainingManager`를 사용합니다.
- 학습 시작·상태 조회는 녹화 루프와 별도입니다. 학습 프로세스는 웹 서버와 독립 실행됩니다.
- `training.runner`만 시연을 고정 복사하고, 설치된 외부 `~/lerobot`의 학습 코드를 호출합니다.
- Windows 전용 DirectShow 의존성은 `platforms/windows`에 두며 WSL 서버에서 import하지 않습니다.
- 정적 HTML/CSS/JavaScript에는 Python·직렬 포트·학습 프로세스 로직이 없습니다.
- 외부 LeRobot 소스·가상환경은 저장소에 복사하지 않습니다. 필요한 패치는 `patches/`와 `tools/patches/`에서 관리합니다.

## 현재 PC와 기존 명령 호환

루트 `Start-*.cmd`, `View-Episodes.cmd`는 그대로 사용할 수 있습니다. 기존 `workflows/dataset_ui.py`, `workflows/recorder.py`, `workflows/training_jobs.py` 등은 실제 패키지를 불러옵니다. 과거 import의 모듈 객체도 같은 원본을 가리키도록 연결했습니다.

코드 정리 시 실행 중인 웹 서버를 재시작하거나 로봇 연결을 해제하지 않았습니다. 이미 실행 중인 예전 웹 서버가 읽는 `workflows/dataset_ui.html`, `training_ui.js`, `training_ui.css`는 현재 PC에만 호환 스냅샷으로 남겼고 Git에서는 제외합니다. 새 checkout은 `web/dataset-desk/`의 정적 파일을 바로 사용합니다. 정적 파일의 수정 원본은 항상 `web/dataset-desk/`입니다.

런타임 위치도 유지합니다.

| 데이터 | 위치 |
|---|---|
| 실제 녹화 데이터 | WSL `~/.cache/huggingface/lerobot/<owner>/<task>` |
| 학습 복사본·모델·로그 | WSL `~/vla-training/runs/<학습ID>/` |
| 기존 실행 상태·로그·종료 요청 | 프로젝트 `workflows/`의 Git 제외 파일 |
| Windows 카메라 로그 | 기존 `camera-bridge/`의 Git 제외 파일 |

`paths.py`의 `RUNTIME_ROOT`는 기본적으로 기존 `workflows/`를 사용합니다. 독립 개발 서버는 `VLA_RUNTIME_DIR`로 별도 위치를 지정할 수 있습니다. 하드웨어 장치 번호·배포판·Python 경로는 기존 PC 값을 유지했으며 모든 컴퓨터에 자동 적응하는 설정으로 바꾸지는 않았습니다.

## 새 기본 진입점

Ubuntu:

```bash
cd /mnt/c/Users/user/rjsxo
~/lerobot/.venv/bin/python scripts/wsl/dataset_desk.py
# 위 명령은 서버가 이미 실행 중이면 중복 실행하지 마세요.

~/lerobot/.venv/bin/python scripts/wsl/train.py --help
~/lerobot/.venv/bin/python scripts/wsl/train.py --repo se4nchoi/messi --steps 20000 --batch-size 4
```

새 학습 CLI는 웹과 같은 기본 10,000스텝·중복 차단·스냅샷 검증을 사용합니다. 이전 `training/start_messi_smolvla.py` 경로는 2,000스텝 기본값을 유지하며 내부적으로 같은 실행 관리자를 호출합니다.

Windows의 실제 준비 로직은 `scripts/windows/start.ps1`입니다. 설치 스크립트·모터 진단·패치 도구는 파일을 읽거나 테스트를 실행한다는 이유만으로 자동 실행하지 않습니다.

## 검사 실행

Ubuntu (실제 장치를 사용하지 않는 검사):

```bash
cd /mnt/c/Users/user/rjsxo
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
