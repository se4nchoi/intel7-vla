# Physical AI Studio camera fix

The icSpring 32e6:9211 camera produced damaged MJPEG frames through WSL USB/IP.
DirectShow capture on Windows produced clean images at 640x480, 30 fps.

The `physical-ai-camera-bridge` Windows scheduled task runs `server.py` at login.
It captures the camera through DirectShow and serves an MJPEG stream on
`http://127.0.0.1:8765/camera.mjpg`. The listener is bound only to localhost.
Docker Desktop reaches it at `http://host.docker.internal:8765/camera.mjpg`.
Health: `http://127.0.0.1:8765/health`.

Studio project `test1` uses the same camera name `follower_cam`, ID
`0d292e02-9fb4-42ad-bb5a-08c59fc76f3e`, and Environment references.
Its driver is now `ipcam`. The installed Studio version cannot change camera
driver through PUT (it validates against the old model class), so only the input
fields of this camera row were changed in a validated SQLite transaction.
The original API object and exact database row are backed up in this folder.

`usbipd-autoattach` still runs for the robot arms. The camera VID:PID is excluded
in `C:\ProgramData\usbipd-autoattach\usbipd-autoattach.ps1`; the camera should
show **Shared**, while both robot controllers should show **Attached**.
Do not manually attach this camera to WSL while the bridge is used.

Files:
- `server.py`: reconnecting camera capture and local MJPEG server.
- `bridge.log`: capture and reconnect logs.
- `install.ps1`: administrator setup for exclusion and login task.
- `original-camera.json`, `original-camera-row.json`: original camera settings.
- `original-usbipd-autoattach.ps1`: original system autoattach script.
- `original-autoattach-task.xml`: original task snapshot.
- `verified.jpg`: Studio preview after the fix, visually checked for tiling.

Verified: 288 actual Studio preview frames over 10 seconds, 279 distinct JPEGs;
the captured preview has continuous geometry and no strip-wise color corruption.
The bridge and original autoattach tasks were both running after installation.

The bridge uses the only Windows camera (DirectShow index 0). If additional
cameras are connected, verify the device selection before recording.
