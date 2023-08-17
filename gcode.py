#!./venv/bin/python
import sys
import serial
from itertools import count
import time

# TIMEOUT VALUE
TIMEOUT = 0.2
# ABSOLUTE MAX Loop count
MAX_TIMEOUTS = int(2 / TIMEOUT)
# length of the command queue waiting for "ok\r\n"
BUFFER_SIZE = 10
BUFFER_FULL_PAUSE_DURATION = 0.01

commands_buffer = []
commands_expected_ack = []
missed_commands_list = []


def send_gcode_and_wait(ser, gcode_command, expects=3):
    """Add `gcode_command` to the buffer and send it.
    `expects` tells the number of expected "ok" after sending `gcode_command`
    If the buffer is full, waits a bit and read the responses to mark aknowledged commands and pop them from the buffer.
    On error, fills the replay_buffer with the gcode commands which occurred after the error.
    If you see errors, try increasing `BUFFER_FULL_DELAY` or decreasing `BUFFER_SIZE`
    """
    # log the command in the buffer
    commands_buffer.append(gcode_command)
    # records how many "ok" are expected
    commands_expected_ack.append(2 if len(gcode_command) == 1 else 1)
    gcode_command = gcode_command.encode() + b"\r\n"
    ser.write(gcode_command)

    response = b""

    if len(commands_buffer) > BUFFER_SIZE:
        time.sleep(BUFFER_FULL_PAUSE_DURATION)
        loopcount = count()

        end_beacon = b"ok\r\n" * commands_expected_ack[-1]
        while not response.endswith(end_beacon):
            response += ser.read(expects)

            if b"error" in response:
                time.sleep(BUFFER_FULL_PAUSE_DURATION)
                print(response, commands_buffer, missed_commands_list)
                for resp in response.split(b"\r\n"):
                    if resp == b"ok":
                        commands_buffer.pop(0)
                        commands_expected_ack.pop(0)
                    elif resp.startswith(b"error"):
                        missed_commands_list.extend(commands_buffer.copy())
                        commands_buffer.clear()
                        commands_expected_ack.clear()
                        ser.read(100)  # flush
                        ser.flush()
                        return response
            if next(loopcount) > MAX_TIMEOUTS:
                break

    commands_buffer[0 : response.count(b"ok")] = []
    # print(f"{gcode_command}")
    return response


def gcode_iterator(fobj):
    """Iterates over the lines of fobj unless the `replay_buffer` isn't empty, then use it in priority"""
    for line in fobj:
        dx = line.find(";")  # strip comments
        if dx >= 0:
            line = line[:dx]
        gcode_command = line.strip()
        if not gcode_command:
            continue
        while missed_commands_list:
            yield missed_commands_list.pop(0)
        yield gcode_command


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <gcode_filename> <serial_device>")
        return

    gcode_filename = sys.argv[1]
    serial_device = sys.argv[2]

    # Auto-detect and open the USB-serial device
    ser = serial.Serial(timeout=TIMEOUT)
    ser.baudrate = 115200  # Set the baud rate according to your device
    ser.port = serial_device
    ser.open()
    # start fresh
    ser.flushInput()
    ser.read(100)
    # Send the ~ command before starting engraving
    send_gcode_and_wait(ser, "~")

    # Open the G-code file
    with open(gcode_filename, "r", encoding="utf-8") as file:
        for gcode_command in gcode_iterator(file):
            send_gcode_and_wait(ser, gcode_command)

    ser.close()


if __name__ == "__main__":
    main()
