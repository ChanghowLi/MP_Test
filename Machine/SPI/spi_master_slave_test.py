"""Interactive machine.SPI tests for the CPKCOR_RA8P1 board.

Copy this file to the board and run it from the MicroPython REPL.  The simple
and stress modes require MOSI and MISO to be connected together.  The manual
mode is intended for an SPI analyser or another SPI device.
"""

import gc
from machine import Pin, SPI


# Keep this list explicit: these are the SPI IDs enabled by mpconfigboard.h.
# IDs 0 and 1 are dedicated SPI peripherals; IDs 2 through 7 use SCI in SPI
# mode.  SCI-SPI supports 8-bit transfers only.
SPI_BUSES = {
    0: ("P702", "P701", "P700"),  # SCK, MOSI, MISO
    1: ("P102", "P101", "P100"),
    2: ("P402", "P400", "P401"),  # SCI1: SCK, TXD/MOSI, RXD/MISO
    3: ("P803", "P801", "P802"),  # SCI2
    4: ("P708", "P415", "P414"),  # SCI4
    5: ("PB04", "PB03", "PB02"),  # SCI5
    6: ("PC12", "PC14", "PC13"),  # SCI6
    7: ("P513", "P805", "P806"),  # SCI8
}

DEFAULT_BAUDRATE = 1000000
LOOPBACK_DATA = bytes((0x00, 0x01, 0x55, 0xAA, 0xFE, 0xFF, 0x12, 0x34))
SPEED_TEST_BAUDRATES = (
    1000000,
    5000000,
    10000000,
    15000000,
    20000000,
    25000000,
    30000000,
    40000000,
    50000000,
    60000000,
)
# Keep potentially fatal regression cases explicit so they can be disabled
# quickly if a future firmware change reintroduces the bug.
RUN_KNOWN_HANG_TESTS = True


def print_buses():
    print("可用 SPI id：")
    for spi_id in sorted(SPI_BUSES):
        sck, mosi, miso = SPI_BUSES[spi_id]
        print("  {}: SCK={}, MOSI={}, MISO={}".format(spi_id, sck, mosi, miso))


def input_int(prompt, minimum=None, maximum=None, default=None):
    while True:
        suffix = " [{}]".format(default) if default is not None else ""
        value = input(prompt + suffix + ": ").strip()
        if not value and default is not None:
            return default
        try:
            value = int(value, 0)
        except ValueError:
            print("请输入整数（可以使用 0x 前缀）。")
            continue
        if minimum is not None and value < minimum:
            print("数值不能小于 {}。".format(minimum))
        elif maximum is not None and value > maximum:
            print("数值不能大于 {}。".format(maximum))
        else:
            return value


def select_spi_id(prompt="请输入 SPI id（q 返回）："):
    print_buses()
    while True:
        value = input(prompt).strip().lower()
        if value == "q":
            return None
        try:
            spi_id = int(value, 0)
        except ValueError:
            print("请输入上面列出的 id，或输入 q 返回。")
            continue
        if spi_id in SPI_BUSES:
            return spi_id
        print("SPI id {} 不在可用列表中。".format(spi_id))


def print_result(name, passed, detail=""):
    state = "PASS" if passed else "FAIL"
    if detail:
        print("[{}] {}: {}".format(state, name, detail))
    else:
        print("[{}] {}".format(state, name))
    return passed


def simple_test():
    spi_id = select_spi_id()
    if spi_id is None:
        return
    _, mosi, miso = SPI_BUSES[spi_id]
    input("请用杜邦线连接 {}(MOSI) 与 {}(MISO)，连接完成后按回车开始。".format(mosi, miso))

    spi = None
    passed = 0
    total = 0
    try:
        print("调用: SPI({}, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)".format(spi_id))
        spi = SPI(spi_id, baudrate=DEFAULT_BAUDRATE, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)

        received = bytearray(len(LOOPBACK_DATA))
        spi.write_readinto(LOOPBACK_DATA, received)
        total += 1
        passed += print_result("write_readinto", bytes(received) == LOOPBACK_DATA,
                               "TX={} RX={}".format(LOOPBACK_DATA, bytes(received)))

        received = spi.read(len(LOOPBACK_DATA), 0xA5)
        expected = bytes((0xA5,)) * len(LOOPBACK_DATA)
        total += 1
        passed += print_result("read", received == expected,
                               "期望={} 实际={}".format(expected, received))

        received = bytearray(len(LOOPBACK_DATA))
        spi.readinto(received, 0x5A)
        expected = bytes((0x5A,)) * len(LOOPBACK_DATA)
        total += 1
        passed += print_result("readinto", bytes(received) == expected,
                               "期望={} 实际={}".format(expected, bytes(received)))

        result = spi.write(LOOPBACK_DATA)
        total += 1
        passed += print_result("write", result is None, "返回值={!r}".format(result))
    except Exception as exc:
        print("[FAIL] 简单测试发生异常: {}: {}".format(type(exc).__name__, exc))
    finally:
        if spi is not None:
            try:
                spi.deinit()
            except Exception as exc:
                print("[FAIL] deinit: {}: {}".format(type(exc).__name__, exc))
    print("简单测试完成：{}/{} 项通过。".format(passed, total))


