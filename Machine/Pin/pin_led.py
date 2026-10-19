import time

from machine import Pin


def main():
    p110 = Pin("P110", Pin.OUT)
    p601 = Pin("P601", Pin.OUT)
    print("LED Flashing, Press Ctrl+C to exit")
    while True:
        p110.on()
        p601.off()
        time.sleep_ms(500)
        p110.off()
        p601.on()
        time.sleep_ms(500)


if __name__ == "__main__":
    main()
