import machine


if __name__ == '__main__':
    backup_a = machine.mem_backup()
    backup_b = machine.mem_backup(0)
    try:
        backup_c = machine.mem_backup(1)
    except ValueError:
        print("Get expect exception: ValueError, because these is only one backup memory")
    except Exception as e:
        print("Unexpected exception: ", e)

    print("backup_a length: %d" % len(backup_a))
    print("backup_b length: %d" % len(backup_b))

    if backup_a[0] == 0x00:
        wcache = list()
        for i in range(0, len(backup_a)):
            wcache.append(int(i * 4))
        for i in range(1, len(backup_a)):
            backup_a[i] = wcache[i - 1]
        for i in range(1, len(backup_b)):
            if backup_b[i] != wcache[i - 1]:
                print("WR compare failed before soft reset at %d" % i)
                print("write: %d, read: %d" % (wcache[i - 1], backup_b[i]))
                break
        else:
            backup_a[0] = 0x01
            print("WR compare PASS before soft reset")
            print("Please exec soft reset")
    else:
        wcache = list()
        for i in range(0, len(backup_a)):
            wcache.append(int(i * 4))
        for i in range(1, len(backup_b)):
            if backup_b[i] != wcache[i - 1]:
                print("WR compare failed after soft reset at %d" % i)
                print("write: %d, read: %d" % (wcache[i - 1], backup_b[i]))
                break
        else:
            backup_a[0] = 0x00
            print("WR compare PASS after soft reset")
            print("You can exec soft reset, then will rewrite backup memory")

