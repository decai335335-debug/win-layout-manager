import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", ctypes.c_long * 4),
        ("rcWork", ctypes.c_long * 4),
        ("dwFlags", ctypes.c_ulong)
    ]

monitors = []

def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
    rect = lprcMonitor.contents
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(mi)
    user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
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
    print(f"  显示器: {width}x{height} | primary={is_primary} | vertical={is_vertical} | rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
    return True

MONITORENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_long)

print("检测到的显示器：")
user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
print(f"\n总计: {len(monitors)} 个")
