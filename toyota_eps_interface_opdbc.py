import can
import cantools
import time
from opendbc.can.packer import CANPacker

can_channel = "can0"
dbc_fp = "toyota_corolla_simple.dbc"
db = cantools.database.load_file(dbc_fp)
can_bus = can.interface.Bus(can_channel, bustype='socketcan')
steer_counter = 0
static_commands = [
            (0x1C4, 8, b'\x05\xea\x1b\x08\x00\x00\xc0\x9f'),
            (0x4CB, 8, b'f\x06\x08\n\x02\x00\x00\x00'),
        ]

packer = CANPacker(dbc_fp)

min_torque = 0
max_torque = 1280
freq = 40
torque_increment = 5/freq
current_torque = 0
torque_forward = True

default_steer_request = 1
default_set_me_1 = 1

while True:
    input_msg = can_bus.recv()
    try:
        for static_command in static_commands:
            static_msg = can.Message(timestamp=time.time(), is_rx=False, arbitration_id=int(static_command[0]), is_extended_id=False, dlc=static_command[1], data=bytearray(static_command[2]))
            can_bus.send(static_msg)
        if current_torque >= max_torque:
            torque_forward = False
        elif current_torque <= min_torque:
            torque_forward = True
        values = {
            "STEER_REQUEST": default_steer_request,
            "STEER_TORQUE_CMD": current_torque,
            "SET_ME_1": default_set_me_1
        }
        steer_msg = packer.make_can_msg("STEERING_LKA", 0, values)
        steer_msg = can.Message(
            timestamp=time.time(),
            arbitration_id=steer_msg[0],
            is_extended_id=False,
            is_remote_frame=False,
            is_error_frame=False,
            channel=can_channel,
            dlc=5,
            data=steer_msg[2],
            is_fd=False,
            is_rx=False,
            bitrate_switch=False,
            error_state_indicator=False,
            check=False
        )
        print(db.decode_message(steer_msg.arbitration_id, steer_msg.data))
        steer_counter += 1
        steer_counter %= 64
        if torque_forward:
            current_torque += 0.1
        else:
            current_torque -= 0.1
        can_bus.send(steer_msg)
        try:
            print(db.decode_message(input_msg.arbitration_id, input_msg.data))
        except:
            pass
    except KeyboardInterrupt:
        exit()
    time.sleep(1/freq)
