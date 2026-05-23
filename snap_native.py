#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 11 原生 Snap Layouts 自动分配（实验性）
用法: python snap_native.py <窗口标题关键词> <区域>

区域选项:
  left      = 左半屏 (Win + ←)
  right     = 右半屏 (Win + →)
  3-left    = 三分栏左侧
  3-center  = 三分栏中间
  3-right   = 三分栏右侧
"""

import sys
import time
import ctypes
import ctypes.wintypes
import keyboard

# Fix Windows GBK console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

user32 = ctypes.windll.user32


def find_window_by_title(keyword):
    """Find window by title keyword using EnumWindows"""
    found = []
    
    def enum_callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w < 100 or h < 100:
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value.strip()
        if keyword.lower() in title.lower():
            found.append((hwnd, title, w, h))
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    
    if not found and keyword.lower() in ("explorer", "文件资源管理器"):
        import psutil
        skip_titles = ["program manager", "任务栏", "通知", "操作中心", "start"]
        def enum_proc(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w < 300 or h < 300:
                return True
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value.strip()
            if any(skip in title.lower() for skip in skip_titles):
                return True
            try:
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                proc = psutil.Process(pid.value)
                if proc.name().lower() == "explorer.exe":
                    found.append((hwnd, title, w, h))
            except Exception:
                pass
            return True
        user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
    
    if not found:
        return None, None
    found.sort(key=lambda x: x[2] * x[3], reverse=True)
    return found[0][0], found[0][1]


def bring_to_front(hwnd):
    """Activate window and bring to foreground"""
    foreground = user32.GetForegroundWindow()
    cur_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    fg_thread = user32.GetWindowThreadProcessId(foreground, None)
    user32.AttachThreadInput(cur_thread, fg_thread, True)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(cur_thread, fg_thread, False)
    time.sleep(0.8)


def snap_with_win_arrow(hwnd, direction):
    """Simple left/right snap using Win + Arrow"""
    print(f"  → 激活窗口...")
    bring_to_front(hwnd)
    arrow = 'left' if direction == "left" else 'right'
    print(f"  → 发送 Win + {arrow}...")
    keyboard.send(f'win+{arrow}')
    time.sleep(0.5)


def snap_with_win_z(hwnd, zone):
    """
    Use Win + Z Snap Layouts to assign window to a zone.
    zone: "3-left" | "3-center" | "3-right"
    
    Navigation logic (discovered via snap_debug.py):
    - Win+Z opens Snap Layouts
    - Tab navigates sequentially through 9 layouts
    - Step 6 = 3-zone layout (default focused on LEFT zone)
    - Within 3-zone: Right moves to center, then right
    """
    print(f"  → 激活窗口...")
    bring_to_front(hwnd)
    
    # Open Snap Layouts
    print(f"  → 发送 Win + Z...")
    keyboard.send('win+z')
    time.sleep(2.5)  # Wait for UI to fully appear
    
    # Navigate to 3-zone layout (6th item, press Tab 6 times)
    print(f"  → 选择三分栏布局 (Tab x6)...")
    for i in range(6):
        keyboard.send('tab')
        time.sleep(0.8)
        print(f"    Tab {i+1}/6")
    
    # Navigate to specific zone within the 3-zone layout
    # Default focus is on LEFT zone after Tab x6
    print(f"  → 选择区域: {zone}...")
    if zone == "3-left":
        # Already on left zone, no action needed
        pass
    elif zone == "3-center":
        keyboard.send('right')
        time.sleep(0.5)
    elif zone == "3-right":
        keyboard.send('right')
        time.sleep(0.5)
        keyboard.send('right')
        time.sleep(0.5)
    
    # Confirm
    print(f"  → 确认 (Enter)...")
    keyboard.send('enter')
    time.sleep(2.0)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    keyword = sys.argv[1]
    zone = sys.argv[2]
    
    print(f"🔍 查找窗口: {keyword}")
    hwnd, title = find_window_by_title(keyword)
    if not hwnd:
        print("❌ 未找到窗口")
        sys.exit(1)
    
    print(f"✅ 找到: {title}")
    print(f"⏳ 3秒后开始分配...")
    time.sleep(3)
    
    print(f"🎯 分配到: {zone}")
    
    if zone in ("left", "right"):
        snap_with_win_arrow(hwnd, zone)
    elif zone in ("3-left", "3-center", "3-right"):
        snap_with_win_z(hwnd, zone)
    else:
        print(f"❌ 未知区域: {zone}")
        sys.exit(1)
    
    print("✅ 完成")


if __name__ == "__main__":
    main()
