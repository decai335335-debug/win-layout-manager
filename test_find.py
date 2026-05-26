import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snap_native import find_window_by_title

for name in ["Kimi Code", "QClaw", "Visual Studio Code", "Tabbit"]:
    hwnd, title = find_window_by_title(name)
    if hwnd:
        print(f"✅ {name}: 找到 '{title}' (hwnd={hwnd})")
    else:
        print(f"❌ {name}: 未找到")
