"""Independent snapshot/validation/training supervisor; no web-service lifecycle dependency."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import time

from intel7_vla.paths import PROJECT_ROOT as PROJECT
from .options import validated_options
from .jobs import read_json, write_json

def signature(root):
    return {str(p.relative_to(root)):(p.stat().st_size,p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


def run_job(folder, manager_factory=None):
    """Independent supervisor survives Dataset Desk restarts and records exit status."""
    folder=Path(folder)
    if manager_factory is None:
        from .jobs import TrainingManager
        manager_factory = TrainingManager
    manager=manager_factory()
    data=read_json(folder/'run.json')
    options=validated_options(data['options'])
    runtime=dict(phase='preparing',log=str(folder/'train.log'),output_dir=str(folder/'output'))
    def phase(name,message):
        runtime.update(phase=name,message=message)
        write_json(folder/'runtime.json',runtime)
        print(message,flush=True)
    try:
        phase('preparing','저장된 데이터셋을 별도 학습 폴더에 복사합니다.')
        source=manager.cache/options['repo']
        before=signature(source)
        snapshot=folder/'dataset'
        shutil.copytree(source,snapshot)
        if signature(source)!=before:
            raise ValueError('복사 중 원본 데이터가 변경됐습니다. 녹화·편집을 멈춘 뒤 다시 시작해 주세요.')
        phase('preparing','관절값·동작값과 모든 에피소드의 카메라 프레임을 확인합니다.')
        import numpy as np
        import pyarrow.parquet as pq
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        info=read_json(snapshot/'meta/info.json')
        counts={}
        for p in sorted((snapshot/'data').rglob('*.parquet')):
            table=pq.read_table(p)
            for key in ('action','observation.state'):
                values=np.asarray(table[key].to_pylist())
                if not np.isfinite(values).all():
                    raise ValueError(f'{key}에 비정상 수치가 있습니다.')
            for ep in table['episode_index'].to_pylist():
                counts[ep]=counts.get(ep,0)+1
        if sum(counts.values())!=info['total_frames'] or set(counts)!=set(range(info['total_episodes'])):
            raise ValueError('데이터 파일과 메타데이터의 에피소드·프레임 수가 다릅니다.')
        cameras=[k for k,v in info['features'].items() if v.get('dtype')=='video']
        if not cameras:
            raise ValueError('영상 카메라가 없는 데이터셋입니다.')
        ds=LeRobotDataset(options['repo'],root=snapshot,video_backend='pyav')
        offset=0
        for ep,count in sorted(counts.items()):
            for index in (offset,offset+count//2,offset+count-1):
                sample=ds[index]
                for camera in cameras:
                    if sample[camera].ndim!=3:
                        raise ValueError(f'Episode {ep}: {camera} 영상 형식이 다릅니다.')
            offset+=count
        del ds
        manifest={}
        for p in snapshot.rglob('*'):
            if p.is_file():
                with p.open('rb') as stream:
                    manifest[str(p.relative_to(snapshot))]=hashlib.file_digest(stream,'sha256').hexdigest()
        write_json(folder/'dataset-sha256.json',manifest)
        adapted=folder/'base-model'
        adapted.mkdir()
        for p in manager.base.iterdir():
            if p.name!='config.json':
                (adapted/p.name).symlink_to(p.resolve())
        config=read_json(manager.base/'config.json')
        from lerobot.utils.feature_utils import dataset_to_policy_features
        features=dataset_to_policy_features(info['features'])
        config['input_features']={key:dict(type=value.type.value,shape=list(value.shape))
                                  for key,value in features.items() if key!='action'}
        write_json(adapted/'config.json',config)
        args=[str(manager.lerobot/'.venv/bin/python'),str(PROJECT/'wsl/train_bf16.py'),
            f"--dataset.repo_id={options['repo']}",f'--dataset.root={snapshot}',
            '--dataset.video_backend=pyav',f"--dataset.eval_split={options['eval_split']}",
            f'--policy.path={adapted}','--policy.device=cuda','--policy.use_amp=true','--policy.push_to_hub=false',
            f"--batch_size={options['batch_size']}",f"--num_workers={options['num_workers']}",
            f"--steps={options['steps']}",f"--save_freq={options['save_freq']}",
            f"--eval_steps={options['save_freq'] if options['eval_split'] else 0}",
            '--max_eval_samples=64','--env_eval_freq=0','--prefetch_factor=2',
            '--log_freq=10',f"--seed={options['seed']}",
            f"--policy.optimizer_lr={options['learning_rate']}",
            f"--policy.scheduler_warmup_steps={options['warmup_steps']}",
            f"--policy.scheduler_decay_steps={options['steps']}",
            '--wandb.enable=false',f'--output_dir={folder}/output','--job_name=dataset_desk_smolvla']
        write_json(folder/'command.json',args)
        phase('running','데이터 복사·검증 완료. GPU 학습을 시작합니다. 추가 수집은 다음 학습에 반영됩니다.')
        env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','OMP_NUM_THREADS':'2',
             'MKL_NUM_THREADS':'2','TOKENIZERS_PARALLELISM':'false','PYTHONUNBUFFERED':'1'}
        result=subprocess.run(args,cwd=manager.lerobot,env=env)
        write_json(folder/'exit.json',dict(returncode=result.returncode,finished=time.time()))
        phase('completed' if result.returncode==0 else 'failed',
              '학습이 완료됐습니다.' if result.returncode==0 else '학습이 종료됐습니다. 로그를 확인해 주세요.')
    except Exception as exc:
        import traceback
        traceback.print_exc()
        runtime.update(phase='failed',error=str(exc),message='학습 준비 또는 실행 중 오류가 발생했습니다.')
        write_json(folder/'runtime.json',runtime)
        write_json(folder/'exit.json',dict(returncode=1,finished=time.time()))
        raise