def input_firstbit():
    while True:
        value = input("firstbit（0=MSB，1=LSB） [0]: ").strip()
        if value in ("", "0"):
            return SPI.MSB
        if value == "1":
            return SPI.LSB
        print("请输入 0 或 1。")


def input_optional_pins():
    print("如需使用板级默认引脚，下面三项全部直接按回车。")
    sck = input("SCK 引脚名: ").strip()
    mosi = input("MOSI 引脚名: ").strip()
    miso = input("MISO 引脚名: ").strip()
    if not sck and not mosi and not miso:
        return {}
    if not sck or not mosi or not miso:
        print("SCK、MOSI、MISO 必须全部指定；请重新输入。")
        return input_optional_pins()
    return {"sck": Pin(sck), "mosi": Pin(mosi), "miso": Pin(miso)}


def select_manual_operation():
    operations = {
        "1": "read",
        "2": "readinto",
        "3": "write",
        "4": "write_readinto",
    }
    while True:
        print("\n请选择手动测试 API：")
        print("1. SPI.read()")
        print("2. SPI.readinto()")
        print("3. SPI.write()")
        print("4. SPI.write_readinto()")
        print("q. 返回")
        choice = input("请选择：").strip().lower()
        if choice == "q":
            return None
        if choice in operations:
            return operations[choice]
        print("无效选项，请重新输入。")


def run_manual_operation(spi, operation, length):
    transmit = bytes((index & 0xFF for index in range(length)))
    if operation == "read":
        return spi.read(length, 0x00)
    if operation == "readinto":
        received = bytearray(length)
        spi.readinto(received, 0x00)
        return bytes(received)
    if operation == "write":
        spi.write(transmit)
        return None
    if operation == "write_readinto":
        received = bytearray(length)
        spi.write_readinto(transmit, received)
        return bytes(received)
    raise ValueError("不支持的手动测试 API: {}".format(operation))


def manual_test():
    spi_id = select_spi_id()
    if spi_id is None:
        return
    operation = select_manual_operation()
    if operation is None:
        return

    baudrate = input_int("baudrate (Hz)", minimum=1, default=DEFAULT_BAUDRATE)
    polarity = input_int("polarity", minimum=0, maximum=1, default=0)
    phase = input_int("phase", minimum=0, maximum=1, default=0)
    bits = input_int("bits", minimum=1, default=8)
    firstbit = input_firstbit()
    try:
        pin_args = input_optional_pins()
        cs_name = input("自动 CS 引脚名（直接回车表示不使用）: ").strip()
        cs = Pin(cs_name) if cs_name else None
    except Exception as exc:
        print("[FAIL] 创建 Pin 对象失败: {}: {}".format(type(exc).__name__, exc))
        return
    length = input_int("收发长度（字节）", minimum=0, default=16)

    firstbit_name = "SPI.MSB" if firstbit == SPI.MSB else "SPI.LSB"
    print("即将调用: SPI({}, baudrate={}, polarity={}, phase={}, bits={}, firstbit={}, cs={!r}{})".format(
        spi_id, baudrate, polarity, phase, bits, firstbit_name, cs,
        ", 自定义三线引脚" if pin_args else ""))
    input("请连接 SPI 测试仪；确认电平和接线正确后按回车开始。")

    spi = None
    try:
        spi = SPI(spi_id, baudrate=baudrate, polarity=polarity, phase=phase,
                  bits=bits, firstbit=firstbit, cs=cs, **pin_args)
        transmit = bytes((index & 0xFF for index in range(length)))
        if operation == "read":
            print("调用: spi.read({}, 0x00)".format(length))
        elif operation == "readinto":
            print("调用: spi.readinto(bytearray({}), 0x00)".format(length))
        elif operation == "write":
            print("调用: spi.write({})".format(transmit))
        else:
            print("调用: spi.write_readinto({}, bytearray({}))".format(transmit, length))

        received = run_manual_operation(spi, operation, length)
        if operation in ("write", "write_readinto"):
            print("发送内容: {}".format(transmit))
        else:
            print("发送填充值: 00")
        if received is not None:
            print("接收内容: {}".format(received))
            print("十六进制接收: {}".format(" ".join("{:02x}".format(value) for value in received)))
        print("[完成] SPI.{}() 调用完成，请核对主从机收发数据。".format(operation))
    except Exception as exc:
        print("[FAIL] 手动测试异常: {}: {}".format(type(exc).__name__, exc))
    finally:
        if spi is not None:
            try:
                spi.deinit()
            except Exception as exc:
                print("[FAIL] deinit: {}: {}".format(type(exc).__name__, exc))


