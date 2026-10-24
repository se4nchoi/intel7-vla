# intel7-vla — 로봇 시연 수집과 VLA 학습 실험

SO-101 Leader/Follower로 시연을 수집하고 영상·관절 데이터를 확인하여 ACT/SmolVLA 학습과 추후 로봇 실행 실험에 활용하는 팀 프로젝트입니다. Windows와 WSL 코드를 하나의 저장소에서 관리합니다.

현재 작업은 **빨간 공을 집고, 집은 위치에서 왼쪽/오른쪽의 열린 경로를 판단해 두 콘 사이로 굴리거나 슛해서 득점하기**입니다. 기본 데이터셋은 `se4nchoi/messi`입니다.

> Pick up the red ball, identify the open lane to the left or right of the pickup location, and roll or shoot the ball between the two cones to score a goal.

## 현재 구현 상태

- Windows 카메라 2대의 DirectShow → MJPEG → ZMQ → WSL LeRobot 영상 전달
- Dataset Desk 웹 화면에서 에피소드 영상·관절값 조회와 재생
- 로봇 연결, Leader 추종, 녹화·저장·버리기, 연결 해제 제어
- Rerun 실시간 카메라·관절 시각화
- Physical AI Studio 실행과 카메라·RGB 인코더 문제 우회 스크립트
- 학습 탭에서 파라미터 설정·SmolVLA 학습 시작·진행률·loss·체크포인트·로그 확인. 모델 파일 자체와 실제 작업 성공률은 포함하지 않습니다.

**2026-10-23 현재 PC 작업 상태를 공유하는 초기 버전입니다.** USB 시리얼·카메라 이름·Windows Python 경로가 코드에 남아 있으므로 새 PC에서는 [팀원 설치 안내](docs/SETUP.ko.md)에 따라 수정해야 합니다. clone만으로 실행 환경이 복원되지는 않습니다.

## 실행 구조

```text
Windows 카메라 2대 → DirectShow/MJPEG (8765 / 8766)
  ├─ Docker Physical AI Studio (선택)
  └─ ZMQ relay (5555 / 5556)
       └─ WSL Ubuntu: LeRobot + Dataset Desk + Rerun
            └─ ~/.cache/huggingface/lerobot/<owner>/<task>
SO-101 Leader/Follower USB → usbipd → WSL 직렬 포트
```

카메라는 Windows에 두고 로봇 USB만 WSL에 연결합니다. Docker는 LeRobot 경로에 필요하지 않습니다. 현재 카메라명은 `follower_cam` / `field_cam`, DirectShow 장치명은 `icspring camera` / `USB HD`입니다.

## 설치와 사용

현재 PC의 명령별 실행 예시는 [우리 설정에 맞춘 LeRobot 명령어 안내](docs/LEROBOT-COMMANDS.ko.md)를 참고하세요. 수동 조종·녹화·데이터 조회·편집·BF16 학습·rollout·replay·재보정을 정리했습니다.

1. [팀원 설치 안내](docs/SETUP.ko.md)에 따라 의존성과 장치를 준비합니다.
2. PC 경로·Python 실행 경로·USB 시리얼·카메라 이름·캘리브레이션을 맞춥니다.
3. `windows/` 폴더의 실행 파일을 더블클릭합니다.

| 실행 파일 | 용도 |
|---|---|
| `windows/Start-LeRobot.cmd` | USB·카메라·ZMQ 준비 후 Dataset Desk 열기 |
| `windows/Start-Dataset-Viewer.cmd` | 저장된 데이터셋 조회 |
| `windows/Start-Studio.cmd` | 기존 Studio 컨테이너 시작 |
| `windows/View-Episodes.cmd` | 최근 읽을 수 있는 에피소드를 Rerun에서 보기 |

Dataset Desk: <http://localhost:8877> / Studio: <http://localhost:7860>

시작 파일만 실행하면 녹화하지 않습니다. 화면에서 `로봇 연결 + Rerun` → 자세 확인 → `녹화 시작` → `중지 · 저장` 순서로 사용합니다. `추종 켜기 (저장 안 함)`도 실제 로봇을 움직입니다. 브라우저를 닫아도 연결은 유지되므로 종료 전 `연결 해제`를 누르세요.

두 팔의 모터 전원과 USB를 연결하고 시작 자세를 비슷하게 맞추며 작업 공간을 비우세요. Studio와 LeRobot이 같은 직렬 포트를 동시에 사용하지 않도록 합니다.

## 저장소 구성

최상위 폴더는 실행되는 위치(Windows / WSL)로 나눴습니다.

