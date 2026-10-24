"""Local SmolVLA jobs: bounded options, immutable snapshots and restart-safe status."""
from contextlib import contextmanager
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from intel7_vla.paths import PROJECT_ROOT
PROJECT = PROJECT_ROOT
from .options import DEFAULTS, BASE_REVISION, validated_options
from .progress import tail_log, parse_progress


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {} if default is None else default


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def process_identity(pid):
    try:
        raw = Path(f'/proc/{int(pid)}/stat').read_text()
        fields = raw[raw.rfind(')')+2:].split()
        if fields[0] == 'Z':
            return None
        return fields[19]  # field 22: kernel start ticks; protects against PID reuse.
    except (OSError, ValueError, IndexError, TypeError):
        return None


def job_process_alive(pid, run, ticks=None):
    identity = process_identity(pid)
    if identity is None or (ticks is not None and identity != str(ticks)):
        return False
    try:
        args = Path(f'/proc/{int(pid)}/cmdline').read_bytes().decode().split('\0')
        return (str(run) in args and any(a.endswith('/run_training_job.py') for a in args)) or any(
            a.startswith('--output_dir=') and Path(a.split('=', 1)[1]).parent == run for a in args)
    except (OSError, ValueError):
        return False


class TrainingManager:
    def __init__(self, runs=None, cache=None, lerobot=None):
        self.runs = Path(runs) if runs else Path.home()/'vla-training/runs'
        self.cache = Path(cache) if cache else Path.home()/'.cache/huggingface/lerobot'
        self.lerobot = Path(lerobot) if lerobot else Path.home()/'lerobot'
        self.base = Path.home()/f'.cache/huggingface/hub/models--lerobot--smolvla_base/snapshots/{BASE_REVISION}'
        self._children = []

    @contextmanager
    def lock(self):
        self.runs.mkdir(parents=True, exist_ok=True)
        with (self.runs/'.launch.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def folder(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', job_id):
            raise ValueError('유효하지 않은 학습 ID입니다.')
        path = self.runs/job_id
        if not (path/'run.json').is_file():
            raise ValueError('학습 기록이 없습니다.')
        return path

    def describe(self, folder):
        data = read_json(folder/'run.json')
        runtime = read_json(folder/'runtime.json')
        output = Path(runtime.get('output_dir', data.get('output_dir', folder/'output')))
        log_path = Path(runtime.get('log', data.get('log', folder/'train.log')))
        content = tail_log(log_path)
        progress = parse_progress(content)
        config = read_json(output/'checkpoints/last/pretrained_model/train_config.json')
        if not config:
            config = read_json(output/'train_config.json')
        options = data.get('options', {})
        if not options and config:
            options = dict(repo=config.get('dataset',{}).get('repo_id','se4nchoi/messi'),
                steps=config.get('steps',data.get('steps',0)),batch_size=config.get('batch_size'),
                num_workers=config.get('num_workers'),seed=config.get('seed'),
                eval_split=config.get('dataset',{}).get('eval_split',0),save_freq=config.get('save_freq'),
                learning_rate=config.get('policy',{}).get('optimizer_lr'),
                warmup_steps=config.get('policy',{}).get('scheduler_warmup_steps'))
        total = options.get('steps', data.get('steps', config.get('steps', progress['total_steps'])))
        alive = job_process_alive(data.get('pid'), folder, data.get('start_ticks'))
        exit_info = read_json(folder/'exit.json')
        final_model = output/'checkpoints/last/pretrained_model/model.safetensors'
        if alive:
            state = runtime.get('phase', 'running')
        elif exit_info:
            state = 'completed' if exit_info.get('returncode') == 0 else 'failed'
        elif total and progress['step'] >= total and final_model.is_file():
            state = 'completed'
        elif data.get('managed') and not data.get('pid') and time.time()-data.get('created', 0) < 15:
            state = 'preparing'
        else:
            state = 'interrupted' if progress['step'] else 'failed'
        checkpoints = []
        for p in sorted((output/'checkpoints').glob('[0-9]*/pretrained_model/model.safetensors')):
            if p.parent.parent.name.isdigit():
                checkpoints.append(dict(step=int(p.parent.parent.name), path=str(p.parent), bytes=p.stat().st_size))
        source_info = read_json(folder/'dataset/meta/info.json')
        created = data.get('created', folder.stat().st_mtime)
        error = runtime.get('error', '')
        if state in ('failed', 'interrupted') and not error:
            error = next((line for line in reversed(content.splitlines()) if re.search(r'Error:|Exception:',line)),
                         '학습 프로세스가 종료됐습니다. 로그와 저장된 체크포인트를 확인해 주세요.')
        return dict(id=folder.name, state=state, active=alive, created=created,
            repo=options.get('repo',data.get('repo',config.get('dataset',{}).get('repo_id','se4nchoi/messi'))),
            model='SmolVLA', options=options or dict(steps=total,batch_size=data.get('batch_size',config.get('batch_size'))),
            total_steps=total, step=progress['step'],
            percent=min(100,round(100*progress['step']/total,1)) if total else 0,
            eta=progress['eta'] if alive and state=='running' else None,
            loss=progress['losses'][-1]['loss'] if progress['losses'] else None,
            eval_loss=progress['evaluations'][-1]['loss'] if progress['evaluations'] else None,
            losses=progress['losses'], evaluations=progress['evaluations'],
            episodes=data.get('episodes',source_info.get('total_episodes')),
            frames=data.get('frames',source_info.get('total_frames')),
            message=runtime.get('message',''),error=error,checkpoints=checkpoints,
            output_dir=str(output),log_path=str(log_path),run_dir=str(folder),
            log=progress['log'],pid=data.get('pid'),finished=exit_info.get('finished'))

    def jobs(self):
        # Reap children without stopping independent running jobs.
        self._children = [p for p in self._children if p.poll() is None]
        result = []
        for record in self.runs.glob('*/run.json'):
            try:
                result.append(self.describe(record.parent))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(result,key=lambda j:j['created'],reverse=True)

    def preparing(self):
        return any(j['state']=='preparing' for j in self.jobs())

    def status(self, selected=None):
        jobs = self.jobs()
        current = next((j for j in jobs if j['active']), jobs[0] if jobs else None)
        if selected:
            current = self.describe(self.folder(selected))
        summaries = [{k:v for k,v in j.items() if k not in ('log','losses','evaluations','checkpoints')} for j in jobs[:20]]
        return dict(current=current,jobs=summaries,busy=any(j['active'] or j['state']=='preparing' for j in jobs),
                    defaults=DEFAULTS)

    def start(self, body):
        options = validated_options(body)
        source = (self.cache/options['repo']).resolve()
        if self.cache.resolve() not in source.parents:
            raise ValueError('유효하지 않은 데이터셋 경로입니다.')
        info = read_json(source/'meta/info.json')
        episodes = info.get('total_episodes',0)
        if episodes < 2 or info.get('total_frames',0) == 0:
            raise ValueError('저장 완료된 에피소드가 2개 이상 필요합니다.')
        if options['eval_split'] and math.ceil(episodes*options['eval_split']) >= episodes:
            raise ValueError('검증 분리 후 학습 에피소드가 남아야 합니다.')
        if not (self.base/'model.safetensors').is_file():
            raise ValueError('로컬 SmolVLA 기본 모델이 없습니다. 모델을 먼저 준비해 주세요.')
        python = self.lerobot/'.venv/bin/python'
        if not python.is_file():
            raise ValueError('WSL LeRobot 가상환경을 찾을 수 없습니다.')
        with self.lock():
            if self.status()['busy']:
                raise ValueError('이미 준비 중이거나 실행 중인 학습이 있습니다.')
            # Also prevent overlap with CLI training not registered in our job history.
            for cmd in Path('/proc').glob('[0-9]*/cmdline'):
                try:
                    args=cmd.read_bytes().decode().split('\0')
                    if any(a.endswith('/lerobot-train') or a=='lerobot.scripts.lerobot_train' or
                           a.endswith('/train_bf16.py') for a in args):
                        raise ValueError('다른 CLI 학습이 실행 중입니다. 종료 후 다시 시작해 주세요.')
                except (OSError, UnicodeError):
                    continue
            name='messi-smolvla-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
            folder=self.runs/name
            folder.mkdir()
            data=dict(managed=True,created=time.time(),options=options,episodes=episodes,
                      frames=info['total_frames'],base_revision=BASE_REVISION,repo=options['repo'])
            write_json(folder/'run.json',data)
            write_json(folder/'runtime.json',dict(phase='preparing',message='데이터셋 복사·검증을 준비하고 있습니다.'))
            try:
                with (folder/'train.log').open('a') as log:
                    child=subprocess.Popen([str(python),str(PROJECT/'wsl/run_training_job.py'),str(folder)],
                        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                        cwd=self.lerobot,start_new_session=True)
                data.update(pid=child.pid,start_ticks=process_identity(child.pid))
                write_json(folder/'run.json',data)
                self._children.append(child)
            except Exception as exc:
                write_json(folder/'runtime.json',dict(phase='failed',error=str(exc)))
                write_json(folder/'exit.json',dict(returncode=1,finished=time.time()))
                raise
            return dict(ok=True,id=name)


def run_job(folder):
    """Compatibility API; the supervisor lives separately from job management."""
    from .runner import run_job as supervise
    return supervise(folder, manager_factory=TrainingManager)
