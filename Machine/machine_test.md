# machine_test.py

## 测试环境

- 测试脚本：`Machine/machine_test.py`
- 被测接口：模块级 `machine` API
- 文件系统：MRAM LittleFS，挂载点 `/mram`

## 运行方式

将 `machine_test.py` 上传到开发板文件系统根目录，在 MicroPython REPL 中执行：

```python
import machine_test
machine_test.main()
```

菜单包含基础功能、安全 RAM 访问、全局中断开关、`idle()`、复位及 backup memory 测试。复位测试必须输入 `RESET` 才会执行。

## 运行结果

### machine.mem8

- 输入：主菜单输入 `2`，再按回车开始。
- 测试：在专用 `bytearray` 的安全 RAM 地址写入 `0xA5`并读回比较。
- 结果：`[PASS] machine.mem8`。

### machine.mem16

- 输入：主菜单输入 `2`，再按回车开始。
- 测试：在同一安全 RAM 地址写入 `0x5AA5`并读回比较。
- 结果：`[PASS] machine.mem16`。

### machine.mem32

- 输入：主菜单输入 `2`，再按回车开始。
- 测试：在同一安全 RAM 地址写入 `0xA55A1234`，读回后按32位无符号数比较。
- 结果：原始读回值为 `-1520823756`，归一化后为 `0xA55A1234`，`[PASS] machine.mem32`。三项内存测试汇总为 `3/3` 通过。

### machine.mem_backup()

- 输入：主菜单输入 `5`，复位菜单输入 `4`，确认时输入 `RESET`。
- 测试：保存 backup memory 原内容，写入 `0x52413850`并执行软复位。复位后重新运行 `machine_test.main()`，依次输入 `5`、`5`检查标记。
- 结果：`[PASS] mem_backup软复位保持: 读取值=0x52413850；原32位内容已恢复`。

### machine.reset()

- 输入：主菜单输入 `5`，复位菜单输入 `3`，确认时输入 `RESET`。
- 测试：开发板执行硬件复位；重新运行脚本后依次输入 `5`、`1`查询复位原因。
- 结果：开发板正常重启，`reset_cause=2`，对应 `machine.HARD_RESET`，结果：PASS。

### machine.soft_reset()

- 输入：主菜单输入 `5`，复位菜单输入 `2`，确认时输入 `RESET`。
- 测试：开发板执行软复位；重新运行脚本后依次输入 `5`、`1`查询复位原因。
- 结果：开发板正常软复位，`reset_cause=0`，对应 `machine.SOFT_RESET`，结果：PASS。

### machine.reset_cause()

- 输入：主菜单输入 `5`，复位菜单输入 `1`。
- 测试：分别在软复位和硬件复位后读取复位原因。
- 结果：软复位后为 `0`，硬件复位后为 `2`，均与对应常量一致，结果：PASS。

### machine.disable_irq()

- 输入：主菜单输入 `3`，再按回车开始。
- 测试：第一次调用保存原状态并关闭中断，第二次调用读取关闭后的状态。
- 通过标准：关闭前状态为 `0`，关闭后状态为 `1`。
- 结果：`[PASS] machine.disable_irq: 关闭前状态=0，关闭后状态=1`。

### machine.enable_irq()

- 输入：与 `machine.disable_irq()` 共用主菜单第 `3` 项。
- 测试：使用原状态恢复中断，再次调用 `machine.disable_irq()`读取恢复后的状态，随后立即恢复该状态。
- 通过标准：恢复后读取到状态 `0`。
- 结果：`[PASS] machine.enable_irq: 恢复后状态=0`。

### machine.freq()

- 输入：主菜单输入 `1`，再按回车开始。
- 测试：查询 CPU 时钟频率，检查返回值为大于0的整数；不测试运行时修改频率。
- 结果：`[PASS] machine.freq: 返回值=... Hz`。

### machine.idle()

- 输入：主菜单输入 `4`，再按回车开始。
- 测试：调用 `machine.idle()`进入一次等待中断状态，确认发生中断后能够继续执行；如果5秒仍未返回，按 `Ctrl-C`中止。
- 结果：`[PASS] machine.idle: 已从等待中断状态返回`。

### machine.unique_id()

- 输入：主菜单输入 `1`，再按回车开始。
- 测试：连续读取两次，检查返回值为非空 `bytes`、内容不全为零且两次一致。
- 结果：通过时输出 `[PASS] machine.unique_id: 长度=...，值=...`。

### machine.rng()

- 输入：主菜单输入 `1`，再按回车开始。
- 测试：连续读取8次，检查每个结果都是 `0`至`0xFFFFFF`范围内的整数，并且8次结果不全相同。
- 结果：通过时输出 `[PASS] machine.rng: 8次结果=(...)`。

### machine.wake_reason()接口框架

- 输入：主菜单输入 `1`，再按回车开始。
- 测试：仅检查当前接口返回 `machine.WAKE_UNKNOWN`。
- 结果：`[PASS] machine.wake_reason: 期望WAKE_UNKNOWN=...，实际=...`。该结果只代表接口框架可调用，不代表低功耗唤醒功能已经完成。

## 当前结论

本轮板端实测确认：

- `machine.mem8`、`machine.mem16`和`machine.mem32`能够在安全RAM区域正确读写。
- `machine.disable_irq()`与`machine.enable_irq()`能够保存并恢复全局中断状态。
- `machine.freq()`能够查询当前CPU时钟频率。
- `machine.idle()`能够正常返回。
- `machine.soft_reset()`和`machine.reset()`能够分别产生正确的复位原因。
- `machine.mem_backup()`内容能够跨软复位保持，测试结束后能够恢复原内容。
- `machine.unique_id()`能够稳定返回非零的唯一ID，`machine.rng()`能够返回有效范围内且有变化的随机数。
- `machine.wake_reason()`当前只确认接口框架能够返回`machine.WAKE_UNKNOWN`，不代表低功耗唤醒功能已经完成。

## 注意事项

- `soft_reset()`和`reset()`会立即中断当前REPL流程，必须放在其它非复位测试之后执行。
