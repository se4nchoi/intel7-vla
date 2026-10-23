"""Use only temporary demo data; verify real videos, reindexing and undo."""
import _bootstrap  # repository source path, no environment mutation
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import av
import pyarrow.parquet as pq
import rerun as rr
from intel7_vla.recording.recorder import Recorder
from intel7_vla.datasets.editing import delete_episode, restore_episode, revision, undo_available
from lerobot.utils.feature_utils import build_dataset_frame


with TemporaryDirectory(prefix='episode-edit-check-') as tmp:
    cache=Path(tmp);root=cache/'local/test';root.parent.mkdir()
    app=Recorder(demo=True,dataset_root=root,repo_id='local/test',task='test')
    app.open_dataset()
    for ep in range(3):
        for frame in range(12):
            obs, action=app.observe()
            app.dataset.add_frame({**build_dataset_frame(app.dataset.features,obs,prefix='observation'),
                **build_dataset_frame(app.dataset.features,action,prefix='action'),'task':'test'})
        app.dataset.save_episode()
    app.dataset.finalize();app.dataset=None
    # A single open writer packs multiple episodes into the same MP4.
    assert len(list(root.glob('videos/**/*.mp4')))==2
    before=revision(root)
    original=[]
    for p in sorted(root.glob('data/**/*.parquet')):original+=pq.read_table(p).to_pylist()
    delete_episode(cache,'local/test',root,1,before)
    rows=[]
    for p in sorted(root.glob('data/**/*.parquet')):rows+=pq.read_table(p).to_pylist()
    expected=[r for r in original if r['episode_index']!=1]
    assert [r['action'] for r in rows]==[r['action'] for r in expected]
    assert [r['observation.state'] for r in rows]==[r['observation.state'] for r in expected]
    assert {r['episode_index'] for r in rows}=={0,1}
    assert [r['index'] for r in rows]==list(range(len(rows)))
    for key in ('follower_cam','field_cam'):
        frames=0
        for p in root.glob(f'videos/observation.images.{key}/**/*.mp4'):
            with av.open(str(p)) as container:frames+=sum(1 for _ in container.decode(video=0))
        assert frames==len(rows),(key,frames,len(rows))
    assert undo_available(cache,'local/test',root)
    try:delete_episode(cache,'local/test',root,0,before)
    except ValueError:pass
    else:raise AssertionError('stale selection accepted')
    restore_episode(cache,'local/test',root)
    assert revision(root)==before
    delete_episode(cache,'local/test',root,2,revision(root))
    delete_episode(cache,'local/test',root,1,revision(root))
    delete_episode(cache,'local/test',root,0,revision(root))
    assert json.loads((root/'meta/info.json').read_text())['total_episodes']==0
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    ds=LeRobotDataset.resume('local/test',root=root)
    ds.finalize()
    restore_episode(cache,'local/test',root)
    assert json.loads((root/'meta/info.json').read_text())['total_episodes']==1
    print('PASS: middle deletion, both videos, joint rows, indexes, stale revision, undo, last episode and empty resume')
