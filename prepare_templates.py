"""Build the five-screen profile from supplied screenshots, in p1..p5 order."""
import argparse
import json
import shutil
from pathlib import Path
from PIL import Image
from bot import ROOT, CONFIG, DEFAULT_ANTI_STUCK


def prepare(paths):
    images = [Image.open(p).convert("RGB") for p in paths]
    size = images[0].size
    if any(im.size != size for im in images):
        raise ValueError("五张截图必须具有相同尺寸。")
    references = ROOT / "reference_screens"
    references.mkdir(exist_ok=True)
    for i, image in enumerate(images, 1):
        image.save(references / f"p{i}.png")
    if CONFIG.exists():
        shutil.copy2(CONFIG, ROOT / "config.before_screenshots.json")
    folder = ROOT / "templates"
    folder.mkdir(exist_ok=True)

    def crop(index, name, rect):
        # Coordinates measured on the 2048x1152 conversation preview.
        rect = [round(v * size[i % 2] / (2048 if i % 2 == 0 else 1152))
                for i, v in enumerate(rect)]
        path = folder / f"{name}.png"
        images[index].crop(rect).save(path)
        return {"path": f"templates/{name}.png", "rect": rect,
                "relative_rect": [v / size[i % 2] for i, v in enumerate(rect)]}

    specs = [
        ("start", 0, [195, 1010, 310, 1052], {"key": "f"}, None),
        ("return_lobby", 2, [120, 1068, 225, 1100], {"click": True},
         [75, 155, 625, 218]),
        ("confirm", 1, [884, 686, 937, 715], {"click": True},
         [903, 446, 1154, 496]),
        ("continue_results", 3, [166, 1075, 210, 1097], {"key": "esc"},
         [1700, 85, 1986, 135]),
        ("close_rewards", 4, [167, 1074, 210, 1098], {"key": "esc"},
         [875, 199, 980, 225]),
    ]
    cfg = {"window_title": "PUBG", "threshold": .90, "stable_frames": 3,
           "interval": 0.5, "mouse_corner_pause": False, "cooldown": 12, "screen_size": list(size), "templates": {},
           "anti_stuck": dict(DEFAULT_ANTI_STUCK),
           "overlay": {"enabled": True},
           "movement": {"enabled": True, "jump_delay_seconds": 120,
                        "pickup_enabled": True, "pickup_interval_seconds": 0.5,
                        "pickup_delay_after_jump_seconds": 30,
                        "sprint": True, "turn_right_pixels": 4050,
                        "look_down_pixels": 5000, "keyboard_backend": "scan"}}
    for name, index, rect, action, guard in specs:
        entry = crop(index, name, rect)
        entry.update(action=action, screen_size=list(size))
        if guard:
            entry["guards"] = [crop(index, name + "_guard", guard)]
        if name in ("confirm", "return_lobby"):
            centre = (909, 700) if name == "confirm" else (171, 1083)
            entry["click_point"] = [round(centre[0] * size[0] / 2048),
                                     round(centre[1] * size[1] / 1152)]
            entry["relative_click_point"] = [centre[0] / 2048, centre[1] / 1152]
        cfg["templates"][name] = entry
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Prepared five-screen profile:", size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs=5, type=Path, help="p1 p2 p3 p4 p5")
    prepare(parser.parse_args().images)
