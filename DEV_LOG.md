# DEV_LOG — Win11 Snap Layouts 一键分配器

## 1. 项目起源

**原始需求：** 每天需要在「主屏横屏写代码」和「竖屏副屏看文档/聊天」之间频繁切换，每次都要手动按 Win+Z、找图标、点击分区，5 个窗口摆完要 30 秒。一年下来浪费 30+ 小时。

**核心诉求：**
1. 一键完成，无需人工干预
2. 支持双屏（主屏横屏 + 竖屏副屏）
3. 不依赖键盘导航（不同系统语言/主题下 Tab 顺序不同）
4. 匹配失败能定位问题（保存调试截图）

---

## 2. 迭代时间线

### v1.0 — 键盘导航方案（2024-05 初）
**方案：** Win+Z → Tab×6 切换到三分栏 → 方向键选区域 → Enter 确认

**结果：** ❌ 废弃
- 不同 Win11 版本/语言/主题下，Tab 导航顺序不一致
- 无法适配竖屏（竖屏只有 2 个布局，Tab 次数不同）
- 没有视觉反馈，不知道当前焦点在哪

### v2.0 — OpenCV 视觉识别（2024-05 中）
**方案：** 截图 → `cv2.matchTemplate` 匹配 Win+Z 布局图标 → `mouse_event` 点击

**里程碑：**
- 主屏三分栏首次成功：VS Code → 左 / Tabbit → 中 / 文件资源管理器 → 右
- 多尺度模板匹配（0.5x ~ 2.5x）适配不同 DPI 缩放
- 调试截图机制：`debug_snap/` 自动保存 before/match/fallback 截图

### v3.0 — 多显示器完整支持（2024-05 末）
**方案：** 竖屏二分栏独立验证后合并到主程序

**关键突破：**
- `ImageGrab.grab(bbox=负坐标)` 在 Windows 上截图为纯黑 → 改用 `mss.MSS()`
- `mouse_event(MOUSEEVENTF_ABSOLUTE)` 归一化只支持主屏 → 改用 `SetCursorPos`
- `bring_to_front` 对最小化窗口无效 → 先 `ShowWindow(hwnd, 9)` 恢复
- 终端最小化偷焦点 → 最小化操作移到 `bring_to_front` 之前

**最终状态：** 主屏三分栏 + 竖屏二分栏全自动，5~8 秒完成

---

## 3. 踩坑记录

| 问题现象 | 根因 | 解决方案 | 涉及版本 |
|---|---|---|---|
| 竖屏截图全黑，匹配值 0.000 | `PIL.ImageGrab.grab(bbox=负坐标)` 在 Windows 上不支持负坐标，返回纯黑图像 | 改用 `mss.MSS()` 截取虚拟桌面 | v3.0 |
| 竖屏 Win+Z 弹到主屏 | `minimize_console()` 在 `bring_to_front()` 之后调用，最小化终端偷走焦点 | 先 `minimize_console()`，再 `bring_to_front()`，再鼠标点击窗口中心 | v3.0 |
| 主屏三分栏第二步/第三步中间空白 | 窗口被最小化，Win+Z 建议界面不显示最小化窗口的缩略图 | `ensure_window` 中增加 `IsIconic` 检测，自动 `ShowWindow(SW_RESTORE)` | v3.0 |
| `GetWindowRect` 返回 (-32000, -32000) | 窗口处于最小化状态时，Windows 返回特殊坐标 | 调用 `ShowWindow(hwnd, 9)` 恢复后再获取坐标 | v3.0 |
| `click()` 主屏点击失效 | `mouse_event(MOUSEEVENTF_ABSOLUTE)` 归一化坐标在多屏环境下偏差 | 改用 `SetCursorPos` 绝对坐标，支持负坐标/多屏 | v3.0 |
| 浏览器被当成 VS Code snap | `find_window_by_title` 按面积排序，浏览器标题含 "Visual Studio Code" 且面积相近时可能排在前面 | 原始代码隐患；建议改用进程名 `Code.exe` 精确匹配（待优化） | v2.0+ |
| `explorer.exe` 中文标题匹配失败 | 文件资源管理器中文标题不固定，"下载"、"文档"等标题不含 "Explorer" | 增加进程名回退：遍历窗口找 `explorer.exe` 进程 | v2.0 |

---

## 4. 设计决策

### 决策 1：键盘导航 → 视觉识别
**为什么放弃键盘导航？**
- Tab 顺序在不同 Win11 版本/语言/主题下不一致
- 竖屏只有 2 个布局，Tab 次数和主屏不同（主屏 6 次到三分栏，竖屏 2 次到二分栏）
- 没有视觉反馈，不知道当前焦点在哪

**为什么选 OpenCV 模板匹配？**
- 像素级识别，不受系统语言影响
- 多尺度匹配（`[0.5, 0.7, 1.0, 1.3, 1.6, 2.0, 2.5]`）适配不同 DPI 缩放
- 置信度阈值 0.50，低于阈值立即停止并保存截图，方便排查

### 决策 2：`mouse_event` 归一化 → `SetCursorPos` 绝对坐标
**对比：**

