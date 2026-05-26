#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Win11 Snap Layouts 一键分配器 — 主屏三分栏专用

主屏: VS Code(左) | Tabbit(中) | 文件资源管理器(右)
竖屏: Kimi Code / QClaw 只做位置检测，不参与 Snap

用法:
  python snap_all.py
"""

import sys
import time
import argparse
import os
import ctypes
import keyboard
import cv2
import numpy as np
from PIL import ImageGrab
import mss

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snap_native import find_window_by_title, bring_to_front

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

user32 = ctypes.windll.user32
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")

# ==============================================================================
# 程序自动启动配置
# ==============================================================================
# 当脚本找不到对应窗口时，会自动启动这里配置的可执行文件。
# 如果某个程序已经常驻后台，或者不需要自动启动，设为 None 即可。
# 支持相对路径和绝对路径。请根据你电脑上的实际安装位置修改。
APP_CONFIGS = {
    # 主屏三分栏
    "Visual Studio Code": r"C:\Users\15403\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "Tabbit": None,                     # 浏览器/Web 应用，通常已打开
    "Explorer": None,                   # 文件资源管理器，脚本内部有特殊处理

    # 竖屏二分栏
    "Kimi Code": r"C:\Users\15403\AppData\Local\Programs\kimi-desktop\Kimi.exe",
    "QClaw": None,                      # 请填写实际路径，例如 r"C:\Path\To\QClaw.exe"
}
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)

# Virtual desktop metrics for multi-monitor screenshot
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
VIRTUAL_X = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
VIRTUAL_Y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
VIRTUAL_W = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
VIRTUAL_H = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

# Mouse constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000

# Template cache: pre-load images to avoid repeated disk I/O
_TEMPLATE_CACHE = {}


def load_template(template_path):
    """Load template from disk or cache. Returns BGR numpy array."""
    if template_path in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[template_path]
    if not os.path.exists(template_path):
        return None
    file_bytes = np.fromfile(template_path, dtype=np.uint8)
    template = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if template is not None:
        _TEMPLATE_CACHE[template_path] = template
    return template


def move_mouse(x, y):
    abs_x = int(x * 65535 / SCREEN_WIDTH)
    abs_y = int(y * 65535 / SCREEN_HEIGHT)
    user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)


def click(x, y, description=""):
    print(f"   🖱️  点击 {description}: ({int(x)}, {int(y)})")
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.02)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.03)  # 从 0.1s 削减到 0.03s，Win11 UI 响应足够快


def take_screenshot():
    """Screenshot primary monitor only (same as v5)."""
    img = ImageGrab.grab()
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def screenshot_all():
    """Screenshot entire virtual desktop (all monitors)."""
    with mss.MSS() as sct:
        monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)
        arr = np.array(screenshot)
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)


def save_debug_screenshot(name, click_x=None, click_y=None):
    # 调试截图已禁用以提升速度（PNG写磁盘是最大瓶颈，单次200-500ms）
    # 如需排查匹配问题，手动取消注释下方代码：
    # debug_dir = os.path.join(SCRIPT_DIR, "debug_snap")
    # os.makedirs(debug_dir, exist_ok=True)
    # screenshot = take_screenshot()
    # if click_x is not None and click_y is not None:
    #     cv2.drawMarker(screenshot, (int(click_x), int(click_y)), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
    # cv2.imwrite(os.path.join(debug_dir, f"{name}.png"), screenshot)
    pass


def save_debug_all(name, click_x=None, click_y=None):
    # 调试截图已禁用以提升速度
    pass


def get_window_center(hwnd):
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(int(hwnd), ctypes.byref(rect))
    return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2


def find_icon(template_path, search_region=None):
    """Find template on virtual desktop. Returns (screen_x, screen_y, scale, w, h) or None."""
    template = load_template(template_path)
    if template is None:
        print(f"   ❌ 模板不存在或无法读取: {os.path.basename(template_path)}")
        return None

    img = screenshot_all()
    if search_region:
        x1, y1, x2, y2 = search_region
        img = img[y1:y2, x1:x2]
        off_x, off_y = x1, y1
    else:
        off_x, off_y = 0, 0

    best = None
    best_val = 0
    best_scale = 1.0
    best_w, best_h = template.shape[1], template.shape[0]

    # Fast path: try 1.0x first
    for scale in [1.0, 0.7, 1.3, 0.5, 1.6, 2.0, 2.5]:
        resized = cv2.resize(template, None, fx=scale, fy=scale)
        h, w = resized.shape[:2]
        if h > img.shape[0] or w > img.shape[1]:
            continue
        result = cv2.matchTemplate(img, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_val:
            best_val = max_val
            sx = off_x + max_loc[0] + w // 2 + VIRTUAL_X
            sy = off_y + max_loc[1] + h // 2 + VIRTUAL_Y
            best = (sx, sy)
            best_scale = scale
            best_w, best_h = w, h
        if scale == 1.0 and max_val >= 0.70:
            break

    if best and best_val >= 0.45:  # 阈值从 0.50 降到 0.45，给边缘情况余量
        print(f"   ✅ 匹配: 置信度={best_val:.3f} 屏幕坐标=({int(best[0])}, {int(best[1])})")
        return (*best, best_scale, best_w, best_h)
    else:
        print(f"   ❌ 匹配失败 (最佳={best_val:.3f})")
        return None


def find_template(template_path, confidence=0.55):
    """Multiscale template matching on primary monitor screenshot."""
    template = load_template(template_path)
    if template is None:
        print(f"   ❌ 模板不存在或无法读取: {os.path.basename(template_path)}")
        return None

    screenshot = take_screenshot()

    best_match = None
    best_val = 0
    best_scale = 1.0
    best_w, best_h = template.shape[1], template.shape[0]

    # Fast path: try 1.0x first (99% match at 1.0x based on actual data)
    for scale in [1.0, 0.7, 1.3, 0.5, 1.6, 2.0, 2.5]:
        resized = cv2.resize(template, None, fx=scale, fy=scale)
        h, w = resized.shape[:2]
        if h > screenshot.shape[0] or w > screenshot.shape[1]:
            continue

        result = cv2.matchTemplate(screenshot, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_val:
            best_val = max_val
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            best_match = (center_x, center_y)
            best_scale = scale
            best_w, best_h = w, h
        # Early exit: if 1.0x already has very high confidence, skip remaining scales
        if scale == 1.0 and max_val >= 0.70:
            break

    if best_match and best_val >= confidence:
        print(f"   ✅ 匹配: 置信度={best_val:.3f} 缩放={best_scale:.1f}x")
        return (*best_match, best_scale, best_w, best_h)
    else:
        print(f"   ❌ 匹配失败 (最佳={best_val:.3f} < {confidence})")
        return None


def snap_first_window(hwnd, zone):
    """VS Code: Win+Z → match 3column_layout.png → click left zone."""
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE: 先恢复窗口（如果被最小化）
    time.sleep(0.05)  # 削减: 0.1 → 0.05
    bring_to_front(hwnd)
    print("   → Win+Z 打开 Snap Layouts...")
    keyboard.send('win+z')
    time.sleep(0.4)  # VS Code 的 Win+Z 弹出需要稍长时间确保动画完成

    template_path = os.path.join(ASSETS_DIR, "3column_layout.png")
    print(f"   🔍 搜索布局模板...")
    save_debug_screenshot("before_layout")
    result = find_template(template_path, confidence=0.50)

    if result:
        center_x, center_y, scale, w, h = result
        click_x = center_x - w // 3  # left zone
        click_y = center_y
        save_debug_screenshot("match_layout", click_x, click_y)
        click(click_x, click_y, "3column.left")
        time.sleep(0.2)
    else:
        print("   → 回退到 Tab×6...")
        save_debug_screenshot("fallback_layout")
        for _ in range(6):
            keyboard.send('tab')
            time.sleep(0.1)
        keyboard.send('enter')
        time.sleep(0.2)


def snap_suggestion_window(icon_name, description):
    """Click suggestion thumbnail (Tabbit / FileManager)."""
    template_path = os.path.join(ASSETS_DIR, f"icon_{icon_name}.png")
    print(f"   🔍 搜索缩略图: icon_{icon_name}.png...")
    print(f"   ⏳ 等待缩略图稳定...")
    time.sleep(0.2)

    save_debug_screenshot(f"before_{icon_name}")
    result = find_template(template_path, confidence=0.50)

    if result:
        click_x, click_y = result[0], result[1]
        save_debug_screenshot(f"match_{icon_name}", click_x, click_y)
        click(click_x, click_y, description)
    else:
        print(f"   ⚠️  未找到，回退到 Enter...")
        save_debug_screenshot(f"fallback_{icon_name}")
        keyboard.send('enter')
        time.sleep(0.2)


def snap_vertical(hwnd, layout_template, zone_offset_desc, vregion):
    """Snap window on vertical monitor: Win+Z → match layout → click zone."""
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.05)  # 削减: 0.1 → 0.05
    bring_to_front(hwnd)
    # 移除冗余 sleep: bring_to_front 已确保窗口前置

    cx, cy = get_window_center(hwnd)
    print(f"   🖱️  点击窗口中心确保焦点: ({cx}, {cy})")
    click(cx, cy, "window.center")
    # 移除冗余 sleep: click 内部已有 0.03s post-delay

    print("   → Win+Z...")
    keyboard.send('win+z')
    time.sleep(0.2)

    save_debug_all("v_before_layout")
    result = find_icon(layout_template, search_region=vregion)

    if not result:
        save_debug_all("v_fail_layout")
        print("   ❌ 竖屏布局匹配失败")
        return False

    sx, sy, scale, w, h = result
    if zone_offset_desc == "top":
        click_x = sx
        click_y = sy - int(h * 0.25)
    else:  # bottom
        click_x = sx
        click_y = sy + int(h * 0.25)

    save_debug_all("v_click_layout", click_x, click_y)
    click(click_x, click_y, f"2row.{zone_offset_desc}")
    return True


def snap_vertical_suggestion(hwnd, icon_template, vregion):
    """Click suggestion thumbnail on vertical monitor."""
    print(f"   ⏳ 等待建议界面渲染...")
    time.sleep(0.6)  # Win11 需要时间来渲染 bottom 区域的建议缩略图
    save_debug_all("v_before_suggestion")
    result = find_icon(icon_template, search_region=vregion)
    if not result:
        save_debug_all("v_fail_suggestion")
        print("   ❌ 建议界面匹配失败")
        return False
    click_x, click_y = result[0], result[1]
    save_debug_all("v_click_suggestion", click_x, click_y)
    click(click_x, click_y, "suggestion")
    return True


# ============ Monitor Detection (for position correction only) ============
class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.c_uint32),
    ]


def get_monitors():
    monitors = []
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(mi)
        user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        monitors.append({
            'handle': hMonitor,
            'rect': (rect.left, rect.top, rect.right, rect.bottom),
            'work': (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom),
            'is_primary': bool(mi.dwFlags & 1),
            'width': width,
            'height': height,
            'is_vertical': width < height,
        })
        return True
    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_long)
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
    return monitors


def get_monitor_by_type(monitors, monitor_type):
    if monitor_type == "primary":
        primary = [m for m in monitors if m['is_primary']]
        if primary:
            return primary[0]
        return max(monitors, key=lambda m: m['width'])
    elif monitor_type == "vertical":
        vertical = [m for m in monitors if m['is_vertical']]
        if vertical:
            return min(vertical, key=lambda m: m['rect'][0])
        return None
    return None


def get_window_monitor(hwnd):
    return user32.MonitorFromWindow(hwnd, 2)


def move_window_to_monitor(hwnd, monitor):
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    work = monitor['work']
    x = work[0] + (work[2] - work[0] - w) // 2
    y = work[1] + (work[3] - work[1] - h) // 2
    SWP_NOZORDER = 0x0004
    user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER)
    time.sleep(0.05)  # 削减: 0.1 → 0.05，窗口动画足够快


def ensure_window(keyword, exe, target_monitor_type, monitors):
    print(f"\n🔍 检查: {keyword}")
    hwnd, title = find_window_by_title(keyword)
    
    if not hwnd and exe:
        print(f"   🚀 启动: {exe}")
        os.startfile(exe)
        time.sleep(1.5)
        hwnd, title = find_window_by_title(keyword)
    
    if not hwnd:
        print(f"   ❌ 未找到: {keyword}")
        return None, None
    
    print(f"   ✅ 找到: {title or keyword}")
    
    target_monitor = get_monitor_by_type(monitors, target_monitor_type)
    if target_monitor:
        current_hmon = get_window_monitor(hwnd)
        if current_hmon != target_monitor['handle']:
            print(f"   🔄 移动到 {target_monitor_type}...")
            bring_to_front(hwnd)
            move_window_to_monitor(hwnd, target_monitor)
            print(f"   ✅ 已移动")
        else:
            print(f"   ✅ 已在 {target_monitor_type}")
    
    # 恢复最小化窗口（否则 Win+Z 建议界面不会显示它）
    if user32.IsIconic(hwnd):
        print(f"   🔄 窗口被最小化，恢复中...")
        user32.ShowWindow(hwnd, 9)
        time.sleep(0.1)
    
    return hwnd, title


# ============ Main ============
def snap_three_zones(step_by_step=False):
    print("=" * 60)
    print("🖥️  Win11 Snap Layouts — 主屏三分栏")
    print("=" * 60)
    print()
    print("主屏: VS Code → left | Tabbit → center | 文件资源管理器 → right")
    print("竖屏: Kimi Code / QClaw 只检测位置，不参与 Snap")
    print()

    if step_by_step:
        input("⏳ 按 Enter 开始...")
    else:
        print("⏳ 开始...")
        time.sleep(0.05)  # 削减初始等待: 0.1 → 0.05

    # Phase 1: Detect monitors
    print("\n" + "=" * 60)
    print("🔎 阶段1: 检测显示器")
    print("-" * 60)
    monitors = get_monitors()
    print(f"   发现 {len(monitors)} 个显示器")
    for i, m in enumerate(monitors):
        orientation = "竖屏" if m['is_vertical'] else "横屏"
        primary = " [主屏]" if m['is_primary'] else ""
        print(f"     显示器{i}: {m['width']}x{m['height']} {orientation}{primary}")

    # Phase 2: Ensure all windows on correct monitors
    print("\n" + "=" * 60)
    print("🔎 阶段2: 纠正窗口位置")
    print("-" * 60)
    
    kim_hwnd, _ = ensure_window("Kimi Code", APP_CONFIGS.get("Kimi Code"), "vertical", monitors)
    qclaw_hwnd, _ = ensure_window("QClaw", APP_CONFIGS.get("QClaw"), "vertical", monitors)
    
    vc_hwnd, _ = ensure_window("Visual Studio Code", APP_CONFIGS.get("Visual Studio Code"), "primary", monitors)
    tb_hwnd, _ = ensure_window("Tabbit", APP_CONFIGS.get("Tabbit"), "primary", monitors)
    fm_hwnd, _ = ensure_window("Explorer", APP_CONFIGS.get("Explorer"), "primary", monitors)

    if not vc_hwnd:
        print("❌ VS Code 未就绪，中止")
        return

    # Phase 3: Primary screen — 3column
    print("\n" + "=" * 60)
    print("🎯 阶段3: 主屏三分栏")
    print("=" * 60)

    # VS Code → left
    print(f"\n{'='*60}")
    print("[1/3] 🎯 VS Code → left")
    print("-" * 60)
    snap_first_window(vc_hwnd, "left")
    print("   ✅ VS Code 已分配到 left")

    # Tabbit → center
    print(f"\n{'='*60}")
    print("[2/3] 🎯 Tabbit → center")
    print("-" * 60)
    if step_by_step:
        input("⏳ 按 Enter 继续...")
    snap_suggestion_window("tabbit", "Tabbit")
    print("   ✅ Tabbit 已分配到 center")

    # FileManager → right
    print(f"\n{'='*60}")
    print("[3/3] 🎯 文件资源管理器 → right")
    print("-" * 60)
    if step_by_step:
        input("⏳ 按 Enter 继续...")
    snap_suggestion_window("filemanager", "文件资源管理器")
    print("   ✅ 文件资源管理器 已分配到 right")

    print()
    print("=" * 60)
    print("✅ 主屏三分栏完成！")
    print("=" * 60)

    # Phase 4: Vertical screen — 2row
    print("\n" + "=" * 60)
    print("🎯 阶段4: 竖屏上下二分栏")
    print("=" * 60)

    vert = get_monitor_by_type(monitors, "vertical")
    if vert and kim_hwnd and qclaw_hwnd:
        vx1 = vert['rect'][0] - VIRTUAL_X
        vy1 = vert['rect'][1] - VIRTUAL_Y
        vx2 = vert['rect'][2] - VIRTUAL_X
        vy2 = vert['rect'][3] - VIRTUAL_Y
        vregion = (vx1, vy1, vx2, vy2)

        # Kimi Code → top
        print(f"\n{'='*60}")
        print("[4a/4] 🎯 Kimi Code → top")
        print("-" * 60)
        layout_path = os.path.join(ASSETS_DIR, "layout_2row.png")
        ok = snap_vertical(kim_hwnd, layout_path, "top", vregion)
        if ok:
            print("   ✅ Kimi Code 已分配到 top")
            # QClaw → bottom：Win11 自动显示建议缩略图，直接点击即可
            print(f"\n{'='*60}")
            print("[4b/4] 🎯 QClaw → bottom")
            print("-" * 60)
            icon_path = os.path.join(ASSETS_DIR, "icon_qclaw.png")
            ok2 = snap_vertical_suggestion(qclaw_hwnd, icon_path, vregion)
            if ok2:
                print("   ✅ QClaw 已分配到 bottom")
            else:
                print("   ⚠️ QClaw 分配失败")
        else:
            print("   ⚠️ Kimi Code 分配失败，跳过竖屏")
    else:
        # 明确提示具体是哪个条件不满足，方便排查
        if not vert:
            print("   ℹ️ 竖屏显示器未检测到，跳过")
        elif not kim_hwnd:
            print("   ℹ️ Kimi Code 窗口未找到（且未配置自动启动路径），跳过竖屏")
        elif not qclaw_hwnd:
            print("   ℹ️ QClaw 窗口未找到（且未配置自动启动路径），跳过竖屏")
        else:
            print("   ℹ️ 竖屏未就绪，跳过")

    print()
    print("=" * 60)
    print("✅ 全部完成！")
    print("=" * 60)
    print(f"\n📁 调试截图: {os.path.join(SCRIPT_DIR, 'debug_snap')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", action="store_true", help="分步执行")
    args = parser.parse_args()
    snap_three_zones(step_by_step=args.step)


if __name__ == "__main__":
    main()
