import unittest
from bot import Gate, match, detect, load_templates, read_config, ROOT, perform_action, RoundMovement, MotionMonitor, WindowsInput, run, pause_state
from unittest.mock import Mock, patch, call


def minimap_fixture():
    """Use an optional private screenshot or deterministic synthetic terrain."""
    import cv2
    import numpy as np
    path = ROOT / "reference_screens/minimap.png"
    if path.exists():
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    rng = np.random.default_rng(918)
    return cv2.GaussianBlur(rng.integers(0, 256, (1440, 2560, 3), dtype=np.uint8), (3, 3), .7)


def state_fixture(index, cfg, templates):
    """Optional local screenshots are never needed by a public clone."""
    import cv2
    import numpy as np
    path = ROOT / "reference_screens" / f"p{index}.png"
    if path.exists():
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    w, h = cfg["screen_size"]
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    name = ["start", "confirm", "return_lobby", "continue_results", "close_rewards"][index - 1]
    primary, guards = templates[name]
    for img, rect in [primary, *guards]:
        x, y = rect[:2]
        padded = cv2.copyMakeBorder(img, 8, 8, 8, 8, cv2.BORDER_REPLICATE)
        frame[y-8:y+img.shape[0]+8, x-8:x+img.shape[1]+8] = padded
    return frame


class DetectionTests(unittest.TestCase):
    def test_stability_reset_and_cooldown(self):
        gate = Gate(3, 20)
        self.assertFalse(gate.ready("start", 0))
        self.assertFalse(gate.ready("start", 1))
        self.assertTrue(gate.ready("start", 2))
        gate.record("start", 2)
        for t in (3, 4, 5):
            self.assertFalse(gate.ready("start", t))
        self.assertTrue(gate.ready("start", 22))
        gate.ready(None, 23)
        self.assertFalse(gate.ready("start", 24))
        self.assertFalse(gate.ready("return_lobby", 25))

    def test_matching_position_and_absent_button(self):
        import cv2
        import numpy as np
        rng = np.random.default_rng(42)
        frame = rng.integers(0, 256, (300, 400, 3), dtype=np.uint8)
        template = frame[120:150, 210:270].copy()
        result = match(frame, template, [200, 110, 280, 160], cv2, .99)
        self.assertEqual(result[:2], (240, 135))
        self.assertIsNone(match(np.zeros_like(frame), template, [200, 110, 280, 160], cv2, .99))

    def test_five_screens_at_multiple_resolutions(self):
        import cv2
        import numpy as np
        cfg = read_config()
        templates = load_templates(cfg, cv2, np)
        expected = ["start", "confirm", "return_lobby", "continue_results", "close_rewards"]
        for i, name in enumerate(expected, 1):
            frame = state_fixture(i, cfg, templates)
            for size in [(2559, 1440), (1920, 1080), (2560, 1440), (1280, 720), (3440, 1440)]:
                with self.subTest(screen=i, size=size):
                    scaled = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
                    result = detect(scaled, cfg, templates, cv2)
                    self.assertIsNotNone(result)
                    self.assertEqual(result[0], name)
        self.assertIsNone(detect(np.zeros_like(frame), cfg, templates, cv2))

    def test_keyboard_and_click_actions(self):
        cfg = read_config()
        controller = Mock()
        for name, key in [("start", "f"), ("continue_results", "esc"), ("close_rewards", "esc")]:
            perform_action(name, (100, 200, 1), cfg, controller)
            controller.press.assert_called_with(key)
        controller.click.assert_not_called()
        perform_action("confirm", (100, 200, 1), cfg, controller)
        controller.click.assert_called_once_with(100, 200)

    def test_widescreen_edge_anchored_layout(self):
        import cv2
        import numpy as np
        cfg = read_config()
        templates = load_templates(cfg, cv2, np)
        rw, rh = cfg["screen_size"]
        w, h = 3440, 1440
        scale = h / rh
        for name, (primary, guards) in templates.items():
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            for img, rect in [primary, *guards]:
                left, top, right, bottom = rect
                centre = (left + right) / 2
                offset = 0 if centre < rw / 3 else (w - rw * scale if centre > rw * 2 / 3 else (w - rw * scale) / 2)
                x, y = round(left * scale + offset), round(top * scale)
                resized = cv2.resize(img, (round(img.shape[1] * scale), round(img.shape[0] * scale)))
                padded = cv2.copyMakeBorder(resized, 8, 8, 8, 8, cv2.BORDER_REPLICATE)
                frame[y-8:y + resized.shape[0]+8, x-8:x + resized.shape[1]+8] = padded
            with self.subTest(state=name):
                result = detect(frame, cfg, templates, cv2)
                self.assertIsNotNone(result)
                self.assertEqual(result[0], name)


