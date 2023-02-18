import can
import time

def calc_checksum(can_msg):
    checksum = sum(bytearray([(can_msg.arbitration_id >> 8) & 0xFF, can_msg.arbitration_id & 0xFF, can_msg.dlc]) + can_msg.data[:-1])
    return checksum & 0xFF

can_bus = can.interface.Bus('can0', bustype='socketcan')
counter = 2000

while True:
    can_msg = can.Message(arbitration_id=740, is_extended_id=True, dlc=5, data=bytearray([counter, 5, 0, 80, 0]))
    can_msg = can.Message(arbitration_id=740, is_extended_id=True, dlc=5, data=bytearray([counter, 5, 0, 80, calc_checksum(can_msg)]))
    input_msg = can_bus.recv()
    print(input_msg)
    can_bus.send(can_msg)
    print("Sent")
    time.sleep(1)
    counter += 1
    if counter == 256:
        counter = 80