class StressRunner:
    def __init__(self):
        self.failed = 0
        self.passed = 0

    def expect_ok(self, description, call_text, function):
        print("\n调用前: {}".format(call_text))
        try:
            function()
        except Exception as exc:
            self.failed += 1
            print("[FAIL] {}，意外异常 {}: {}".format(description, type(exc).__name__, exc))
            return False
        self.passed += 1
        print("[PASS] {}".format(description))
        return True

    def expect_exception(self, description, call_text, exception_types, function):
        print("\n调用前: {}".format(call_text))
        try:
            function()
        except exception_types as exc:
            self.passed += 1
            print("[PASS] 捕获预期异常 {}: {}".format(type(exc).__name__, exc))
            return True
        except Exception as exc:
            self.failed += 1
            print("[FAIL] 异常类型错误，得到 {}: {}".format(type(exc).__name__, exc))
            return False
        self.failed += 1
        print("[FAIL] {}，调用未抛出异常".format(description))
        return False

    def expect_handled(self, description, call_text, function):
        """Pass if a hardware boundary either works or raises a Python exception."""
        print("\n调用前: {}".format(call_text))
        try:
            function()
        except Exception as exc:
            self.passed += 1
            print("[PASS] 边界值被安全拒绝 {}: {}".format(type(exc).__name__, exc))
            return True
        self.passed += 1
        print("[PASS] {}，边界值被硬件/驱动接受".format(description))
        return True


def make_and_deinit(spi_id, **kwargs):
    spi = SPI(spi_id, **kwargs)
    spi.deinit()


def test_repeated_lifecycle(runner, spi_id, iterations):
    def repeat():
        for index in range(iterations):
            if index % 10 == 0:
                print("  生命周期循环 {}/{}".format(index + 1, iterations))
            spi = SPI(spi_id, baudrate=DEFAULT_BAUDRATE)
            spi.deinit()
            # deinit must be idempotent.
            spi.deinit()
        gc.collect()
    runner.expect_ok("反复申请、释放并重复 deinit", "重复 {} 次: SPI({}); deinit(); deinit()".format(iterations, spi_id), repeat)


def test_same_instance(runner, spi_id, iterations):
    def repeat():
        first = SPI(spi_id, baudrate=DEFAULT_BAUDRATE)
        try:
            for _ in range(iterations):
                current = SPI(spi_id)
                if current is not first:
                    raise AssertionError("同一 id 返回了不同对象")
        finally:
            first.deinit()
    runner.expect_ok("同一 SPI id 多次申请返回同一实例", "重复 {} 次: SPI({})".format(iterations, spi_id), repeat)


