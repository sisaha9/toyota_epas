import cantools
import can
import multiprocessing
import time
from pathlib import Path

class ToyotaInterface():
    def __init__(self, dbc_fp, can_interface, debug, read_hz, write_hz):
        self.db = cantools.database.load_file(dbc_fp)
        self.can_bus = can.interface.Bus(can_interface, bustype='socketcan')
        self.debug = debug
        self.read_pause = 1/read_hz
        self.write_pause = 1/write_hz
        self.steer_counter = 0
        self.static_commands = [
            (0x1C4, 8, b'\x05\xea\x1b\x08\x00\x00\xc0\x9f'),
            (0x4CB, 8, b'f\x06\x08\n\x02\x00\x00\x00'),
            (0x7A1, 8, b'\x02\x13\x81')
        ]
        self.send_steer_torque_command = {
            'COUNTER': 0,
            'SET_ME_1': 1,
            'STEER_REQUEST': 1,
            'STEER_TORQUE_CMD': 1,
            'LKA_STATE': 1,
            'CHECKSUM': 0
        }
        self.send_wheel_speeds_command = {
            'WHEEL_SPEED_FR': 67.67,
            'WHEEL_SPEED_FL': 67.67,
            'WHEEL_SPEED_RR': 67.67,
            'WHEEL_SPEED_RL': 67.67,
        }
        self.send_steer_sensor_command = {
            "STEER_ANGLE": 0,
            "STEER_FRACTION": 0,
            "STEER_RATE": 0,
        }
        self.send_speed_command = {
            "ENCODER": 0,
            "SPEED": 250,
            "CHECKSUM": 0,
        }
        self.send_brake_command = {
            "BRAKE_PRESSURE": 0,
            "BRAKE_POSITION": 0,
            "BRAKE_PRESSED": 0
        }
        self.send_brake_2_command = {
            "BRAKE_PRESSED": 0
        }
        self.start_time = time.time()
    
    def start(self):
        self.unrecognized_ids = []
        read_thread = multiprocessing.Process(target=self.read_can_messages, name = "CAN Reader")
        read_thread.start()
        write_thread = multiprocessing.Process(target=self.write_can_messages, name = "CAN Writer")
        write_thread.start()
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Keyboard interrupt detected. Stopping the threads...")
            read_thread.terminate()
            write_thread.terminate()
            if self.debug:
                print(set(self.unrecognized_ids))
    
    def write_can_messages(self):
        while True:
            try:
                for static_command in self.static_commands:
                    if time.time() - self.start_time < 20 and int(static_command[0]) == 1953:
                        continue
                    static_msg = can.Message(timestamp=time.time(), arbitration_id=int(static_command[0]), is_extended_id=False, dlc=static_command[1], data=bytearray(static_command[2]))
                    self.can_bus.send(static_msg)
    
                wheel_speeds_send_msg = self.db.get_message_by_name('WHEEL_SPEEDS')
                steer_sensor_send_msg = self.db.get_message_by_name('STEER_ANGLE_SENSOR')
                speed_send_msg = self.db.get_message_by_name('SPEED')
                steer_torque_send_msg = self.db.get_message_by_name('STEERING_LKA')
                brake_module_send_msg = self.db.get_message_by_name('BRAKE_MODULE')
                brake_2_send_msg = self.db.get_message_by_name("BRAKE_2")

                self.send_steer_torque_command['COUNTER'] = self.steer_counter

                wheel_speeds_cmd = wheel_speeds_send_msg.encode(self.send_wheel_speeds_command)
                steer_sensor_cmd = steer_sensor_send_msg.encode(self.send_steer_sensor_command)
                speed_cmd = speed_send_msg.encode(self.send_speed_command)
                brake_module_cmd = brake_module_send_msg.encode(self.send_brake_command)
                brake_2_cmd = brake_2_send_msg.encode(self.send_brake_2_command)
                steer_torque_cmd = steer_torque_send_msg.encode(self.send_steer_torque_command)

                wheel_speeds_msg = can.Message(timestamp=time.time(), arbitration_id=wheel_speeds_send_msg.frame_id, data=wheel_speeds_cmd)
                steer_sensor_msg = can.Message(timestamp=time.time(), arbitration_id=steer_sensor_send_msg.frame_id, data=steer_sensor_cmd)
                speed_msg = can.Message(timestamp=time.time(), arbitration_id=speed_send_msg.frame_id, data=speed_cmd)
                brake_module_msg = can.Message(timestamp=time.time(), arbitration_id=brake_module_send_msg.frame_id, data=brake_module_cmd)
                brake_2_msg = can.Message(timestamp=time.time(), arbitration_id=brake_2_send_msg.frame_id, data=brake_2_cmd)
                steer_torque_msg = can.Message(timestamp=time.time(), arbitration_id=steer_torque_send_msg.frame_id, data=steer_torque_cmd)

                self.send_speed_command['CHECKSUM'] = self.calculate_toyota_checksum(speed_msg)
                self.send_steer_torque_command['CHECKSUM'] = self.calculate_toyota_checksum(steer_torque_msg)
                
                speed_cmd = speed_send_msg.encode(self.send_speed_command)
                steer_torque_cmd = steer_torque_send_msg.encode(self.send_steer_torque_command)
                speed_msg = can.Message(timestamp=time.time(), arbitration_id=speed_send_msg.frame_id, data=speed_cmd)
                steer_torque_msg = can.Message(timestamp=time.time(), arbitration_id=steer_torque_send_msg.frame_id, data=steer_torque_cmd)
                
                # print(steer_sensor_msg)
                self.can_bus.send(brake_module_msg)
                self.can_bus.send(brake_2_msg)
                self.can_bus.send(wheel_speeds_msg)
                self.can_bus.send(steer_sensor_msg)
                self.can_bus.send(speed_msg)
                self.can_bus.send(steer_torque_msg)

                # print(self.db.decode_message(steer_torque_msg.arbitration_id, steer_torque_msg.data))
                self.steer_counter += 1
                self.steer_counter %= 63
                time.sleep(self.write_pause)
            except KeyboardInterrupt:
                print("Keyboard Interrupting Write")
    
    def calculate_toyota_checksum(self, input_msg):
        checksum = sum(bytearray([(input_msg.arbitration_id >> 8) & 0xFF, input_msg.arbitration_id & 0xFF, input_msg.dlc]) + input_msg.data[:-1])
        return checksum & 0xFF

    def read_can_messages(self):
        while True:
            try:
                steer_torque_sensor_msg = self.db.get_message_by_name('STEER_TORQUE_SENSOR')
                eps_status_msg = self.db.get_message_by_name('EPS_STATUS')
                input_msg = self.can_bus.recv()
                decoded_msg = self.db.decode_message(input_msg.arbitration_id, input_msg.data)
                # print(input_msg)
                # print(self.calculate_toyota_checksum(input_msg), input_msg.data[-1])
                # print(decoded_msg)
                time.sleep(self.read_pause)
            except KeyError as e:
                missing_frame_id = int(str(e).split("'")[0])
                if missing_frame_id == 1961:
                    print(input_msg)
                self.unrecognized_ids.append(missing_frame_id)
                if self.debug:
                    if len(self.unrecognized_ids) > 0:
                        print(len(set(self.unrecognized_ids)))
                        print(set(self.unrecognized_ids))
                    else:
                        print("No missing IDs yet")
            except KeyboardInterrupt:
                print("Keyboard Interrupting Read")
                return

if __name__ == "__main__":
    toyota_interface = ToyotaInterface(Path("toyotadbc.dbc"), "can0", debug=True, read_hz=84, write_hz=84)
    toyota_interface.start()
