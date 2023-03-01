# from pynput import keyboard
# import time

# def on_press(key):
#     try:
#         print(f"{key.char} was pressed")
#     except AttributeError:
#         print(f"{key} was special pressed")

# listener = keyboard.Listener(on_press=on_press)
# listener.start()
# counter = 0
# try:
#     while True:
#         # if counter % 10000000 == 0:
#         print('Hello World')
#         counter += 1
#         time.sleep(1)
# except KeyboardInterrupt:
#     pass

import can
import cantools
import time

db = cantools.database.load_file('toyota_corolla.dbc')
can_bus = can.interface.Bus('can0', bustype='socketcan')
steer_counter = 128
static_commands = [
            (0x1C4, 8, b'\x05\xea\x1b\x08\x00\x00\xc0\x9f'),
            (0x4CB, 8, b'f\x06\x08\n\x02\x00\x00\x00'),
            # (0x7A1, 8, b'\x02\x13\x81'),
            # (0x224, 0, b'\x00\x00\x00')
        ]

def calculate_toyota_checksum(input_msg):
    checksum = sum(bytearray([(input_msg.arbitration_id >> 8) & 0xFF, input_msg.arbitration_id & 0xFF, input_msg.dlc]) + input_msg.data[:-1])
    return checksum & 0xFF

while True:
    try:
        input_msg = can_bus.recv()
        for static_command in static_commands:
            static_msg = can.Message(timestamp=time.time(), is_rx=False, arbitration_id=int(static_command[0]), is_extended_id=False, dlc=static_command[1], data=bytearray(static_command[2]))
            can_bus.send(static_msg)
        can_msg = can.Message(timestamp=time.time(), is_rx=False, dlc=5, is_extended_id=False, arbitration_id=int(0x2E4), data=bytearray([steer_counter, 5, 0, 128, 0]))
        # can_msg = can.Message(timestamp=time.time(), is_rx=False, dlc=5, is_extended_id=False, arbitration_id=int(0x2E4), data=bytearray([steer_counter, 251, 0, 128, 0]))
        can_msg.data[-1] = calculate_toyota_checksum(can_msg)
        # can_bus.send(can_msg)
        try:
            print(db.decode(input_msg.arbitration_id, input_msg.data))
        except:
            pass
        # print(can_msg)
        steer_counter += 1
        if steer_counter == 256:
            steer_counter = 128
    except KeyboardInterrupt:
        exit()
    time.sleep(1/100)
