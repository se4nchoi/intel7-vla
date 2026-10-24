# 초기 공유본 검증 기록

2026-10-23 현재 PC에서 수행했습니다.

- 기존 `workflows/check_dataset_ui.py` 통합 검사 통과: 대기 중 데이터 미생성, 2개 에피소드 저장·이어 저장, 버리기 후 에피소드 수 유지.
- 관절 행 28개와 두 카메라 영상의 디코딩 프레임 56개 확인.
- WSL LeRobot 패치가 현재 수정본과 일치함을 `git apply --reverse --check`로 확인.
- 추적 대상 Python 22개 파일의 AST 구문 검사와 PowerShell 스크립트 구문 검사 통과.
- 새 README·설치 안내·패치 문서의 상대 링크 대상 존재 확인.
- 업로드 대상에서 알려진 Hugging Face/GitHub 토큰 패턴과 개인키 헤더가 발견되지 않음.

이번 업로드 과정에서 실제 로봇 동작, 새 PC 설치, GPU 학습을 재검증하지는 않았습니다. 기존 실행 코드의 PC 경로·장치 설정을 유지했고 변경은 문서·Git 제외 규칙·줄바꿈 정책·WSL 패치/설정 보관 및 일부 파일 끝 빈 줄 정리입니다.

- WSL bash에서 추적 대상 셸 스크립트의 구문 검사도 통과했습니다.

## 코드 구조 분리 검증 — 2026-10-23

- 실제 Python 구현을 `src/intel7_vla/`의 녹화·데이터·학습·웹·Windows 브리지 패키지로 분리했습니다.
- 웹 HTML/CSS/JS 원본, OS 실행 스크립트, 진단·패치 도구, 테스트를 별도 경로에 두고 예전 실행 경로는 호환 진입점으로 유지했습니다.
- `tests/check_dataset_ui.py`, `check_episode_edit.py`, `check_viewer_backpressure.py`, `check_rerun_reconnect.py`, `check_training_jobs.py` 통과.
- `tests/check_training_ui.cjs`, `tests/check_ui_controls.cjs` 및 이전 JS 검사 진입점 통과.
- Python 65개 파일 구문, PowerShell 구문, WSL 셸 구문, 문서 상대 링크, 새/기존 CLI 도움말 검사 통과.
- 기존 8877 서버를 유지한 채 8891의 별도 데모 서버에서 기본 HTML, 정적 자산 4개, 이전 학습 JS 주소, 기존 학습 기록 조회를 확인했습니다.
- 분리 후에도 과거 Python import가 같은 실제 모듈 객체를 참조함을 확인했습니다.
- 최신 10,000스텝 학습과 이전 2,000스텝 학습이 완료 상태로 조회되며, 이번 정리에서 새 학습·실제 카메라/모터 검사·웹 서버 재시작은 수행하지 않았습니다.

독립 검사 서버는 검사 후 정상 종료했습니다. 실제 장치 동작과 브라우저 화면의 시각 재검증은 이 구조 정리 검사의 범위에 포함하지 않았습니다.

## 플랫폼별 폴더 재구성 검증 — 2026-10-24

개인 노트북(Windows 11, WSL 배포판 없음)에서 수행했습니다.

- 최상위를 `windows/`, `wsl/`, `studio/`, `tools/`, `docs/`로 재구성하고 호환 진입점(`workflows/`, `camera-bridge/`, `lerobot-camera-bridge/`, `training/`, 루트 probe)을 삭제했습니다.
- 스크립트의 `C:\Users\user\rjsxo`, `/mnt/c/Users/user/rjsxo` 하드코딩을 자기 위치 기준 경로 계산으로 바꿨습니다. 로그·상태 파일은 `runtime/`(Git 제외)로 모았습니다.
- Python 52개 파일 구문, `wsl/` 셸 스크립트 `bash -n`, PowerShell 10개 파서 검사 통과.
- `tests/check_training_ui.cjs`, `tests/check_ui_controls.cjs` 통과. 문서 상대 링크 확인.
- WSL·LeRobot·실제 장치가 없어 Python 통합 검사(`tests/check_*.py`), 실행 파일 동작, 카메라·모터는 재검증하지 않았습니다.
