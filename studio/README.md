# Physical AI Studio 자료 (1일차)

2026-10-22 Intel Physical AI Studio 실습에서 만든 설정·우회 자료입니다. LeRobot 경로(`windows/`, `wsl/`)에는 필요하지 않으며, Studio를 다시 쓸 때 참고합니다. Studio 실행 자체는 `windows/Start-Studio.cmd`가 기존 컨테이너를 시작합니다.

| 경로 | 내용 |
|---|---|
| `camera-bridge-share/` | Studio용 Windows 카메라 → MJPEG 브리지 수업 배포본 (설치 스크립트 포함) |
| `recording-encoder-fix/` | Studio 컨테이너의 RGB 녹화 gray12le/HEVC 오류 우회 패치와 검증 스크립트 |
| `performance-recovery/` | 자동 배치 확장으로 메모리가 부족했던 학습의 복구 기록과 원래 `.wslconfig` |
| `docker-compose.override.yaml` | WSL `/dev` 전체를 Studio 컨테이너와 공유 (USB 핫플러그) |
| `studio_export_calibration.py` | Studio DB의 SO-101 보정값을 LeRobot 보정 파일로 내보내기 |

설치 순서 원본은 [docs/COURSE-SETUP.ko.md](../docs/COURSE-SETUP.ko.md), 기준 버전은 [tools/patches/README.md](../tools/patches/README.md)를 참고하세요.
