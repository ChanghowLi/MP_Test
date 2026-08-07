import machine
import vfs


def test_wr():
    with open("/sd/test.txt", "w") as f:
        f.write("Hello from MicroPython\n")
    print("write done")

    with open("/sd/test.txt", "r") as f:
        content = f.read()
    print("content: ", content)
    pass


if __name__ == '__main__':
    sd = machine.SDCard()
    sd.init()

    buf = bytearray(512)
    sd.readblocks(0, buf)
    print("OEM/filesystem =", bytes(buf[3:11]))
    if buf.find(b'NTFS') != -1:
        print("Erase first sector")
        zero = bytearray(512)
        sd.writeblocks(0, zero)

    sd_vfs = vfs.VfsFat(sd)
    vfs.mount(sd_vfs, "/sd", mkfs=True)

    test_wr()
