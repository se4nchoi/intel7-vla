from pathlib import Path
import shutil
import importlib.util

spec=importlib.util.find_spec('lerobot.datasets.video_utils')
path=Path(spec.origin)
source=path.read_text()
old='        self._depth_encoder = depth_encoder or depth_encoder_defaults()'
new='        # Initialize depth only when depth streams are actually recorded.\n        self._depth_encoder = depth_encoder'
anchor='''        if depth_video_keys is None:
            depth_video_keys = []

        for video_key in video_keys:'''
replacement='''        if depth_video_keys is None:
            depth_video_keys = []

        if depth_video_keys and self._depth_encoder is None:
            self._depth_encoder = depth_encoder_defaults()

        for video_key in video_keys:'''
backup=Path('/app/storage/patches/lerobot-lazy-depth/video_utils.py.original')
backup.parent.mkdir(parents=True,exist_ok=True)
if new in source and replacement in source:
    print('Patch already installed')
else:
    assert source.count(old)==1 and source.count(anchor)==1, 'Unexpected LeRobot version; no changes made'
    if not backup.exists(): shutil.copy2(path,backup)
    source=source.replace(old,new).replace(anchor,replacement)
    compile(source,str(path),'exec')
    path.write_text(source)
    print('Patched',path)
print('Original backup:',backup)

# DatasetWriter also eagerly initialized depth, independently of streaming.
spec=importlib.util.find_spec('lerobot.datasets.dataset_writer')
path=Path(spec.origin)
source=path.read_text()
old='        self._depth_encoder = depth_encoder or depth_encoder_defaults()'
new='''        # RGB datasets must not require an available depth encoder.
        self._depth_encoder = depth_encoder
        if self._depth_encoder is None and self._meta.depth_keys:
            self._depth_encoder = depth_encoder_defaults()'''
backup=Path('/app/storage/patches/lerobot-lazy-depth/dataset_writer.py.original')
if new in source:
    print('DatasetWriter patch already installed')
else:
    assert source.count(old)==1, 'Unexpected DatasetWriter version; no writer changes made'
    if not backup.exists(): shutil.copy2(path,backup)
    source=source.replace(old,new)
    compile(source,str(path),'exec')
    path.write_text(source)
    print('Patched',path)
print('Original writer backup:',backup)
