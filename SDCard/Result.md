# base_wr.py

注意此脚本只能直接在 REPL 执行。此脚本测试 SDCard 的基本读写功能，将尝试初始化并挂载 SDCard，若成功，则通过文件流在 SDCard 上创建文件并进行简单读写。涉及的非标准 API：

- `class machine.SDCard()` 
    - `init()` 
    - `readblocks(block_num, buf)` 
    - `writeblocks(block_num, buf)` 
- `class vfs.VfsFat(block_dev)` 
    - `mount(fsobj, mount_point, *, readonly)` 

## 硬件连接

- 一张 SD Card

## 运行结果

![](./Result.assets/Snipaste_2026-08-07_10-05-12.png)

## 注意事项

- 如果未能识别或挂载 SD Card 的已有格式，程序将格式化 SD Card 并重新建立文件系统