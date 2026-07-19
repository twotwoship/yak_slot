import serial


PORT = "/dev/serial0"
BAUD_RATE = 9600
TEST_MESSAGE = b"SLOTGUARD_UART_TEST\n"


with serial.Serial(
    port=PORT,
    baudrate=BAUD_RATE,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
) as uart:
    uart.reset_input_buffer()

    uart.write(TEST_MESSAGE)
    uart.flush()

    received = uart.readline()


print(f"Sent     : {TEST_MESSAGE!r}")
print(f"Received : {received!r}")


if received == TEST_MESSAGE:
    print("UART loopback: PASS")
else:
    print("UART loopback: FAIL")
