"""Interactive machine.Pin GPIO tests for the CPKCOR_RA8P1 board."""

import time
from machine import Pin


def print_result(name, passed, detail=""):
    state = "PASS" if passed else "FAIL"
    print("[{}] {}{}".format(state, name, ": " + detail if detail else ""))
    return passed


def input_pin_name(prompt):
    while True:
        name = input(prompt).strip().upper()
        numeric_port = len(name) == 4 and name[1:].isdigit()
        alpha_port = len(name) == 4 and name[1].isalpha() and name[2:].isdigit()
        if name.startswith("P") and (numeric_port or alpha_port):
            return name
        print("请输入类似 P006、PB04 或 PC12 的CPU引脚名。")


def output_test():
    name = input_pin_name("请输入确认可安全输出的引脚名（例如 P006）: ")
    print("下一步：将逻辑分析仪接到 {} 并共地，然后按回车输出10个慢速脉冲。".format(name))
    input()
    pin = None
    try:
        pin = Pin(name, Pin.OUT, value=0)
        print("调用: Pin({!r}, Pin.OUT, value=0)".format(name))
        for _ in range(10):
            pin.on()
            time.sleep_ms(100)
            pin.off()
            time.sleep_ms(100)
        print_result("GPIO输出脉冲", True, "应观察到10个高、低各100 ms的脉冲")
    except Exception as exc:
        print_result("GPIO输出脉冲", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        if pin is not None:
            pin.init(Pin.IN, pull=None)


def input_loopback_test():
    output_name = input_pin_name("请输入确认可安全输出的引脚名: ")
    input_name = input_pin_name("请输入确认可安全输入的引脚名: ")
    if output_name == input_name:
        print("[FAIL] 输出与输入必须是两个不同引脚。")
        return
    print("下一步：用杜邦线连接 {}(输出) 与 {}(输入)，连接后按回车。".format(output_name, input_name))
    input()
    output = None
    try:
        output = Pin(output_name, Pin.OUT, value=0)
        target = Pin(input_name, Pin.IN, pull=None)
        passed = 0
        pattern = (0, 1, 0, 1, 1, 0)
        for index, expected in enumerate(pattern):
            output.value(expected)
            time.sleep_ms(10)
            actual = target.value()
            passed += print_result("第{}次输入读取".format(index + 1), actual == expected,
                                   "期望={} 实际={}".format(expected, actual))
        print("输入回接测试完成：{}/{} 项通过。".format(passed, len(pattern)))
    except Exception as exc:
        print_result("GPIO输入回接", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        if output is not None:
            output.init(Pin.IN, pull=None)


def helper_test():
    name = input_pin_name("请输入确认可安全输出的引脚名: ")
    print("下一步：可将逻辑分析仪接到 {}；按回车后测试 value/call/on/off/high/low/toggle。".format(name))
    input()
    pin = None
    try:
        pin = Pin(name, Pin.OUT, value=0)
        checks = (
            ("value(1)", lambda: pin.value(1), 1),
            ("直接调用 pin(0)", lambda: pin(0), 0),
            ("on()", pin.on, 1),
            ("off()", pin.off, 0),
            ("high()", pin.high, 1),
            ("low()", pin.low, 0),
            ("toggle()", pin.toggle, 1),
        )
        passed = 0
        for label, function, expected in checks:
            function()
            passed += print_result(label, pin.value() == expected, "读取值={}".format(pin.value()))
        print("辅助方法测试完成：{}/{} 项通过。".format(passed, len(checks)))
    except Exception as exc:
        print_result("Pin辅助方法", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        if pin is not None:
            pin.init(Pin.IN, pull=None)


def configuration_test():
    name = input_pin_name("请输入确认可安全配置的引脚名: ")
    print("下一步：断开该引脚上的外部驱动，随后按回车测试 init/mode/pull/drive。")
    input()
    try:
        pin = Pin(name, Pin.IN, pull=Pin.PULL_UP)
        passed = 0
        passed += print_result("PULL_UP配置", pin.pull() == Pin.PULL_UP, "pull={}".format(pin.pull()))
        pin.init(Pin.OUT, value=0, drive=Pin.DRIVE_0)
        passed += print_result("init切换OUT", pin.mode() == Pin.OUT, "mode={}".format(pin.mode()))
        for drive in (Pin.DRIVE_0, Pin.DRIVE_1, Pin.DRIVE_2, Pin.DRIVE_3):
            pin.drive(drive)
            passed += print_result("drive={}".format(drive), pin.drive() == drive)
        pin.init(Pin.IN, pull=None)
        passed += print_result("init切回IN", pin.mode() == Pin.IN)
        print("配置测试完成：{}/7 项通过。".format(passed))
    except Exception as exc:
        print_result("Pin配置", False, "{}: {}".format(type(exc).__name__, exc))


def namespace_test():
    name = input_pin_name("请输入要检查的CPU引脚名: ")
    try:
        direct = Pin(name)
        cpu = getattr(Pin.cpu, name)
        board = getattr(Pin.board, name)
        print_result("Pin.cpu对象一致", cpu is direct)
        print_result("Pin.board对象一致", board is direct)
    except Exception as exc:
        print_result("Pin.cpu/Pin.board", False, "{}: {}".format(type(exc).__name__, exc))


def invalid_test():
    pin_name = input_pin_name("请输入确认可安全配置且已断开外部信号的引脚名: ")
    print("下一步：确认 {} 未连接外部设备，然后按回车测试非法参数。".format(pin_name))
    input()
    cases = (
        ("不存在的引脚", lambda: Pin("P999")),
        ("错误的引脚类型", lambda: Pin(None)),
        ("非法mode值", lambda: Pin(pin_name, 0x7FFFFFFF)),
        ("错误的mode类型", lambda: Pin(pin_name, "OUT")),
        ("非法pull值", lambda: Pin(pin_name, Pin.IN, pull=99)),
        ("错误的pull类型", lambda: Pin(pin_name, Pin.IN, pull="PULL_UP")),
        ("非法drive值", lambda: Pin(pin_name, Pin.OUT, drive=99)),
        ("错误的drive类型", lambda: Pin(pin_name, Pin.OUT, drive="DRIVE_0")),
        ("输入模式使用value", lambda: Pin(pin_name, Pin.IN, value=1)),
        ("输入模式使用drive", lambda: Pin(pin_name, Pin.IN, drive=Pin.DRIVE_0)),
        ("非ALT模式使用alt", lambda: Pin(pin_name, Pin.OUT, alt=1)),
        ("错误的alt类型", lambda: Pin(pin_name, Pin.ALT, alt="SPI")),
        ("未提供mode时配置参数", lambda: Pin(pin_name, pull=Pin.PULL_UP)),
        ("未知关键字参数", lambda: Pin(pin_name, Pin.IN, unsupported=1)),
    )
    passed = 0
    for case_name, function in cases:
        try:
            function()
        except (TypeError, ValueError, NotImplementedError) as exc:
            passed += print_result(case_name, True, "{}: {}".format(type(exc).__name__, exc))
        except Exception as exc:
            print_result(case_name, False, "异常类型错误 {}: {}".format(type(exc).__name__, exc))
        else:
            print_result(case_name, False, "调用未抛出异常")

    if hasattr(Pin, "PULL_DOWN"):
        try:
            Pin(pin_name, Pin.IN, pull=Pin.PULL_DOWN)
        except (TypeError, ValueError, NotImplementedError) as exc:
            passed += print_result("不支持的PULL_DOWN", True, "{}: {}".format(type(exc).__name__, exc))
        except Exception as exc:
            print_result("不支持的PULL_DOWN", False, "异常类型错误 {}: {}".format(type(exc).__name__, exc))
        else:
            print_result("不支持的PULL_DOWN", False, "调用未抛出异常")
    else:
        passed += print_result("PULL_DOWN未提供", True, "当前RA8P1端口不支持内部下拉")

    total = len(cases) + 1
    print("非法参数测试完成：{}/{} 项通过。".format(passed, total))


def main():
    while True:
        print("\n1. 输出脉冲测试")
        print("2. 输入输出回接测试")
        print("3. value/on/off/toggle辅助方法测试")
        print("4. init/pull/drive配置测试")
        print("5. Pin.cpu/Pin.board对象测试")
        print("6. 非法参数测试")
        print("q. 退出")
        try:
            choice = input("下一步请输入选项: ").strip().lower()
            if choice == "1":
                output_test()
            elif choice == "2":
                input_loopback_test()
            elif choice == "3":
                helper_test()
            elif choice == "4":
                configuration_test()
            elif choice == "5":
                namespace_test()
            elif choice == "6":
                invalid_test()
            elif choice == "q":
                print("测试结束。")
                return
            else:
                print("无效选项，请按菜单重新输入。")
        except KeyboardInterrupt:
            print("\n输入或测试被中断，已返回主菜单。")


if __name__ == "__main__":
    main()
