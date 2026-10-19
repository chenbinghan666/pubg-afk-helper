"""A non-activating, click-through Windows status panel."""
from collections import deque
import ctypes
import logging
import time
import tkinter as tk


class StatusOverlay(logging.Handler):
    def __init__(self, live):
        super().__init__()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", .94)
        width, height = 450, 400
        x = max(0, self.root.winfo_screenwidth() - width - 24)
        self.root.geometry(f"{width}x{height}+{x}+24")
        self.root.configure(bg="#111827")
        tk.Label(self.root, text="PUBG 自动流程 · " + ("执行中" if live else "仅识别预览"),
                 font=("Microsoft YaHei", 12, "bold"), fg="#93c5fd", bg="#111827").pack(pady=(12, 6))
        self.status = tk.Label(self.root, text="初始化识别模板…", wraplength=420,
                               justify="left", anchor="w", font=("Microsoft YaHei", 13, "bold"),
                               fg="#f9fafb", bg="#111827")
        self.status.pack(fill="x", padx=14, pady=(0, 8))
        self.events = tk.Label(self.root, wraplength=420, justify="left", anchor="nw",
                               font=("Microsoft YaHei", 10), fg="#cbd5e1", bg="#111827")
        self.events.pack(fill="both", expand=True, padx=14)
        tk.Label(self.root, text="F8 暂停  |  F7 继续  |  F9 退出\n窗口置顶、鼠标穿透，不抢游戏焦点",
                 font=("Microsoft YaHei", 10), fg="#fbbf24", bg="#111827").pack(pady=8)
        self.lines = deque(maxlen=3)
        self.next_pump = 0
        self.closed = False
        self.root.update_idletasks()
        self._native_styles()
        self.root.deiconify()
        self.root.update_idletasks()

    def _native_styles(self):
        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        self.hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        get_style = user32.GetWindowLongPtrW
        set_style = user32.SetWindowLongPtrW
        get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
        get_style.restype = ctypes.c_ssize_t
        set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
        set_style.restype = ctypes.c_ssize_t
        # WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        style = get_style(self.hwnd, -20)
        set_style(self.hwnd, -20, style | 0x20 | 0x08000000 | 0x80)
        user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        user32.SetWindowPos(self.hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0013)
        # Keep the panel out of screen recognition on supported Windows builds.
        try:
            user32.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            user32.SetWindowDisplayAffinity(self.hwnd, 0x11)
        except AttributeError:
            pass

    def emit(self, record):
        if record.levelno >= logging.INFO:
            self.lines.append(time.strftime("%H:%M:%S", time.localtime(record.created)) +
                              " " + record.getMessage()[:85])

    def update_status(self, text):
        if self.closed:
            return
        now = time.monotonic()
        if now < self.next_pump:
            return
        self.next_pump = now + .2
        self.status.configure(text=text)
        self.events.configure(text="\n".join(self.lines))
        self.root.update_idletasks()
        self.root.update()

    def finish(self, text):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            self.update_status(text)
            time.sleep(.05)
        self.close()

    def close(self):
        if not getattr(self, "closed", True):
            self.closed = True
            self.root.destroy()
        super().close()
