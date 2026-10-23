"""Read only: verify native Windows UART over time, without torque/position writes."""
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'.camera-tools'))
import serial
from serial.tools import list_ports

deadline=time.monotonic()+10
ports=[]
while time.monotonic()<deadline:
    ports=[p for p in list_ports.comports() if p.serial_number=='5B90149145']
    if ports: break
    time.sleep(.25)
if len(ports)!=1: raise SystemExit('Leader Windows COM port not found')
with serial.Serial(ports[0].device,1000000,timeout=.1,write_timeout=1) as bus:
    print('Windows direct:',ports[0].device,flush=True)
    start=time.monotonic()
    rounds=0
    failures=0
    last_print=-5
    while time.monotonic()-start<25:
        positions=[]
        for motor in range(1,7):
            payload=[motor,4,2,56,2]
            bus.reset_input_buffer()
            bus.write(bytes([255,255,*payload,(~sum(payload))&255]))
            reply=bus.read(8)
            valid=(len(reply)==8 and reply[:3]==bytes([255,255,motor])
                   and reply[3]==4 and reply[4]==0 and sum(reply[2:])%256==255)
            positions.append(int.from_bytes(reply[5:7],'little') if valid else None)
            failures+=not valid
        rounds+=1
        elapsed=time.monotonic()-start
        if elapsed-last_print>=5:
            print(f'{elapsed:.1f}s rounds={rounds} failures={failures} raw_positions={positions}',flush=True)
            last_print=elapsed
        if failures>=12: raise SystemExit('Persistent native Windows UART failure')
        time.sleep(.03)
    print(f'PASS: {rounds*6} position reads, {failures} failures, 25 seconds',flush=True)
