"""Interactive tests for module-level machine APIs on CPKCOR_RA8P1."""

import os
import struct
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
    print("\n本测试会检查 freq()、unique_id()、rng()、reset_cause() 和 wake_reason()。")
    print("下一步：直接按回车开始，不需要接线。")
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

    try:
        value = machine.reset_cause()
        total += 1
        passed += print_result("machine.reset_cause", isinstance(value, int), "返回值={}".format(value))
    except Exception as exc:
        total += 1
        print_result("machine.reset_cause", False, "{}: {}".format(type(exc).__name__, exc))

    try:
        value = machine.wake_reason()
        total += 1
        passed += print_result("machine.wake_reason", value == machine.WAKE_UNKNOWN,
                               "期望WAKE_UNKNOWN={}，实际={}".format(machine.WAKE_UNKNOWN, value))
    except Exception as exc:
        total += 1
        print_result("machine.wake_reason", False, "{}: {}".format(type(exc).__name__, exc))

    print("基础测试完成：{}/{} 项通过。".format(passed, total))


def memory_test():
    print("\n本测试只访问专用 bytearray 的 RAM，不访问固定地址或外设寄存器。")
    print("下一步：直接按回车开始。")
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
    print("\n本测试会关闭全局中断并检查状态，再恢复中断并确认恢复后的状态。")
    print("下一步：直接按回车执行。")
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
    print("\nmachine.idle() 会执行一次等待中断，系统节拍等中断通常会使它很快返回。")
    print("下一步：直接按回车；若5秒仍未返回，请按 Ctrl-C。")
    input()
    try:
        print("调用: machine.idle()")
        machine.idle()
        print_result("machine.idle", True, "已从等待中断状态返回")
    except Exception as exc:
        print_result("machine.idle", False, "{}: {}".format(type(exc).__name__, exc))


def backup_write_and_soft_reset():
    print("\n此测试会写入 backup memory，然后执行软复位，当前REPL会中断。")
    print("下一步：输入 RESET 并回车确认；其它输入表示取消。")
    if input("确认输入: ").strip() != "RESET":
        print("已取消。")
        return
    try:
        os.stat(BACKUP_SAVE_FILE)
        print("[FAIL] 已存在 {}；请先选择“检查 backup 标记”完成或清理上一次测试。".format(BACKUP_SAVE_FILE))
        return
    except OSError:
        pass
    backup = machine.mem_backup()
    with open(BACKUP_SAVE_FILE, "wb") as file:
        file.write(struct.pack("<I", backup[0] & 0xFFFFFFFF))
    backup[0] = BACKUP_MARKER
    print("已保存原内容并写入标记。软复位后重新执行 import machine_test; machine_test.main()，选择复位测试，再选择检查标记。")
    machine.soft_reset()


def backup_check():
    try:
        with open(BACKUP_SAVE_FILE, "rb") as file:
            saved = file.read(4)
        if len(saved) != 4:
            raise ValueError("backup save file length is not 4")
        original = struct.unpack("<I", saved)[0]
        backup = machine.mem_backup(0)
        actual = backup[0] & 0xFFFFFFFF
        passed = actual == BACKUP_MARKER
        backup[0] = original
        os.remove(BACKUP_SAVE_FILE)
        print_result("mem_backup软复位保持", passed,
                     "读取值=0x{:08x}；原32位内容已恢复".format(actual))
    except Exception as exc:
        print_result("mem_backup软复位保持", False, "{}: {}".format(type(exc).__name__, exc))


def confirmed_reset(kind):
    description = "软复位" if kind == "soft" else "硬件复位"
    print("\n{}会立即中断当前REPL。".format(description))
    print("下一步：输入 RESET 并回车确认；其它输入表示取消。")
    if input("确认输入: ").strip() != "RESET":
        print("已取消。")
        return
    if kind == "soft":
        machine.soft_reset()
    else:
        machine.reset()


def reset_menu():
    while True:
        print("\n1. 查询 reset_cause")
        print("2. 执行 soft_reset")
        print("3. 执行硬件 reset")
        print("4. 写 backup 标记并 soft_reset")
        print("5. 检查 backup 标记")
        print("q. 返回主菜单")
        choice = input("下一步请输入选项: ").strip().lower()
        if choice == "1":
            print("reset_cause={}".format(machine.reset_cause()))
        elif choice == "2":
            confirmed_reset("soft")
        elif choice == "3":
            confirmed_reset("hard")
        elif choice == "4":
            backup_write_and_soft_reset()
        elif choice == "5":
            backup_check()
        elif choice == "q":
            return
        else:
            print("无效选项，请按菜单重新输入。")


def main():
    while True:
        print("\n1. machine基础测试")
        print("2. mem8/mem16/mem32安全RAM测试")
        print("3. 全局中断开关测试")
        print("4. idle测试")
        print("5. 复位与mem_backup测试")
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
            elif choice == "5":
                reset_menu()
            elif choice == "q":
                print("测试结束。")
                return
            else:
                print("无效选项，请按菜单重新输入。")
        except KeyboardInterrupt:
            print("\n输入或测试被中断，已返回主菜单。")


if __name__ == "__main__":
    main()
