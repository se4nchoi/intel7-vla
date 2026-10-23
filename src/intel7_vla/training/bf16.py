"""Run installed LeRobot with CUDA BF16 autocast for SmolVLA BF16 weights."""
import runpy
import torch

def main():
    if not torch.cuda.is_bf16_supported():
        raise SystemExit('This SmolVLA launcher requires CUDA BF16 support.')
    torch.set_autocast_dtype('cuda', torch.bfloat16)
    runpy.run_module('lerobot.scripts.lerobot_train', run_name='__main__')

if __name__ == '__main__':
    main()
