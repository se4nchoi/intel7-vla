# 우리 PC의 LeRobot 명령어

2026-10-23 설치된 Ubuntu-24.04의 CLI 도움말·소스와 프로젝트 설정 기준입니다. 아래 예시는 사용 안내이며 실제 로봇 실행·재보정·데이터 편집을 수행한 기록이 아닙니다.

## 1. 실행 환경과 공통 설정

PowerShell에서 먼저 준비합니다.

```powershell
cd C:\Users\user\rjsxo
.\Start-LeRobot.cmd
```

USB 연결과 Windows 카메라 브리지, ZMQ relay를 준비하는 프로젝트 실행 파일입니다. 준비 완료 후 Dataset Desk의 녹화·추종을 중지하고 **연결 해제**한 다음 다른 로봇 CLI를 사용합니다. 같은 직렬 포트를 웹 UI와 CLI가 동시에 열면 안 됩니다. 카메라 브리지·relay는 유지합니다.

이후 아래 명령은 **Ubuntu Bash**에서 실행합니다. PowerShell과 Bash 문법을 섞지 마세요.

```powershell
wsl -d Ubuntu-24.04
```

Ubuntu에서 한 번 설정합니다.

```bash
cd /home/user/lerobot
source .venv/bin/activate
export PATH="$HOME/.local/bin:$PATH"
PROJECT=/mnt/c/Users/user/rjsxo
FOLLOWER=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90150163-if00
LEADER=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90149145-if00
DATA=/home/user/.cache/huggingface/lerobot/se4nchoi/messi
RUN=/home/user/vla-training/runs/messi-smolvla-20261023-143728
MODEL=/home/user/vla-training/runs/messi-smolvla-20261023-153438-3c5ed1/output/checkpoints/last/pretrained_model
TASK='Pick up the red ball, identify the open lane to the left or right of the pickup location, and roll or shoot the ball between the two cones to score a goal.'
GATEWAY=$(python "$PROJECT/workflows/camera_address.py")
CAMERAS="{\"follower_cam\":{\"type\":\"zmq\",\"server_address\":\"$GATEWAY\",\"port\":5555,\"camera_name\":\"follower_cam\",\"width\":640,\"height\":480,\"fps\":30},\"field_cam\":{\"type\":\"zmq\",\"server_address\":\"$GATEWAY\",\"port\":5556,\"camera_name\":\"field_cam\",\"width\":640,\"height\":480,\"fps\":30}}"
export LEROBOT_RERUN_MEMORY_LIMIT=128MB
```

| 항목 | 우리 설정 |
|---|---|
| Follower | `so101_follower`, 보정 ID `follower` |
| Leader | `so101_leader`, 보정 ID `leader` |
| 관절 단위 | 두 팔 모두 `use_degrees=false` |
| 카메라 | `follower_cam`, `field_cam`; ZMQ 5555/5556; 640×480; 30fps |
| 데이터셋 | `se4nchoi/messi`; 위 `$DATA` |
| 모델 | 위 `$MODEL`; 완료된 두 번째 학습의 10,000스텝 결과 |

`camera1` 등으로 카메라 이름을 바꾸면 학습 모델 입력과 어긋납니다. `redball`은 다른 데이터셋입니다. 새 모델 학습 후에는 `$MODEL` 및 rollout 스크립트의 경로를 갱신해야 합니다.

## 2. 자주 쓰는 명령 목록

| 목적 | 명령 | 우리 환경에서 사용하는 방법 |
|---|---|---|
| 리더로 수동 조종 | `lerobot-teleoperate` | 두 팔의 포트·ID·단위와 두 카메라 설정 |
| 시연 녹화 | `lerobot-record` | 기존 `record.sh` 또는 Dataset Desk 녹화 버튼 |
| 저장 데이터 보기 | `lerobot-dataset-viz` | 기존 `view-episodes.sh` 권장 |
| 데이터 구조·개수 확인 | `lerobot-edit-dataset --operation.type=info` | `messi`의 repo ID와 로컬 root |
| 실패 에피소드 제외·분할·병합 | `lerobot-edit-dataset` | 결과를 별도 데이터셋으로 저장 |
| 모델 학습 | `lerobot-train` | 우리 SmolVLA는 BF16 실행 파일 또는 학습 UI 사용 |
| 모델로 실제 팔 제어 | `lerobot-rollout` | WSL `~/lerobot/.venv/bin/rollout_messi` (venv 자동 활성화) |
| 저장한 관절 동작 재현 | `lerobot-replay` | `messi` 에피소드 번호와 Follower 설정 |
| 팔 보정 | `lerobot-calibrate` | 해당 팔의 기존 ID 유지, 필요할 때만 |
| 직렬 포트 찾기 | `lerobot-find-port` | USB 분리 안내를 따르는 대화형 도구 |
| 설치 환경 확인 | `lerobot-info` | 버전·의존성 진단 |
| 시뮬레이션 평가 | `lerobot-eval` | 대응 환경 필요; 현재 messi 실물 평가는 rollout 사용 |

