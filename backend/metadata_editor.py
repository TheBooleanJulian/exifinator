"""
metadata_editor.py
Backend logic for the Camera Metadata Batch Editor.
Wraps the exiftool CLI (bundled or system-installed) — kept separate from the
GUI so it can be tested and reused headlessly.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".tif", ".tiff", ".png", ".heic", ".heif",
    ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2",
}

# Tag groups exposed in the GUI. Each entry maps a checkbox label to the
# actual exiftool tag name(s) that get written together.
FIELD_GROUPS = {
    "EXIF Artist":            ["EXIF:Artist"],
    "EXIF Copyright":         ["EXIF:Copyright"],
    "IPTC By-line (Creator)": ["IPTC:By-line"],
    "IPTC Copyright Notice":  ["IPTC:CopyrightNotice"],
    "IPTC Credit":            ["IPTC:Credit"],
    "IPTC Source":            ["IPTC:Source"],
    "XMP Creator":            ["XMP-dc:Creator"],
    "XMP Rights":             ["XMP-dc:Rights"],
    "XMP Credit":             ["XMP-photoshop:Credit"],
}

# Which GUI groups should be filled from the "Name" text box vs the
# "Copyright notice" text box.
NAME_FIELDS = {"EXIF Artist", "IPTC By-line (Creator)", "XMP Creator"}
COPYRIGHT_FIELDS = {
    "EXIF Copyright", "IPTC Copyright Notice", "IPTC Credit",
    "IPTC Source", "XMP Rights", "XMP Credit",
}

READ_TAGS = [
    "FileName", "Model", "DateTimeOriginal",
    "EXIF:Artist", "EXIF:Copyright",
    "IPTC:By-line", "IPTC:CopyrightNotice",
    "XMP-dc:Creator", "XMP-dc:Rights",
]


@dataclass
class FileInfo:
    path: Path
    filename: str
    model: str = ""
    date: str = ""
    artist: str = ""
    copyright: str = ""
    selected: bool = True


def find_exiftool() -> str:
    """Locate the exiftool executable — bundled next to Exifinator.py (the
    app root, one level up from this backend/ module) first, falling back
    to whatever is on PATH."""
    here = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    for candidate in ("exiftool.exe", "exiftool"):
        bundled = here / candidate
        if bundled.exists():
            return str(bundled)
    found = shutil.which("exiftool")
    if found:
        return found
    raise FileNotFoundError(
        "exiftool was not found. Install it from https://exiftool.org "
        "and make sure it's on your PATH, or place the executable next "
        "to this program."
    )


def _run_exiftool(exiftool: str, args: list[str]) -> subprocess.CompletedProcess:
    """Run exiftool with the given arguments via an -@ argfile rather than
    directly on the command line. A folder with enough files (or long paths)
    can push the command line past Windows' ~32K character limit, which
    fails with WinError 206 ("filename or extension is too long") even
    though every individual path is well within MAX_PATH."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".args", delete=False, encoding="utf-8-sig"
    ) as f:
        f.write("\n".join(args))
        argfile = f.name
    try:
        return subprocess.run([exiftool, "-@", argfile], capture_output=True, text=True)
    finally:
        Path(argfile).unlink(missing_ok=True)


def scan_folder(folder: Path, recursive: bool = False) -> list[FileInfo]:
    """Scan a folder for image files and read their current authorship tags."""
    exiftool = find_exiftool()
    pattern = "**/*" if recursive else "*"
    files = sorted(
        p for p in Path(folder).glob(pattern)
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    if not files:
        return []

    args = ["-j", "-fast2"] + [f"-{t}" for t in READ_TAGS] + [str(f) for f in files]
    result = _run_exiftool(exiftool, args)
    if result.returncode not in (0, 1):  # exiftool returns 1 on minor warnings
        raise RuntimeError(f"exiftool scan failed: {result.stderr.strip()}")

    records = json.loads(result.stdout or "[]")
    out = []
    for f, rec in zip(files, records):
        out.append(FileInfo(
            path=f,
            filename=rec.get("FileName", f.name),
            model=rec.get("Model", ""),
            date=rec.get("DateTimeOriginal", ""),
            artist=rec.get("Artist", "") or rec.get("Creator", ""),
            copyright=rec.get("Copyright", "") or rec.get("CopyrightNotice", "") or rec.get("Rights", ""),
        ))
    return out


def build_tag_args(name_value: str, copyright_value: str, active_groups: list[str]) -> list[str]:
    """Translate GUI selections into exiftool -Tag=Value arguments."""
    args = []
    for group in active_groups:
        tags = FIELD_GROUPS.get(group, [])
        if group in NAME_FIELDS:
            value = name_value
        elif group in COPYRIGHT_FIELDS:
            value = copyright_value
        else:
            continue
        if not value:
            continue
        for tag in tags:
            args.append(f"-{tag}={value}")
    return args


def apply_edits(
    files: list[Path],
    name_value: str,
    copyright_value: str,
    active_groups: list[str],
    keep_backup: bool = True,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Write the selected tags to the selected files.

    Returns (success, message). In dry_run mode nothing is written; the
    command that *would* run is returned instead for preview.
    """
    if not files:
        return False, "No files selected."

    tag_args = build_tag_args(name_value, copyright_value, active_groups)
    if not tag_args:
        return False, "No fields selected, or the text boxes are empty."

    exiftool = find_exiftool()
    args = list(tag_args)
    args.append("-overwrite_original" if not keep_backup else "-P")  # -P preserves file mod date, keeps _original backup by default
    args += [str(f) for f in files]

    if dry_run:
        return True, " ".join([exiftool] + args)

    result = _run_exiftool(exiftool, args)
    if result.returncode not in (0, 1):
        return False, result.stderr.strip() or "Unknown exiftool error."
    return True, result.stdout.strip()


if __name__ == "__main__":
    print("This is a backend module, not the app. Run: python Exifinator.py")
