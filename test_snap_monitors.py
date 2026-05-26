import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.c_uint32),
    ]

monitors = []

def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
    rect = lprcMonitor.contents
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(mi)
    ok = user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    is_primary = bool(mi.dwFlags & 1)
    is_vertical = width < height
    monitors.append({
        'handle': hMonitor,
        'rect': (rect.left, rect.top, rect.right, rect.bottom),
        'width': width,
        'height': height,
        'is_primary': is_primary,
        'is_vertical': is_vertical,
    })
    print(f"  显示器: {width}x{height} | primary={is_primary} | vertical={is_vertical} | rect=({rect.left},{rect.top},{rect.right},{rect.bottom}) | GetMonitorInfoW={ok}")
    return True

MONITORENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_long)

print("用 snap_all.py 的 MONITORINFO 定义检测显示器：")
user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
print(f"\n总计: {len(monitors)} 个")

vert = [m for m in monitors if m['is_vertical']]
print(f"竖屏数量: {len(vert)}")