`teleoperate`, `record`, `replay`, `rollout`은 실제 팔을 움직입니다. 작업 공간과 시작 자세를 확인하고 모터 전원을 바로 끌 수 있게 준비합니다.

## 3. 리더로 조종만 하기 — teleoperate

```bash
lerobot-teleoperate \
  --robot.type=so101_follower --robot.port="$FOLLOWER" \
  --robot.id=follower --robot.use_degrees=false \
  --robot.cameras="$CAMERAS" \
  --teleop.type=so101_leader --teleop.port="$LEADER" \
  --teleop.id=leader --teleop.use_degrees=false \
  --fps=30 --display_data=true --display_compressed_images=true
```

리더 움직임을 Follower가 따라갑니다. 데이터는 저장하지 않습니다. Dataset Desk의 `추종 켜기 (저장 안 함)`도 사용할 수 있습니다.

## 4. 시연 수집 — record

일상 수집은 Dataset Desk에서 `로봇 연결 + Rerun` → `녹화 시작` → `중지 · 저장` 순서가 편합니다.

표준 CLI를 쓰려면 이미 모든 설정이 들어 있는 실행 파일을 사용합니다.

```bash
# 구성·데이터 호환성 검사. 모터 연결이나 녹화를 시작하지 않음.
bash "$PROJECT/lerobot-camera-bridge/record.sh" --check

# 실제 수동 조종과 녹화 시작
bash "$PROJECT/lerobot-camera-bridge/record.sh"
```

이 실행 파일에는 카메라 2대, 두 팔, task, `se4nchoi/messi`, 30fps, Hub 업로드 끄기가 설정돼 있습니다. 기존 데이터가 있으면 이어 저장합니다. 기본값은 에피소드 50개, 회당 60초, reset 60초입니다. 웹 녹화와 동시에 실행하지 마세요.

## 5. 영상·관절값 확인 — dataset-viz

```bash
# 최근 저장 완료된 에피소드
bash "$PROJECT/workflows/view-episodes.sh"

# 에피소드 0 (번호는 0부터 시작)
bash "$PROJECT/workflows/view-episodes.sh" 0
```

프로젝트 실행 파일은 읽을 수 있는 저장 완료 데이터로 스냅샷을 만들어 Rerun에 표시합니다. 녹화 세션을 정상 저장·종료한 뒤 확인하세요. 이 작업은 로봇을 움직이지 않습니다.

원본 데이터셋이 완전히 닫힌 상태에서 직접 실행할 수도 있습니다.

```bash
lerobot-dataset-viz --repo-id se4nchoi/messi --root "$DATA" \
  --episode-index 0 --num-workers 0 --batch-size 4 \
  --display-compressed-images
```

## 6. 데이터 정보·편집 — edit-dataset

데이터 개수와 feature 확인:

```bash
lerobot-edit-dataset --repo_id=se4nchoi/messi --root="$DATA" \
  --operation.type=info --operation.show_features=true
```

예를 들어 에피소드 2가 실패한 시연일 때, 이를 제외한 **새 데이터셋**을 만듭니다. 실제 제외할 번호로 바꿔 사용하세요.

```bash
lerobot-edit-dataset --repo_id=se4nchoi/messi --root="$DATA" \
  --operation.type=delete_episodes --operation.episode_indices='[2]' \
  --new_repo_id=se4nchoi/messi_clean \
  --new_root=/home/user/.cache/huggingface/lerobot/se4nchoi/messi_clean \
  --push_to_hub=false
```

출력 폴더는 새 경로를 사용하고, 녹화·학습용 복사 중에는 편집하지 마세요. 새 데이터로 학습할 때 repo ID와 root를 함께 변경합니다. `split`, `merge`, `recompute_stats`, `modify_tasks`, `reencode_videos` 등도 설치돼 있으며 작업별 옵션은 다음처럼 확인합니다.

```bash
lerobot-edit-dataset --operation.type=split --help
lerobot-edit-dataset --operation.type=merge --help
```

