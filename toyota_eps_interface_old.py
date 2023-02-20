import cantools
import can
import multiprocessing
import time
from pathlib import Path

class ToyotaInterface():
    def __init__(self, dbc_fp, can_interface, debug, read_hz, write_steer_hz, write_accel_hz, write_static_hz, write_ui_hz):
        self.db = cantools.database.load_file(dbc_fp)
        self.can_bus = can.interface.Bus(can_interface, bustype='socketcan')
        self.debug = debug
        self.read_pause = 1/read_hz
        self.write_steer_pause = 1/write_steer_hz
        self.write_accel_pause = 1/write_accel_hz
        self.write_static_pause = 1/write_static_hz
        self.write_ui_pause = 1/write_ui_hz
        self.steer_counter = 0
        self.static_counter = 0
        self.static_commands = [
            (0x128, 3, b'\xf4\x01\x90\x83\x00\x37'),
            (0x141, 2, b'\x00\x00\x00\x46'),
            (0x160, 7, b'\x00\x00\x08\x12\x01\x31\x9c\x51'),
            (0x161, 7, b'\x00\x1e\x00\x00\x00\x80\x07'),
            (0x283, 3, b'\x00\x00\x00\x00\x00\x00\x8c'),
            (0x2E6, 3, b'\xff\xf8\x00\x08\x7f\xe0\x00\x4e'),
            (0x2E7, 3, b'\xa8\x9c\x31\x9c\x00\x00\x00\x02'),
            (0x33E, 20, b'\x0f\xff\x26\x40\x00\x1f\x00'),
            (0x344, 5, b'\x00\x00\x01\x00\x00\x00\x00\x50'),
            (0x365, 20, b'\x00\x00\x00\x80\x03\x00\x08'),
            (0x366, 20, b'\x00\x00\x4d\x82\x40\x02\x00'),
            (0x470, 100, b'\x00\x00\x02\x7a'),
            (0x4CB, 100, b'\x0c\x00\x00\x00\x00\x00\x00\x00'),
        ]
        self.send_steer_torque_command = {
            'COUNTER': 0,
            'SET_ME_1': 1,
            'STEER_REQUEST': 1,
            'STEER_TORQUE_CMD': 1,
            'LKA_STATE': 1,
            'CHECKSUM': 0
        }
        self.send_accel_command = {
            'ACCEL_CMD': 1,
            'ALLOW_LONG_PRESS': 1,
            'ACC_MALFUNCTION': 0,
            'RADAR_DIRTY': 0,
            'DISTANCE': 0,
            'MINI_CAR': 1,
            'ACC_TYPE': 1,
            'CANCEL_REQ': 0,
            'ACC_CUT_IN': 0,
            'PERMIT_BRAKING': 1,
            'RELEASE_STANDSTILL': 1,
            'ITS_CONNECT_LEAD': 0,
            'ACCEL_CMD_ALT': 1,
            'CHECKSUM': 0
        }
        self.send_ui_command = {
            "TWO_BEEPS": 0,
            "LDA_ALERT": 0,
            "RIGHT_LINE": 2,
            "LEFT_LINE": 2,
            "BARRIERS": 0,
            # static signals
            "SET_ME_X02": 2,
            "SET_ME_X01": 1,
            "LKAS_STATUS": 1,
            "REPEATED_BEEPS": 0,
            "LANE_SWAY_FLD": 7,
            "LANE_SWAY_BUZZER": 0,
            "LANE_SWAY_WARNING": 0,
            "LDA_FRONT_CAMERA_BLOCKED": 0,
            "TAKE_CONTROL": 0,
            "LANE_SWAY_SENSITIVITY": 2,
            "LANE_SWAY_TOGGLE": 1,
            "LDA_ON_MESSAGE": 0,
            "LDA_SPEED_TOO_LOW": 0,
            "LDA_SA_TOGGLE": 1,
            "LDA_SENSITIVITY": 2,
            "LDA_UNAVAILABLE": 0,
            "LDA_MALFUNCTION": 0,
            "LDA_UNAVAILABLE_QUIET": 0,
            "ADJUSTING_CAMERA": 0,
            "LDW_EXIST": 1,
        }
    
    def start(self):
        self.unrecognized_ids = []
        read_thread = multiprocessing.Process(target=self.read_can_messages, name = "CAN Reader")
        read_thread.start()
        write_steer_thread = multiprocessing.Process(target=self.write_steer_can_messages, name = "CAN Steer Writer")
        write_accel_thread = multiprocessing.Process(target=self.write_accel_can_messages, name = "CAN Accel Writer")
        write_static_thread = multiprocessing.Process(target=self.write_static_can_messages, name = "CAN Static Writer")
        write_ui_thread = multiprocessing.Process(target=self.write_ui_can_messages, name = "CAN UI Writer")
        write_steer_thread.start()
        write_accel_thread.start()
        write_static_thread.start()
        write_ui_thread.start()
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Keyboard interrupt detected. Stopping the threads...")
            read_thread.terminate()
            write_steer_thread.terminate()
            write_accel_thread.terminate()
            write_static_thread.terminate()
            write_ui_thread.terminate()
            if self.debug:
                print(set(self.unrecognized_ids))
    
    def write_static_can_messages(self):
        while True:
            try:
                for static_command in self.static_commands:
                    if self.static_counter % static_command[1] == 0:
                        static_msg = can.Message(arbitration_id=int(static_command[0]), data=bytearray(static_command[2]))
                        self.can_bus.send(static_msg)
                self.static_counter += 1
                self.static_counter %= 2100
                time.sleep(self.write_static_pause)
            except KeyboardInterrupt:
                print("Keyboard Interrupting static Write")
    
    def write_accel_can_messages(self):
        while True:
            try:
                accel_send_msg = self.db.get_message_by_name('ACC_CONTROL')

                accel_cmd = accel_send_msg.encode(self.send_accel_command)

                accel_msg = can.Message(arbitration_id=accel_send_msg.frame_id, data=accel_cmd)

                self.send_accel_command['CHECKSUM'] = self.calculate_toyota_checksum(accel_msg)

                accel_cmd = accel_send_msg.encode(self.send_accel_command)
                accel_msg = can.Message(arbitration_id=accel_send_msg.frame_id, data=accel_cmd)

                self.can_bus.send(accel_msg)

                # print(self.db.decode_message(accel_msg.arbitration_id, accel_msg.data))

                time.sleep(self.write_accel_pause)
            except KeyboardInterrupt:
                print("Keyboard Interrupting accel Write")
    
    def write_steer_can_messages(self):
        while True:
            try:
                steer_torque_send_msg = self.db.get_message_by_name('STEERING_LKA')

                self.send_steer_torque_command['COUNTER'] = self.steer_counter

                steer_torque_cmd = steer_torque_send_msg.encode(self.send_steer_torque_command)

                steer_torque_msg = can.Message(arbitration_id=steer_torque_send_msg.frame_id, data=steer_torque_cmd)

                self.send_steer_torque_command['CHECKSUM'] = self.calculate_toyota_checksum(steer_torque_msg)

                steer_torque_cmd = steer_torque_send_msg.encode(self.send_steer_torque_command)
                steer_torque_msg = can.Message(arbitration_id=steer_torque_send_msg.frame_id, data=steer_torque_cmd)
                
                self.can_bus.send(steer_torque_msg)

                # print(self.db.decode_message(steer_torque_msg.arbitration_id, steer_torque_msg.data))
                self.steer_counter += 1
                self.steer_counter %= 63
                time.sleep(self.write_steer_pause)
            except KeyboardInterrupt:
                print("Keyboard Interrupting Steer Write")
    
    def write_ui_can_messages(self):
        while True:
            try:
                ui_send_msg = self.db.get_message_by_name('LKAS_HUD')

                ui_cmd = ui_send_msg.encode(self.send_ui_command)

                ui_msg = can.Message(arbitration_id=ui_send_msg.frame_id, data=ui_cmd)
                
                self.can_bus.send(ui_msg)

                # print(self.db.decode_message(steer_torque_msg.arbitration_id, steer_torque_msg.data))
                time.sleep(self.write_ui_pause)
            except KeyboardInterrupt:
                print("Keyboard Interrupting UI Write")
    
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
                # print(input_msg.data[-1])
                # print(self.calculate_toyota_checksum(input_msg), input_msg.data[-1])
                print(decoded_msg)
                time.sleep(self.read_pause)
            except KeyError as e:
                missing_frame_id = int(str(e).split("'")[0])
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
    toyota_interface = ToyotaInterface(Path("toyotadbc.dbc"), "can0", debug=False, read_hz=100, write_steer_hz=100, write_accel_hz=100, write_static_hz=100, write_ui_hz=1)
    toyota_interface.start()
