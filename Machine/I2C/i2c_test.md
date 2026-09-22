# I2C（IIC）AT24C02 测试

## 硬件连接

| RA8P1 | AT24C02 |
| --- | --- |
| `P512 / SCL` | `SCL` |
| `P511 / SDA` | `SDA` |
| `3.3V` | `VCC` |
| `GND` | `GND` |

AT24C02 使用开发板 `3.3V` 供电并与 RA8P1 共地。

## 运行

复制测试脚本到 `/mram`：

```powershell
python tools\pyboard.py --device COM9 --baudrate 2000000 --wait 5 --filesystem cp ports\renesas-ra8\i2c.py :/mram/i2c.py
```

REPL 中运行：

```python
import i2c
```

测试参数：

- I2C：`I2C(1)`，`400 kHz`
- EEPROM：AT24C02，`256 Byte`
- 从机地址：`0x50`
- 内部地址：`0x00 ~ 0xFF`
- 每次读写：`1 Byte`

## 测试内容

进行两轮全片读写校验：

1. `0x00 ~ 0xFF` 全部写入 `0xFF`，逐地址读回校验。
2. 每个地址写入对应值 `0x00 ~ 0xFF`，逐地址读回校验。

测试结果：

```text
Test 1: full chip 0xFF: PASS
Test 2: full chip 0x00..0xFF: PASS
```

![I2C1 400kHz AT24C02 读写测试通过](i2c.assets/I2C_AT24C02_Full_Chip_Test_PASS.png)
