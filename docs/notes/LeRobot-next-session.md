# LeRobot next-session preparation

Target environment: Ubuntu-24.04, `/home/user/lerobot`, repository tag v0.6.1,
Python 3.12 virtual environment `/home/user/lerobot/.venv`.

## Models downloaded and inspected

- `lerobot/smolvla_base`, revision `5e8d12a6e2975b0e5e5fce7c8caf47c371d257b6`.
  The model.safetensors file is 906,712,520 bytes.
- `HuggingFaceTB/SmolVLM2-500M-Video-Instruct`, revision
  `7b375e1b73b11138ff12fe22c8f2822d8fe03467`.
  The PyTorch weights, tokenizer and processor/config files were downloaded;
  optional `onnx/*` conversions are not required and were excluded.

Both repositories are cached under `/home/user/.cache/huggingface/hub`.
The safetensors headers and required tokenizer/config files were inspected.
Studio's saved Hugging Face token was not printed or copied. Public downloads
were performed without a token. CLI authentication is separate from Studio.

## Open the environment

In Ubuntu, not Windows PowerShell:

```bash
cd ~/lerobot
source .venv/bin/activate
lerobot-info
```

Core installation command used in the existing user terminal:

```bash
uv pip install -e ".[core_scripts,training,feetech,smolvla]"
```

`evdev` and CUDA / policy-import checks are performed after that installation
finishes. Check the current verification result before starting the project.

## Before recording or inference

- Resolve the leader motor communication problem; USB Attached alone is not
  proof that the motors are responding.
- Export the existing calibration using the provided Studio export script, or
  use a properly verified LeRobot calibration for each physical arm.
- The working Windows MJPEG bridge is currently configured for Docker Studio.
  Its `host.docker.internal` URL did not respond from Ubuntu during preparation.
  Do not copy the PDF's USB `/dev/video*` setup unchanged: the camera remains
  on Windows for the bridge. Adapt and verify Ubuntu camera input separately.
- Stop Studio before giving LeRobot control of the robot serial devices or
  launching LeRobot training. Leave the Windows camera bridge running if used.
- Start training conservatively: batch 4, data-loader workers 2. Do not run
  Studio training and LeRobot training at the same time on this 16 GB PC.

No training, rollout or robot motion was started as part of model preparation.
