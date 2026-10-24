import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'.camera-tools'))
import serial
from serial.tools import list_ports
ports=[p for p in list_ports.comports() if p.serial_number=='5B90149145']
print('LEADER_WINDOWS_PORTS',[(p.device,p.serial_number) for p in ports],flush=True)
assert len(ports)==1
with serial.Serial(ports[0].device,1000000,timeout=.2,write_timeout=1) as bus:
    for motor in range(1,7):
        bus.reset_input_buffer();bus.write(bytes([255,255,motor,2,1,(~(motor+3))&255]))
        print('WINDOWS_PING',motor,bus.read(8).hex() or 'NO_RESPONSE',flush=True)
