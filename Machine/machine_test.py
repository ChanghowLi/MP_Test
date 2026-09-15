import machine


BACKUP_MARKER = 0x52413850
BACKUP_SAVE_FILE = "_machine_backup_test.bin"


def print_result(name, passed, detail=""):
    state = "PASS" if passed else "FAIL"
    if detail:
        print("[{}] {}: {}".format(state, name, detail))
    else:
        print("[{}] {}".format(state, name))
    return passed


def expect_exception(name, exception_types, function):
    try:
        function()
    except exception_types as exc:
        return print_result(name, True, "捕获预期异常 {}: {}".format(type(exc).__name__, exc))
    except Exception as exc:
        return print_result(name, False, "异常类型错误 {}: {}".format(type(exc).__name__, exc))
    return print_result(name, False, "调用未抛出异常")


def basic_test():
    print("\n检查 freq()、unique_id()、rng()")
    print("按回车开始")
    input()
    passed = 0
    total = 0

    try:
        value = machine.freq()
        total += 1
        passed += print_result("machine.freq", isinstance(value, int) and value > 0, "返回值={} Hz".format(value))
    except Exception as exc:
        total += 1
        print_result("machine.freq", False, "{}: {}".format(type(exc).__name__, exc))

    try:
        first = machine.unique_id()
        second = machine.unique_id()
        ok = isinstance(first, bytes) and len(first) > 0 and any(first) and first == second
        total += 1
        passed += print_result("machine.unique_id", ok, "长度={}，值={}".format(len(first), first.hex()))
    except Exception as exc:
        total += 1
        print_result("machine.unique_id", False, "{}: {}".format(type(exc).__name__, exc))

    try:
        values = tuple(machine.rng() for _ in range(8))
        ok = all(isinstance(value, int) and 0 <= value <= 0xFFFFFF for value in values) and len(set(values)) > 1
        total += 1
        passed += print_result("machine.rng", ok, "8次结果={}".format(values))
    except Exception as exc:
        total += 1
        print_result("machine.rng", False, "{}: {}".format(type(exc).__name__, exc))

    print("基础测试完成：{}/{} 项通过。".format(passed, total))


def memory_test():
    print("\n使用 machine.mem 访问 RAM。访问地址位于 MicroPython heap")
    print("按回车开始。")
    input()
    try:
        import uctypes
    except ImportError as exc:
        print_result("导入 uctypes", False, str(exc))
        return

    buf = bytearray(16)
    base = uctypes.addressof(buf)
    address = (base + 3) & ~3
    original = bytes(buf)
    passed = 0
    try:
        machine.mem8[address] = 0xA5
        passed += print_result("machine.mem8", machine.mem8[address] == 0xA5, "地址=0x{:08x}".format(address))
        machine.mem16[address] = 0x5AA5
        passed += print_result("machine.mem16", machine.mem16[address] == 0x5AA5, "地址=0x{:08x}".format(address))
        machine.mem32[address] = 0xA55A1234
        read32 = machine.mem32[address]
        normalized32 = read32 & 0xFFFFFFFF
        passed += print_result("machine.mem32", normalized32 == 0xA55A1234,
                               "地址=0x{:08x} 原始值={} 32位值=0x{:08x}".format(address, read32, normalized32))
    except Exception as exc:
        print("[FAIL] 内存访问异常 {}: {}".format(type(exc).__name__, exc))
    finally:
        for index, value in enumerate(original):
            buf[index] = value
    print("内存访问测试完成：{}/3 项通过。".format(passed))


def irq_control_test():
    print("\n将关闭全局中断并检查状态，再恢复中断并确认恢复后的状态。")
    print("按回车执行。")
    input()
    original_state = None
    try:
        print("调用: original_state = machine.disable_irq()")
        original_state = machine.disable_irq()
        print("调用: disabled_state = machine.disable_irq()")
        disabled_state = machine.disable_irq()
        print("调用: machine.enable_irq(original_state)")
        machine.enable_irq(original_state)
        print("调用: restored_state = machine.disable_irq()")
        restored_state = machine.disable_irq()
        print("调用: machine.enable_irq(restored_state)")
        machine.enable_irq(restored_state)
        disable_passed = original_state == 0 and disabled_state == 1
        enable_passed = restored_state == original_state
        disable_detail = "关闭前状态={}，关闭后状态={}".format(original_state, disabled_state)
        enable_detail = "恢复后状态={}".format(restored_state)
        original_state = None
        print_result("machine.disable_irq", disable_passed, disable_detail)
        print_result("machine.enable_irq", enable_passed, enable_detail)
    except Exception as exc:
        print_result("disable_irq/enable_irq", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        if original_state is not None:
            machine.enable_irq(original_state)


def idle_test():
    print("\n执行 machine.idle() 等待中断，当前使用 FreeRTOS，因此 SysTick 中断将使其很快返回")
    print("按回车执行")
    input()
    try:
        print("调用: machine.idle()")
        machine.idle()
        print_result("machine.idle", True, "已从等待中断状态返回")
    except Exception as exc:
        print_result("machine.idle", False, "{}: {}".format(type(exc).__name__, exc))


def main():
    while True:
        print("\n1. machine 基础测试")
        print("2. machine.mem 测试")
        print("3. 全局中断开关测试")
        print("4. idle 测试")
        print("q. 退出")
        try:
            choice = input("下一步请输入选项: ").strip().lower()
            if choice == "1":
                basic_test()
            elif choice == "2":
                memory_test()
            elif choice == "3":
                irq_control_test()
            elif choice == "4":
                idle_test()
            elif choice == "q":
                print("测试结束。")
                return
            else:
                print("无效选项，请按菜单重新输入。")
        except KeyboardInterrupt:
            print("\n输入或测试被中断，已返回主菜单。")


if __name__ == "__main__":
    main()
