import sys
import serial
import time

# Maximum number of retries for safe commands
MAX_RETRIES_SAFE = 3
# Delay (in seconds) after encountering an error before retrying
ERROR_RETRY_DELAY = 0.5


def send_gcode_and_wait(ser, gcode_command, wait_for_ok=True, retries=0):
    # Send the G-code command
    ser.write((gcode_command + "\r\n").encode())
    ser.flush()

    response = b""
    while not response.endswith(b"ok\r\n"):
        response += ser.read()

        if b"error" in response:
            print(f"Error response: {response.decode()}")
            if retries < MAX_RETRIES_SAFE:
                print("Retrying...")
                time.sleep(ERROR_RETRY_DELAY)  # Add a delay before retrying
                return send_gcode_and_wait(ser, gcode_command, wait_for_ok, retries + 1)
            else:
                print("Max retries reached. Aborting.")
                raise SystemExit()

    return response


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <gcode_filename> <serial_device>")
        return

    try:
        gcode_filename = sys.argv[1]
        serial_device = sys.argv[2]

        # Auto-detect and open the USB-serial device
        ser = serial.Serial()
        ser.baudrate = 115200  # Set the baud rate according to your device
        ser.port = serial_device
        ser.open()
        # Send the ~ command before starting engraving
        send_gcode_and_wait(ser, "~", retries=MAX_RETRIES_SAFE)  # Retry the "~" command

        # Open the G-code file
        with open(gcode_filename, "r") as file:
            for line in file:
                dx = line.find(";")  # strip comments
                if dx >= 0:
                    line = line[:dx]
                gcode_command = line.strip()
                if not gcode_command:
                    continue

                # Retry safe commands
                safe_commands = ["M5", "M9", "M30", "G28", "G53"]
                if any(gcode_command.startswith(cmd) for cmd in safe_commands):
                    send_gcode_and_wait(ser, gcode_command, retries=MAX_RETRIES_SAFE)
                else:
                    send_gcode_and_wait(ser, gcode_command)

        # Close the serial connection
        ser.close()

    except Exception as e:
        print("An error occurred:", e)


if __name__ == "__main__":
    main()
