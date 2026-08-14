import machine

from micropython import const


FREE_DTCM = const(0x20000000)
FREE_RAM = const(0x2207D000)

test_size = 1024 * 32
wcache = bytearray(test_size)
rcache = bytearray(test_size)

class AccessMode():
    BYTE = const(0)
    HALF_WORD = const(1)
    WORD = const(2)


def read_from_memory(addr: int, data: bytearray, am: int) -> None:
    i = 0
    if am == AccessMode.BYTE:
        while i < len(data):
            data[i] = machine.mem8[addr + i]
            i = i + 1
    elif am == AccessMode.HALF_WORD:
        while i < (len(data) // 2):
            offset = i * 2
            val = machine.mem16[addr + offset]
            data[offset] = val & 0xFF
            data[offset + 1] = (val >> 8) & 0xFF
            i = i + 1
    elif am == AccessMode.WORD:
        while i < (len(data) // 4):
            offset = i * 4
            val = machine.mem32[addr + offset]
            data[offset] = val & 0xFF
            data[offset + 1] = (val >> 8) & 0xFF
            data[offset + 2] = (val >> 16) & 0xFF
            data[offset + 3] = (val >> 24) & 0xFF
            i = i + 1


def write_to_memory(addr: int, data: bytearray, am: int) -> None:
    i = 0
    if am == AccessMode.BYTE:
        while i < len(data):
            machine.mem8[addr + i] = data[i]
            i = i + 1
    elif am == AccessMode.HALF_WORD:
        while i < (len(data) // 2):
            offset = i * 2
            val = data[offset] | (data[offset + 1] << 8)
            machine.mem16[addr + offset] = val
            i = i + 1
    elif am == AccessMode.WORD:
        while i < (len(data) // 4):
            offset = i * 4
            val = data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16) | (data[offset + 3] << 24)
            machine.mem32[addr + offset] = val
            i = i + 1
    else:
        print("Unknown access mode")


if __name__ == "__main__":
    i = 0
    while i < test_size:
        wcache[i] = i
        i = i + 1
    write_to_memory(FREE_DTCM, wcache, AccessMode.BYTE)
    read_from_memory(FREE_DTCM, rcache, AccessMode.BYTE)
    i = 0
    while i < test_size:
        if rcache[i] != wcache[i]:
            print("RW Compare failed with machine.mem8")
            print("target address: 0x%X" % FREE_DTCM)
            print("failed at: %d. W[%d], R[%d]" % (i, wcache[i], rcache[i]))
            break
        i = i + 1
    else:
        print("RW Compare with machine.mem8 at 0x%X PASS" % FREE_DTCM)
    write_to_memory(FREE_RAM, wcache, AccessMode.BYTE)
    read_from_memory(FREE_RAM, rcache, AccessMode.BYTE)
    i = 0
    while i < test_size:
        if rcache[i] != wcache[i]:
            print("RW Compare failed with machine.mem8")
            print("target address: 0x%X" % FREE_RAM)
            print("failed at: %d. W[%d], R[%d]" % (i, wcache[i], rcache[i]))
            break
        i = i + 1
    else:
        print("RW Compare with machine.mem8 at 0x%X PASS" % FREE_RAM)

    i = 0
    while i < test_size:
        val = i * 2 % 16384
        wcache[i] = val & 0xFF
        wcache[i + 1] = (val >> 8) & 0xFF
        i = i + 2
    write_to_memory(FREE_DTCM, wcache, AccessMode.HALF_WORD)
    read_from_memory(FREE_DTCM, rcache, AccessMode.HALF_WORD)
    i = 0
    while i < test_size:
        if rcache[i] != wcache[i]:
            print("RW Compare failed with machine.mem16")
            print("target address: 0x%X" % FREE_DTCM)
            val_w = wcache[i] | (wcache[i + 1] << 8)
            val_r = rcache[i] | (rcache[i + 1] << 8)
            print("failed at: %d. W[%d], R[%d]" % (i, val_w, val_r))
            break
        i = i + 1
    else:
        print("RW Compare with machine.mem16 at 0x%X PASS" % FREE_DTCM)
    write_to_memory(FREE_RAM, wcache, AccessMode.HALF_WORD)
    read_from_memory(FREE_RAM, rcache, AccessMode.HALF_WORD)
    i = 0
    while i < test_size:
        if rcache[i] != wcache[i]:
            print("RW Compare failed with machine.mem16")
            print("target address: 0x%X" % FREE_RAM)
            val_w = wcache[i] | (wcache[i + 1] << 8)
            val_r = rcache[i] | (rcache[i + 1] << 8)
            print("failed at: %d. W[%d], R[%d]" % (i, val_w, val_r))
            break
        i = i + 1
    else:
        print("RW Compare with machine.mem16 at 0x%X PASS" % FREE_RAM)

    i = 0
    while i < test_size:
        val = i * 3
        wcache[i] = val & 0xFF
        wcache[i + 1] = (val >> 8) & 0xFF
        wcache[i + 2] = (val >> 16) & 0xFF
        wcache[i + 3] = (val >> 24) & 0xFF
        i = i + 4
    write_to_memory(FREE_DTCM, wcache, AccessMode.WORD)
    read_from_memory(FREE_DTCM, rcache, AccessMode.WORD)
    i = 0
    while i < test_size:
        if rcache[i] != wcache[i]:
            print("RW Compare failed with machine.mem32")
            print("target address: 0x%X" % FREE_DTCM)
            val_w = wcache[i] | (wcache[i + 1] << 8) | (wcache[i + 2] << 16) | (wcache[i + 3] << 24)
            val_r = rcache[i] | (rcache[i + 1] << 8) | (rcache[i + 2] << 16) | (rcache[i + 3] << 24)
            print("failed at: %d. W[%d], R[%d]" % (i, val_w, val_r))
            break
        i = i + 1
    else:
        print("RW Compare with machine.mem32 at 0x%X PASS" % FREE_DTCM)
    write_to_memory(FREE_RAM, wcache, AccessMode.WORD)
    read_from_memory(FREE_RAM, rcache, AccessMode.WORD)
    i = 0
    while i < test_size:
        if rcache[i] != wcache[i]:
            print("RW Compare failed with machine.mem32")
            print("target address: 0x%X" % FREE_RAM)
            val_w = wcache[i] | (wcache[i + 1] << 8) | (wcache[i + 2] << 16) | (wcache[i + 3] << 24)
            val_r = rcache[i] | (rcache[i + 1] << 8) | (rcache[i + 2] << 16) | (rcache[i + 3] << 24)
            print("failed at: %d. W[%d], R[%d]" % (i, val_w, val_r))
            break
        i = i + 1
    else:
        print("RW Compare with machine.mem32 at 0x%X PASS" % FREE_RAM)