## 7. 학습 — train

일상 사용은 Dataset Desk 학습 탭에서 데이터셋을 선택해 새 학습을 시작합니다. 학습용 데이터 복사와 설정 기록을 관리합니다.

CLI로 첫 실험과 같은 구성을 새로 학습하려면 아래처럼 실행합니다. `$RUN/base-two-cameras`는 기존 첫 실험에서 만든 2카메라용 베이스 설정입니다. 입력은 당시의 불변 데이터 스냅샷이고, 출력은 새 디렉터리입니다.

```bash
OUT="/home/user/vla-training/manual-messi-$(date +%Y%m%d-%H%M%S)"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
python "$PROJECT/training/train_bf16.py" \
  --dataset.repo_id=se4nchoi/messi --dataset.root="$RUN/dataset" \
  --dataset.video_backend=pyav --dataset.eval_split=0.2 \
  --policy.path="$RUN/base-two-cameras" \
  --policy.device=cuda --policy.use_amp=true --policy.push_to_hub=false \
  --batch_size=4 --num_workers=2 --prefetch_factor=2 \
  --steps=2000 --save_freq=500 --log_freq=10 \
  --eval_steps=500 --max_eval_samples=64 --env_eval_freq=0 \
  --policy.scheduler_warmup_steps=200 --policy.scheduler_decay_steps=2000 \
  --wandb.enable=false --output_dir="$OUT" --job_name=messi_manual
```

`train_bf16.py`는 설치된 `lerobot-train` 모듈을 BF16 autocast로 실행합니다. 이 PC에서는 일반 AMP 실행 시 FP16 GradScaler와 BF16 gradient가 충돌했던 기록이 있습니다. 위 명령은 추가 학습(resume)이 아니라 베이스에서 새 학습을 시작합니다. 최근 추가 시연도 반영하려면 학습 UI로 새 스냅샷을 만드는 방법을 권장합니다. 수동 CLI 학습은 UI의 관리형 학습과 기록 방식이 다릅니다.

## 8. 학습 모델 실행 — rollout

```bash
# 처음에는 5초 시험
~/lerobot/rollout_messi.sh --duration=5

# 기본 60초
~/lerobot/rollout_messi.sh
```

현재 실행 파일은 위 `$MODEL`에 해당하는 두 번째 학습의 10,000스텝 결과를 사용합니다(최종 검증 loss 0.0618). `base` 전략은 추론만 수행하고 평가 데이터를 저장하지 않습니다. 성공률은 시작 상태를 매번 맞추고 집기·방향 선택·득점을 기록해 계산합니다.

최신 기본 실행 설정: `~/lerobot/rollout_messi.sh`와 `~/lerobot/.venv/bin/rollout_messi_no_target_cap` 모두 새 모델·RTC·15Hz action·2배 보간(30Hz 목표)·관절 목표 변화 제한 없음으로 맞췄습니다. 기본 60초, 화면 표시와 시작 자세 자동 복귀는 꺼져 있습니다. 아래 속도 조정 기록의 `max_relative_target=0.5`는 이후 실물 동작을 막는 문제가 관찰돼 제거했습니다. 새 모델 파일과 전체 CLI 인자를 하드웨어 연결 없이 검증했으며, 새 모델의 실물 성공률은 아직 확인하지 않았습니다.

2026-10-23 실행 중 3Hz 제어 지연·Rerun 채널 대기와 중복 rollout 4개가 확인돼 실행 파일을 수정했습니다. 기본 화면 표시를 끄고, 동시 실행 잠금과 CPU thread 제한을 추가했으며, 종료 시 시작 자세로 자동 복귀를 껐습니다. 30Hz 목표는 유지합니다. 화면 표시를 다시 켜면 동일한 병목이 재발할 수 있습니다. 잠금 오류가 나면 기존 실행 상태를 확인하고 중복 실행하지 마세요. 실제 제어 속도와 떨림 개선 여부는 별도 실물 시험이 필요합니다.

추가로 저장 시연 1프레임으로 하드웨어 없는 추론 시간을 측정했습니다. 동기식은 50-action chunk 생성 때 약 211~261ms(첫 호출 694ms) 동안 제어 루프를 막았습니다. 비동기 RTC는 10초 시험에서 첫 action까지 약 1초, 이후 270개 action 공급 중 빈 queue tick 0회, queue 읽기 최대 0.18ms였습니다. 이 결과를 기준으로 launcher 기본값을 `--inference.type=rtc --inference.rtc.execution_horizon=30 --inference.queue_threshold=30`으로 변경했습니다. 기존 실행 파일은 WSL `~/lerobot/rollout_messi.before-rtc.sh`에 보관했습니다. 고정된 저장 관측값으로 수행한 시험이므로 실제 로봇·카메라·시리얼 통신의 지연이나 모델 작업 성공률을 검증한 결과는 아닙니다.

