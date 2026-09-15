import time
import machine
from machine import Pin


_hard_count = bytearray(1)


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


def prepare_loopback():
    output_name = input_pin_name("输入用于产生边沿的输出引脚: ")
    irq_name = input_pin_name("输入支持 IRQ 的输入引脚: ")
    if output_name == irq_name:
        print("[FAIL] 输出与IRQ输入必须是两个不同引脚。")
        return None, None, None, None
    print("用杜邦线连接 {}(输出) 与 {}(IRQ输入)，连接后按回车。".format(output_name, irq_name))
    input()
    target = Pin(irq_name)
    output = Pin(output_name, Pin.OUT, value=0)
    return output, target, output_name, irq_name


def pulse(output, count, delay_ms=10):
    for _ in range(count):
        output.value(1)
        time.sleep_ms(delay_ms)
        output.value(0)
        time.sleep_ms(delay_ms)


def wait_for_callback(count, expected, timeout_ms=100):
    for _ in range(timeout_ms):
        if count[0] >= expected:
            return True
        time.sleep_ms(1)
    return count[0] >= expected


def edge_test():
    print("\n1. 上升沿\n2. 下降沿\n3. 双边沿")
    choice = input("下一步请输入边沿类型: ").strip()
    options = {
        "1": (Pin.IRQ_RISING, "上升沿", 5),
        "2": (Pin.IRQ_FALLING, "下降沿", 5),
        "3": (Pin.IRQ_RISING | Pin.IRQ_FALLING, "双边沿", 10),
    }
    if choice not in options:
        print("无效选项，已返回主菜单。")
        return
    output, target, _output_name, _irq_name = prepare_loopback()
    if output is None:
        return
    trigger, label, expected = options[choice]
    count = [0]
    received_pin = [None]

    def handler(pin):
        count[0] += 1
        received_pin[0] = pin

    try:
        output.value(0)
        time.sleep_ms(20)
        print("调用: irq = input_pin.irq(handler, trigger={}, priority=1, hard=False)".format(label))
        irq = target.irq(handler=handler, trigger=trigger, priority=1, hard=False)
        pulse(output, 5)
        callbacks_in_time = wait_for_callback(count, expected)
        raw_isr_count, overflow_count, _hard_callback_count, _hard_error_count = machine._pin_irq_stats(target)
        print_result(label + "次数", callbacks_in_time and count[0] == expected,
                     "期望={} 实际={}".format(expected, count[0]))
        print_result("回调Pin对象", received_pin[0] is target)
        print("[INFO] C层ISR次数={}".format(raw_isr_count))
        print("[INFO] Python回调次数={}".format(count[0]))
        print("[INFO] 待处理边沿计数溢出次数={}".format(overflow_count))
    except Exception as exc:
        print_result(label + "IRQ", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        target.irq(handler=None)
        output.deinit()


def disable_test():
    output, target, _output_name, _irq_name = prepare_loopback()
    if output is None:
        return
    count = [0]

    def handler(_pin):
        count[0] += 1

    try:
        target.irq(handler=handler, trigger=Pin.IRQ_RISING)
        pulse(output, 1)
        time.sleep_ms(20)
        before = count[0]
        print("调用: input_pin.irq(handler=None)")
        target.irq(handler=None)
        pulse(output, 1)
        time.sleep_ms(20)
        print_result("handler=None禁用", before == 1 and count[0] == before,
                     "禁用前={} 禁用后={}".format(before, count[0]))
        target.irq(handler=handler, trigger=Pin.IRQ_RISING)
        pulse(output, 1)
        time.sleep_ms(20)
        print_result("重新启用IRQ", count[0] == before + 1, "实际={}".format(count[0]))
    except Exception as exc:
        print_result("IRQ启停", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        target.irq(handler=None)
        output.deinit()


def hard_irq_test():
    output, target, _output_name, _irq_name = prepare_loopback()
    if output is None:
        return
    _hard_count[0] = 0
    try:
        import micropython
        micropython.alloc_emergency_exception_buf(100)
    except Exception:
        pass

    def handler(_pin):
        _hard_count[0] += 1

    try:
        print("调用: input_pin.irq(..., trigger=IRQ_RISING, hard=True)")
        target.irq(handler=handler, trigger=Pin.IRQ_RISING, hard=True)
        pulse(output, 5)
        time.sleep_ms(20)
        raw_isr_count, _overflow_count, hard_callback_count, hard_error_count = machine._pin_irq_stats(target)
        print_result("硬中断计数", _hard_count[0] == 5, "期望=5 实际={}".format(_hard_count[0]))
        print("[INFO] C层ISR次数={}".format(raw_isr_count))
        print("[INFO] Python硬回调成功次数={}".format(hard_callback_count))
        print("[INFO] 硬回调异常次数={}".format(hard_error_count))
    except Exception as exc:
        print_result("硬中断", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        target.irq(handler=None)
        output.deinit()


def stress_test():
    output, target, _output_name, _irq_name = prepare_loopback()
    if output is None:
        return
    try:
        count_requested = int(input("下一步请输入脉冲次数 [100]: ").strip() or "100")
        delay_ms = int(input("请输入每个半周期毫秒数 [1]: ").strip() or "1")
    except ValueError:
        print("请输入正整数，已返回主菜单。")
        return
    if count_requested <= 0 or delay_ms < 0:
        print("次数必须大于0，延时不能为负数。")
        return
    count = [0]

    def handler(_pin):
        count[0] += 1

    try:
        target.irq(handler=handler, trigger=Pin.IRQ_RISING)
        pulse(output, count_requested, delay_ms)
        time.sleep_ms(20)
        print_result("IRQ脉冲计数", count[0] == count_requested,
                     "期望={} 实际={}".format(count_requested, count[0]))
    except Exception as exc:
        print_result("IRQ压力", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        target.irq(handler=None)
        output.deinit()


def latency_test():
    output, target, output_name, irq_name = prepare_loopback()
    if output is None:
        return
    response_name = input_pin_name("请输入用于IRQ响应标记的安全输出引脚: ")
    if response_name in (output_name, irq_name):
        print("[FAIL] 响应引脚必须与边沿输出和IRQ输入引脚都不同。")
        output.deinit()
        return
    response = Pin(response_name, Pin.OUT, value=0)
    print("下一步：逻辑分析仪D0接IRQ输入，D1接响应引脚 {}，并与开发板共地。".format(response_name))
    print("设置D0上升沿触发并开始采集，然后按回车产生一次边沿。")
    input()

    def handler(_pin):
        response.value(1)

    try:
        target.irq(handler=handler, trigger=Pin.IRQ_RISING, hard=False)
        output.value(0)
        response.value(0)
        time.sleep_ms(20)
        output.value(1)
        for _ in range(100):
            if response.value() == 1:
                break
            time.sleep_ms(1)
        print_result("软IRQ响应标记", response.value() == 1)
        print("[INFO] 请测量D0上升沿到D1上升沿的时间；这是软IRQ响应延迟，需人工记录。")
    except Exception as exc:
        print_result("IRQ延迟标记", False, "{}: {}".format(type(exc).__name__, exc))
    finally:
        target.irq(handler=None)
        output.deinit()
        response.deinit()


def invalid_test():
    irq_name = input_pin_name("请输入一个支持IRQ且当前未外接信号的安全输入引脚: ")
    print("下一步：确认该引脚未被外部驱动，然后按回车测试不支持的参数。")
    input()
    target = Pin(irq_name)
    cases = (
        ("IRQ_HIGH_LEVEL", (ValueError,), lambda: target.irq(handler=lambda _pin: None, trigger=Pin.IRQ_HIGH_LEVEL)),
        ("wake参数", (NotImplementedError,),
         lambda: target.irq(handler=lambda _pin: None, trigger=Pin.IRQ_RISING, wake=0)),
    )
    passed = 0
    try:
        for name, exceptions, function in cases:
            try:
                function()
            except exceptions as exc:
                passed += print_result(name, True, "捕获预期异常 {}: {}".format(type(exc).__name__, exc))
            except Exception as exc:
                print_result(name, False, "异常类型错误 {}: {}".format(type(exc).__name__, exc))
            else:
                print_result(name, False, "调用未抛出异常")
    finally:
        target.irq(handler=None)
    print("非法参数测试完成：{}/{} 项通过。".format(passed, len(cases)))


def main():
    while True:
        print("\n1. 上升沿/下降沿/双边沿测试")
        print("2. IRQ禁用与重新启用测试")
        print("3. hard=True硬中断测试")
        print("4. IRQ脉冲计数压力测试")
        print("5. 逻辑分析仪测软IRQ响应延迟")
        print("6. 不支持参数异常测试")
        print("q. 退出")
        try:
            choice = input("下一步请输入选项: ").strip().lower()
            if choice == "1":
                edge_test()
            elif choice == "2":
                disable_test()
            elif choice == "3":
                hard_irq_test()
            elif choice == "4":
                stress_test()
            elif choice == "5":
                latency_test()
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
