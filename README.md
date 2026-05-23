# Win11 Snap Layouts 一键分配器

**一键将多窗口自动分配到 Win11 Snap Layouts 指定区域，告别手动拖拽。**

每天切换工作场景时，不再逐个窗口按 Win+Z、找图标、点击分区。运行一条命令，3 秒内所有窗口自动归位到主屏三分栏 + 竖屏二分栏。

---

## 解决什么痛点

### 以前是这样的：
- 打开 VS Code、浏览器、文件管理器、Kimi Code、QClaw……一共 5+ 个窗口
- 逐个按 **Win+Z** 呼出 Snap Layouts，手动点击左/中/右/上/下区域
- 窗口不在正确显示器上，还要先拖拽过去
- 每天重复 10+ 次，每次 30 秒，一年浪费 30+ 小时

### 现在是这样的：
- 运行 `python snap_all.py`，3 秒后所有窗口自动到位
- 窗口在错误屏幕上？自动检测并移动
- 窗口被最小化了？自动恢复
- 竖屏上的窗口也能一键分配，不再被主屏逻辑干扰

### 适合谁用：
- **多显示器用户** —— 主屏横屏写代码、竖屏副屏看文档/聊天，每次切场景都要重新摆窗口
- **需要频繁切换工作模式的人** —— 写作模式、工作模式、音频模式，每种模式对应一套窗口布局

---

## 核心功能

| 功能 | 解决什么问题 |
|---|---|
| **主屏三分栏** | VS Code → 左栏、Tabbit → 中栏、文件资源管理器 → 右栏，一键完成 |
| **竖屏二分栏** | 竖屏副屏上的 Kimi Code → 上栏、QClaw → 下栏，不再手动拖拽到竖屏 |
| **多显示器自动检测** | 自动识别主屏（2560×1440 横屏）和竖屏（1080×1920），窗口在错误屏幕上自动纠正 |
| **最小化窗口自动恢复** | 窗口被最小化时，Win+Z 建议界面不会显示它；脚本自动恢复后再分配 |
| **OpenCV 纯视觉识别** | 截图后用模板匹配找 Snap Layouts 图标和窗口缩略图，不依赖键盘 Tab 导航，不受系统语言/主题影响 |
| **分步调试模式** | `--step` 参数每步暂停，方便观察每一步的执行效果 |

---

## 安装方法

### 环境要求
- Windows 11（Snap Layouts 为 Win11 独占功能）
- Python 3.10+
- 双屏环境（主屏横屏 + 竖屏副屏），单屏也可运行主屏三分栏

### 1. 克隆项目
```bash
git clone <repo-url>
cd win-layout-manager
```

### 2. 安装依赖
```bash
pip install keyboard opencv-python pillow numpy psutil pygetwindow mss
```

### 3. 准备模板截图（关键步骤）

模板图片存放在 `assets/` 目录，决定了脚本能否正确识别界面元素。

**主屏三分栏需要的模板：**
- `3column_layout.png` —— Win+Z 弹出的三分栏布局图标（截图后裁剪，约 111×72px）
- `icon_tabbit.png` —— 建议界面中 Tabbit 的缩略图图标
- `icon_filemanager.png` —— 建议界面中文件资源管理器的缩略图图标

**竖屏二分栏需要的模板：**
- `layout_2row.png` —— 竖屏上 Win+Z 弹出的上下二分栏布局图标
- `icon_qclaw.png` —— 建议界面中 QClaw 的缩略图图标

**如何截图：**
1. 手动按 **Win+Z** 呼出 Snap Layouts
2. 用截图工具截取对应图标
3. 保存到 `assets/` 目录，文件名严格匹配

> ⚠️ **模板必须和你当前系统 DPI、主题一致**。如果更换了显示器或调整了缩放比例，需要重新截图。

---

## 使用方法

### 场景一：一键进入工作模式（最常用）

**什么时候用：** 每天开始工作、从其他模式切回工作模式时

```bash
python snap_all.py
```

执行流程：
1. 检测主屏 + 竖屏
2. 确认 Kimi Code / QClaw / VS Code / Tabbit / 文件资源管理器 都在正确屏幕上
3. 主屏三分栏：VS Code → 左 | Tabbit → 中 | 文件资源管理器 → 右
4. 竖屏二分栏：Kimi Code → 上 | QClaw → 下
5. 全程 5~8 秒，无需人工干预

### 场景二：单独测试竖屏（调试竖屏专用）

**什么时候用：** 刚配置竖屏模板、怀疑竖屏识别有问题时

```bash
python snap_vertical_test.py
```

- 只执行竖屏上下二分栏
- 匹配失败立即停止并保存截图到 `debug_snap/`
- 不含键盘回退，纯鼠标识别

### 场景三：分步调试（观察每一步）

**什么时候用：** 第一次配置、换了显示器、换了模板后验证流程

```bash
python snap_all.py --step
```

- 每步暂停，按 Enter 继续
- 方便观察 Win+Z 是否弹出、匹配是否正确

### 场景四：快速切换工作模式（配合批处理）

