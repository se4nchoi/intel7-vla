"""Transactional local episode editing. Originals remain available for undo."""
import hashlib
import json
from pathlib import Path
import time
import uuid


def revision(root):
    digest = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file():
            stat = p.stat()
            digest.update(f'{p.relative_to(root)}:{stat.st_size}:{stat.st_mtime_ns}\n'.encode())
    return digest.hexdigest()


def entries(cache, repo):
    result = []
    for p in (Path(cache)/'.dataset-desk-history').glob('*/manifest.json'):
        data = json.loads(p.read_text())
        if data['repo'] == repo and data['state'] == 'deleted':
            result.append((p, data))
    return sorted(result, key=lambda item: item[1]['created'], reverse=True)


def undo_available(cache, repo, root):
    history = entries(cache, repo)
    return bool(history and history[0][1]['after'] == revision(root))


def delete_episode(cache, repo, root, episode, expected_revision):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.datasets.dataset_metadata import LeRobotDatasetMetadata
    from lerobot.datasets.dataset_tools import delete_episodes
    root = Path(root)
    if revision(root) != expected_revision:
        raise ValueError('데이터셋이 변경됐습니다. 새로고침 후 다시 선택하세요.')
    info = json.loads((root/'meta/info.json').read_text())
    total = info['total_episodes']
    if not 0 <= episode < total:
        raise ValueError('에피소드가 존재하지 않습니다.')
    folder = Path(cache)/'.dataset-desk-history'/uuid.uuid4().hex
    folder.mkdir(parents=True)
    staged = folder/'edited'
    # The official editor repacks shared videos and reindexes data/metadata.
    if total > 1:
        source = LeRobotDataset(repo, root=root)
        edited = delete_episodes(source, [episode], output_dir=staged, repo_id=repo)
        assert edited.meta.total_episodes == total-1
        assert edited.meta.total_frames == source.meta.total_frames-int(source.meta.episodes[episode]['length'])
        del edited, source
    else:
        # Keep an empty dataset (and its feature schema) ready for new recording.
        empty = LeRobotDatasetMetadata.create(repo, fps=info['fps'], features=info['features'],
            robot_type=info.get('robot_type'), root=staged,
            use_videos=bool(info.get('video_path')))
        empty.finalize()
    if revision(root) != expected_revision:
        raise ValueError('편집 중 데이터셋이 변경됐습니다. 원본은 유지했습니다.')
    manifest = dict(repo=repo, episode=episode, created=time.time(), state='prepared', after=revision(staged))
    file = folder/'manifest.json'
    file.write_text(json.dumps(manifest))
    root.rename(folder/'original')
    try:
        staged.rename(root)
    except BaseException:
        (folder/'original').rename(root)
        raise
    manifest['state'] = 'deleted'
    file.write_text(json.dumps(manifest))
    return dict(ok=True, episodes=total-1)


def restore_episode(cache, repo, root):
    history = entries(cache, repo)
    if not history:
        raise ValueError('복원할 삭제 이력이 없습니다.')
    file, data = history[0]
    if data['after'] != revision(root):
        raise ValueError('삭제 후 새 녹화 등으로 데이터셋이 변경돼 복원을 중단했습니다. 백업은 보존돼 있습니다.')
    folder = file.parent
    Path(root).rename(folder/'removed-version')
    try:
        (folder/'original').rename(root)
    except BaseException:
        (folder/'removed-version').rename(root)
        raise
    data['state'] = 'restored'
    file.write_text(json.dumps(data))
    return dict(ok=True)
