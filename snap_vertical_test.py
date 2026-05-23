#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竖屏上下二分栏 — 独立测试脚本（纯鼠标识别，无键盘回退）

原则：
  1. Win+Z 必须在竖屏上弹出
  2. 截图找 layout_2row.png → 鼠标点击上栏
  3. 匹配失败就停，保存截图，绝不自动按键盘

用法:
  python snap_vertical_test.py
"""

import sys
import time
import os
import ctypes
import keyboard
import cv2
import numpy as np
from PIL import ImageGrab
import mss

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snap_native import find_window_by_title, bring_to_front
from snap_all import (
    get_monitors, get_monitor_by_type, ensure_window, MONITORINFO
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")

# Virtual desktop
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
VIRTUAL_X = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
VIRTUAL_Y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
VIRTUAL_W = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
VIRTUAL_H = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)


def screenshot_all():
    with mss.mss() as sct:
        # monitor[0] is the virtual desktop containing all monitors
        monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)
        arr = np.array(screenshot)
        # mss returns BGRA, convert to BGR
        bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    print(f"   [diag] 截图尺寸: {bgr.shape}, 均值: {bgr.mean():.1f}, 最小: {bgr.min()}, 最大: {bgr.max()}")
    return bgr


def save_debug(name, click_x=None, click_y=None):
    debug_dir = os.path.join(SCRIPT_DIR, "debug_snap")
    os.makedirs(debug_dir, exist_ok=True)
    img = screenshot_all()
    if click_x is not None and click_y is not None:
        # Convert screen coords to screenshot coords
        sx = int(click_x - VIRTUAL_X)
        sy = int(click_y - VIRTUAL_Y)
        cv2.drawMarker(img, (sx, sy), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
    path = os.path.join(debug_dir, f"{name}.png")
    cv2.imwrite(path, img)
    print(f"   📸 {name}.png")


def find_icon(template_path, search_region=None):
    """Find template. Returns (screen_x, screen_y) or None. No keyboard fallback."""
    if not os.path.exists(template_path):
        print(f"   ❌ 模板不存在: {os.path.basename(template_path)}")
        return None

    img = screenshot_all()
    if search_region:
        x1, y1, x2, y2 = search_region
        img = img[y1:y2, x1:x2]
        off_x, off_y = x1, y1
    else:
        off_x, off_y = 0, 0

    file_bytes = np.fromfile(template_path, dtype=np.uint8)
    template = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if template is None:
        return None

    best = None
    best_val = 0
    best_scale = 1.0
    best_w, best_h = template.shape[1], template.shape[0]

    for scale in [0.5, 0.7, 1.0, 1.3, 1.6, 2.0, 2.5]:
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

    if best and best_val >= 0.50:
        print(f"   ✅ 匹配: 置信度={best_val:.3f} 屏幕坐标=({int(best[0])}, {int(best[1])})")
        return (*best, best_scale, best_w, best_h)
    else:
        print(f"   ❌ 匹配失败 (最佳={best_val:.3f})")
        return None


def click_screen(x, y, desc=""):
    print(f"   🖱️  点击 {desc}: ({int(x)}, {int(y)})")
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.1)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.5)


def get_window_center(hwnd):
    rect = ctypes.wintypes.RECT()
    ok = user32.GetWindowRect(int(hwnd), ctypes.byref(rect))
    print(f"   [diag] GetWindowRect ok={ok}, rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
    if not ok:
        return None, None
    return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2


def minimize_console():
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 6)
        time.sleep(0.3)


def restore_console():
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 9)
        time.sleep(0.3)


def main():
    print("=" * 60)
    print("🖥️  竖屏上下二分栏 — 纯鼠标识别测试")
    print("=" * 60)
    print("\n原则: 匹配失败就停，绝不自动按键盘")
    print()

    monitors = get_monitors()
    vert = get_monitor_by_type(monitors, "vertical")
    if not vert:
        print("❌ 未找到竖屏")
        return

    # Screenshot region of vertical monitor
    vx1 = vert['rect'][0] - VIRTUAL_X
    vy1 = vert['rect'][1] - VIRTUAL_Y
    vx2 = vert['rect'][2] - VIRTUAL_X
    vy2 = vert['rect'][3] - VIRTUAL_Y
    vregion = (vx1, vy1, vx2, vy2)
    print(f"竖屏截图区域: {vregion}")
    print(f"屏幕区域: {vert['rect']}")
    print()

    # Ensure windows
    print("⏳ 3秒后开始...")
    time.sleep(3)
    
    kim_hwnd, _ = ensure_window("Kimi Code", None, "vertical", monitors)
    qclaw_hwnd, _ = ensure_window("QClaw", None, "vertical", monitors)
    if not kim_hwnd or not qclaw_hwnd:
        print("❌ 窗口未就绪")
        return

    # === Step 1: Kimi Code → Win+Z → click top ===
    print("\n" + "=" * 60)
    print("[1/2] 🎯 Kimi Code → Win+Z → 点击上栏")
    print("-" * 60)

    minimize_console()  # 先最小化终端，避免偷焦点
    
    # 先恢复窗口（如果被最小化），再激活
    user32.ShowWindow(kim_hwnd, 9)
    time.sleep(0.5)
    bring_to_front(kim_hwnd)
    time.sleep(0.5)
    
    # 用鼠标点击窗口中心，确保焦点真正在竖屏上
    cx, cy = get_window_center(kim_hwnd)
    if cx is not None:
        print(f"   🖱️  点击 Kimi Code 中心确保焦点: ({cx}, {cy})")
        click_screen(cx, cy, "KimiCode.center")
        time.sleep(0.5)
    
    print("   → Win+Z...")
    keyboard.send('win+z')
    time.sleep(2.0)

    save_debug("v_before_layout")
    result = find_icon(os.path.join(ASSETS_DIR, "layout_2row.png"), search_region=vregion)

    if not result:
        save_debug("v_fail_layout")
        restore_console()
        print("\n❌ layout_2row.png 匹配失败")
        print("   请检查 debug_snap/v_before_layout.png")
        print("   确认 Win+Z 是否在竖屏上弹出")
        return

    sx, sy, scale, w, h = result
    click_x = sx
    click_y = sy - int(h * 0.25)  # top zone
    
    save_debug("v_click_layout", click_x, click_y)
    click_screen(click_x, click_y, "2row.top")
    print("   ✅ Kimi Code → top")
    time.sleep(2.5)

    # === Step 2: QClaw → suggestion → click ===
    print("\n" + "=" * 60)
    print("[2/2] 🎯 建议界面 → 点击 QClaw")
    print("-" * 60)
    
    print("⏳ 等待建议界面...")
    time.sleep(2.0)

    save_debug("v_before_qclaw")
    result = find_icon(os.path.join(ASSETS_DIR, "icon_qclaw.png"), search_region=vregion)

    if not result:
        save_debug("v_fail_qclaw")
        restore_console()
        print("\n❌ icon_qclaw.png 匹配失败")
        print("   请检查 debug_snap/v_before_qclaw.png")
        return

    click_screen(result[0], result[1], "QClaw")
    print("   ✅ QClaw → bottom")

    restore_console()
    print()
    print("=" * 60)
    print("✅ 竖屏测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
