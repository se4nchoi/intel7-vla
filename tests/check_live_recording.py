"""Verify live images and joint data through the recorder, without commanding motors."""
import _bootstrap  # repository source path, no environment mutation
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.request import urlopen

import av
import numpy as np
import pyarrow.parquet as pq
from lerobot.cameras.zmq import ZMQCamera, ZMQCameraConfig
from lerobot.utils.feature_utils import build_dataset_frame
from intel7_vla.common.camera_address import camera_host
from intel7_vla.recording.recorder import Recorder, CAMERAS, NAMES


with TemporaryDirectory(prefix='lerobot-live-recording-check-') as directory:
    root=Path(directory)/'dataset'
    root.mkdir()  # Match the existing empty messi directory, without touching it.
    app=Recorder(demo=True,dataset_root=root,repo_id='local/recording_check',task='temporary validation')
    cameras={}
    try:
        for name,port in CAMERAS.items():
            camera=ZMQCamera(ZMQCameraConfig(server_address=camera_host(),port=port,
                camera_name=name,width=640,height=480,fps=30))
            cameras[name]=camera
            camera.connect()
        app.open_dataset()
        app.update(state='recording')
        for index in range(30):
            tick=time.monotonic()
            with urlopen('http://127.0.0.1:8877/api/status',timeout=3) as response:
                state=json.load(response)
            if state['state'] not in ('ready','recording','saving'):
                raise RuntimeError('Live robot state unavailable: '+state.get('error',state['state']))
            observation={key:float(state['follower'][key]) for key in [n+'.pos' for n in NAMES]}
            action=state.get('command') or state['leader']
            for name,camera in cameras.items():
                image=camera.async_read(timeout_ms=3000)
                assert image.shape==(480,640,3)
                observation[name]=image
            frame={**build_dataset_frame(app.dataset.features,observation,prefix='observation'),
                   **build_dataset_frame(app.dataset.features,action,prefix='action'),
                   'task':'temporary validation'}
            app.dataset.add_frame(frame)
            app.update(frames=index+1)
            time.sleep(max(0,1/30-(time.monotonic()-tick)))
        app.save()
        info=json.loads((root/'meta/info.json').read_text())
        assert info['total_episodes']==1 and info['total_frames']==30,info
        rows=[]
        for file in root.glob('data/**/*.parquet'):rows.extend(pq.read_table(file).to_pylist())
        assert len(rows)==30
        assert all(len(row['observation.state'])==6 and len(row['action'])==6 for row in rows)
        assert np.isfinite([row['observation.state'] for row in rows]).all()
        counts={}
        for file in root.glob('videos/**/*.mp4'):
            with av.open(str(file)) as container:
                frames=list(container.decode(video=0))
                assert all(frame.width==640 and frame.height==480 for frame in frames)
                counts[file.relative_to(root).parts[1]]=len(frames)
        assert counts=={'observation.images.follower_cam':30,'observation.images.field_cam':30},counts
        print(json.dumps({'result':'PASS','episodes':1,'joint_rows':len(rows),'videos':counts,
            'resolution':'640x480','fps':info['fps'],'source':'live cameras and live robot status',
            'messi_modified':False,'motor_commands_sent':False}),flush=True)
    finally:
        app.close_devices()
        for camera in cameras.values():
            if camera.is_connected:camera.disconnect()
