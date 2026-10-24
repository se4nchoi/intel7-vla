# WSL 변경 재현

2026-10-23 현재 작업 트리 기준입니다.

| 구성 요소 | 기준 |
|---|---|
| LeRobot upstream | https://github.com/huggingface/lerobot |
| LeRobot HEAD | `7e241bd630a3719a56157a497ce5d08f244784f1` (패키지 0.6.1) |
| Python | 3.12 가상환경 |
| pyzmq / rerun-sdk / av | 27.2.0 / 0.33.1 / 15.1.0 |
| Studio HEAD | `9fd6fbea534bfcfcb9747f8902f7e85a37bedc73` |

`lerobot-0.6.1-local.patch`는 WSL에서 수정한 두 파일의 전체 diff입니다. ZMQ JPEG를 RGB로 변환하고 Rerun 영상을 static 대신 시간축에 기록합니다.

아직 수정하지 않은 위 기준 커밋에서 실제 clone 경로에 맞춰 적용합니다.

```bash
cd ~/lerobot
git apply --check /mnt/c/Users/<사용자>/intel7-vla/tools/patches/lerobot-0.6.1-local.patch
git apply /mnt/c/Users/<사용자>/intel7-vla/tools/patches/lerobot-0.6.1-local.patch
```

이미 적용한 환경에는 중복 적용하지 마세요. 같은 변경을 적용하는 `tools/patches/patch_zmq_rgb.py`와 `tools/patches/patch_rerun_images.py`도 보관하며 실행 준비 과정에서 사용합니다.

Studio의 docker compose override는 `studio/docker-compose.override.yaml`입니다(WSL `/dev` 전체를 컨테이너와 공유). Studio 저장소에는 그 외 소스 수정이 없었습니다. 컨테이너 전체를 백업한 것은 아니며 알려진 RGB 인코더 변경은 `studio/recording-encoder-fix/`로 별도 재현합니다.

상위 프로젝트 소스 전체와 가상환경은 복사하지 않습니다. 해당 프로젝트 라이선스와 설치 안내를 따르세요.
