"""Read-only UART ping before launching the textbook recording session."""
import serial

failed = []
for role, serial_number in [('Leader','5B90149145'),('Follower','5B90150163')]:
    path = f'/dev/serial/by-id/usb-1a86_USB_Single_Serial_{serial_number}-if00'
    found = []
    try:
        with serial.Serial(path,1000000,timeout=.15,write_timeout=1) as port:
            for motor in range(1,7):
                for _ in range(3):
                    port.reset_input_buffer()
                    port.write(bytes([255,255,motor,2,1,(~(motor+3))&255]))
                    response = port.read(6)
                    if (len(response)==6 and response[:3]==bytes([255,255,motor])
                            and response[3]==2 and response[4]==0
                            and sum(response[2:])%256==255):
                        found.append(motor)
                        break
        print(f'{role}: {len(found)}/6 motor replies ({serial_number})',flush=True)
        if len(found)!=6:
            failed.append(f'{role}: missing motor IDs {[i for i in range(1,7) if i not in found]}')
    except (OSError,serial.SerialException) as exc:
        failed.append(f'{role}: {exc}')
if failed:
    raise SystemExit('\n'.join(failed)+'\nNo movement commands were sent. Check this arm USB/DC/UART connection before recording.')
