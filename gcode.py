#!./venv/bin/python
import sys
import serial
from itertools import count
import time

# Maximum number of retries for safe commands
MAX_RETRIES_SAFE = 3
# Delay (in seconds) after encountering an error before retrying
ERROR_RETRY_DELAY = 0.5
# TIMEOUT VALUE
TIMEOUT = 0.2
# ABSOLUTE MAX Loop count
MAX_TIMEOUTS = int(2 / TIMEOUT)
# Retry enabled commands
SAFE_COMMANDS = ["G0", "M5", "M9", "M30", "G28", "G53"]
# length of the command queue waiting for "ok\r\n"
BUFFER_SIZE = 10
cmd_buffer = []
replay_buffer = []


def send_gcode_and_wait(ser, gcode_command, wait_for_ok=True, retries=0, expects=3):
    # Send the G-code command
    short_command = len(gcode_command) == 1
    gcode_command = gcode_command.encode() + b"\r\n"
    ser.write(gcode_command)
    cmd_buffer.append(gcode_command)

    response = b""

    if len(cmd_buffer) > BUFFER_SIZE:
        loopcount = count()

        end_beacon = b"ok\r\nok\r\n" if short_command else b"ok\r\n"
        while not response.endswith(end_beacon):
            response += ser.read(expects)

            if b"error" in response:
                for i, resp in enumerate(response.split(b"\r\n")):
                    if resp == b"ok":
                        cmd_buffer.pop(0)
                    elif resp.startswith(b"error"):
                        replay_buffer.append(cmd_buffer.copy())
            if next(loopcount) > MAX_TIMEOUTS:
                break

    cmd_buffer[0 : response.count(b"ok")] = []
    print(gcode_command, response)
    return response


def gcode_iterator(fd):
    for line in fd:
        dx = line.find(";")  # strip comments
        if dx >= 0:
            line = line[:dx]
        gcode_command = line.strip()
        if not gcode_command:
            continue
        while replay_buffer:
            yield replay_buffer.pop(0)
        yield gcode_command


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <gcode_filename> <serial_device>")
        return

    try:
        gcode_filename = sys.argv[1]
        serial_device = sys.argv[2]

        # Auto-detect and open the USB-serial device
        ser = serial.Serial(timeout=0.1)
        ser.baudrate = 115200  # Set the baud rate according to your device
        ser.port = serial_device
        ser.open()
        # start fresh
        ser.read(100)
        # Send the ~ command before starting engraving
        send_gcode_and_wait(ser, "~", retries=MAX_RETRIES_SAFE)  # Retry the "~" command

        # Open the G-code file
        with open(gcode_filename, "r") as file:
            for gcode_command in gcode_iterator(file):
                if any(gcode_command.startswith(cmd) for cmd in SAFE_COMMANDS):
                    send_gcode_and_wait(ser, gcode_command, retries=MAX_RETRIES_SAFE)
                else:
                    send_gcode_and_wait(ser, gcode_command)

        ser.close()

    except Exception as e:
        print("An error occurred:", e)


if __name__ == "__main__":
    main()
