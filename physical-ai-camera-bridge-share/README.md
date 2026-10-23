# Physical AI Studio 카메라 타일링 우회 — 수업 배포용

## 배포할 파일

이 폴더 전체를 ZIP으로 공유하면 됩니다. Codex 설치는 필요 없습니다.
학생 PC의 원래 Studio DB·프로젝트·캘리브레이션 파일은 서로 공유하지 않습니다.

검증한 원리: icSpring 카메라를 Windows DirectShow로 촬영한 뒤, 같은 PC의
Docker Studio에 HTTP MJPEG로 전달합니다. 카메라는 Windows에 남고 로봇 팔만 WSL에 연결됩니다.
컨테이너 이미지나 Studio 소스 코드는 수정하지 않습니다.

## 대상 환경

- Windows 11, Docker Desktop의 WSL2 Linux 컨테이너.
- 실행 중인 Physical AI Studio와 기존 `usbipd-autoattach` 예약 작업.
- 기존 스크립트: `C:\ProgramData\usbipd-autoattach\usbipd-autoattach.ps1`.
- icSpring USB 카메라 한 대: VID:PID `32e6:9211`.
- Windows Python 3.12 이상. WSL 안의 Python은 사용할 수 없습니다.
- 첫 설치 시 인터넷 연결 필요: 전용 가상환경에 OpenCV·NumPy를 설치합니다.

한 PC에서 실제 검증한 Studio 이미지는 `0.3.0-dev-7b099fe1`입니다.
여러 PC용 설치 스크립트는 구문 검사를 마쳤으며, 다른 PC의 실제 설치 검증은 아직입니다.
우선 학생 PC 한 대에 적용해 확인한 뒤 전체 배포하세요.

## 설치

1. 카메라를 연결하고 Windows 카메라 앱, OBS 등 카메라 사용 앱을 닫습니다.
2. 평소 Studio를 사용하는 **동일한 Windows 계정**에서 PowerShell을 관리자 권한으로 엽니다.
3. ZIP을 푼 폴더로 이동해 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Python을 자동으로 못 찾으면 실제 Windows Python 경로를 지정합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe "C:\실제경로\python.exe"
```

설치 위치는 `%LOCALAPPDATA%\PhysicalAICameraBridge`이며 ZIP을 푼 폴더는 설치 후 옮겨도 됩니다.
로그인 시 `physical-ai-camera-bridge` 작업으로 자동 실행됩니다.
기존 USB 자동 연결 스크립트는 백업하고 카메라 VID:PID만 제외 목록에 추가합니다.
로봇의 설정·캘리브레이션과 Studio DB는 설치 스크립트가 수정하지 않습니다.

## Studio에서 연결 — 각 PC에서 한 번

1. Cameras → Configure new camera → IP camera를 선택합니다.
2. 이름은 `follower_cam_windows`처럼 기존 카메라와 구분되게 입력합니다.
3. URL: **`http://host.docker.internal:8765/camera.mjpg`**
4. 해상도 **640 × 480**, FPS **30**으로 저장하고 미리보기를 확인합니다.
5. 기존 Environment를 편집해 깨지는 USB 카메라 대신 새 IP 카메라를 선택합니다.

각 PC의 프로젝트·로봇·카메라 ID는 달라도 됩니다. ID를 복사하거나 DB를 덮어쓰지 않습니다.
이미 촬영한 데이터셋에 영향이 없도록 기존 USB 카메라는 새 경로 확인 전까지 보관하세요.
새 데이터셋에서는 선택한 카메라 이름을 모델 입력 이름과 맞춰 사용하세요.

## 확인

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
usbipd list
Get-ScheduledTask -TaskName usbipd-autoattach,physical-ai-camera-bridge
```

- health: `ok=True`, frames가 증가해야 합니다.
- 로봇 USB: `Attached`; 카메라 USB: `Shared` 또는 `Not shared`가 정상입니다.
- 카메라를 수동으로 WSL에 attach하지 마세요.
- Studio 미리보기에서 선이 연속되고 타일링·색상 깨짐이 없는지 직접 확인합니다.
- localhost 전용 서버여서 영상이 인터넷 서버나 LAN에 공개되지 않습니다.

Docker 내부에서 연결 확인:

```powershell
docker exec physical-ai-studio-cuda .venv/bin/python -c 'import urllib.request; print(urllib.request.urlopen("http://host.docker.internal:8765/health",timeout=4).read())'
```

컨테이너 이름이 다르면 해당 이름으로 바꿉니다.

## 제한 및 제거

기본 DirectShow 카메라 인덱스는 0입니다. 노트북 내장 카메라나 여러 카메라가 있으면
`server.py`의 `cv2.VideoCapture(0, ...)` 인덱스를 실제 카메라에 맞춰 바꿔야 합니다.
이 패키지는 한 대의 카메라용입니다. 자동 화이트밸런스·노출의 일반적인 변화까지 고정하지는 않습니다.
브리지 또는 Windows 세션이 꺼지면 카메라 영상도 중단됩니다.

제거하려면 관리자 PowerShell에서 `physical-ai-camera-bridge` 작업을 중지·삭제하고,
USB 자동 연결 스크립트에서 **해당 카메라의 제외 항목만** 제거한 뒤 USB 자동 연결 작업을 재시작합니다.
원본 스크립트는 설치 폴더의 `original-autoattach.ps1`에 있으나,
설치 후 다른 설정을 바꿨다면 백업 전체를 덮어쓰지 말고 제외 항목만 복구하세요.
Studio Environment의 입력도 원래 카메라로 바꿉니다.

로봇의 `Connection failed`는 별도 문제일 수 있습니다. 이 PC에서는 멈춘 leader USB 연결을
재연결하고 백그라운드 owner를 정리해 해결했으며, 그 일시적인 조치는 이 카메라 패키지에 포함하지 않습니다.
