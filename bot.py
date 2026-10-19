"""Windows screen-template loop. No game memory access or game injection."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import logging
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
NAMES = ("confirm", "return_lobby", "continue_results", "close_rewards", "start")
LABELS = {"start": "开始游戏", "return_lobby": "返回大厅", "confirm": "退出/返回确认",
          "continue_results": "继续结算", "close_rewards": "关闭奖励页"}
DEFAULT_ACTIONS = {"start": {"key": "f"}, "continue_results": {"key": "esc"},
                   "close_rewards": {"key": "esc"}}
DEFAULT_MINIMAP_RECT = (.852, .739, .980, .968)
DEFAULT_ANTI_STUCK = {"enabled": True, "check_after_jump_seconds": 30,
                      "stationary_seconds": 1, "cooldown_seconds": 15,
                      "mean_change_threshold": 2.5, "stable_tile_fraction": .85,
                      "motion_confirm_frames": 2, "backward_seconds": 1.2,
                      "sidestep_seconds": 1.5, "vault_enabled": True,
                      "vault_settle_seconds": 2.0, "vault_observe_seconds": 3.0,
                      "minimap_relative_rect": list(DEFAULT_MINIMAP_RECT)}


class MotionMonitor:
    """Compare only minimap terrain; mask the rotating player marker."""
    def __init__(self, seconds=1, cooldown=15, mean_threshold=2.5,
                 stable_tile_fraction=.85, motion_confirm_frames=2, minimap_rect=None):
        if any(not math.isfinite(v) or v <= 0 for v in (seconds, cooldown, mean_threshold)):
            raise ValueError("卡墙时间、冷却和变化阈值必须为正有限数值。")
        if not 0 < stable_tile_fraction <= 1 or motion_confirm_frames < 1:
            raise ValueError("稳定分块比例应在 (0,1] 内，移动确认帧数应至少为 1。")
        self.seconds, self.cooldown, self.threshold = seconds, cooldown, mean_threshold
        self.stable_tile_fraction = stable_tile_fraction
        self.motion_confirm_frames = motion_confirm_frames
        self.minimap_rect = self.validate_rect(minimap_rect)
        self.next_check = 0
        self.reset()

    def reset(self):
        self.baseline = None
        self.since = None
        self.motion_streak = 0
        self.quiet_seconds = 0
        self.stable_fraction = 0
        self.median_change = 0
        self.status = "等待有效画面"

    @staticmethod
    def validate_rect(rect):
        rect = tuple(DEFAULT_MINIMAP_RECT if rect is None else rect)
        if (len(rect) != 4 or any(not math.isfinite(v) for v in rect)
                or not 0 <= rect[0] < rect[2] <= 1 or not 0 <= rect[1] < rect[3] <= 1):
            raise ValueError("minimap_relative_rect 应为有效的 [左,上,右,下] 相对位置，范围 0 至 1。")
        return rect

    @staticmethod
    def sample(frame, cv2, rect=None):
        h, w = frame.shape[:2]
        left, top, right, bottom = DEFAULT_MINIMAP_RECT if rect is None else rect
        roi = frame[round(h * top):round(h * bottom), round(w * left):round(w * right)]
        if min(roi.shape[:2]) < 8:
            return None
        gray = cv2.cvtColor(cv2.resize(roi, (128, 128)), cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 1)
        # Flat coloured walls/floors are valid. Only near-black/white blanks
        # are excluded, rather than all scenes with little texture.
        blank = gray.std() < 1 and (gray.mean() < 3 or gray.mean() > 252)
        if blank:
            return None
        # The terrain scrolls with movement, while the central arrow/direction
        # cone may rotate or blink even when the character is blocked.
        cv2.circle(gray, (64, 64), 16, 0, thickness=-1)
        return gray

    @staticmethod
    def changed(first, second, cv2, threshold=2.5):
        diff = cv2.absdiff(first, second)
        return float(diff.mean()) > threshold or float((diff > 12).mean()) > .03

    def update(self, frame, now, cv2):
        import numpy as np
        if now < self.next_check:
            self.reset()
            self.status = f"脱困冷却 {math.ceil(self.next_check - now)} 秒"
            return False
        gray = self.sample(frame, cv2, self.minimap_rect)
        # Blank/loading screens provide no useful motion evidence.
        if gray is None:
            self.reset()
            self.status = "跳过纯黑/纯白画面"
            return False
        if self.baseline is None:
            self.baseline, self.since = gray, now
            self.status = "建立小地图基准"
            return False
        # 4x4 minimap terrain tiles, excluding the central marker.
        diff = cv2.absdiff(gray, self.baseline).astype("float32")
        tiles = diff.reshape(4, 32, 4, 32).mean(axis=(1, 3))
        self.stable_fraction = float((tiles <= self.threshold).mean())
        self.median_change = float(np.median(tiles))
        moving = self.stable_fraction < self.stable_tile_fraction
        self.motion_streak = self.motion_streak + 1 if moving else 0
        if self.motion_streak >= self.motion_confirm_frames:
            self.baseline, self.since = gray, now
            self.motion_streak = 0
            self.quiet_seconds = 0
            self.status = "小地图持续变化，重新计时"
            return False
        self.quiet_seconds = now - self.since
        self.status = "稳定 %.1f/%g 秒；稳定分块 %.0f%%；变化中位数 %.1f" % (
            self.quiet_seconds, self.seconds, 100 * self.stable_fraction, self.median_change)
        if not moving and self.quiet_seconds >= self.seconds:
            self.next_check = now + self.cooldown
            self.reset()
            self.status = "连续稳定达到阈值，触发脱困"
            return True
        return False


class RoundMovement:
    """Timed jump, held W and separate F taps; release on interruption."""
    def __init__(self, controller, delay=120, enabled=True, live=True,
                 pickup_enabled=True, pickup_interval=0.5, absence_frames=3,
                 pickup_delay=30, backward_seconds=1.2, sidestep_seconds=1.5,
                 sprint=True, turn_right_pixels=4050, look_down_pixels=5000,
                 vault_enabled=True, vault_settle_seconds=2, vault_observe_seconds=3,
                 minimap_rect=None):
        if not math.isfinite(delay) or delay <= 0:
            raise ValueError("jump_delay_seconds 必须是大于零的有限秒数。")
        if not math.isfinite(pickup_interval) or pickup_interval <= 0:
            raise ValueError("pickup_interval_seconds 必须是大于零的有限秒数。")
        if not math.isfinite(pickup_delay) or pickup_delay < 0:
            raise ValueError("pickup_delay_after_jump_seconds 必须是非负有限秒数。")
        if any(not math.isfinite(v) or v <= 0 for v in (backward_seconds, sidestep_seconds)):
            raise ValueError("后退与横移时间必须为正有限数值。")
        if not isinstance(turn_right_pixels, int) or not 0 <= turn_right_pixels <= 20000:
            raise ValueError("turn_right_pixels 必须是 0 至 20000 的整数。")
        if not isinstance(look_down_pixels, int) or abs(look_down_pixels) > 20000:
            raise ValueError("look_down_pixels 必须是 -20000 至 20000 的整数。")
        if any(not math.isfinite(v) or v <= 0 for v in (vault_settle_seconds, vault_observe_seconds)):
            raise ValueError("跨越动画等待时间与观察时间必须为正有限数值。")
        self.controller, self.delay = controller, delay
        self.enabled, self.live = enabled, live
        self.started = None
        self.jumped = False
        self.holding = False
        self.pickup_enabled, self.pickup_interval = pickup_enabled, pickup_interval
        self.next_pickup = None
        self.armed = False
        self.absent_count = 0
        self.absence_frames = max(1, int(absence_frames))
        self.pickup_delay, self.pickup_ready_at = pickup_delay, None
        self.jumped_at = None
        self.backward_seconds, self.sidestep_seconds = backward_seconds, sidestep_seconds
        self.extra_key = None
        self.recovery_phase = None
        self.recovery_deadline = 0
        self.recovery_count = 0
        self.sprint, self.sprinting = sprint, False
        self.turn_right_pixels = turn_right_pixels
        self.turned = False
        self.look_down_pixels, self.looked_down = look_down_pixels, False
        self.next_refresh = 0
        self.vault_enabled = vault_enabled
        self.vault_settle_seconds, self.vault_observe_seconds = vault_settle_seconds, vault_observe_seconds
        self.vault_baseline = None
        self.vault_motion_frames = 0
        self.minimap_rect = MotionMonitor.validate_rect(minimap_rect)

    def key_up(self, key):
        if self.live:
            failsafe = getattr(self.controller, "FAILSAFE", None)
            try:
                if failsafe is not None:
                    self.controller.FAILSAFE = False
                self.controller.keyUp(key)
            finally:
                if failsafe is not None:
                    self.controller.FAILSAFE = failsafe

    def release(self):
        self.next_pickup = None
        self.recovery_phase = None
        self.vault_baseline = None
        self.vault_motion_frames = 0
        try:
            if self.holding:
                self.holding = False
                self.key_up("w")
                logging.info("已松开 W" if self.live else "预览：松开 W")
        finally:
            try:
                if self.sprinting:
                    self.sprinting = False
                    self.key_up("shift")
            finally:
                if self.extra_key:
                    key, self.extra_key = self.extra_key, None
                    self.key_up(key)

    def reset(self):
        self.release()
        self.started, self.jumped = None, False
        self.armed, self.absent_count = False, 0
        self.pickup_ready_at = None
        self.jumped_at = None
        self.recovery_count = 0
        self.turned = False
        self.looked_down = False

    def recover(self, now):
        if not self.jumped or not self.holding or self.recovery_phase:
            return
        self.recovery_count += 1
        self.next_pickup = None
        if self.vault_enabled:
            self.recovery_phase = "vault_press"
            self.recovery_deadline = now + .15
            self.extra_key = "c"
            self.sprinting = True
            if self.live:
                self.controller.keyDown("shift")
                self.controller.keyDown("c")
            logging.info("疑似卡墙：保持向前，先尝试 Shift + C 跨越，暂停拾取")
            return
        self.begin_backward(now)

    def begin_backward(self, now):
        self.release()
        self.recovery_phase = "backward"
        self.extra_key = "s"
        self.recovery_deadline = now + self.backward_seconds
        if self.live:
            self.controller.keyDown("s")
        logging.info("%s疑似卡墙：松开 W，后退 %.1f 秒", "" if self.live else "预览：", self.backward_seconds)

    def observe_recovery_motion(self, frame, now, cv2):
        if self.recovery_phase != "vault_watch":
            return
        sample = MotionMonitor.sample(frame, cv2, self.minimap_rect)
        if sample is None:
            return
        if self.vault_baseline is None:
            self.vault_baseline = sample
            return
        if MotionMonitor.changed(sample, self.vault_baseline, cv2):
            self.vault_motion_frames += 1
        else:
            self.vault_motion_frames = 0
        if self.vault_motion_frames >= 2:
            self.recovery_phase = None
            self.vault_baseline = None
            self.next_pickup = now + self.pickup_interval
            if not self.sprint and self.sprinting:
                self.key_up("shift")
                self.sprinting = False
            logging.info("跨越后连续检测到小地图变化，视为脱困，恢复拾取")

    def arm(self):
        if self.enabled and not self.armed:
            self.armed = True
            self.absent_count = 0
            logging.info("已开始匹配，等待大厅界面连续 %d 次消失后开始计时", self.absence_frames)

    def start(self, now):
        if self.enabled and self.started is None:
            self.armed = True
            self.started = now
            logging.info("大厅已消失，开始本局计时：%.1f 秒后尝试按 F 跳伞", self.delay)

    def observe(self, name, now):
        if name in NAMES and name != "start":
            self.reset()
        elif name == "start":
            self.absent_count = 0
            if self.started is not None:
                logging.info("检测到大厅，重置本局计时")
                self.reset()
        elif name is None and self.armed and self.started is None:
            self.absent_count += 1
            if self.absent_count >= self.absence_frames:
                self.start(now)

    def tick(self, now, name):
        if not self.enabled or self.started is None or name is not None:
            return
        if self.recovery_phase:
            if now < self.recovery_deadline:
                return
            if self.recovery_phase == "vault_press":
                self.key_up("c")
                self.extra_key = None
                self.recovery_phase = "vault_settle"
                self.recovery_deadline = now + self.vault_settle_seconds
                logging.info("已松开 C，等待跨越动画稳定")
                return
            if self.recovery_phase == "vault_settle":
                self.recovery_phase = "vault_watch"
                self.recovery_deadline = now + self.vault_observe_seconds
                self.vault_baseline = None
                self.vault_motion_frames = 0
                logging.info("检查跨越后是否恢复移动")
                return
            if self.recovery_phase == "vault_watch":
                logging.info("跨越后未检测到持续移动，改用后退和横移")
                self.begin_backward(now)
                return
            key, self.extra_key = self.extra_key, None
            self.key_up(key)
            if self.recovery_phase == "backward":
                self.recovery_phase = "sidestep"
                self.extra_key = "a" if self.recovery_count % 2 else "d"
                self.recovery_deadline = now + self.sidestep_seconds
                if self.live:
                    self.controller.keyDown(self.extra_key)
                logging.info("%s向%s横移 %.1f 秒", "" if self.live else "预览：",
                             "左" if self.extra_key == "a" else "右", self.sidestep_seconds)
                return
            self.recovery_phase = None
            logging.info("脱困动作完成，恢复前进与拾取")
        if not self.jumped and now - self.started >= self.delay:
            if self.live:
                self.controller.press("f")
            self.jumped = True
            self.jumped_at = now
            self.pickup_ready_at = now + self.pickup_delay
            logging.info("已按 F 尝试跳伞" if self.live else "预览：按 F 尝试跳伞")
        if self.jumped and not self.turned:
            if self.live and self.turn_right_pixels:
                self.controller.move_relative(self.turn_right_pixels, 0)
            self.turned = True
            logging.info("%s跳伞后向右转视角（相对鼠标位移 %d，目标约 90°，需按灵敏度校准）",
                         "" if self.live else "预览：", self.turn_right_pixels)
        if self.jumped and not self.holding:
            # Set ownership first so cleanup can release after a failed keyDown.
            self.holding = True
            self.sprinting = bool(self.sprint)
            if self.live:
                self.controller.keyDown("w")
                if self.sprint:
                    self.controller.keyDown("shift")
            self.next_refresh = now + 2
            self.next_pickup = max(now + self.pickup_interval, self.pickup_ready_at)
            logging.info("%s持续按住 %s，等待死亡界面", "" if self.live else "预览：",
                         "W + Shift 疾跑" if self.sprint else "W")
            if self.pickup_enabled:
                logging.info("跳伞后等待 %.1f 秒，再约每 %.1f 秒点按一次 F 拾取", self.pickup_delay, self.pickup_interval)
        if self.holding and now >= self.next_refresh:
            if self.live:
                self.controller.keyDown("w")
                if self.sprint:
                    self.controller.keyDown("shift")
            self.next_refresh = now + 2
        if self.holding and not self.looked_down and now >= self.pickup_ready_at:
            if self.live and self.look_down_pixels:
                self.controller.move_relative(0, self.look_down_pixels)
            self.looked_down = True
            logging.info("跳伞后等待结束，向下压视角至地面，然后开始拾取")
        if (self.holding and self.pickup_enabled and self.next_pickup is not None
                and now >= self.next_pickup):
            if self.live:
                # press sends down+up for each tap. Never hold F like W.
                self.controller.press("f")
            logging.debug("点按 F 拾取" if self.live else "预览：点按 F 拾取")
            # No burst of queued taps after slow scans or an interruption.
            self.next_pickup = now + self.pickup_interval


def dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()


def read_config():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    example = ROOT / "config.example.json"
    if example.exists():
        return json.loads(example.read_text(encoding="utf-8"))
    return {"window_title": "PUBG", "threshold": 0.94, "stable_frames": 3,
            "interval": 1.0, "cooldown": 20, "templates": {}}


def capture(name):
    import tkinter as tk
    from PIL import ImageTk
    import pyautogui

    print(f"5 秒后截取主屏幕，请切换到包含【{LABELS[name]}】按钮的游戏界面。")
    time.sleep(5)
    shot = pyautogui.screenshot()
    window = tk.Tk()
    window.title("拖动框选按钮；Esc 取消")
    window.attributes("-fullscreen", True)
    window.attributes("-topmost", True)
    canvas = tk.Canvas(window, highlightthickness=0, cursor="crosshair")
    canvas.pack(fill="both", expand=True)
    photo = ImageTk.PhotoImage(shot)
    canvas.create_image(0, 0, image=photo, anchor="nw")
    canvas.create_text(shot.width // 2, 28,
                       text=f"拖动框选【{LABELS[name]}】按钮，尽量包含文字及边框；Esc 取消",
                       fill="red", font=("Microsoft YaHei", 18, "bold"))
    selection = {}

    def down(event):
        selection["origin"] = (event.x, event.y)
        if "box" in selection:
            canvas.delete(selection["box"])
        selection["box"] = canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                   outline="red", width=2)

    def move(event):
        if "origin" in selection:
            canvas.coords(selection["box"], *selection["origin"], event.x, event.y)

    def up(event):
        if "origin" not in selection:
            return
        x, y = selection["origin"]
        rect = [min(x, event.x), min(y, event.y), max(x, event.x), max(y, event.y)]
        if rect[2] - rect[0] < 16 or rect[3] - rect[1] < 12:
            return
        selection["rect"] = rect
        window.destroy()

    canvas.bind("<ButtonPress-1>", down)
    canvas.bind("<B1-Motion>", move)
    canvas.bind("<ButtonRelease-1>", up)
    window.bind("<Escape>", lambda _: window.destroy())
    window.mainloop()
    if "rect" not in selection:
        print("已取消。")
        return
    rect = selection["rect"]
    config = read_config()
    # Existing templates must use the same resolution.
    for entry in config["templates"].values():
        if entry.get("screen_size", list(shot.size)) != list(shot.size):
            raise ValueError("分辨率已改变，请删除旧 config.json 和 templates 后重新录制。")
    folder = ROOT / "templates"
    folder.mkdir(exist_ok=True)
    shot.crop(rect).save(folder / f"{name}.png")
    config["screen_size"] = list(shot.size)
    old = config["templates"].get(name, {})
    config["templates"][name] = {"path": f"templates/{name}.png", "rect": rect,
                                  "screen_size": list(shot.size),
                                  "action": old.get("action", DEFAULT_ACTIONS.get(name, {"click": True}))}
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存【{LABELS[name]}】模板。")


class Gate:
    """Require consecutive detections and rate-limit each button separately."""
    def __init__(self, frames, cooldown):
        self.frames, self.cooldown = frames, cooldown
        self.name, self.count = None, 0
        self.last = {}

    def reset(self):
        self.name, self.count = None, 0

    def ready(self, name, now):
        if name is None:
            self.reset()
            return False
        self.count = self.count + 1 if self.name == name else 1
        self.name = name
        return self.count >= self.frames and now - self.last.get(name, float("-inf")) >= self.cooldown

    def record(self, name, now):
        self.last[name] = now
        self.reset()


def match(frame, template, rect, cv2, threshold):
    h, w = frame.shape[:2]
    left, top, right, bottom = rect
    left, top = max(0, left - 80), max(0, top - 80)
    right, bottom = min(w, right + 80), min(h, bottom + 80)
    roi = frame[top:bottom, left:right]
    th, tw = template.shape[:2]
    if roi.shape[0] < th or roi.shape[1] < tw:
        return None
    # Correlation is less sensitive to button brightness and hover effects.
    roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    if gray.std() < 1:
        return None
    roi = cv2.GaussianBlur(roi, (3, 3), 0.6)
    gray = cv2.GaussianBlur(gray, (3, 3), 0.6)
    _, confidence, _, location = cv2.minMaxLoc(cv2.matchTemplate(roi, gray, cv2.TM_CCOEFF_NORMED))
    if confidence < threshold:
        return None
    return (left + location[0] + tw // 2, top + location[1] + th // 2, confidence)


def load_templates(cfg, cv2, np):
    def load(entry):
        img = cv2.imdecode(np.fromfile(ROOT / entry["path"], dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"无法读取模板：{entry['path']}")
        relative = entry.get("relative_rect")
        rect = ([round(v * cfg["screen_size"][i % 2]) for i, v in enumerate(relative)]
                if relative else entry["rect"])
        return img, rect
    return {name: (load(cfg["templates"][name]),
                   [load(g) for g in cfg["templates"][name].get("guards", [])])
            for name in NAMES if name in cfg["templates"]}


def detect(frame, cfg, templates, cv2):
    h, w = frame.shape[:2]
    rw, rh = cfg["screen_size"]
    original = frame

    def relative_match(img, rect, threshold):
        region = [round(v * (w / rw if i % 2 == 0 else h / rh)) for i, v in enumerate(rect)]
        scaled = cv2.resize(img, (max(1, round(img.shape[1] * w / rw)),
                                 max(1, round(img.shape[0] * h / rh))), interpolation=cv2.INTER_AREA)
        return match(frame, scaled, region, cv2, threshold)

    for name, ((template, rect), guards) in templates.items():
        threshold = cfg["templates"][name].get("threshold", cfg["threshold"])
        point = relative_match(template, rect, threshold)
        if point and all(relative_match(img, region, threshold) for img, region in guards):
            entry = cfg["templates"][name]
            # A text anchor need not be the clickable button centre.
            x, y = entry.get("click_point", (point[0] * rw / w, point[1] * rh / h))
            if "relative_click_point" in entry:
                x, y = (entry["relative_click_point"][0] * rw,
                        entry["relative_click_point"][1] * rh)
            return name, (round(x * w / rw), round(y * h / rh), point[2])
    # Some widescreen layouts keep UI scale tied to height and anchor panels
    # to screen edges rather than stretching them horizontally.
    if abs((w / h) / (rw / rh) - 1) > .01:
        scale = h / rh

        def anchored(img, rect):
            left, top, right, bottom = rect
            centre = (left + right) / 2
            if centre < rw / 3:
                offset = 0
            elif centre > rw * 2 / 3:
                offset = w - rw * scale
            else:
                offset = (w - rw * scale) / 2
            region = [round(left * scale + offset), round(top * scale),
                      round(right * scale + offset), round(bottom * scale)]
            scaled = cv2.resize(img, (max(1, round(img.shape[1] * scale)),
                                     max(1, round(img.shape[0] * scale))),
                                interpolation=cv2.INTER_AREA)
            return match(original, scaled, region, cv2, cfg["threshold"])

        for name, ((template, rect), guards) in templates.items():
            point = anchored(template, rect)
            if point and all(anchored(img, region) for img, region in guards):
                return name, point
    return None


def perform_action(name, point, cfg, controller):
    action = cfg["templates"][name].get("action", DEFAULT_ACTIONS.get(name, {"click": True}))
    if "key" in action:
        if action["key"] not in ("f", "esc"):
            raise ValueError("仅支持 F 和 Esc 按键。")
        controller.press(action["key"])
    else:
        controller.click(*point[:2])


def foreground_matches(expected):
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    handle = user32.GetForegroundWindow()
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(ctypes.c_void_p(handle), title, len(title))
    return bool(expected) and expected.casefold() in title.value.casefold()


def pause_state(paused, pause_pressed, resume_pressed):
    # Separate, idempotent commands. Pause wins if both keys are held.
    if pause_pressed:
        return True
    if resume_pressed:
        return False
    return paused


class WindowsInput:
    """Ordinary OS input, with relative mouse motion for the game camera."""
    SCANS = {"w": 0x11, "a": 0x1e, "s": 0x1f, "d": 0x20,
             "f": 0x21, "c": 0x2e, "shift": 0x2a, "esc": 0x01}

    def __init__(self, backend, scan_codes=True):
        self.backend = backend
        self.scan_codes = scan_codes

    def __getattr__(self, name):
        return getattr(self.backend, name)

    @property
    def FAILSAFE(self):
        return self.backend.FAILSAFE

    @FAILSAFE.setter
    def FAILSAFE(self, value):
        self.backend.FAILSAFE = value

    def move_relative(self, dx, dy):
        self.backend.failSafeCheck()
        ctypes.windll.user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)

    def _send_scan(self, key, up=False):
        # INPUT requires a full-size union, including MOUSEINPUT, on Win64.
        class Keyboard(ctypes.Structure):
            _fields_ = [("vk", wintypes.WORD), ("scan", wintypes.WORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("extra", ctypes.c_size_t)]
        class Mouse(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("data", wintypes.DWORD), ("flags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]
        class Payload(ctypes.Union):
            _fields_ = [("keyboard", Keyboard), ("mouse", Mouse)]
        class Input(ctypes.Structure):
            _fields_ = [("kind", wintypes.DWORD), ("payload", Payload)]
        entry = Input(kind=1, payload=Payload(keyboard=Keyboard(0, self.SCANS[key],
                                                               0x0008 | (0x0002 if up else 0), 0, 0)))
        send = ctypes.windll.user32.SendInput
        send.argtypes = [wintypes.UINT, ctypes.c_void_p, ctypes.c_int]
        send.restype = wintypes.UINT
        if send(1, ctypes.byref(entry), ctypes.sizeof(entry)) != 1:
            raise RuntimeError("Windows 未接受模拟按键，请检查脚本与游戏的运行权限是否一致。")

    def keyDown(self, key):
        if not self.scan_codes:
            return self.backend.keyDown(key)
        self.backend.failSafeCheck()
        self._send_scan(key)

    def keyUp(self, key):
        if not self.scan_codes:
            return self.backend.keyUp(key)
        self.backend.failSafeCheck()
        self._send_scan(key, up=True)

    def press(self, key):
        if not self.scan_codes:
            return self.backend.press(key)
        self.keyDown(key)
        try:
            time.sleep(.05)
        finally:
            failsafe = self.FAILSAFE
            try:
                self.FAILSAFE = False
                self.keyUp(key)
            finally:
                self.FAILSAFE = failsafe


def movement_status(movement, now, name=None):
    if movement.recovery_phase:
        phases = {"vault_press": "Shift + C 跨越", "vault_settle": "等待跨越动画稳定",
                  "vault_watch": "检查跨越是否恢复移动", "backward": "S 后退",
                  "sidestep": "A 左横移" if movement.extra_key == "a" else "D 右横移"}
        return "脱困：" + phases[movement.recovery_phase]
    if name and name != "start":
        return "识别到：" + LABELS[name]
    if movement.started is not None:
        if not movement.jumped:
            return f"进入房间：距按 F 跳伞 {max(0, math.ceil(movement.delay - (now - movement.started)))} 秒"
        if now < movement.pickup_ready_at:
            return f"W + Shift 前进：距 F 拾取 {math.ceil(movement.pickup_ready_at - now)} 秒"
        return "W + Shift 疾跑；每 %.1f 秒点按 F 拾取" % movement.pickup_interval
    if movement.armed:
        return "等待大厅消失：%d/%d 次" % (movement.absent_count, movement.absence_frames)
    return "等待识别大厅/结算界面"


def anti_stuck_status(movement, monitor, now, enabled, grace):
    if not enabled:
        return "防卡墙已关闭"
    if movement.jumped_at is None:
        return "防卡墙：等待跳伞"
    remaining = grace - (now - movement.jumped_at)
    if remaining > 0:
        return "防卡墙：%d 秒后开始检测" % math.ceil(remaining)
    if movement.recovery_phase:
        return "防卡墙：正在脱困"
    if not movement.holding:
        return "防卡墙：等待恢复前进"
    return "防卡墙：" + monitor.status


def run(live, overlay=None):
    import cv2
    import numpy as np
    import pyautogui

    cfg = read_config()
    if not all(name in cfg["templates"] for name in ("start", "return_lobby")):
        raise ValueError("请先录制 start 和 return_lobby 两个必需模板。")
    threshold = float(cfg["threshold"])
    if not 0 < threshold <= 1 or cfg["interval"] <= 0 or cfg["stable_frames"] < 1 or cfg["cooldown"] < 1:
        raise ValueError("识别阈值、间隔、连续帧数或冷却时间无效。")
    templates = load_templates(cfg, cv2, np)
    gate = Gate(cfg["stable_frames"], cfg["cooldown"])
    movement_cfg = cfg.get("movement", {})
    stuck_cfg = {**DEFAULT_ANTI_STUCK, **cfg.get("anti_stuck", {})}
    grace = float(stuck_cfg["check_after_jump_seconds"])
    if not math.isfinite(grace) or grace < 0:
        raise ValueError("卡墙检测的跳伞后等待时间必须是非负有限秒数。")
    monitor = MotionMonitor(float(stuck_cfg["stationary_seconds"]),
                            float(stuck_cfg["cooldown_seconds"]),
                            float(stuck_cfg["mean_change_threshold"]),
                            float(stuck_cfg["stable_tile_fraction"]),
                            int(stuck_cfg["motion_confirm_frames"]),
                            stuck_cfg["minimap_relative_rect"])
    input_controller = WindowsInput(pyautogui, movement_cfg.get("keyboard_backend", "scan") == "scan")
    movement = RoundMovement(input_controller,
                             float(movement_cfg.get("jump_delay_seconds", 120)),
                             movement_cfg.get("enabled", True), live,
                             movement_cfg.get("pickup_enabled", True),
                             float(movement_cfg.get("pickup_interval_seconds", 0.5)),
                             cfg["stable_frames"],
                             float(movement_cfg.get("pickup_delay_after_jump_seconds", 30)),
                             float(stuck_cfg["backward_seconds"]),
                             float(stuck_cfg["sidestep_seconds"]),
                             movement_cfg.get("sprint", True),
                             movement_cfg.get("turn_right_pixels", 4050),
                             movement_cfg.get("look_down_pixels", 5000),
                             stuck_cfg.get("vault_enabled", True),
                             float(stuck_cfg["vault_settle_seconds"]),
                             float(stuck_cfg["vault_observe_seconds"]),
                             stuck_cfg["minimap_relative_rect"])
    corner_pause = bool(cfg.get("mouse_corner_pause", False))
    pyautogui.FAILSAFE = corner_pause
    pyautogui.PAUSE = 0.2
    paused = False
    pause_reason = "已暂停：按 F7 继续"
    wait_reason = None
    logging.info("模式：%s。F8 暂停，F7 继续，F9 停止；鼠标角落暂停%s。", "实际点击" if live else "仅识别",
                 "已启用" if corner_pause else "已关闭（自动转视角不会触发暂停）")
    next_scan = 0
    next_motion_log = 0
    last_name = None
    try:
        while True:
            try:
                user32 = ctypes.windll.user32
                if user32.GetAsyncKeyState(0x78) & 0x8000:  # F9
                    logging.info("F9：退出程序，释放所有脚本按键")
                    return
                new_paused = pause_state(paused,
                                         bool(user32.GetAsyncKeyState(0x77) & 0x8000),
                                         bool(user32.GetAsyncKeyState(0x76) & 0x8000))
                if user32.GetAsyncKeyState(0x77) & 0x8000:
                    pause_reason = "F8 已暂停：按 F7 继续"
                corners = getattr(pyautogui, "FAILSAFE_POINTS", [(0, 0)])
                if not isinstance(corners, (tuple, list)):
                    corners = [(0, 0)]
                if corner_pause and tuple(pyautogui.position()) in corners:
                    new_paused = True
                    pause_reason = "鼠标角落保护已暂停：移开鼠标后按 F7 继续"
                if new_paused != paused:
                    paused = new_paused
                    gate.reset()
                    next_scan = 0
                    logging.info("已暂停" if paused else "已继续")
                active = foreground_matches(cfg["window_title"])
                reason = pause_reason if paused else (None if active else "游戏未在前台：切回游戏后自动继续")
                if reason != wait_reason:
                    if reason:
                        logging.info(reason)
                    elif wait_reason:
                        logging.info("恢复运行：游戏在前台")
                    wait_reason = reason
                if overlay:
                    now_ui = time.monotonic()
                    overlay.update_status(reason or (
                        movement_status(movement, now_ui, last_name) + "\n" +
                        anti_stuck_status(movement, monitor, now_ui, stuck_cfg["enabled"], grace)))
                if reason:
                    movement.release()
                    monitor.reset()
                    gate.reset()
                    next_scan = 0
                    time.sleep(0.05)
                    continue
                if time.monotonic() < next_scan:
                    # Movement timing is independent of the screenshot interval.
                    # Foreground/pause/stop checks above run before every tick.
                    movement.tick(time.monotonic(), last_name)
                    time.sleep(0.05)
                    continue
                shot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
                found = detect(frame, cfg, templates, cv2)
                now = time.monotonic()
                name = found[0] if found else None
                last_name = name
                # Detect death before the jump timer or movement can send input.
                movement.observe(name, now)
                if not foreground_matches(cfg["window_title"]):
                    movement.release()
                    monitor.reset()
                    gate.reset()
                    next_scan = 0
                    continue
                if gate.ready(name, now):
                    _, (x, y, confidence) = found
                    # Do not press F again and cancel matchmaking while counting down.
                    if name != "start" or not movement.armed:
                        action = cfg["templates"][name].get("action", DEFAULT_ACTIONS.get(name, {"click": True}))
                        logging.info("%s【%s】 动作 %s 置信度 %.3f 坐标 (%d,%d)", "执行" if live else "检测到", LABELS[name], action, confidence, x, y)
                        if live:
                            perform_action(name, (x, y, confidence), cfg, input_controller)
                        if name == "start":
                            movement.arm()
                    gate.record(name, now)
                if name is None:
                    movement.observe_recovery_motion(frame, now, cv2)
                if (stuck_cfg["enabled"] and name is None and movement.holding and movement.looked_down
                        and not movement.recovery_phase
                        and movement.jumped_at is not None and now - movement.jumped_at >= grace):
                    if monitor.update(frame, now, cv2):
                        movement.recover(time.monotonic())
                else:
                    monitor.reset()
                if movement.jumped and now >= next_motion_log:
                    logging.info(anti_stuck_status(movement, monitor, now, stuck_cfg["enabled"], grace))
                    next_motion_log = now + 10
                movement.tick(time.monotonic(), name)
                next_scan = time.monotonic() + cfg["interval"]
                time.sleep(0.05)
            except pyautogui.FailSafeException:
                paused = True
                pause_reason = "鼠标角落保护已暂停：移开鼠标后按 F7 继续"
                movement.release()
                monitor.reset()
                gate.reset()
                next_scan = 0
                logging.info(pause_reason)
    finally:
        movement.release()


def main():
    parser = argparse.ArgumentParser(description="PUBG 主屏幕按钮识别工具")
    parser.add_argument("--capture", choices=NAMES, help="录制指定按钮模板")
    parser.add_argument("--live", action="store_true", help="启用实际鼠标点击；默认仅识别")
    args = parser.parse_args()
    dpi_aware()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "bot.log", encoding="utf-8")])
    overlay = None
    final_status = "程序已停止；已释放脚本按键"
    try:
        if args.capture:
            capture(args.capture)
        else:
            if read_config().get("overlay", {}).get("enabled", True):
                from status_overlay import StatusOverlay
                overlay = StatusOverlay(args.live)
                logging.getLogger().addHandler(overlay)
            run(args.live, overlay)
    except KeyboardInterrupt:
        logging.info("已停止。")
    except Exception:
        final_status = "程序异常停止：请查看终端或 bot.log"
        logging.exception("程序停止，请检查上述原因。")
        raise SystemExit(1)
    finally:
        if overlay:
            logging.getLogger().removeHandler(overlay)
            overlay.finish(final_status)


if __name__ == "__main__":
    main()