def test_invalid_parameters(runner, spi_id):
    runner.expect_exception("不存在的负数 id 必须被拒绝", "SPI(-1)", (ValueError,), lambda: SPI(-1))
    runner.expect_exception("不存在的大 id 必须被拒绝", "SPI(0x3fffffff)", (ValueError,), lambda: SPI(0x3fffffff))
    runner.expect_exception("非整数 id 必须被拒绝", "SPI('0')", (TypeError,), lambda: SPI("0"))

    for value in (0, -1):
        runner.expect_exception("非法 baudrate 必须被拒绝", "SPI({}, baudrate={})".format(spi_id, value),
                                (ValueError,), lambda value=value: make_and_deinit(spi_id, baudrate=value))
    for name, values in (("polarity", (-1, 2)), ("phase", (-1, 2))):
        for value in values:
            kwargs = {name: value}
            runner.expect_exception("非法 {} 必须被拒绝".format(name), "SPI({}, {}={})".format(spi_id, name, value),
                                    (ValueError,), lambda kwargs=kwargs: make_and_deinit(spi_id, **kwargs))
    for value in (-1, 0, 1, 7, 9, 15, 64):
        runner.expect_exception("不支持的 bits 必须被拒绝", "SPI({}, bits={})".format(spi_id, value),
                                (ValueError,), lambda value=value: make_and_deinit(spi_id, bits=value))
    if spi_id >= 2:
        for value in (16, 32):
            runner.expect_exception("SCI-SPI 不支持的 bits 必须被拒绝", "SPI({}, bits={})".format(spi_id, value),
                                    (ValueError,), lambda value=value: make_and_deinit(spi_id, bits=value))
    else:
        for value in (16, 32):
            runner.expect_ok("专用 SPI 支持 bits={}".format(value),
                             "SPI({}, bits={}); deinit()".format(spi_id, value),
                             lambda value=value: make_and_deinit(spi_id, bits=value))
    for value in (-1, 2, 255):
        runner.expect_exception("非法 firstbit 必须被拒绝", "SPI({}, firstbit={})".format(spi_id, value),
                                (ValueError,), lambda value=value: make_and_deinit(spi_id, firstbit=value))
    runner.expect_exception("不完整的引脚组必须被拒绝", "SPI({}, sck=Pin('P702'))".format(spi_id),
                            (ValueError,), lambda: make_and_deinit(spi_id, sck=Pin("P702")))
    runner.expect_exception("pins 元组参数不受支持", "SPI({}, pins=(...))".format(spi_id),
                            (TypeError,), lambda: SPI(spi_id, pins=(Pin("P702"), Pin("P701"), Pin("P700"))))


def test_boundary_baudrates(runner, spi_id):
    for baudrate in (1, 25000000, 60000000, 60000001, 0x3FFFFFFF):
        runner.expect_handled("baudrate={} 不得导致崩溃".format(baudrate),
                              "SPI({}, baudrate={}); deinit()".format(spi_id, baudrate),
                              lambda baudrate=baudrate: make_and_deinit(spi_id, baudrate=baudrate))


def test_transfer_arguments(runner, spi_id):
    spi = SPI(spi_id, baudrate=DEFAULT_BAUDRATE)
    try:
        runner.expect_ok("零长度 write", "spi.write(b'')", lambda: spi.write(b""))
        runner.expect_ok("零长度 read", "spi.read(0)", lambda: spi.read(0))
        runner.expect_ok("零长度 readinto", "spi.readinto(bytearray(0))", lambda: spi.readinto(bytearray(0)))
        runner.expect_ok("零长度 write_readinto", "spi.write_readinto(b'', bytearray(0))",
                         lambda: spi.write_readinto(b"", bytearray(0)))
        if RUN_KNOWN_HANG_TESTS:
            # extmod currently converts nbytes to size_t before allocation.
            runner.expect_exception("负读取长度必须被拒绝", "spi.read(-1)",
                                    (ValueError, OverflowError, MemoryError), lambda: spi.read(-1))
        else:
            print("\n[SKIP] spi.read(-1)：当前固件已确认会卡死；修复 C 实现后将 RUN_KNOWN_HANG_TESTS 改为 True 复测")
        runner.expect_exception("read 的 write 必须为一个字节", "spi.read(1, 256)", (ValueError,), lambda: spi.read(1, 256))
        runner.expect_exception("readinto 的 write 必须为一个字节", "spi.readinto(bytearray(1), 256)",
                                (ValueError,), lambda: spi.readinto(bytearray(1), 256))
        runner.expect_exception("只读缓冲区不能作为 readinto 目标", "spi.readinto(b'1234')",
                                (TypeError,), lambda: spi.readinto(b"1234"))
        runner.expect_exception("收发缓冲区长度不同必须被拒绝", "spi.write_readinto(b'1234', bytearray(3))",
                                (ValueError,), lambda: spi.write_readinto(b"1234", bytearray(3)))
        runner.expect_exception("非缓冲区不能用于 write", "spi.write(None)", (TypeError,), lambda: spi.write(None))
    finally:
        spi.deinit()

    spi = SPI(spi_id, baudrate=DEFAULT_BAUDRATE)
    spi.deinit()
    runner.expect_exception("deinit 后传输必须被拒绝", "spi.write(b'1')  # spi 已 deinit",
                            (OSError,), lambda: spi.write(b"1"))