## 9. 저장 동작을 실물에서 재현 — replay

현재 rollout launcher는 관절 속도가 빠르다는 실물 관찰에 따라 추가로 `--fps=15 --interpolation_multiplier=2 --robot.max_relative_target=0.5`를 사용합니다. 모델 action 소비율은 원래 30Hz에서 15Hz로 낮추고, 중간 목표값을 보간해 제어 목표 주기는 30Hz로 유지합니다. `0.5`는 현재 관절 위치에서 목표까지의 정규화 단위 제한이며 도/초 속도값이 아닙니다. 이 제한은 목표 추종 지연을 만들 수 있고 추가 모터 읽기가 필요합니다. 설정 파싱은 검증했으며 변경 후 실물 속도·안정성은 아직 확인하지 않았습니다.

```bash
lerobot-replay \
  --robot.type=so101_follower --robot.port="$FOLLOWER" \
  --robot.id=follower --robot.use_degrees=false \
  --dataset.repo_id=se4nchoi/messi --dataset.root="$DATA" \
  --dataset.episode=0 --dataset.fps=30 --play_sounds=false
```

저장된 action을 팔에 보냅니다. 모델 판단이나 카메라 기반 보정은 하지 않으며, 영상 보기와 달리 실제 팔이 움직입니다. 녹화 당시 시작 자세와 주변 배치를 맞추고 실행하세요.

## 10. 진단·재보정

```bash
# 소프트웨어 환경
lerobot-info

# 현재 USB 직렬 장치
ls -l /dev/serial/by-id/

# GPU 상태
nvidia-smi

# USB를 분리해 전후 차이로 포트를 찾는 대화형 도구
lerobot-find-port
```

우리 카메라는 Windows → MJPEG → ZMQ 구조입니다. `lerobot-find-cameras`의 WSL OpenCV 탐색 결과만으로 정상 여부를 판단하지 마세요. Windows PowerShell에서 브리지 상태를 확인합니다.

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8766/health
```

아래 보정은 매번 실행하는 절차가 아닙니다. 팔 조립·모터 교체 등으로 다시 보정해야 할 때만 사용합니다. 기존 보정 파일을 먼저 보관하고, 화면에서 요구하는 수동 자세·범위 측정을 따릅니다.

```bash
# Follower 재보정
lerobot-calibrate --robot.type=so101_follower --robot.port="$FOLLOWER" \
  --robot.id=follower --robot.use_degrees=false

# Leader 재보정
lerobot-calibrate --teleop.type=so101_leader --teleop.port="$LEADER" \
  --teleop.id=leader --teleop.use_degrees=false
```

## 11. 그 외 설치된 명령

| 명령 | 용도·현재 적용 여부 |
|---|---|
| `lerobot-eval` | Gym 계열 환경 평가. 현재 실물 messi 환경을 그대로 실행할 설정은 준비돼 있지 않음 |
| `lerobot-find-cameras` | 직접 연결 카메라 탐색. 우리 ZMQ 연결 진단은 브리지 상태와 실제 프레임 확인 사용 |
| `lerobot-setup-motors` | 모터 초기 ID 등 설정. 이미 구성한 팔의 일상 실행에는 필요 없음 |
| `lerobot-find-joint-limits` | 지원 하드웨어의 관절 한계 측정. SO101 적용 가능 여부를 별도 확인해야 함 |
| `lerobot-setup-can` | CAN 장치 준비. 현재 USB 직렬 SO101 구성에는 필요 없음 |
| `lerobot-imgtransform-viz` | 학습 이미지 변환 확인 |
| `lerobot-annotate` | 데이터 주석 도구. 작업별 옵션 확인 후 사용 |
| `lerobot-train-tokenizer` | 별도 토크나이저 학습. 현재 SmolVLA 미세학습에는 필요 없음 |

도움말은 로봇을 연결하지 않고 확인할 수 있습니다. 예: `lerobot-rollout --strategy.type=base --robot.type=so101_follower --help`. 명령마다 옵션 표기가 다릅니다. `dataset-viz`는 `--repo-id`, 학습·녹화는 `--dataset.repo_id`, 편집은 `--repo_id`를 사용합니다.