def baseline_movement(controller, **kwargs):
    settings = dict(delay=60, pickup_delay=30, vault_enabled=False, look_down_pixels=0)
    settings.update(kwargs)
    return RoundMovement(controller, **settings)


def legacy_movement(controller, **kwargs):
    return baseline_movement(controller, delay=90, pickup_delay=0, sprint=False, turn_right_pixels=0, **kwargs)


class StuckTests(unittest.TestCase):
    def test_stable_scene_triggers_at_one_second(self):
        import cv2
        import numpy as np
        frame = np.full((180, 320, 3), 100, dtype=np.uint8)
        monitor = MotionMonitor()
        self.assertFalse(monitor.update(frame, 0, cv2))
        self.assertFalse(monitor.update(frame, .5, cv2))
        self.assertFalse(monitor.update(frame, .99, cv2))
        self.assertTrue(monitor.update(frame, 1, cv2))

    def test_main_scene_animation_does_not_hide_stuck(self):
        import cv2
        import numpy as np
        rng = np.random.default_rng(23)
        frame = rng.integers(40, 140, (180, 320, 3), dtype=np.uint8)
        monitor = MotionMonitor(seconds=10)
        monitor.update(frame, 0, cv2)
        for now in range(1, 11):
            noisy = frame.copy()
            noisy[40:108, 64:104] = rng.integers(0, 256, (68, 40, 3), dtype=np.uint8)
            self.assertEqual(monitor.update(noisy, now, cv2), now == 10)

    def test_slow_scene_drift_does_not_trigger_stuck(self):
        import cv2
        import numpy as np
        frame = np.random.default_rng(24).integers(20, 100, (180, 320, 3), dtype=np.uint8)
        monitor = MotionMonitor(seconds=10)
        monitor.update(frame, 0, cv2)
        for now in range(1, 16):
            self.assertFalse(monitor.update(frame + now * 6, now, cv2))

    def test_flat_wall_is_valid_motion_evidence(self):
        import cv2
        import numpy as np
        frame = np.full((180, 320, 3), 100, dtype=np.uint8)
        monitor = MotionMonitor(seconds=10)
        self.assertFalse(monitor.update(frame, 0, cv2))
        self.assertTrue(monitor.update(frame, 10, cv2))

    def test_static_scenery_triggers_after_ten_seconds_and_cools_down(self):
        import cv2
        import numpy as np
        frame = np.random.default_rng(1).integers(0, 256, (180, 320, 3), dtype=np.uint8)
        monitor = MotionMonitor(seconds=10)
        self.assertFalse(monitor.update(frame, 0, cv2))
        self.assertFalse(monitor.update(frame, 9.99, cv2))
        self.assertTrue(monitor.update(frame, 10, cv2))
        self.assertFalse(monitor.update(frame, 20, cv2))
        self.assertFalse(monitor.update(frame, 25, cv2))
        self.assertFalse(monitor.update(frame, 34.99, cv2))
        self.assertTrue(monitor.update(frame, 35, cv2))

    def test_motion_resets_timer_hud_is_ignored_and_blank_is_skipped(self):
        import cv2
        import numpy as np
        rng = np.random.default_rng(2)
        frame = rng.integers(20, 180, (180, 320, 3), dtype=np.uint8)
        monitor = MotionMonitor(seconds=10)
        monitor.update(frame, 0, cv2)
        changed = frame + 30
        self.assertFalse(monitor.update(changed, 9, cv2))
        self.assertFalse(monitor.update(changed, 10, cv2))
        hud = changed.copy()
        hud[:30] = 255
        self.assertFalse(monitor.update(hud, 19, cv2))
        self.assertTrue(monitor.update(hud, 20, cv2))
        blank_monitor = MotionMonitor(seconds=10)
        self.assertFalse(blank_monitor.update(np.zeros_like(frame), 0, cv2))
        self.assertFalse(blank_monitor.update(np.zeros_like(frame), 100, cv2))

    def test_nonblocking_recovery_alternates_sides_and_resumes_pickup(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = baseline_movement(controller)
        move.start(0)
        move.tick(60, None)
        move.recover(100)
        self.assertFalse(move.holding)
        controller.keyDown.assert_called_with("s")
        count = controller.press.call_count
        move.tick(101.19, None)
        self.assertEqual(controller.press.call_count, count)
        move.tick(101.2, None)
        controller.keyUp.assert_called_with("s")
        controller.keyDown.assert_called_with("a")
        move.tick(102.71, None)
        controller.keyUp.assert_called_with("a")
        controller.keyDown.assert_any_call("w")
        move.tick(103.21, None)
        self.assertEqual(controller.press.call_count, count + 1)
        move.recover(200)
        move.tick(201.2, None)
        controller.keyDown.assert_called_with("d")
        move.observe("confirm", 202)
        controller.keyUp.assert_called_with("d")
        self.assertIsNone(move.recovery_phase)
        self.assertFalse(move.holding)

    def test_cancel_backward_releases_s_and_preview_never_sends_inputs(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = baseline_movement(controller)
        move.start(0)
        move.tick(60, None)
        move.recover(100)
        move.release()
        controller.keyUp.assert_called_with("s")
        self.assertTrue(controller.FAILSAFE)
        preview_controller = Mock()
        preview = baseline_movement(preview_controller, live=False)
        preview.start(0)
        preview.tick(60, None)
        preview.recover(100)
        preview.tick(101.2, None)
        preview.tick(102.71, None)
        preview.release()
        self.assertEqual(preview_controller.mock_calls, [])


class NewBehaviorTests(unittest.TestCase):
    def test_minimap_only_ignores_scene_timer_and_central_marker(self):
        import cv2
        import numpy as np
        frame = minimap_fixture()
        h, w = frame.shape[:2]
        monitor = MotionMonitor()
        base = monitor.sample(frame, cv2)
        changed = np.zeros_like(frame)
        rect = monitor.minimap_rect
        x1, y1, x2, y2 = [round(v * (w if i % 2 == 0 else h)) for i, v in enumerate(rect)]
        changed[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
        cx, cy = (x1+x2)//2, (y1+y2)//2
        changed[cy-15:cy+15, cx-15:cx+15] = (255, 255, 255)
        sample = monitor.sample(changed, cv2)
        self.assertLess(float(cv2.absdiff(base, sample).mean()), .1)
        self.assertFalse(monitor.update(frame, 0, cv2))
        self.assertTrue(monitor.update(changed, 1, cv2))

    def test_scrolling_minimap_terrain_resets_stuck_timer(self):
        import cv2
        import numpy as np
        frame = minimap_fixture()
        h, w = frame.shape[:2]
        monitor = MotionMonitor()
        x1, y1, x2, y2 = [round(v * (w if i % 2 == 0 else h)) for i, v in enumerate(monitor.minimap_rect)]
        terrain = frame[y1:y2, x1:x2].copy()
        monitor.update(frame, 0, cv2)
        for now in (.5, 1, 1.5, 2):
            moved = frame.copy()
            transform = np.float32([[1, 0, now*8], [0, 1, now*4]])
            moved[y1:y2, x1:x2] = cv2.warpAffine(terrain, transform, (x2-x1, y2-y1), borderMode=cv2.BORDER_REFLECT)
            self.assertFalse(monitor.update(moved, now, cv2))

    def test_minimap_sampling_scales_with_screen_resolution(self):
        import cv2
        import numpy as np
        frame = minimap_fixture()
        reference = MotionMonitor.sample(frame, cv2)
        for size in ((1280, 720), (1920, 1080), (2560, 1440)):
            with self.subTest(size=size):
                sample = MotionMonitor.sample(cv2.resize(frame, size), cv2)
                self.assertIsNotNone(sample)
                self.assertEqual(sample.shape, (128, 128))
                self.assertLess(float(cv2.absdiff(reference, sample).mean()), 4)

    def test_calibrated_turn_and_120_second_wait(self):
        controller = Mock()
        move = RoundMovement(controller)
        move.start(0)
        move.tick(119.99, None)
        controller.press.assert_not_called()
        move.tick(120, None)
        controller.move_relative.assert_called_once_with(4050, 0)
        controller.press.assert_called_once_with("f")
        move.tick(149.99, None)
        controller.press.assert_called_once()
        move.tick(150, None)
        controller.move_relative.assert_called_with(0, 5000)
        self.assertEqual(controller.press.call_count, 2)

    def test_new_timing_ground_view_once_and_sprint_refresh(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = RoundMovement(controller, delay=90, turn_right_pixels=900, pickup_delay=60)
        move.start(0)
        move.tick(89.99, None)
        controller.press.assert_not_called()
        move.tick(90, None)
        controller.keyDown.assert_has_calls([call("w"), call("shift")])
        move.tick(92, None)
        self.assertEqual(controller.keyDown.call_args_list[-2:], [call("w"), call("shift")])
        move.tick(149.99, None)
        controller.move_relative.assert_called_once_with(900, 0)
        controller.press.assert_called_once_with("f")
        move.tick(150, None)
        controller.move_relative.assert_called_with(0, 5000)
        self.assertEqual(controller.press.call_count, 2)
        move.release()
        move.tick(151, None)
        self.assertEqual(controller.move_relative.call_count, 2)
        move.observe("return_lobby", 152)
        self.assertFalse(move.looked_down)
        controller.keyUp.assert_has_calls([call("w"), call("shift")])

    def test_vault_motion_succeeds_without_backward(self):
        import cv2
        import numpy as np
        controller = Mock()
        move = RoundMovement(controller, delay=90, turn_right_pixels=900, pickup_delay=60)
        move.start(0)
        move.tick(90, None)
        move.tick(150, None)
        move.recover(170)
        self.assertTrue(move.holding)
        controller.keyDown.assert_has_calls([call("shift"), call("c")])
        move.tick(170.16, None)
        controller.keyUp.assert_called_with("c")
        move.tick(172.17, None)
        self.assertEqual(move.recovery_phase, "vault_watch")
        frame = np.random.default_rng(12).integers(20, 150, (180, 320, 3), dtype=np.uint8)
        move.observe_recovery_motion(frame, 172.2, cv2)
        move.observe_recovery_motion(frame + 30, 173.2, cv2)
        self.assertIsNotNone(move.recovery_phase)
        move.observe_recovery_motion(frame + 40, 174.2, cv2)
        self.assertIsNone(move.recovery_phase)
        self.assertNotIn(call("s"), controller.keyDown.call_args_list)
        before = controller.press.call_count
        move.tick(174.7, None)
        self.assertEqual(controller.press.call_count, before + 1)

    def test_failed_vault_falls_back_and_cleans_all_keys(self):
        import cv2
        import numpy as np
        controller = Mock()
        controller.FAILSAFE = True
        move = RoundMovement(controller, delay=90, turn_right_pixels=900, pickup_delay=60)
        move.start(0)
        move.tick(90, None)
        move.recover(170)
        move.tick(170.16, None)
        move.tick(172.17, None)
        frame = np.random.default_rng(15).integers(0, 256, (180, 320, 3), dtype=np.uint8)
        for now in (172.2, 173.2, 174.2):
            move.observe_recovery_motion(frame, now, cv2)
        move.tick(175.18, None)
        self.assertEqual(move.recovery_phase, "backward")
        controller.keyUp.assert_has_calls([call("w"), call("shift")])
        controller.keyDown.assert_called_with("s")
        move.tick(176.39, None)
        controller.keyDown.assert_called_with("a")
        move.tick(177.90, None)
        self.assertTrue(move.holding)
        self.assertTrue(move.sprinting)
        move.recover(200)
        move.observe("confirm", 200.1)
        controller.keyUp.assert_has_calls([call("w"), call("shift"), call("c")])
        self.assertFalse(move.holding)
        self.assertIsNone(move.extra_key)

    def test_scan_code_input_uses_left_shift_and_sends_keyup_for_taps(self):
        import ctypes
        import struct
        backend = Mock()
        backend.FAILSAFE = True
        adapter = WindowsInput(backend)
        packets = []
        send = Mock(side_effect=lambda count, data, size: packets.append(ctypes.string_at(data, size)) or 1)
        with patch("bot.ctypes.windll.user32.SendInput", send), patch("bot.time.sleep"):
            adapter.keyDown("w")
            adapter.keyDown("shift")
            adapter.press("f")
            adapter.keyUp("shift")
        payload_offset = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 4
        decoded = [(struct.unpack_from("H", packet, payload_offset + 2)[0],
                    struct.unpack_from("I", packet, payload_offset + 4)[0]) for packet in packets]
        self.assertEqual(decoded, [(0x11, 8), (0x2a, 8), (0x21, 8), (0x21, 10), (0x2a, 10)])
        self.assertEqual(len(packets[0]), 40 if payload_offset == 8 else 28)
        backend.press.assert_not_called()
        self.assertTrue(backend.FAILSAFE)


class MovementTests(unittest.TestCase):
    def test_automatic_ground_view_at_corner_does_not_pause(self):
        import numpy as np
        controller = Mock()
        controller.FAILSAFE = True
        controller.position.return_value = (1919, 1079)
        controller.FAILSAFE_POINTS = [(0, 0), (1919, 1079)]
        controller.screenshot.return_value = np.zeros((2, 2, 3), dtype=np.uint8)
        user32 = Mock()
        iterations = 0

        def key_state(key):
            nonlocal iterations
            if key == 0x78:
                iterations += 1
                return 0x8000 if iterations >= 6 else 0
            return 0

        user32.GetAsyncKeyState.side_effect = key_state
        cfg = read_config()
        cfg.update(stable_frames=1, interval=.001, mouse_corner_pause=False)
        cfg["movement"] = {"jump_delay_seconds": .01, "pickup_delay_after_jump_seconds": .01,
                           "turn_right_pixels": 0, "keyboard_backend": "legacy"}
        overlay = Mock()
        with patch.dict("sys.modules", {"pyautogui": controller}), \
                patch("bot.read_config", return_value=cfg), \
                patch("bot.load_templates", return_value={}), \
                patch("bot.foreground_matches", return_value=True), \
                patch("bot.ctypes.windll.user32", user32), \
                patch("bot.WindowsInput.move_relative") as turn, \
                patch("bot.detect", side_effect=[("start", (1, 1, 1)), None, None, None, None]), \
                self.assertLogs(level="INFO") as logs:
            run(True, overlay)
        turn.assert_called_once_with(0, 5000)
        self.assertFalse(controller.FAILSAFE)
        self.assertFalse(any("已暂停" in line for line in logs.output))
        self.assertTrue(any("向下压视角" in line for line in logs.output))
        controller.keyUp.assert_has_calls([call("w"), call("shift")])

    def test_jump_turn_once_and_sprint_releases_on_interrupt(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = baseline_movement(controller, turn_right_pixels=750)
        move.start(0)
        move.tick(60, None)
        self.assertEqual(controller.method_calls[:4], [call.press("f"), call.move_relative(750, 0),
                                                      call.keyDown("w"), call.keyDown("shift")])
        move.release()
        controller.keyUp.assert_has_calls([call("w"), call("shift")])
        move.tick(75, None)
        controller.move_relative.assert_called_once_with(750, 0)
        self.assertEqual(controller.keyDown.call_args_list[-2:], [call("w"), call("shift")])
        move.recover(100)
        self.assertFalse(move.sprinting)
        move.tick(101.2, None)
        move.tick(102.71, None)
        self.assertTrue(move.sprinting)
        controller.move_relative.assert_called_once()
        move.observe("return_lobby", 103)
        self.assertFalse(move.holding)
        self.assertFalse(move.sprinting)

    def test_corner_exception_pauses_and_f7_resumes_instead_of_exiting(self):
        import numpy as np
        class CornerError(Exception):
            pass
        controller = Mock()
        controller.FailSafeException = CornerError
        controller.FAILSAFE = True
        controller.position.return_value = (1, 1)
        controller.screenshot.return_value = np.zeros((2, 2, 3), dtype=np.uint8)
        controller.press.side_effect = [None, CornerError("corner"), None]
        user32 = Mock()
        iterations = 0

        def key_state(key):
            nonlocal iterations
            if key == 0x78:
                iterations += 1
                return 0x8000 if iterations >= 6 else 0
            if key == 0x76 and iterations >= 4:
                return 0x8000
            return 0

        user32.GetAsyncKeyState.side_effect = key_state
        cfg = read_config()
        cfg.update(stable_frames=1, interval=.001, mouse_corner_pause=True)
        cfg["movement"] = {"jump_delay_seconds": .01, "turn_right_pixels": 0, "keyboard_backend": "legacy"}
        overlay = Mock()
        with patch.dict("sys.modules", {"pyautogui": controller}), \
                patch("bot.read_config", return_value=cfg), \
                patch("bot.load_templates", return_value={}), \
                patch("bot.foreground_matches", return_value=True), \
                patch("bot.ctypes.windll.user32", user32), \
                patch("bot.detect", side_effect=[("start", (1, 1, 1)), None, None, None, None]), \
                self.assertLogs(level="INFO") as logs:
            run(True, overlay)
        self.assertTrue(any("角落保护已暂停" in line for line in logs.output))
        self.assertTrue(any("已继续" in line for line in logs.output))
        self.assertEqual(controller.press.call_count, 3)
        controller.keyDown.assert_has_calls([call("w"), call("shift")])
        controller.keyUp.assert_has_calls([call("w"), call("shift")])

    def test_separate_pause_and_resume_keys_are_idempotent(self):
        self.assertTrue(pause_state(False, True, False))
        self.assertTrue(pause_state(True, True, False))
        self.assertFalse(pause_state(True, False, True))
        self.assertFalse(pause_state(False, False, True))
        self.assertTrue(pause_state(False, True, True))
        self.assertTrue(pause_state(True, False, False))
        self.assertFalse(pause_state(False, False, False))

    def test_lobby_disappearance_then_jump_then_pickup_delay(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = baseline_movement(controller)
        move.arm()
        move.observe("start", 1000)  # matchmaking may take as long as needed
        move.tick(1000, "start")
        self.assertIsNone(move.started)
        move.observe(None, 1001)
        move.observe("start", 1002)  # one missed detection must not start timer
        move.observe(None, 1003)
        move.observe(None, 1004)
        self.assertIsNone(move.started)
        move.observe(None, 1005)
        self.assertEqual(move.started, 1005)
        move.tick(1064.99, None)
        controller.press.assert_not_called()
        move.tick(1065, None)
        controller.press.assert_called_once_with("f")
        controller.keyDown.assert_any_call("w")
        move.tick(1094.99, None)
        controller.press.assert_called_once()
        move.tick(1095, None)
        self.assertEqual(controller.press.call_count, 2)
        move.tick(1095.49, None)
        self.assertEqual(controller.press.call_count, 2)
        move.tick(1095.5, None)
        self.assertEqual(controller.press.call_count, 3)
        move.observe("return_lobby", 1096)
        self.assertFalse(move.armed)
        controller.keyUp.assert_any_call("w")

    def test_resume_does_not_skip_airborne_pickup_delay(self):
        controller = Mock()
        move = baseline_movement(controller)
        move.start(0)
        move.tick(60, None)
        move.release()
        move.tick(75, None)
        controller.press.assert_called_once_with("f")
        move.tick(89.99, None)
        controller.press.assert_called_once()
        move.tick(90, None)
        self.assertEqual(controller.press.call_count, 2)

    def test_pickup_taps_every_half_second_while_w_stays_held(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = legacy_movement(controller)
        move.start(0)
        move.tick(90, None)
        controller.press.assert_called_once_with("f")  # jump
        move.tick(90.49, None)
        self.assertEqual(controller.press.call_count, 1)
        move.tick(90.5, None)
        move.tick(91, None)
        self.assertEqual(controller.press.call_count, 3)
        controller.keyDown.assert_any_call("w")
        controller.keyUp.assert_not_called()
        move.observe("return_lobby", 91.1)
        move.tick(100, "return_lobby")
        move.tick(101, None)
        self.assertEqual(controller.press.call_count, 3)
        controller.keyUp.assert_any_call("w")

    def test_pickup_can_be_disabled_and_never_bursts_after_resume(self):
        controller = Mock()
        move = legacy_movement(controller, pickup_enabled=False)
        move.start(0)
        move.tick(90, None)
        move.tick(1000, None)
        controller.press.assert_called_once_with("f")
        enabled = legacy_movement(controller)
        enabled.start(0)
        enabled.tick(90, None)
        enabled.release()
        enabled.tick(1000, None)
        self.assertEqual(controller.press.call_count, 2)  # no pickup on resume
        enabled.tick(1000.5, None)
        self.assertEqual(controller.press.call_count, 3)

    def test_long_round_death_and_next_round(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = legacy_movement(controller)
        move.start(10)
        move.tick(99.9, None)
        controller.press.assert_not_called()
        move.tick(100, None)
        controller.press.assert_called_once_with("f")
        controller.keyDown.assert_any_call("w")
        move.tick(3600, None)
        self.assertEqual(controller.press.call_count, 2)  # one pickup; no catch-up burst
        move.observe("return_lobby", 3601)
        controller.keyUp.assert_any_call("w")
        self.assertIsNone(move.started)
        move.start(3700)
        move.tick(3790, None)
        self.assertEqual(controller.press.call_count, 3)

    def test_suspend_resume_and_cleanup_with_failsafe(self):
        controller = Mock()
        controller.FAILSAFE = True
        move = legacy_movement(controller)
        move.start(0)
        move.tick(90, None)
        move.release()
        self.assertTrue(controller.FAILSAFE)
        self.assertFalse(move.holding)
        move.tick(100, None)
        self.assertEqual(controller.keyDown.call_count, 2)
        controller.press.assert_called_once_with("f")
        move.reset()
        self.assertEqual(controller.keyUp.call_count, 2)

    def test_death_preempts_jump_and_preview_never_sends_keys(self):
        controller = Mock()
        move = legacy_movement(controller)
        move.start(0)
        move.observe("confirm", 90)
        move.tick(90, "confirm")
        controller.press.assert_not_called()
        preview = legacy_movement(controller, live=False)
        preview.start(0)
        preview.tick(90, None)
        preview.release()
        self.assertEqual(controller.mock_calls, [])

    def test_lobby_does_not_receive_timed_jump(self):
        controller = Mock()
        move = legacy_movement(controller)
        move.start(0)
        move.start(20)
        self.assertEqual(move.started, 0)
        move.observe("start", 90)
        move.tick(90, "start")
        controller.press.assert_not_called()
        self.assertIsNone(move.started)

    def test_f9_releases_w_in_running_loop(self):
        import numpy as np
        controller = Mock()
        controller.FAILSAFE = True
        controller.position.return_value = (1, 1)
        controller.screenshot.return_value = np.zeros((2, 2, 3), dtype=np.uint8)
        user32 = Mock()
        calls = 0

        def key_state(key):
            nonlocal calls
            if key == 0x78:
                calls += 1
                return 0x8000 if calls >= 4 else 0
            return 0

        user32.GetAsyncKeyState.side_effect = key_state
        cfg = read_config()
        cfg.update(stable_frames=1, interval=.001, mouse_corner_pause=True)
        cfg["movement"] = {"enabled": True, "jump_delay_seconds": .01, "turn_right_pixels": 0, "keyboard_backend": "legacy"}
        with patch.dict("sys.modules", {"pyautogui": controller}), \
                patch("bot.read_config", return_value=cfg), \
                patch("bot.load_templates", return_value={}), \
                patch("bot.foreground_matches", return_value=True), \
                patch("bot.ctypes.windll.user32", user32), \
                patch("bot.detect", side_effect=[("start", (1, 1, 1)), None, None]):
            run(True)
        self.assertEqual(controller.press.call_count, 2)
        controller.keyDown.assert_any_call("w")
        controller.keyUp.assert_any_call("w")
        self.assertTrue(controller.FAILSAFE)


if __name__ == "__main__":
    unittest.main()