| 경로 | 역할 |
|---|---|
| `windows/` | **Windows에서 실행**: 더블클릭 실행 파일, 준비·카메라 브리지·ZMQ relay, `setup/` 설치 스크립트 |
| `wsl/` | **Ubuntu(WSL)에서 실행**: Dataset Desk 서버·녹화·학습·재생, `setup/` 최초 준비 |
| `src/intel7_vla/` | 웹 API·녹화·데이터 편집·학습·Windows 브리지의 실제 Python 구현 |
| `web/dataset-desk/` | HTML·CSS·JavaScript 화면 원본 |
| `tools/` | `diagnostics/` 수동 진단, `patches/` LeRobot 패치, `maintenance/` |
| `tests/` | 녹화·편집·학습 API·화면 회귀 검사 |
| `config/calibration-examples/` | 현재 실물 장치의 참고 보정값 |
| `studio/` | 1일차 Physical AI Studio 자료 (카메라 브리지 배포본, 인코더 우회, compose override 등) |
| `docs/` | 설치·운영·명령어·학습·카메라·구조 안내, `notes/` 과거 기록 |
| `runtime/` | 로그·상태 파일 (자동 생성, Git 제외) |

코드를 수정할 위치와 의존 방향은 **[코드 구조 안내](docs/ARCHITECTURE.ko.md)**에 정리했습니다.

| 문서 | 내용 |
|---|---|
| [SETUP](docs/SETUP.ko.md) | 새 PC 설치와 PC별 설정 |
| [OPERATIONS](docs/OPERATIONS.ko.md) | 실행 파일 동작·녹화·삭제·오류 대응 |
| [LEROBOT-COMMANDS](docs/LEROBOT-COMMANDS.ko.md) | 우리 설정에 맞춘 LeRobot CLI |
| [TRAINING](docs/TRAINING.ko.md) | SmolVLA 학습 기록과 학습 탭 |
| [CAMERA-RELAY](docs/CAMERA-RELAY.ko.md) / [CAMERA-BRIDGE](docs/CAMERA-BRIDGE.ko.md) | Windows 카메라 → ZMQ → WSL 구조 |
| [COURSE-SETUP](docs/COURSE-SETUP.ko.md) | 수업용 Windows 11 설치 순서 원본 |
| [tools/patches](tools/patches/README.md) | LeRobot·Studio 기준 버전과 패치 | 하위 문서에는 과거 단일 카메라·`redball` 기록도 있습니다. 현재 두 카메라 `messi` 설치는 이 README와 팀원 설치 안내를 우선합니다.

## 코드와 데이터 공유

- GitHub에는 소스·문서·패치를 올립니다. 가상환경·로그·캐시·임시 ZIP·영상·모델은 제외합니다.
- 데이터는 WSL `~/.cache/huggingface/lerobot/<owner>/<task>`에 저장되며 Git push로 공유되지 않습니다. 필요하면 별도로 Hugging Face Hub 등에 업로드하고 링크를 공유합니다.
- 토큰은 각자 로컬에서 인증하고 커밋하지 않습니다. Studio와 WSL CLI 인증은 별개입니다.
- `config/calibration-examples/`의 보정 파일은 현재 실물 장치의 참고 자료입니다. 다른 팔에는 해당 하드웨어의 보정값을 사용해야 합니다.

## 팀 협업

소유자가 GitHub Settings → Collaborators에서 팀원을 초대합니다. 팀원은 초대를 수락한 계정으로 clone합니다.

```powershell
git clone https://github.com/se4nchoi/intel7-vla.git
cd intel7-vla
git switch -c feature/작업이름
# 수정·검증 후
git add <변경한파일>
git commit -m "변경 내용"
git push -u origin feature/작업이름
```

GitHub에서 PR을 만들고 검토 후 합칩니다. 작업 전 로컬 변경을 커밋한 뒤 `git switch main`, `git pull --ff-only`로 최신 코드를 받습니다. WSL `~/lerobot`은 별도 upstream 저장소이므로 팀 변경은 이 저장소의 코드·패치로 반영합니다.

## 검증

하드웨어 없이 대기·저장·이어 저장·버리기와 영상 디코딩을 확인하는 기존 통합 검사는 WSL LeRobot 가상환경에서 실행합니다.

```bash
cd ~/lerobot
.venv/bin/python /mnt/c/Users/<사용자>/intel7-vla/tests/check_dataset_ui.py
```

실제 USB·모터·카메라·GPU 학습은 각 PC에서 따로 확인해야 합니다.
