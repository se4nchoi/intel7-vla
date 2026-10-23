# RGB recording: gray12le / HEVC error (v2)

The installed LeRobot StreamingVideoEncoder eagerly creates DepthEncoderConfig,
even for RGB-only recordings. This container resolves `hevc` to `hevc_qsv`,
which cannot accept `gray12le`. Thus loading a recording dataset fails before
RGB recording starts. The USB-camera bridge is unrelated to this failure.

Version 2 patches both StreamingVideoEncoder and DatasetWriter. The streaming patch initializes the default depth encoder only when `start_episode`
actually receives depth keys. DatasetWriter initializes depth defaults only if dataset metadata has depth keys. Explicit depth configs are preserved; real depth
recording still requires a suitable depth encoder and is not fixed by this patch.
RGB format is unchanged; no depth data is converted into RGB or discarded.

## Apply

In PowerShell, from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\apply.ps1
```

If the container has another name, add `-Container NAME`.
Then stop recording / Teleoperate, ensure the robot is stable, and restart Studio:

```powershell
docker restart physical-ai-studio-cuda
```

The installer intentionally does not restart robot control automatically.
This is a container code modification, separate from the Windows camera bridge.
It survives `docker restart` but must be reapplied after container recreation,
image updates or dependency reinstallation. It checks exact source patterns and
refuses unexpected versions. Reapplying the same patch is safe.

Original file backup in Docker persistent storage:
`/app/storage/patches/lerobot-lazy-depth/video_utils.py.original`.
Copy that file back to the printed package path and restart Studio to revert.
Keep the original backup paired with the dependency version it came from.

## Verification performed

- Reproduced `DepthEncoderConfig()` failing with the reported pixel-format error.
- Used Studio's own RGB codec selection (`libsvtav1` on this PC).
- Encoded and decoded 12 distinct synthetic RGB frames via StreamingVideoEncoder.
- Asserted the depth config factory was never called during RGB-only recording.
- No robot motion, production dataset writes or live recording during verification.

`verify-rgb.py` is the diagnostic used in this exact container; it deliberately
expects the depth codec failure and should not be treated as a general test for
other FFmpeg builds.

## Additional v2 verification

Created a real LeRobotDataset, saved an episode, finalized, resumed and saved a second episode, reopened the dataset, and decoded all 24 RGB video frames. Both depth-default factories were guarded against any call during this RGB-only integration test. Original DatasetWriter backup: /app/storage/patches/lerobot-lazy-depth/dataset_writer.py.original.
