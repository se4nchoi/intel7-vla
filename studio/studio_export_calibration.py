#!/usr/bin/env python3
"""Physical AI Studio(v0.3.x)에 저장된 SO-101 캘리브레이션을 LeRobot 캘리브레이션 파일로 내보낸다.

Studio v0.3 부터 캘리브레이션은 JSON 파일이 아니라 Studio DB(로봇 설정)에 들어 있다.
이 스크립트는 Studio API 에서 꺼내 LeRobot 이 읽는 위치에 저장한다.

  python3 studio_export_calibration.py            # 모든 프로젝트의 SO-101 로봇
  python3 studio_export_calibration.py redball    # 특정 프로젝트만

저장 위치 (파일명 = Studio 로봇 이름 = LeRobot 명령의 --robot.id / --teleop.id)
  팔로워: ~/.cache/huggingface/lerobot/calibration/robots/so_follower/<이름>.json
  리더:   ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/<이름>.json
"""
import json
import os
import sys
import urllib.request

API = os.environ.get("STUDIO_API", "http://localhost:7860/api")
ROOT = os.path.expanduser("~/.cache/huggingface/lerobot/calibration")
TARGET = {"SO101_Follower": ("robots", "so_follower"), "SO101_Leader": ("teleoperators", "so_leader")}


def get(path):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.load(r)


only = sys.argv[1] if len(sys.argv) > 1 else None
written = 0
for proj in get("/projects"):
    if only and proj["name"] != only:
        continue
    for robot in get(f"/projects/{proj['id']}/robots"):
        kind = TARGET.get(robot["type"])
        calib = (robot.get("payload") or {}).get("calibration")
        if not kind:
            continue
        if not calib:
            print(f"[skip] {proj['name']}/{robot['name']} ({robot['type']}): Studio 에서 캘리브레이션 안 됨")
            continue
        out_dir = os.path.join(ROOT, *kind)
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, f"{robot['name']}.json")
        with open(out, "w") as f:
            json.dump(calib, f, indent=4)
        print(f"[ok]   {proj['name']}/{robot['name']} -> {out}")
        written += 1
print(f"{written} 개 저장")
