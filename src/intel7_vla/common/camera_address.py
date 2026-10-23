"""Windows camera endpoint in either WSL NAT or mirrored networking."""
import subprocess


def camera_host():
    try:
        mode = subprocess.check_output(['wslinfo','--networking-mode'],text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):
        mode = 'nat'
    if mode == 'mirrored':
        return '127.0.0.1'
    return subprocess.check_output(['ip','route','show','default'],text=True).split()[2]


if __name__=='__main__': print(camera_host())
