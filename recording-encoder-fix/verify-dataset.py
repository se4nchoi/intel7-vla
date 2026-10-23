import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np,av
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from internal_datasets.lerobot.streaming_encoding_settings import StreamingEncodingSettings

features={
    'action':{'dtype':'float32','shape':(1,),'names':['joint']},
    'observation.state':{'dtype':'float32','shape':(1,),'names':['joint']},
    'observation.images.follower_cam':{'dtype':'video','shape':(240,320,3),'names':['height','width','channels']},
}
kwargs=StreamingEncodingSettings().with_resolved_vcodec().to_lerobot_write_kwargs()
with tempfile.TemporaryDirectory(prefix='dataset-rgb-integration-') as tmp:
    root=Path(tmp)/'dataset'
    with patch('lerobot.datasets.video_utils.depth_encoder_defaults',side_effect=AssertionError('RGB streaming must not create depth')), patch('lerobot.datasets.dataset_writer.depth_encoder_defaults',side_effect=AssertionError('RGB writer must not create depth')):
        ds=LeRobotDataset.create(repo_id='diagnostics/rgb',fps=30,root=root,features=features,robot_type='SO101 Follower',**kwargs)
        print('PASS_DATASET_CREATE',flush=True)
        for episode in range(2):
            if episode:
                ds=LeRobotDataset.resume(repo_id='diagnostics/rgb',root=root,**kwargs)
                print('PASS_DATASET_RESUME',flush=True)
            for i in range(12):
                image=np.zeros((240,320,3),np.uint8)
                image[:,:,i%3]=50+10*i
                ds.add_frame({'action':np.array([i],np.float32),'observation.state':np.array([i],np.float32),'observation.images.follower_cam':image,'task':'diagnostic RGB recording'})
            ds.save_episode()
            ds.finalize()
            print('PASS_EPISODE_SAVE',episode,flush=True)
        reopened=LeRobotDataset(repo_id='diagnostics/rgb',root=root,video_backend='pyav')
        assert reopened.meta.total_episodes==2,reopened.meta.total_episodes
        assert reopened.meta.total_frames==24,reopened.meta.total_frames
        total=0
        for path in root.rglob('*.mp4'):
            with av.open(str(path)) as video: total+=sum(1 for _ in video.decode(video=0))
        assert total==24,total
        print('PASS_REOPEN: 2 episodes, 24 data frames, 24 decoded RGB video frames',flush=True)
