import json,os,signal,subprocess
from urllib.request import urlopen
with urlopen('http://127.0.0.1:8877/api/status',timeout=3) as r: state=json.load(r)
assert state['state'] in ('error','disconnected'),state
owners=subprocess.run(['fuser','/dev/ttyACM0','/dev/ttyACM1'],capture_output=True,text=True)
assert not owners.stdout.strip(), owners.stdout
pid=int(subprocess.check_output(['fuser','8877/tcp'],stderr=subprocess.DEVNULL).decode().strip())
args=open(f'/proc/{pid}/cmdline','rb').read().decode().replace('\0',' ')
assert 'wsl/dataset_desk.py' in args,args
os.kill(pid,signal.SIGKILL)
print('Stopped idle Dataset Desk; no serial devices open, no recording or following')
