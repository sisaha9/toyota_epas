from pynput import keyboard
import time

def on_press(key):
    try:
        print(f"{key.char} was pressed")
    except AttributeError:
        print(f"{key} was special pressed")

listener = keyboard.Listener(on_press=on_press)
listener.start()
counter = 0
try:
    while True:
        # if counter % 10000000 == 0:
        print('Hello World')
        counter += 1
        time.sleep(1)
except KeyboardInterrupt:
    pass