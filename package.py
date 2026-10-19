"""Build a source distribution without machine-specific virtual environments."""
from zipfile import ZipFile, ZIP_DEFLATED
from bot import ROOT

with ZipFile(ROOT / "PUBG-helper.zip", "w", ZIP_DEFLATED) as archive:
    files = [ROOT / name for name in ("bot.py", "config.example.json", "requirements.txt",
                                     "launch.cmd", "preview.cmd", "install.cmd", "README.md", "status_overlay.py",
                                     "LICENSE", "NOTICE.md", "CHANGELOG.md")]
    files += sorted((ROOT / "docs").glob("*.md"))
    files += sorted((ROOT / "templates").glob("*.png"))
    for path in files:
        archive.write(path, path.relative_to(ROOT))
    # Public release configuration never comes from a user's local overrides.
    archive.write(ROOT / "config.example.json", "config.json")
print("Created PUBG-helper.zip")
