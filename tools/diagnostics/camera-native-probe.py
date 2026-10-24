import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'.camera-tools'))
import cv2
for backend in [cv2.CAP_DSHOW,cv2.CAP_MSMF]:
    cap=cv2.VideoCapture(0,backend)
    try:
        cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
        cap.set(cv2.CAP_PROP_FPS,30)
        print('BACKEND',backend,'OPEN',cap.isOpened(),flush=True)
        good=0; frame=None
        for i in range(45):
            ok,im=cap.read()
            if ok: good+=1; frame=im
            else: break
        if frame is not None:
            cv2.imwrite(str(Path(__file__).resolve().parents[2]/f'runtime/camera-windows-{backend}.jpg'),frame)
            print('NATIVE_FRAMES',good,'SHAPE',frame.shape,flush=True)
    finally: cap.release()
