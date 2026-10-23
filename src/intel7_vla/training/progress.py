"""Bounded log reading and exact-step training/evaluation metrics."""
import math
from pathlib import Path
import re

def tail_log(path, limit=2*1024*1024):
    try:
        with Path(path).open('rb') as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size-limit))
            content = stream.read().decode('utf-8', errors='replace')
        return re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', content).replace('\r', '\n')
    except OSError:
        return ''


def parse_progress(content):
    points, evaluations, events = [], [], []
    step, total, eta = 0, 0, None
    for line in content.splitlines():
        progress = re.search(r'Training:.*?\b(\d+)/(\d+)\s*\[([^\]]+)\]', line)
        if progress:
            step = max(step, int(progress[1]))
            total = int(progress[2])
            eta = progress[3].split('<', 1)[-1].split(',', 1)[0] if '<' in progress[3] else None
        metric = re.search(r'\bstep:([\d.]+)([KMB]?)\b.*?\bloss:([\d.eE+-]+)', line)
        if metric:
            rounded_step = int(float(metric[1])*{'':1,'K':1000,'M':1000000,'B':1000000000}[metric[2]])
            metric_step = (int(progress[1]) if progress else step or rounded_step) if metric[2] else rounded_step
            loss = float(metric[3])
            if math.isfinite(loss):
                points.append({'step':metric_step, 'loss':loss})
            step = max(step, metric_step)
        evaluation = re.search(r'step\s+(\d+):\s+eval_loss=([\d.eE+-]+)', line)
        if evaluation and math.isfinite(float(evaluation[2])):
            evaluations.append({'step':int(evaluation[1]), 'loss':float(evaluation[2])})
        # tqdm and logger frequently share the same physical line. Keep the
        # metric/event suffix while removing repetitive progress-bar output.
        display_line = line[progress.end():].strip() if progress else line
        if display_line.strip() and not display_line.startswith('Loading weights:'):
            events.append(display_line)
    return dict(step=step, total_steps=total, eta=eta, losses=points[-500:],
                evaluations=evaluations[-100:], log='\n'.join(events[-160:]))
