from machine import UART


UART_ID = 2
TIMEOUT_MS = 2000
TIMEOUT_CHAR_MS = 20
CHUNK_SIZE = 256
BASIC_DATA = b"0123456789ABCDEF"
BASIC_ROUNDS = 10
BAUDRATES = (229, 115200, 20_000_000)
SIZE_TESTS = (4, 16, 64)


def baudrate_name(baudrate):
    if baudrate % 1_000_000 == 0:
        return str(baudrate // 1_000_000) + " Mbps"
    return str(baudrate) + " bps"


def loopback_once(uart, tx):
    uart.write(tx)
    rx = uart.read(len(tx))
    uart.flush()
    return rx == tx


def test_size(uart, size_kb, tx):
    rounds = size_kb * 1024 // CHUNK_SIZE

    for _ in range(rounds):
        if not loopback_once(uart, tx):
            return False

    return True


def test_uart():
    print("=== UART loopback ===")
    tx = bytes([i & 0xff for i in range(CHUNK_SIZE)])

    for baudrate in BAUDRATES:
        print("---", baudrate_name(baudrate), "---")
        uart = None

        try:
            uart = UART(UART_ID, baudrate, timeout=TIMEOUT_MS, timeout_char=TIMEOUT_CHAR_MS)

            passed_count = 0
            last_error = None
            for _ in range(BASIC_ROUNDS):
                try:
                    if loopback_once(uart, BASIC_DATA):
                        passed_count += 1
                except Exception as exc:
                    last_error = exc

            basic_passed = passed_count == BASIC_ROUNDS
            result = "PASS" if basic_passed else "FAIL"
            print("16B", str(passed_count) + "/" + str(BASIC_ROUNDS), result, last_error if last_error is not None else "")

            if baudrate == 229:
                continue

            if not basic_passed:
                print("skip 4KB / 16KB / 64KB")
                continue

            for size_kb in SIZE_TESTS:
                rounds = size_kb * 1024 // CHUNK_SIZE
                label = str(size_kb) + "KB (256B x " + str(rounds) + ")"
                try:
                    result = "PASS" if test_size(uart, size_kb, tx) else "FAIL"
                    print(label, result)
                except Exception as exc:
                    print(label, "FAIL", exc)
        except Exception as exc:
            print("FAIL", exc)
        finally:
            if uart is not None:
                uart.deinit()


test_uart()
