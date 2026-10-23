from pathlib import Path
import tempfile
from unittest.mock import patch
import av,numpy as np
from lerobot.configs.video import DepthEncoderConfig,RGBEncoderConfig
from lerobot.datasets.video_utils import StreamingVideoEncoder
from internal_datasets.lerobot.streaming_encoding_settings import StreamingEncodingSettings

try:
    DepthEncoderConfig()
except ValueError as error:
    assert 'gray12le' in str(error)
    print('REPRODUCED: unavailable depth codec still rejected',flush=True)
else:
    raise AssertionError('Expected this container to reject gray12le HEVC')

settings=StreamingEncodingSettings().with_resolved_vcodec()
print('RGB_CODEC',settings.vcodec,flush=True)
rgb=RGBEncoderConfig(vcodec=settings.vcodec,g=None)
with tempfile.TemporaryDirectory(prefix='rgb-encoder-check-') as tmp:
    with patch('lerobot.datasets.video_utils.depth_encoder_defaults',side_effect=AssertionError('RGB must not initialize depth')):
        enc=StreamingVideoEncoder(fps=30,rgb_encoder=rgb,queue_maxsize=30)
        key='observation.images.follower_cam'
        enc.start_episode([key],Path(tmp))
        for i in range(12):
            frame=np.zeros((240,320,3),dtype=np.uint8)
            frame[:,:,i%3]=40+i*15
            enc.feed_frame(key,frame)
        result=enc.finish_episode()
        path=result[key][0]
        with av.open(str(path)) as video:
            decoded=[f.to_ndarray(format='rgb24') for f in video.decode(video=0)]
        assert len(decoded)==12,len(decoded)
        assert decoded[0].shape==(240,320,3)
        assert not np.array_equal(decoded[0],decoded[-1])
        print('PASS: 12 RGB frames saved and decoded; depth encoder never created',flush=True)
