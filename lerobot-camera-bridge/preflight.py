"""Parse recording config and check metadata without connecting robot hardware."""
from pathlib import Path
import sys
from types import SimpleNamespace

import draccus
from lerobot.datasets.io_utils import load_info
from lerobot.scripts.lerobot_record import (
    RecordConfig, aggregate_pipeline_dataset_features, create_initial_features,
    combine_feature_dicts, make_default_processors, make_robot_from_config,
    sanity_check_dataset_robot_compatibility,
)

cfg = draccus.parse(RecordConfig, args=sys.argv[1:])
robot = make_robot_from_config(cfg.robot)  # constructor only; never connect()
teleop_processor, _, observation_processor = make_default_processors()
features = combine_feature_dicts(
    aggregate_pipeline_dataset_features(pipeline=teleop_processor,
        initial_features=create_initial_features(action=robot.action_features), use_videos=cfg.dataset.video),
    aggregate_pipeline_dataset_features(pipeline=observation_processor,
        initial_features=create_initial_features(observation=robot.observation_features), use_videos=cfg.dataset.video),
)
if (Path(cfg.dataset.root) / 'meta/info.json').exists():
    info = load_info(Path(cfg.dataset.root))
    dataset = SimpleNamespace(meta=SimpleNamespace(robot_type=info.robot_type),
                              fps=info.fps, features=info.features)
    sanity_check_dataset_robot_compatibility(dataset, robot, cfg.dataset.fps, features)
elif cfg.resume:
    raise SystemExit('Cannot resume: this dataset has no meta/info.json yet.')
else:
    print('New dataset: metadata will be created when recording starts.')
for port in [cfg.robot.port, cfg.teleop.port]:
    if not Path(port).exists():
        raise SystemExit(f'Missing serial device: {port}')
print('PASS: CLI configuration, dataset features, robot type, fps, and serial device paths')
print('No robot ports opened. No dataset files modified.')
