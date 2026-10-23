"""Local dataset browser and explicit recording controls; no automatic motion."""
import argparse
from dataclasses import asdict
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import signal
import sys
from threading import Lock, Thread
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen
from intel7_vla.datasets.editing import revision, undo_available, delete_episode, restore_episode
from intel7_vla.training.jobs import TrainingManager

from intel7_vla.paths import RUNTIME_ROOT, STATIC_ROOT
ROOT = RUNTIME_ROOT
CACHE = Path.home()/'.cache/huggingface/lerobot'
media_path = next((Path.home()/'.local/share/uv/tools/lelab/lib').glob('python*/site-packages/lelab/episode_media.py'))
spec = importlib.util.spec_from_file_location('lelab_episode_media', media_path)
media = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = media
spec.loader.exec_module(media)
app = worker = None
guard = Lock()
replay = None
training = TrainingManager()


def dataset(repo):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo, re.ASCII):
        raise ValueError('데이터셋 이름은 owner/task 형식이어야 합니다.')
    path = (CACHE/repo).resolve()
    if CACHE.resolve() not in path.parents:
        raise ValueError('Invalid dataset path')
    return path


def catalog():
    result = []
    for p in sorted(CACHE.glob('*/*/meta/info.json')):
        try:
            info = json.loads(p.read_text())
            result.append(dict(repo=str(p.parents[1].relative_to(CACHE)),
                episodes=info.get('total_episodes',0),frames=info.get('total_frames',0),fps=info.get('fps',30)))
        except (OSError,ValueError):
            continue
    return result


def status():
    return app.status() if app else dict(state='disconnected',label='뷰어 모드 · 로봇 미연결',error='',frames=0,elapsed=0,fps=0)


