# PUBG AFK Helper

[简体中文](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/README.md) · **English** · [日本語](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.ja.md) · [Deutsch](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.de.md) · [Français](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.fr.md) · [Español](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.es.md) · [Português](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.pt.md)

Uses OpenCV to recognize PUBG screens, show detection status, and run configurable workflows on Windows. Includes a detection-only preview and offline regression tests.

Python · OpenCV · Windows

[![Windows tests](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)

PUBG automatic process tool based on **OpenCV screen recognition, Windows simulation input and minimap change detection**.
Identify the lobby and checkout interface, perform configurable matching, jump, move, pick up and escape processes, and display the current step through the overhead status window.

## Features

- **interface recognizes**: lobby, return to lobby, exit confirmation, character settlement and reward page; continuous recognition confirmation and limit repeated operations.
- **relative positioning**: scale the template and coordinates according to the screen size, and support edge-aligned search for some widescreen layouts.
- **game process**: time jump after the hall disappears, turn right once, W+Left Shift to continue moving forward, click F to pick up after looking down.
- **Mini map anti-stuck wall**: Only compare the map terrain in the lower right corner and block the central character mark; try Shift+C first, then back up and move left and right according to the detection results.
- **Top status window**: Displays countdown, actions, pause reasons and minimap detection indicators; mouse penetration does not steal the focus of the game.
- **configurable and testable**: JSON configuration, template recording tool, offline regression testing, Windows CI.

The program works through screenshots and normal operating system input, does not read game memory, and does not inject game processes.
The project is still in its early stages; fixed timings and mini-map changes are approximate and cannot confirm the aircraft, actual landing, pickup success, or reward receipt.
Please confirm the game rules and account risks by yourself before use; this project does not provide anti-cheating bypass functions.

## Quick start

Requires **Windows 10/11, Python 3.11+**, the game uses the borderless window mode of the main monitor.

1. Download `PUBG-helper.zip` in the latest Release](https://github.com/chenbinghan666/pubg-afk-helper/releases/latest) of [, or clone this repository.
2. Install Python and check **Add Python to PATH**.
3. Double-click `install.cmd` and wait for the dependency installation to complete.
4. When using it for the first time, double-click **`preview.cmd`**, switch back to the game and check the recognition log; this mode does not send input.
5. After confirming that the recognition is correct, close the preview and double-click **`launch.cmd`** to enable automatic operation.

```powershell
git clone https://github.com/chenbinghan666/pubg-afk-helper.git
cd pubg-afk-helper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bot.py             # Only recognize
.\.venv\Scripts\python.exe bot.py --live      # Enable input
```

Git clones read `config.example.json` by default. Copy it to `config.json` before customization, and the local configuration will not be submitted to Git:

```powershell
Copy-Item config.example.json config.json
```

The warehouse comes with a set of button cropping templates for the Traditional Chinese interface. If the language, game version, HUD scale or layout is different, the template needs to be re-recorded, and it cannot be guaranteed to be directly applicable to all computers.

## Default workflow

```text
Identify the hall → F starts matching
  → Lobby disappearance detected 3 times in a row → wait 120 seconds
  → F Try skydiving → turn right once → W + Left Shift
  → 30 seconds after skydive: looking down at the ground → Tap F every 0.5 seconds
  → Minimap is stable for about 1 second: try to cross, back/traverse if necessary
  → Death/Settlement: Release button → Return to lobby → next round
```

The disappearance of the lobby may also be a loading screen, which does not prove that you have entered the room. All times are adjustable.
The default input offsets for turning right (**4050**) and looking down (**5000**) are starting values. The actual angles depend on your in-game sensitivity and mouse settings.
Sprinting and Shift+C leaping need to be consistent with the game key and hold/toggle settings.

## Keyboard shortcuts

| Button | function |
| --- | --- |
| **F8** | Pause only, releasing keys held by the script |
| **F7** | Just continue |
| **F9** | Exit and release the key |
| **Ctrl+C** | Stop program in terminal |

Input is paused when switching out of the game and will be automatically resumed after switching back; the countdown that has started is still calculated based on the actual elapsed time.
Mouse corner pause is turned off by default to avoid automatic overlooking trigger protection, and can be enabled individually with `mouse_corner_pause`.
Keystroke cleaning cannot be performed when the process is forcibly terminated or the computer is powered off.

## Configuration and troubleshooting

For complete parameters, template recording commands, minimap relative area and sensitivity calibration method, please refer to the [Configuration and Use Manual](../../docs/CONFIGURATION.md).

| question | Priority check |
| --- | --- |
| No recognition or action | Whether the top window shows pause, whether the game is in the foreground, and whether the window title contains `PUBG` |
| Start or settlement recognition failed | Whether the interface language, resolution, HUD scale matches the template |
| Skydive too early / too late | `movement.jump_delay_seconds` |
| Picking up too early/looking down in the wrong direction | `pickup_delay_after_jump_seconds`, `look_down_pixels` and Y-axis reverse settings |
| Wrong right turn angle | Calibrate according to actual rotation angle `turn_right_pixels` |
| Sprinting or leaping has no effect | Keybinding, hold mode, run permissions, and whether the game accepts analog input |
| Anti-jamming wall misjudgment/missing | Stable scale indicators for minimap area, zoom, rotation settings and overhead windows |

The log is written to local `bot.log`. Please remove account, chat, private path and other information before giving feedback.

## develop

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe package.py
```

The test simulates keyboard and mouse input without operating the game. The public version automatically generates synthetic images for testing; if it exists locally
`reference_screens/`, you can use the corresponding personal reference screenshots for additional regression. This directory is not included in the warehouse or distribution package.
CI runs tests on Windows using Python 3.11 and 3.12.
Offline testing cannot replace real game verification under different hardware, game versions and sensitivities.

Main files: `bot.py` is the state machine, recognition and input implementation, `status_overlay.py` is the status window,
`prepare_templates.py` is a five-interface template generation tool, and `package.py` is a distribution package building script.

Welcome to report reproducible problems through [Issues](https://github.com/chenbinghan666/pubg-afk-helper/issues).
Please read the [contribution instructions](../../CONTRIBUTING.md) before submitting changes. For version records, see [CHANGELOG](../../CHANGELOG.md).

## license

Original code and documentation are licensed under [MIT License](../../LICENSE). The game interface cutting, name and trademark still belong to their respective rights holders, please see [third-party statement](../../NOTICE.md) for details. This project has no affiliation or official partnership with KRAFTON / PUBG.
