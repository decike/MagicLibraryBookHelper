# 魔法图书馆整理助手 (Magic Library Book Helper)

这是一个用于游戏《图书管理员：整理魔法图书馆吧！》的外部辅助脚本。

**声明：本项目的大部分代码和文档由 AI（大语言模型）辅助生成，仅供个人学习、游戏辅助使用。**

## ✨ 功能
- 自动识别游戏左上角的书本列表（书名与 Vol 卷号）。
- 根据内置的 `catalog.txt` 目录，自动匹配并显示该书对应的书架号（如 `1M：破坏魔法`）。
- 在游戏画面右侧以带黑边的白字显示，鼠标可穿透，不影响游戏操作。
- 自动适应不同分辨率（基于 2560x1440 缩放）。

## 🚀 直接运行（Python 环境）

### 1. 安装依赖
确保电脑已安装 Python 3.8+，然后在当前目录打开终端，执行：
```bash
pip install -r requirements.txt
```

### 2. 准备目录文件
确保 `catalog.txt` 与脚本在同一目录下。`catalog.txt` 内容格式如下：
```text
1A：魔物学
《魔兽行为学》
《魔兽生态图鉴》
...
2Q：语言
《多种族沟通术》
...
```

### 3. 运行脚本
```bash
python book_shelf_overlay.py
```

### 4. 游戏设置
**必须**将游戏设置为“无边框窗口（Borderless Windowed）”或“窗口化全屏”模式，否则透明覆盖层会被游戏画面遮挡。

## 📦 打包成 EXE（发给朋友用）

如果你想把脚本打包成独立的 exe 文件发给没有 Python 环境的朋友，请使用 PyInstaller。

### 1. 安装打包工具
```bash
pip install pyinstaller
```

### 2. 执行打包命令
在 `magic` 文件夹下打开终端，执行：
```bash
pyinstaller -F --collect-all rapidocr_onnxruntime --collect-all cv2 book_shelf_overlay.py
```
> **参数说明**：
> - `-F`：打包成单个独立的 exe 文件。
> - `--collect-all`：确保 OCR 模型和 OpenCV 依赖被完整打包。

### 3. 发送给朋友
打包完成后，在 `dist` 文件夹中找到 `book_shelf_overlay.exe`。
**重要**：必须将 `book_shelf_overlay.exe` 和 `catalog.txt` 放在同一个文件夹中，一起打包成 zip 发送给朋友。

## ⚠️ 注意事项
1. 如果识别不准，可以调整 `book_shelf_overlay.py` 顶部的 `MATCH_CUTOFF` 阈值（默认 60），调低到 50 或 55 可增加容错率。
2. 如果游戏分辨率不是 2560x1440，脚本会自动按比例缩放。如果发现位置错乱，请修改脚本顶部的 `BASE_W` 和 `BASE_H` 为基础分辨率。
3. 如果使用 exe 版本且没有加 `-w` 参数，想退出程序时，直接关闭黑色命令行窗口，或在其内按 `Ctrl+C` 即可。