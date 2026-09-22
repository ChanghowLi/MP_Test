from machine import I2C
import time


I2C_ID = 1
I2C_FREQ = 400000

EEPROM_ADDR = 0x50
EEPROM_SIZE = 256
WRITE_DELAY_MS = 10


def write_full_chip(i2c, sequential):
    for addr in range(EEPROM_SIZE):
        value = addr & 0xFF if sequential else 0xFF
        i2c.writeto_mem(EEPROM_ADDR, addr, bytes([value]))
        time.sleep_ms(WRITE_DELAY_MS)


def verify_full_chip(i2c, sequential):
    for addr in range(EEPROM_SIZE):
        expected = addr & 0xFF if sequential else 0xFF
        actual = i2c.readfrom_mem(EEPROM_ADDR, addr, 1)[0]

        if actual != expected:
            print(
                "VERIFY FAILED at 0x%02X: expected=0x%02X actual=0x%02X"
                % (addr, expected, actual)
            )
            return False

    return True


def run_test(i2c, name, sequential):
    print("\n%s" % name)
    print("Writing full chip 1 byte at a time...")
    write_full_chip(i2c, sequential)

    print("Reading back 1 byte at a time...")
    if not verify_full_chip(i2c, sequential):
        print("%s: FAIL" % name)
        return False

    print("%s: PASS" % name)
    return True


print("AT24C02 I2C test start")
print("I2C(%d), freq=%d, EEPROM=0x%02X" % (I2C_ID, I2C_FREQ, EEPROM_ADDR))

i2c = I2C(I2C_ID, freq=I2C_FREQ)

try:
    if run_test(i2c, "Test 1: full chip 0xFF", False):
        if run_test(i2c, "Test 2: full chip 0x00..0xFF", True):
            print("\nAT24C02 I2C test: PASS")
finally:
    i2c.deinit()
