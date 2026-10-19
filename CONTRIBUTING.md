# Contributing

Use Python 3.11 or newer on Windows. Install `requirements.txt` in a virtual
environment, then run `python -m unittest -v` before submitting a pull request.
Tests mock input calls and must not send real keyboard or mouse events.

Keep changes focused and include a reproduction or a meaningful regression
test for behavior changes. New timers and recovery actions must remain
interruptible and release all owned keys on pause, focus loss and exit.

Report bugs with the program version, screen resolution, UI scale, relevant
configuration and a short redacted log excerpt. Remove names, chat messages,
account details and local paths from screenshots and logs. Never include
tokens, passwords, the virtual environment or full personal screenshots.

Changes that read or modify game memory, inject into the game process or
attempt to bypass anti-cheat are outside this project's scope.