def test_loopback_stress(runner, spi_id, iterations):
    def repeat():
        spi = SPI(spi_id, baudrate=DEFAULT_BAUDRATE)
        tx = bytearray(256)
        rx = bytearray(256)
        try:
            for index in range(iterations):
                for offset in range(len(tx)):
                    tx[offset] = (index + offset * 17) & 0xFF
                if index % 10 == 0:
                    print("  环回传输 {}/{}".format(index + 1, iterations))
                spi.write_readinto(tx, rx)
                if tx != rx:
                    raise AssertionError("第 {} 轮数据不一致".format(index + 1))
        finally:
            spi.deinit()
    runner.expect_ok("反复环回传输且数据一致", "重复 {} 次: spi.write_readinto(256 bytes)".format(iterations), repeat)


def run_loopback_speed_sweep(spi_id, baudrates, iterations):
    results = []
    for baudrate in baudrates:
        print("\n测试请求速度：{} Hz".format(baudrate))
        spi = None
        error_detail = ""
        try:
            spi = SPI(spi_id, baudrate=baudrate)
            tx = bytearray(256)
            rx = bytearray(256)
            for index in range(iterations):
                for offset in range(len(tx)):
                    tx[offset] = (index + offset * 17) & 0xFF
                spi.write_readinto(tx, rx)
                if tx != rx:
                    raise AssertionError("第 {} 轮数据不一致".format(index + 1))
        except Exception as exc:
            error_detail = "{}: {}".format(type(exc).__name__, exc)
        finally:
            if spi is not None:
                try:
                    spi.deinit()
                except Exception as exc:
                    if not error_detail:
                        error_detail = "deinit {}: {}".format(type(exc).__name__, exc)
        results.append((baudrate, not error_detail, error_detail))
    return results


def loopback_speed_test():
    spi_id = select_spi_id("请输入已将 MOSI 和 MISO 连在一起的 SPI id（q 返回）：")
    if spi_id is None:
        return
    _, mosi, miso = SPI_BUSES[spi_id]
    input("请确认 {}(MOSI) 与 {}(MISO) 已连接，然后按回车。".format(mosi, miso))
    iterations = input_int("每个速度的环回循环次数", minimum=1, maximum=10000, default=100)

    results = run_loopback_speed_sweep(spi_id, SPEED_TEST_BAUDRATES, iterations)
    passed_baudrates = []
    print("\n速度扫描结果：")
    for baudrate, passed, detail in results:
        if passed:
            passed_baudrates.append(baudrate)
            print("  {:>9} Hz  PASS".format(baudrate))
        else:
            print("  {:>9} Hz  FAIL  {}".format(baudrate, detail))

    if passed_baudrates:
        print("最高通过的请求速度：{} Hz".format(max(passed_baudrates)))
    else:
        print("没有速度档位通过测试。")
    print("注意：该结果是最高稳定请求速度，不是仪器实测的 SCK 频率。")


def loopback_stress_test():
    print("警告：本模式会执行大量边界调用。每次调用前都会打印调用形式；若发生 HardFault，重启后可据最后一行定位。")
    spi_id = select_spi_id("请输入已将 MOSI 和 MISO 连在一起的 SPI id（q 返回）：")
    if spi_id is None:
        return
    _, mosi, miso = SPI_BUSES[spi_id]
    input("请确认 {}(MOSI) 与 {}(MISO) 已连接，然后按回车。".format(mosi, miso))
    iterations = input_int("生命周期及环回循环次数", minimum=1, maximum=10000, default=100)

    runner = StressRunner()
    test_repeated_lifecycle(runner, spi_id, iterations)
    test_same_instance(runner, spi_id, iterations)
    test_invalid_parameters(runner, spi_id)
    test_boundary_baudrates(runner, spi_id)
    test_transfer_arguments(runner, spi_id)
    test_loopback_stress(runner, spi_id, iterations)
    print("\n压力测试完成：PASS={}，FAIL={}。".format(runner.passed, runner.failed))
    if runner.failed:
        print("FAIL 表示行为与 Peripheral.md 的约束不一致，请结合对应调用检查 C 实现。")


def input_hex_bytes(prompt, default):
    default_text = " ".join("{:02X}".format(value) for value in default)
    while True:
        value = input("{} [{}]: ".format(prompt, default_text)).strip()
        if not value:
            return default
        try:
            data = bytes(int(item, 16) for item in value.replace(",", " ").split())
        except (ValueError, OverflowError):
            print("请输入以空格分隔的十六进制字节，例如 11 22 33 AA。")
            continue
        if not data:
            print("发送数据不能为空。")
            continue
        return data


