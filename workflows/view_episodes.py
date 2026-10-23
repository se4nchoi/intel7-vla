"""Replay a completed episode in native Rerun, without reading an active writer."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pyarrow.parquet as pq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episode',type=int)
    parser.add_argument('--root',type=Path,default=Path.home()/'.cache/huggingface/lerobot/se4nchoi/messi')
    parser.add_argument('--repo-id',default='se4nchoi/messi')
    args=parser.parse_args()
    root=args.root
    closed=[]
    episode_ids=set()
    total_frames=0
    for path in sorted(root.glob('data/**/*.parquet')):
        try:
            table=pq.read_table(path,columns=['episode_index'])
        except Exception:
            print('Skipping file still being written:',path.name,flush=True)
            continue
        closed.append(path)
        episode_ids.update(table.column('episode_index').to_pylist())
        total_frames+=table.num_rows
    if not episode_ids: raise SystemExit('No completed, closed episodes yet. Save and end the recording session first.')
    episode=max(episode_ids) if args.episode is None else args.episode
    if episode not in episode_ids:
        raise SystemExit(f'Episode {episode} is not finalized. Available: {sorted(episode_ids)}')
    snapshot=Path(tempfile.mkdtemp(prefix='lerobot-episode-view-'))
    for source in root.joinpath('meta').rglob('*'):
        if not source.is_file(): continue
        if source.suffix=='.parquet':
            try: pq.ParquetFile(source)
            except Exception: continue
        destination=snapshot/source.relative_to(root)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    info=json.loads((snapshot/'meta/info.json').read_text())
    info['total_episodes']=max(episode_ids)+1
    info['total_frames']=total_frames
    info['splits']={'train':f'0:{max(episode_ids)+1}'}
    (snapshot/'meta/info.json').write_text(json.dumps(info,indent=2))
    for source in [*closed,*root.glob('videos/**/*.mp4')]:
        destination=snapshot/source.relative_to(root)
        destination.parent.mkdir(parents=True,exist_ok=True)
        os.link(source,destination)
    print(f'Opening saved episode {episode} in Rerun. Completed episodes: {sorted(episode_ids)}',flush=True)
    print(f'Read-only source snapshot: {snapshot}',flush=True)
    # Large Parquet/MP4 files are hard-linked, not copied or modified.
    environment=os.environ.copy()
    environment['LEROBOT_RERUN_MEMORY_LIMIT']='128MB'
    return subprocess.call(['lerobot-dataset-viz','--repo-id',args.repo_id,'--root',str(snapshot),
        '--episode-index',str(episode),'--num-workers','0','--batch-size','4',
        '--display-compressed-images'],env=environment)


if __name__=='__main__': raise SystemExit(main())
