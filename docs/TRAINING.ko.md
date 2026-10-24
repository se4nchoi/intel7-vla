# messi SmolVLA 첫 미세학습

2026-10-23 현재 시연을 사용해 로컬 WSL GPU 학습을 시작했습니다. Hugging Face 클라우드 학습이나 Hub 업로드는 실행하지 않습니다.

- 데이터: `se4nchoi/messi`, 10개 에피소드, 7,840프레임, 30fps, 카메라 2대
- 분리: 에피소드 0~7 학습(6,529프레임), 8~9 검증(1,311프레임)
- 모델: `lerobot/smolvla_base`, revision `5e8d12a6e2975b0e5e5fce7c8caf47c371d257b6`
- 설정: CUDA, BF16 autocast, batch 4, worker 2, 2,000스텝, warmup 200, 체크포인트/검증 500스텝 간격
- 검증 loss: 검증 샘플 최대 64개. 실물 작업 성공률과는 별개입니다.
- 실행 폴더: `/home/user/vla-training/runs/messi-smolvla-20261023-143728`
- 로그: 위 폴더의 `train-bf16-final.log`
- 모델 저장: 위 폴더의 `output-bf16-final/checkpoints/`

원본 시연을 별도 `dataset/`에 복사하고 파일별 SHA256을 저장했습니다. 각 에피소드에서 처음·중간·끝 영상 프레임을 두 카메라 모두 읽고, 모든 action/state 값이 유한한지 확인했습니다. 데이터셋 파일 수와 프레임 수를 확인했으며 전체 영상의 모든 프레임이나 시연의 성공 여부를 검수한 것은 아닙니다.

원본 모델 캐시는 바꾸지 않고 학습 실행 폴더의 `base-two-cameras/config.json`에 실제 `follower_cam` / `field_cam` 입력을 지정했습니다. 현재 LeRobot에서는 CLI의 빈 input_features가 기존 설정을 지우지 않아 첫 시도는 카메라 불일치로 종료됐고, 수정한 설정으로 재시작했습니다.

당시 사용한 `start_messi_smolvla.py`는 삭제했습니다. 같은 설정은 `wsl/train.py --steps 2000`으로 시작합니다. 재실행하면 새 학습을 시작하므로 기존 프로세스가 실행 중인지 먼저 확인하세요.

```bash
tail -f /home/user/vla-training/runs/messi-smolvla-20261023-143728/train-bf16-final.log
```

현재 GPU 여유에 맞춘 첫 실험이며, 10개 시연으로 실물 로봇의 일반화 성능을 보장하지 않습니다. 학습 이후 별도 평가를 거쳐야 합니다. 데이터·모델 공개와 GitHub 커밋은 별도로 진행합니다.

설치된 torch/Accelerate의 FP16 GradScaler가 SmolVLA의 BF16 gradient를 처리하지 못해 두 번째 시도도 첫 업데이트에서 종료됐습니다. 최종 실행은 	raining/train_bf16.py에서 CUDA autocast dtype을 BF16으로 명시하여 GradScaler를 사용하지 않습니다. 원본 LeRobot 소스는 바꾸지 않았습니다.

정상 실행 확인: 40스텝에서 loss 0.360, GPU 사용률 96%, 전체 GPU 메모리 약 3.1GB. 당시 학습은 진행 중이며 완료 기록은 아닙니다.

## 웹에서 학습 시작·조회

Dataset Desk의 **학습** 탭에서 데이터셋과 SmolVLA 파라미터를 설정해 시작할 수 있습니다.

- 기본 10,000스텝이며 20,000 등 직접 입력 가능
- 배치 크기, 학습률, warmup, 검증 에피소드 비율, 저장·검증 간격, worker 수, seed 설정
- 현재 학습과 과거 기록, 진행률, 학습/검증 loss 그래프, 체크포인트 경로, 최신 로그 조회
- 준비·실행 중에는 새 학습 시작을 차단하며 CLI에서 실행한 현재 기록도 표시
- 새 학습 시작 전 녹화·저장·추종을 멈춰야 합니다. 데이터 복사·검증이 끝나면 추가 수집 가능
- 원본 데이터가 아닌 별도 스냅샷으로 학습하며 Hugging Face 업로드는 실행하지 않음
- 웹 페이지·서버를 닫아도 별도 학습 프로세스는 유지됨. PC 절전·WSL 종료 시에는 실행이 끊길 수 있음

실행 기록과 스냅샷·모델은 WSL `~/vla-training/runs/<학습ID>/`에 저장합니다. 화면의 예상 시간은 학습 루프 추정치이며 검증·저장 시간이 추가될 수 있습니다. 검증은 각 작업의 마지막 에피소드들을 비율에 따라 분리하며 최대 64샘플로 loss를 계산합니다. 검증 loss는 실물 작업 성공률이 아닙니다.

백엔드는 `src/intel7_vla/training/jobs.py`, 독립 실행 진입점은 `wsl/run_training_job.py`, 화면은 `web/dataset-desk/assets/training.js`와 `.css`입니다. 학습 시작 API는 임의 명령이나 모델 경로를 받지 않고 현재 로컬 SmolVLA 모델과 허용된 수치 설정만 사용합니다.

### 이번 첫 실험 결과

- 기존 2,000스텝 학습 완료
- 마지막 학습 loss 0.110, 검증 loss 0.0980
- 500 / 1,000 / 1,500 / 2,000스텝 체크포인트 저장
- 최종 모델: `/home/user/vla-training/runs/messi-smolvla-20261023-143728/output-bf16-final/checkpoints/002000/pretrained_model`
- 실제 로봇 성공률은 아직 평가하지 않음

### UI·학습 준비 검사

```bash
cd /mnt/c/Users/<사용자>/intel7-vla
~/lerobot/.venv/bin/python tests/check_training_jobs.py
```

```powershell
node tests/check_training_ui.cjs
node tests/check_ui_controls.cjs
```

백엔드 검사는 임시 데이터에 실제 스냅샷 복사와 카메라 프레임 읽기를 수행하지만 GPU 학습 명령은 대체합니다. 프런트엔드 검사는 DOM/HTTP 테스트 객체에서 실제 화면 스크립트를 실행해 파라미터 전송·오류 처리·진행 갱신을 확인합니다. 브라우저 시각 검증과는 별개입니다.

## 코드 구조

학습 코드는 `src/intel7_vla/training/`의 `options.py`, `progress.py`, `jobs.py`, `runner.py`, `bf16.py`, `cli.py`로 분리했습니다. WSL 실행 진입점은 `wsl/`, 검사는 `tests/`에 있습니다. 새 CLI는 `wsl/train.py`이며 웹과 같은 기본 10,000스텝과 중복 실행 차단을 사용합니다. 자세한 경계는 [코드 구조 안내](ARCHITECTURE.ko.md)를 참고하세요.