def run_master_slave_iterations(spi, transmit, expected_receive, iterations):
    passed = 0
    failed = 0
    for iteration in range(1, iterations + 1):
        input("第 {}/{} 轮：请在 USB2XXX 点击‘读写数据’，准备好后按回车。".format(iteration, iterations))
        received = bytearray(len(transmit))
        try:
            spi.write_readinto(transmit, received)
        except Exception as exc:
            failed += 1
            print("[FAIL] 第 {} 轮异常 {}: {}".format(iteration, type(exc).__name__, exc))
            continue
        if bytes(received) == expected_receive:
            passed += 1
            print("[PASS] 第 {} 轮，RX={}".format(
                iteration, " ".join("{:02x}".format(value) for value in received)))
        else:
            failed += 1
            print("[FAIL] 第 {} 轮，期望={}，实际={}".format(
                iteration,
                " ".join("{:02x}".format(value) for value in expected_receive),
                " ".join("{:02x}".format(value) for value in received)))
    return passed, failed


def master_slave_stress_test():
    spi_id = select_spi_id()
    if spi_id is None:
        return

    baudrate = input_int("baudrate (Hz)", minimum=1, default=100000)
    polarity = input_int("polarity", minimum=0, maximum=1, default=0)
    phase = input_int("phase", minimum=0, maximum=1, default=0)
    bits = input_int("bits", minimum=1, default=8)
    firstbit = input_firstbit()
    try:
        pin_args = input_optional_pins()
        cs_name = input("自动 CS 引脚名: ").strip()
        if not cs_name:
            print("主从机压力测试必须指定自动 CS 引脚。")
            return
        cs = Pin(cs_name)
    except Exception as exc:
        print("[FAIL] 创建 Pin 对象失败: {}: {}".format(type(exc).__name__, exc))
        return

    expected_receive = input_hex_bytes(
        "请输入 USB2XXX 每轮发送的数据",
        bytes((0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA)))
    iterations = input_int("主从机通信循环次数", minimum=1, maximum=10000, default=10)
    transmit = bytes((index & 0xFF for index in range(len(expected_receive))))

    print("RA8 每轮发送: {}".format(" ".join("{:02X}".format(value) for value in transmit)))
    print("期望 RA8 每轮接收: {}".format(" ".join("{:02X}".format(value) for value in expected_receive)))
    print("每轮传输前都需要在 USB2XXX 点击一次‘读写数据’，SPI 参数只配置一次。")

    spi = None
    try:
        spi = SPI(spi_id, baudrate=baudrate, polarity=polarity, phase=phase,
                  bits=bits, firstbit=firstbit, cs=cs, **pin_args)

        passed, failed = run_master_slave_iterations(
            spi, transmit, expected_receive, iterations)
        print("\n主从机压力测试完成：PASS={}，FAIL={}。".format(passed, failed))
    except Exception as exc:
        print("[FAIL] 主从机压力测试异常: {}: {}".format(type(exc).__name__, exc))
    finally:
        if spi is not None:
            try:
                spi.deinit()
            except Exception as exc:
                print("[FAIL] deinit: {}: {}".format(type(exc).__name__, exc))


def stress_test():
    while True:
        print("\n请选择压力测试类型：")
        print("1. 回环健壮性测试")
        print("2. 主从机通信压力测试")
        print("3. 最大速度回环测试")
        print("q. 返回")
        choice = input("请选择：").strip().lower()
        if choice == "1":
            loopback_stress_test()
            return
        if choice == "2":
            master_slave_stress_test()
            return
        if choice == "3":
            loopback_speed_test()
            return
        if choice == "q":
            return
        print("无效选项，请重新输入。")


def main():
    while True:
        print("\n1. 简单测试")
        print("2. 手动测试")
        print("3. 压力测试")
        print("q. 退出")
        try:
            choice = input("请选择：").strip().lower()
            if choice == "1":
                simple_test()
            elif choice == "2":
                manual_test()
            elif choice == "3":
                stress_test()
            elif choice == "q":
                print("测试结束。")
                return
            else:
                print("无效选项，请重新输入。")
        except KeyboardInterrupt:
            print("\n输入被中断，已返回主菜单。")


if __name__ == "__main__":
    main()
