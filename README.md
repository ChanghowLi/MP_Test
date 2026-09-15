Renesas ra8 MicroPython 移植的测试脚本，对应 ports [ChanghowLi/micropython at ra-dev](https://github.com/ChanghowLi/micropython/tree/ra-dev) 

## 脚本执行

若无特殊说明，测试脚本可以直接在 REPL 执行：

- 在串口终端中按 Ctrl+E 进入粘贴模式
- 复制粘贴代码
- 按 Ctrl+D 开始执行

或者上传到 `/mram` 文件系统中再导入并执行：

```bash
# 在 micropython 仓库根目录执行
python tools\pyboard.py --device your_com_port --baudrate 2000000 --filesystem cp /parh/to/py_script :/mram/py_script.py

# 在 REPL 中执行
import xxx
xxx.main()
```

## boot.py 和 main.py

可传到 `/mram` 中实现 上电/复位 时自动执行