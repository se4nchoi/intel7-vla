"""Allowed training parameters and stable local base-model revision."""
import math
import re

DEFAULTS = dict(repo='se4nchoi/messi', steps=10000, batch_size=4, num_workers=2,
                learning_rate=0.0001, warmup_steps=1000, eval_split=0.2,
                save_freq=1000, seed=1000)

BASE_REVISION = '5e8d12a6e2975b0e5e5fce7c8caf47c371d257b6'

REPO_PATTERN = re.compile(r'[\w.-]+/[\w.-]+', re.ASCII)


def validated_options(body):
    if not isinstance(body, dict) or set(body)-set(DEFAULTS):
        raise ValueError('지원하는 학습 파라미터만 입력해 주세요.')
    result = {**DEFAULTS, **body}
    repo = result['repo']
    if not isinstance(repo, str) or not REPO_PATTERN.fullmatch(repo) or any(p in ('.', '..') for p in repo.split('/')):
        raise ValueError('데이터셋 ID는 owner/task 형식이어야 합니다.')
    limits = dict(steps=(10, 200000), batch_size=(1, 8), num_workers=(0, 4),
                  warmup_steps=(0, 50000), save_freq=(10, 50000), seed=(0, 2147483647))
    for name, (low, high) in limits.items():
        value = result[name]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{name}: {low}~{high} 사이 정수를 입력해 주세요.')
    for name, low, high in [('learning_rate', 1e-7, 0.001), ('eval_split', 0.0, 0.4)]:
        value = result[name]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{name}: {low}~{high} 범위를 확인해 주세요.')
    if result['warmup_steps'] >= result['steps']:
        raise ValueError('Warmup은 전체 학습 스텝보다 작아야 합니다.')
    if result['save_freq'] > result['steps']:
        raise ValueError('저장·검증 간격은 전체 스텝 이하여야 합니다.')
    return result