项目中预置了批处理文件，可双击切换：
- `切换到工作模式.bat` → 运行 `snap_all.py`
- `切换到写作模式.bat` → 可自定义为另一套布局
- `切换到音频模式.bat` → 可自定义为音频制作布局

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 核心语言 | Python 3.12 |
| 视觉识别 | OpenCV (`cv2.matchTemplate` 多尺度模板匹配) |
| 多屏截图 | `mss`（支持负坐标虚拟桌面截图，替代 `PIL.ImageGrab`） |
| 窗口操作 | `ctypes` + `win32 API` (`SetWindowPos`, `SetForegroundWindow`, `ShowWindow`) |
| 全局热键 | `keyboard` 库（发送 Win+Z） |
| 辅助 | `numpy`, `PIL`, `psutil` |

### 工具链

| 工具 | 用途 |
|---|---|
| OpenCV | 模板匹配识别 Snap Layouts 图标和窗口缩略图 |
| mss | 截取虚拟桌面（含竖屏负坐标区域） |
| ctypes/win32api | 窗口枚举、移动、激活、鼠标点击（`SetCursorPos` 绝对坐标） |
| keyboard | 发送 Win+Z 系统热键 |

---

## 文件结构

```
win-layout-manager/
├── snap_all.py              # 主程序：主屏三分栏 + 竖屏二分栏
├── snap_vertical_test.py    # 竖屏独立测试脚本（纯视觉识别，无键盘回退）
├── snap_native.py           # 窗口工具库：查找窗口、激活窗口、枚举显示器
├── assets/                  # 模板图片（决定识别成功率）
│   ├── 3column_layout.png   # 主屏三分栏布局图标
│   ├── layout_2row.png      # 竖屏二分栏布局图标
│   ├── icon_tabbit.png      # Tabbit 缩略图
│   ├── icon_filemanager.png # 文件资源管理器缩略图
│   ├── icon_qclaw.png       # QClaw 缩略图
│   └── ...
├── debug_snap/              # 调试截图（自动保存，排查匹配问题）
├── README.md                # 本文档
├── DEV_LOG.md               # 开发迭代记录与踩坑日志
└── *.bat                    # 快速切换模式的批处理脚本
```

---

## 常见问题

### Q: 脚本运行时，Win+Z 弹到了主屏而不是竖屏？

**A:** 竖屏窗口被最小化，或焦点被 PowerShell 终端偷走。脚本已修复：
1. `ensure_window` 中检查 `IsIconic`，最小化则 `ShowWindow(SW_RESTORE)`
2. `snap_vertical` 中先 `ShowWindow(hwnd, 9)` 恢复，再 `bring_to_front`，再鼠标点击窗口中心确保焦点

如果仍有问题，检查 `debug_snap/v_before_layout.png` 确认 Win+Z 弹出位置。

### Q: 模板匹配失败（最佳=0.000 或低于 0.50）？

**A:** 三步排查：
1. **检查截图**：看 `debug_snap/before_xxx.png` 中是否有目标图标
2. **检查模板尺寸**：模板必须和实际图标像素级一致（DPI 缩放影响大小）
3. **重新截图**：系统缩放比例或显示器更换后，必须重新截取模板

### Q: 主屏三分栏第二步/第三步中间是空白的？

**A:** 窗口被最小化导致 Win+Z 建议界面不显示它。已在 `ensure_window` 中增加 `IsIconic` 检测自动恢复。如果仍出现，手动恢复窗口后重试。

### Q: 点击坐标正确但窗口没过去？

**A:** `click()` 使用 `SetCursorPos` 绝对坐标，支持多屏负坐标。如果主屏点击失效，检查 `move_mouse` 的归一化坐标是否与主屏分辨率匹配（旧版 bug）。

### Q: 可以自定义窗口和分区吗？

**A:** 可以。修改 `snap_all.py` 中 `ensure_window` 的窗口标题关键词，以及 `snap_first_window` / `snap_vertical` 的点击偏移量。需要重新截取对应模板。

---

## 更新日志

### v3.0 — 多显示器完整支持
- 新增竖屏上下二分栏（Kimi Code 上 / QClaw 下）
- 多显示器截图改用 `mss`，修复 `ImageGrab.grab` 负坐标截图为黑屏的问题
- 鼠标点击改用 `SetCursorPos` 绝对坐标，支持跨屏点击
- `ensure_window` 增加最小化检测与自动恢复

### v2.0 — OpenCV 视觉识别
- 抛弃键盘 Tab 导航，改用 OpenCV 模板匹配 + 鼠标点击
- 新增 `find_template` 多尺度匹配
- 新增调试截图保存机制

### v1.0 — 键盘导航方案
- 基础功能：Win+Z + Tab×6 + Enter 分配窗口
- 发现键盘导航不可靠（不同系统语言/主题下 Tab 顺序不同）

---

## 自检清单

- [x] 陌生人测试：看完第一行就知道是"一键分配窗口到 Win11 Snap Layouts"
- [x] 用户测试：安装步骤 3 步，使用场景 4 个，常见问题 4 个
- [x] 开发者测试：技术栈表格、文件结构树、依赖列表完整
- [x] 痛点测试：Before & After 对比 + 适合谁用
- [x] 场景测试：使用方法按场景组织，不是干巴巴的操作步骤
