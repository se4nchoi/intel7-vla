# Windows / WSL memory recovery — 2026-10-22

Observed Windows commit usage 96%, about 318 MB available RAM, and WSL swap usage
6.7 GiB. Training job 654cd31e-3a91-4c4d-af3a-9b13e1eef373 used automatic batch
scaling and automatic data-loader workers. Its last training log showed batch
size 128 succeeded and testing 256; multiple loader groups remained resident.

The user authorized stopping training. The normal interrupt endpoint was called,
but the task did not finish cancellation. Studio was stopped, WSL shut down,
Docker Desktop restarted, and Studio started again. The original training task
is now failed after worker recovery; it was not restarted or deleted.

Active `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=8GB
swap=4GB
processors=8

[experimental]
autoMemoryReclaim=gradual
```

Original configuration is `wslconfig.original`. It previously specified 10GB RAM
and 12GB swap. The RAM value is a maximum and swap is disk-backed, not 22GB of
RAM preallocation. Lowering these limits does not fix an unbounded training
request by itself.

For the next training: batch size 4, auto batch-size scaling OFF, data-loader
workers 2 (or 0 if memory remains tight). Do not run multiple trainings at once.
`suggested-training-payload.json` is prepared only; no new training was submitted.
`original-training-job.json` preserves the original request and state snapshot.

Verified Docker sees 8 CPUs and about 7.8 GiB RAM, WSL swap usage returned to zero,
no jobs are running, Studio health is healthy, both robot USB devices are
Attached, and the Windows camera bridge is serving fresh frames. Existing
container recording fixes remained installed. Windows memory numbers change
with Studio startup and other desktop applications; check Task Manager before
starting another training.
