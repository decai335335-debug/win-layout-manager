import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32

def enum_callback(hwnd, _):
    if not user32.IsWindowVisible(hwnd):
        return True
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w < 200 or h < 200:
        return True
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    title = buf.value.strip()
    if title:
        print(f"  {title}")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
print("当前可见窗口标题：")
user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
