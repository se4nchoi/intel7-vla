"""Hardware-free integration check: create, save, resume and discard real dataset frames."""
import _bootstrap  # repository source path, no environment mutation
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time

import av
import pyarrow.parquet as pq
import rerun as rr
from intel7_vla.recording.recorder import Recorder


def wait(app, predicate, timeout=60):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        s=app.status()
        if s['state']=='error':raise AssertionError(s['error'])
        if predicate(s):return
        time.sleep(.05)
    raise AssertionError(app.status())


with TemporaryDirectory(prefix='lerobot-ui-check-') as folder:
    root=Path(folder)/'new_task'
    rr.init('dataset-ui-check')
    app=Recorder(demo=True,dataset_root=root,repo_id='local/ui_check',task='integration task')
    thread=Thread(target=app.run);thread.start()
    try:
        wait(app,lambda s:s['state']=='ready')
        assert not (root/'meta/info.json').exists(), 'Waiting must not create or record a dataset'
        for count in (1,2):
            app.commands.put(('start',{'duration':.4}))
            wait(app,lambda s:s['state']=='ready' and s['episodes']==count)
            info=json.loads((root/'meta/info.json').read_text())
            assert info['total_episodes']==count
            assert info['total_frames']>0
        app.commands.put(('start',{'duration':30}))
        wait(app,lambda s:s['state']=='recording' and s['frames']>3)
        app.commands.put(('discard',{}))
        wait(app,lambda s:s['state']=='ready')
        assert json.loads((root/'meta/info.json').read_text())['total_episodes']==2
        rows=[]
        for p in root.glob('data/**/*.parquet'):rows+=pq.read_table(p).to_pylist()
        assert {r['episode_index'] for r in rows}=={0,1}
        assert len({tuple(r['observation.state']) for r in rows})>1
        decoded=0
        camera_counts={}
        for p in root.glob('videos/**/*.mp4'):
            with av.open(str(p)) as container:
                count=sum(1 for _ in container.decode(video=0));decoded+=count
                key=p.relative_to(root).parts[1]
                camera_counts[key]=camera_counts.get(key,0)+count
        assert set(camera_counts)=={'observation.images.follower_cam','observation.images.field_cam'}
        assert all(count==len(rows) for count in camera_counts.values()), camera_counts
        print(f'PASS: waiting does not record; saved/resumed 2 episodes; discard preserved count; {len(rows)} joint rows; {decoded} decoded video frames')
    finally:
        app.commands.put(('shutdown',{}));thread.join(60)
        assert not thread.is_alive()