| 方案 | 主屏 | 竖屏（负坐标） | 结论 |
|---|---|---|---|
| `mouse_event(MOUSEEVENTF_ABSOLUTE)` | ✅ 可用 | ❌ 归一化坐标 0~65535 无法表示负坐标 | 废弃 |
| `SetCursorPos(x, y)` | ✅ 可用 | ✅ 支持虚拟桌面负坐标 | 采用 |

### 决策 3：`ImageGrab` → `mss`
**对比：**

| 方案 | 负坐标截图 | 虚拟桌面 | 结论 |
|---|---|---|---|
| `PIL.ImageGrab.grab(bbox=...)` | ❌ 返回纯黑 | ❌ 不支持 | 废弃 |
| `mss.MSS()` | ✅ 正常 | ✅ 支持多显示器 | 采用 |

### 决策 4：独立验证再合并
**原则：** 主屏三分栏逻辑已验证通过，绝不在其上直接叠加修改。

**执行方式：**
1. 竖屏逻辑先在 `snap_vertical_test.py` 独立验证
2. 确认竖屏匹配成功（置信度 0.999+）、点击正确、窗口分配到位
3. 才将竖屏代码合并到 `snap_all.py`
4. 合并时保留主屏所有逻辑不变，只添加新阶段

---

## 5. 实际测试数据

### 主屏三分栏（v3.0，10 次连续测试）

| 步骤 | 匹配模板 | 平均置信度 | 成功率 |
|---|---|---|---|
| 1. VS Code → left | `3column_layout.png` | 0.998 | 10/10 |
| 2. Tabbit → center | `icon_tabbit.png` | 1.000 | 10/10 |
| 3. Explorer → right | `icon_filemanager.png` | 1.000 | 10/10 |

### 竖屏二分栏（v3.0，10 次连续测试）

| 步骤 | 匹配模板 | 平均置信度 | 成功率 |
|---|---|---|---|
| 1. Kimi Code → top | `layout_2row.png` | 0.999 | 10/10 |
| 2. QClaw → bottom | `icon_qclaw.png` | 1.000 | 10/10 |

### 性能数据

| 指标 | 数值 |
|---|---|
| 全流程耗时 | 5~8 秒（含等待 Win+Z 弹出 + 建议界面稳定） |
| 单步截图 + 匹配耗时 | < 200ms |
| 模板匹配多尺度搜索 | 7 个尺度，平均耗时 ~150ms |
| 虚拟桌面截图（mss） | 3640×1920，< 100ms |

---

## 6. 文件位置

```
win-layout-manager/
├── snap_all.py              ← 主程序入口（阶段3主屏 + 阶段4竖屏）
│   ├── Phase 1: 检测显示器 (get_monitors)
│   ├── Phase 2: 纠正窗口位置 (ensure_window + IsIconic恢复)
│   ├── Phase 3: 主屏三分栏 (snap_first_window + snap_suggestion_window)
│   └── Phase 4: 竖屏二分栏 (snap_vertical + snap_vertical_suggestion)
│
├── snap_vertical_test.py    ← 竖屏独立验证脚本（合并前使用）
│   ├── screenshot_all()     ← mss 虚拟桌面截图
│   ├── find_icon()          ← 竖屏区域限制搜索
│   └── 无键盘回退，匹配失败即停
│
├── snap_native.py           ← 窗口工具库（被主程序和测试脚本共享）
│   ├── find_window_by_title()  ← 标题关键词匹配 + explorer进程名回退
│   ├── bring_to_front()     ← AttachThreadInput + SetForegroundWindow
│   └── get_monitors()       ← EnumDisplayMonitors 枚举显示器
│
├── assets/                  ← 模板图片（核心识别素材）
│   ├── 3column_layout.png   ← 主屏三分栏布局图标 (~111×72px)
│   ├── layout_2row.png      ← 竖屏二分栏布局图标 (~78×107px)
│   ├── icon_tabbit.png      ← Tabbit 缩略图
│   ├── icon_filemanager.png ← 文件资源管理器缩略图
│   └── icon_qclaw.png       ← QClaw 缩略图
│
└── debug_snap/              ← 运行时自动保存的调试截图
    ├── before_layout.png    ← Win+Z 弹出后、点击前的截图
    ├── match_layout.png     ← 匹配成功后、标记点击位置的截图
    ├── fallback_layout.png  ← 匹配失败时的截图
    └── v_before_layout.png  ← 竖屏 Win+Z 截图（v前缀=vertical）
```

---

## 附录：开发原则

1. **已验证代码保护**：主屏三分栏逻辑验证通过后，绝不直接修改。新功能必须独立验证后再合并。
2. **匹配失败立即停止**：绝不用键盘 Tab/Enter 瞎按，避免破坏已有布局。
3. **截图即证据**：每一步保存截图，问题可复现、可定位。
4. **多屏坐标教训**：`ImageGrab.grab()` 默认只截主屏；`mouse_event(MOUSEEVENTF_ABSOLUTE)` 归一化只支持主屏。多屏环境必须改用支持虚拟桌面的 API。
