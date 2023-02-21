import can
import cantools
import multiprocessing
import time
from pynput.keyboard import Key, Listener

class ToyotaInterface():
    def __init__(self, can_interface='can0'):
        self.db = cantools.database.load_file('toyotadbc.dbc')
        self.can_interface = can_interface
        self.can_bus = can.interface.Bus(self.can_interface, bustype='socketcan')

        # Variables for button presses
        self.flag1 = False
        self.flag2 = False
        self.flag3 = False
        self.flag4 = False

        # CAN Message Lengths
        self.len2 = 3
        self.len3 = 4
        self.len4 = 3
        self.len5 = 3
        self.len6 = 4
        self.len7 = 71

        #CAN Addresses and Data
        self.array_1 = [0x423]
        self.array_2 = [0x367, 0x394, 0x3d3]
        self.array_3 = [0x228, 0x351, 0x3bb, 0xba]
        self.array_4 = [0x262, 0x2e4, 0x3e6]
        self.array_5 = [0x1aa, 0x384, 0x386]
        self.array_6 = [0x283, 0x365, 0x366, 0x3e7]
        self.array_7 = [0x24, 0x25, 0xaa, 0xb4, 0x1c4, 0x1d0, 0x1d2, 0x1d3, 0x223, 0x224, 0x260, 0x2c1, 0x320, 0x343, 0x344, 0x380, 0x381, 0x389, 0x38f, 0x399, 0x3a5, 0x3b0, 0x3b1, 0x3b7, 0x3bc, 0x3e8, 0x3e9, 0x3f9, 0x411, 0x412, 0x413, 0x414, 0x420, 0x45a, 0x489, 0x48a, 0x48b, 0x4ac, 0x4cb, 0x4d3, 0x4ff, 0x610, 0x611, 0x614, 0x615, 0x619, 0x61a, 0x620, 0x621, 0x622, 0x623, 0x624, 0x638, 0x63c, 0x63d, 0x640, 0x680, 0x6f3, 0x770, 0x778, 0x7c6, 0x7ce, 0x7e0, 0x7e1, 0x7e2, 0x7e3, 0x7e4, 0x7e5, 0x7e6, 0x7e7, 0x7e8]
        # self.array_1 = [0x423]
        # self.array_2 = [0x367, 0x394, 0x3d3]
        # self.array_3 = [0x351, 0x3bb, 0xba]
        # self.array_4 = [0x262, 0x2e4, 0x3e6]
        # self.array_5 = [0x1aa, 0x384, 0x386]
        # self.array_6 = [0x283, 0x365, 0x366, 0x3e7]
        # self.array_7 = [0x24, 0x25, 0x1c4, 0x1d0, 0x260, 0x2c1, 0x320, 0x343, 0x344, 0x380, 0x381, 0x389, 0x38f, 0x399, 0x3a5, 0x3b0, 0x3b1, 0x3b7, 0x3e8, 0x3e9, 0x3f9, 0x411, 0x412, 0x413, 0x414, 0x420, 0x45a, 0x489, 0x48a, 0x48b, 0x4ac, 0x4cb, 0x4d3, 0x4ff, 0x610, 0x611, 0x614, 0x615, 0x619, 0x61a, 0x620, 0x621, 0x622, 0x623, 0x624, 0x638, 0x63c, 0x63d, 0x640, 0x680, 0x6f3, 0x770, 0x778, 0x7c6, 0x7ce, 0x7e0, 0x7e1, 0x7e2, 0x7e3, 0x7e4, 0x7e5, 0x7e6, 0x7e7, 0x7e8]

        #0x1d2 byte 7, 1st 4 bits(!=0) = cruise_state
        #0x1d3 byte 2, bit 1 (1) = main_on
        #0xaa = wheel speed
        #0x3bc = GEAR_PACKET
        #0xb4 = SPEED


        self.data1 = [0x00]
        self.data2 = [0x0, 0x0]
        self.data3 = [0x0, 0x0, 0x0, 0x0]
        self.data4 = [0x0, 0x0, 0x0, 0x0, 0x0]
        self.data5 = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
        self.data6 = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
        self.data7 = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
        self.enable1 = [0xf8, 0x24, 0x02, 0xf8, 0x00, 0x01, 0x80, 0x72]
        self.enable2 = [0x00, 0xa8, 0x43, 0x10, 0xee, 0x00, 0x00, 0xc5]
        self.not_in_d = [0x0, 0x20, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]

        self.speed = 0
        self.program_exit = False

        self.counter = 0
        self.keyboard_listener = Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()
    
    def on_key_press(self, key):
        try:
            if key == Key.esc:
                self.keyboard_listener.stop()
                self.program_exit = True
            elif key.char == '1':
                self.flag1 = not self.flag1
            elif key.char == '2':
                self.flag2 = not self.flag2
            elif key.char == '3':
                self.flag3 = not self.flag3
            elif key.char == '4':
                self.flag4 = not self.flag4
        except AttributeError:
            print("Invalid key pressed. Ignoring")

    def start_interface(self):
        # read_thread = multiprocessing.Process(target=self.read_can, name = "CAN Reader")
        # read_thread.start()
        # write_thread = multiprocessing.Process(target=self.write_can, name = "CAN Writer")
        # write_thread.start()
        try:
            while True:
                self.read_can()
                self.write_can()
                if self.program_exit:
                    break
        except KeyboardInterrupt:
            print("Keyboard interrupt")
            # read_thread.terminate()
            # write_thread.terminate()
        exit()
    
    def read_can(self):
        input_msg = self.can_bus.recv()
        try:
            print(self.db.decode_message(input_msg.arbitration_id, input_msg.data))
        except KeyError:
            pass
        time.sleep(1/100)
    
    def send_standard_can_msg(self, id, dlc, data):
        self.can_bus.send(can.Message(int(id), is_extended_id=False, dlc=dlc, data=bytearray(data)))
    
    def send_steer_can_msg(self, id, dlc, data):
        msg = can.Message(int(id), is_extended_id=False, dlc=dlc, data=bytearray(data))
        msg.data[-1] = self.calculate_toyota_checksum(msg)
        self.can_bus.send(msg)
    
    def calculate_toyota_checksum(self, input_msg):
        checksum = sum(bytearray([(input_msg.arbitration_id >> 8) & 0xFF, input_msg.arbitration_id & 0xFF, input_msg.dlc]) + input_msg.data[:-1])
        return checksum & 0xFF
    
    def write_can(self):

        w2 = self.speed & 0xff
        w1 = self.speed >> 8
        wheelpot = [w1, w2, w1, w2, w1, w2, w1, w2]
        speedpak = [0x0, 0x0, 0x0, 0x0, w1, w2, 0x0]

        self.send_standard_can_msg(id=0x423, dlc=1, data=self.data1)
        for i in range(self.len2):
            time.sleep(1/1000)
            self.send_standard_can_msg(id=self.array_2[i], dlc=2, data=self.data2)
        for i in range(self.len3):
            time.sleep(1/1000)
            self.send_standard_can_msg(id=self.array_3[i], dlc=4, data=self.data3)
        for i in range(self.len4):
            time.sleep(1/1000)
            if self.array_4[i] == 0x2E4:
                self.steer_command = [self.counter, 0x05, 0x00, 0x80, 0xF0]
                self.send_steer_can_msg(id=self.array_4[i], dlc=5, data=self.steer_command)
                self.counter += 1
            else:
                self.send_standard_can_msg(id=self.array_4[i], dlc=5, data=self.data4)
        for i in range(self.len5):
            time.sleep(1/1000)
            self.send_standard_can_msg(id=self.array_5[i], dlc=6, data=self.data5)
        for i in range(self.len6):
            time.sleep(1/1000)
            self.send_standard_can_msg(id=self.array_6[i], dlc=7, data=self.data6)
        for i in range(self.len7):
            time.sleep(1/1000)
            self.send_standard_can_msg(id=self.array_7[i], dlc=8, data=self.data7)
            time.sleep(1/1000)
            self.send_standard_can_msg(id=0xaa, dlc=8, data=wheelpot)
            time.sleep(1/1000)
            self.send_standard_can_msg(id=0xb4, dlc=8, data=speedpak)
        
        if self.flag1:
            self.send_standard_can_msg(id=0x1d1, dlc=8, data=self.enable1)
            print("Enabled!")
        else:
            self.send_standard_can_msg(id=0x1d1, dlc=8, data=self.data7)
        
        if self.flag2 and self.flag1:
            self.send_standard_can_msg(id=0x1d2, dlc=8, data=self.enable2)
            print("Engaged!")
        else:
            self.send_standard_can_msg(id=0x1d2, dlc=8, data=self.data7)
        
        if self.flag3:
            self.send_standard_can_msg(id=0x3bc, dlc=8, data=self.data7)
            print("In Drive!")
        else:
            self.send_standard_can_msg(id=0x3bc, dlc=8, data=self.not_in_d)
        time.sleep(1/100)

toyota_interface = ToyotaInterface()
toyota_interface.start_interface()