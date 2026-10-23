"""CLI and web share the same validation, snapshot and duplicate-job guard."""
import argparse
import json

from .jobs import TrainingManager
from .options import DEFAULTS


def main(legacy=False):
    defaults = dict(DEFAULTS)
    if legacy:
        defaults.update(steps=2000,warmup_steps=200,save_freq=500)
    parser=argparse.ArgumentParser(description='로컬 SmolVLA 학습 시작 (Hub 업로드 없음)')
    parser.add_argument('--repo',default=defaults['repo'])
    for name in ('steps','batch_size','num_workers','warmup_steps','save_freq','seed'):
        parser.add_argument('--'+name.replace('_','-'),type=int,default=defaults[name])
    for name in ('learning_rate','eval_split'):
        parser.add_argument('--'+name.replace('_','-'),type=float,default=defaults[name])
    options=vars(parser.parse_args())
    # Respect recording state even when bypassing the web UI.
    from intel7_vla.paths import RUNTIME_ROOT
    from .jobs import read_json
    status=read_json(RUNTIME_ROOT/'native-status.json')
    if status.get('state') in ('connecting','recording','saving','closing') or status.get('teleoperating'):
        parser.error('녹화·저장·추종을 멈춘 뒤 학습을 시작해 주세요.')
    manager=TrainingManager()
    try:
        result=manager.start(options)
    except ValueError as exc:
        parser.error(str(exc))
    result.update(run_dir=str(manager.folder(result['id'])),
                  log=str(manager.folder(result['id'])/'train.log'))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