def heartbeat():
    while True:
        if app and worker and worker.is_alive():
            data = {**status(),'pid':os.getpid(),'updated_at':time.time()}
            temporary = ROOT/'native-status.tmp'
            temporary.write_text(json.dumps(data),encoding='utf-8')
            temporary.replace(ROOT/'native-status.json')
            stop = ROOT/'native-stop.request'
            if stop.exists():
                stop.unlink(missing_ok=True)
                app.commands.put(('shutdown',{}))
        time.sleep(.5)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def reply(self, body, kind='application/json', code=200):
        if not isinstance(body,bytes): body=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            url=urlparse(self.path)
            q={k:v[0] for k,v in parse_qs(url.query).items()}
            if url.path=='/': return self.reply((STATIC_ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
            if url.path=='/api/datasets': return self.reply(catalog())
            if url.path=='/api/status': return self.reply(status())
            if url.path=='/api/training': return self.reply(training.status(q.get('id')))
            assets = {'/assets/desk.js':'desk.js', '/assets/desk.css':'desk.css',
                      '/assets/training.js':'training.js', '/assets/training.css':'training.css',
                      '/training_ui.js':'training.js', '/training_ui.css':'training.css'}
            if url.path in assets:
                return self.reply((STATIC_ROOT/'assets'/assets[url.path]).read_bytes(),
                    'text/javascript; charset=utf-8' if url.path.endswith('.js') else 'text/css; charset=utf-8')
            if url.path=='/api/camera-health':
                cameras={}
                for name,port in [('follower_cam',8765),('field_cam',8766)]:
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/health',timeout=3) as r: cameras[name]=json.load(r)
                    except Exception as exc: cameras[name]={'ok':False,'error':str(exc)}
                return self.reply({'ok':all(c['ok'] for c in cameras.values()),'cameras':cameras})
            path=dataset(q.get('repo','se4nchoi/messi'))
            if url.path=='/api/episodes':
                return self.reply({'info':media.read_info(path),'cameras':media.list_cameras(path),
                    'revision':revision(path),'can_restore':undo_available(CACHE,q['repo'],path),
                    'episodes':[asdict(row) for row in media.read_episode_index(path)]})
            episode=int(q.get('episode','0'))
            if url.path=='/api/episode':
                rows=media.read_episode_index(path)
                row=next(r for r in rows if r.episode_idx==episode)
                camera=q.get('camera') or media.list_cameras(path)[0]
                loc=media.locate_episode_video(path,episode,camera=camera)
                import pyarrow.parquet as pq
                table=pq.read_table(media._resolve_action_file(path,episode),
                    filters=[('episode_index','=',episode)],columns=['observation.state','action'])
                values=table.to_pydict()
                return self.reply({'episode':asdict(row),'start':loc.from_timestamp or 0,
                    'end':(loc.from_timestamp or 0)+(row.duration_s or 0),'joints':values,
                    'names':media.read_info(path)['features']['observation.state'].get('names',[])})
            if url.path=='/api/frame':
                loc=media.locate_episode_video(path,episode,camera=q.get('camera'))
                return self.reply(media.extract_frame_png(loc,int(q.get('frame','0')),max_width=960),'image/png')
            if url.path=='/api/video':
                loc=media.locate_episode_video(path,episode,camera=q.get('camera'))
                size=loc.path.stat().st_size
                start,end=0,size-1
                header=self.headers.get('Range')
                if header:
                    match=re.fullmatch(r'bytes=(\d+)-(\d*)',header)
                    if not match: return self.reply({'error':'Unsupported range'},code=416)
                    start=int(match[1]); end=min(int(match[2]) if match[2] else end,end)
                    if start>end:
                        self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
                self.send_response(206 if header else 200)
                self.send_header('Content-Type','video/mp4')
                self.send_header('Accept-Ranges','bytes')
                self.send_header('Content-Length',str(end-start+1))
                if header:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers()
                with loc.path.open('rb') as f:
                    f.seek(start);remaining=end-start+1
                    while remaining:
                        block=f.read(min(256*1024,remaining))
                        if not block:break
                        self.wfile.write(block);remaining-=len(block)
                return
            return self.reply({'error':'Not found'},code=404)
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as exc:
            self.reply({'error':str(exc)},code=400)

    def do_POST(self):
        global app,worker,replay
        try:
            # Non-simple header prevents cross-origin browser requests from controlling hardware.
            if self.headers.get('X-LeRobot-Control')!='local':raise ValueError('Missing local control header')
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://localhost:{self.server.server_port}',f'http://127.0.0.1:{self.server.server_port}'):
                raise ValueError('Invalid origin')
            length=int(self.headers.get('Content-Length','0'))
            if length>8192:raise ValueError('Request too large')
            body=json.loads(self.rfile.read(length) or '{}')
            with guard:
                action=urlparse(self.path).path.removeprefix('/api/')
                if action=='training-start':
                    s=status()
                    if s['state'] in ('connecting','recording','saving','closing') or s.get('teleoperating'):
                        raise ValueError('새 학습 준비 전 녹화·저장·추종을 멈춰 주세요. 로봇 연결은 유지할 수 있습니다.')
                    return self.reply(training.start(body))
                if action in ('delete-episode','restore-episode','connect','start','follow') and training.preparing():
                    raise ValueError('학습용 데이터 복사·검증 중입니다. 준비가 끝난 뒤 다시 시도해 주세요.')
                if action in ('delete-episode','restore-episode'):
                    if worker and worker.is_alive():
                        raise ValueError('편집 전 카메라·녹화 탭에서 로봇 연결을 해제해 주세요. 녹화 중이라면 먼저 저장하세요.')
                    if replay and replay.poll() is None:
                        raise ValueError('Rerun 에피소드 불러오기가 끝난 뒤 다시 시도하세요.')
                    repo=body['repo'];path=dataset(repo)
                    if action=='delete-episode':
                        result=delete_episode(CACHE,repo,path,int(body['episode']),body['revision'])
                    else:result=restore_episode(CACHE,repo,path)
                    return self.reply(result)
                elif action=='connect':
                    if worker and worker.is_alive():raise ValueError('이미 연결돼 있습니다. 데이터셋 변경 전 연결을 해제하세요.')
                    from intel7_vla.recording.recorder import Recorder,blueprint
                    import rerun as rr
                    repo=body.get('repo','se4nchoi/messi');path=dataset(repo)
                    task=str(body.get('task','')).strip()
                    if not task:raise ValueError('작업 설명을 입력하세요.')
                    app=Recorder(demo=DEMO,dataset_root=path,repo_id=repo,task=task)
                    app.update(message='Rerun 뷰어를 여는 중')
                    from intel7_vla.recording.rerun_session import fresh_stream
                    viewer=fresh_stream()
                    rr.spawn(memory_limit='128MB',executable_path=str(Path(sys.executable).parent/'rerun'),
                        recording=viewer,default_blueprint=blueprint())
                    (ROOT/'native-stop.request').unlink(missing_ok=True)
                    worker=Thread(target=app.run,daemon=True);worker.start()
                elif action=='replay':
                    import subprocess
                    if replay and replay.poll() is None:raise ValueError('앞서 선택한 에피소드를 불러오는 중입니다.')
                    repo=body['repo'];dataset(repo)
                    replay=subprocess.Popen([sys.executable,str(ROOT/'view_episodes.py'),'--repo-id',repo,
                        '--root',str(dataset(repo)),'--episode',str(int(body['episode']))])
                elif action in ('start','stop','discard','follow','disconnect'):
                    if not worker or not worker.is_alive():raise ValueError('먼저 로봇 연결을 눌러 주세요.')
                    state=status()['state']
                    if action=='start':
                        if state!='ready':raise ValueError('연결 완료 후 시작할 수 있습니다.')
                        duration=float(body.get('duration',60))
                        if not 1<=duration<=3600:raise ValueError('녹화 시간은 1~3600초입니다.')
                        body={'duration':duration}
                    if action=='follow' and state!='ready':raise ValueError('녹화 대기 중에 추종을 변경하세요.')
                    app.commands.put(('shutdown' if action=='disconnect' else action,body))
                else:raise ValueError('Unknown action')
            self.reply({'ok':True})
        except Exception as exc:
            logging.exception('Command failed: %s',self.path)
            if self.path=='/api/connect' and app and (worker is None or not worker.is_alive()):
                app.update(state='error',error=str(exc),message='연결 준비 실패. 아래 오류를 확인하세요.')
            self.reply({'error':str(exc)},code=400)

    def log_message(self,fmt,*args):
        if self.path.startswith('/api/status'):return
        logging.info(fmt,*args)


def main():
    global DEMO
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--port',type=int,default=8877)
    args=parser.parse_args();DEMO=args.demo
    logging.basicConfig(level=logging.INFO)
    Thread(target=heartbeat,daemon=True).start()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.daemon_threads=True
    def shutdown(*_):
        if app and worker and worker.is_alive():
            app.commands.put(('shutdown',{}));worker.join(timeout=120)
        Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown);signal.signal(signal.SIGINT,shutdown)
    print(f'LeRobot Dataset Desk: http://localhost:{args.port} (viewer only until Connect)',flush=True)
    server.serve_forever()
    server.server_close()


if __name__ == '__main__':
    main()
