"""
File renamer backend (no UI, standard library only).

RenameEngine computes new names from a set of options, plan_renames() turns a
file list into a conflict-free list of (old, new) moves, and the undo log
helpers persist the last batch so it can be reverted after a restart.
"""

import json
import re
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff",
              ".webp", ".heic", ".heif", ".raw", ".nef", ".cr2", ".cr3",
              ".arw", ".dng", ".raf", ".orf", ".rw2"}


def _undo_file() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) \
        else Path(__file__).resolve().parent.parent
    return base / "exifinator_rename_undo.json"


UNDO_FILE = _undo_file()


def save_undo_log(batch_log):
    """Persist the last batch (list of (new_path, old_path)); empty deletes the file."""
    try:
        if not batch_log:
            UNDO_FILE.unlink(missing_ok=True)
            return
        data = [{"old": str(old), "new": str(new)} for (new, old) in batch_log]
        UNDO_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # undo still works for the current session


def load_undo_log():
    """Return list[(new_path, old_path)] from disk, or [] if missing/corrupt."""
    try:
        data = json.loads(UNDO_FILE.read_text(encoding="utf-8"))
        return [(Path(e["new"]), Path(e["old"])) for e in data]
    except (OSError, ValueError, KeyError, TypeError):
        return []


class RenameEngine:
    """Pure logic: given a file path + options, compute the new name."""

    def __init__(self):
        self.find_text = ""
        self.replace_text = ""
        self.remove_text = ""
        self.remove_is_regex = False
        self.prepend_text = ""
        self.append_text = ""
        self.case_mode = "none"             # none | upper | lower | title
        self.numbering_enabled = False
        self.numbering_position = "suffix"  # prefix | suffix
        self.numbering_start = 1
        self.numbering_digits = 3
        self.numbering_separator = "_"
        self.preset_enabled = False
        self.preset_date = ""
        self.preset_event = ""
        self.preset_photographer = ""
        self.new_extension = ""             # "" = keep original, else e.g. ".jpg"
        self.conflict_mode = "auto_number"  # auto_number | skip | overwrite

    def compute_new_name(self, original_path: Path, index: int) -> str:
        stem = original_path.stem
        ext = original_path.suffix

        # 1. Find & Replace
        if self.find_text:
            stem = stem.replace(self.find_text, self.replace_text)

        # 2. Remove text
        if self.remove_text:
            if self.remove_is_regex:
                try:
                    stem = re.sub(self.remove_text, "", stem)
                except re.error:
                    pass  # invalid regex mid-typing; ignore until valid
            else:
                stem = stem.replace(self.remove_text, "")

        # 3 & 4. Prepend / Append
        stem = f"{self.prepend_text}{stem}{self.append_text}"

        # 5. Case change
        if self.case_mode == "upper":
            stem = stem.upper()
        elif self.case_mode == "lower":
            stem = stem.lower()
        elif self.case_mode == "title":
            stem = stem.title()

        # 5b. Event preset: <date>_<event>_Photo By <photographer>_<name>
        if self.preset_enabled:
            prefix = f"{self.preset_date}_{self.preset_event}_Photo By {self.preset_photographer}"
            stem = f"{prefix}_{stem.lstrip('_')}"

        # 6. Sequential numbering
        if self.numbering_enabled:
            num = str(self.numbering_start + index).zfill(self.numbering_digits)
            if self.numbering_position == "prefix":
                stem = f"{num}{self.numbering_separator}{stem}"
            else:
                stem = f"{stem}{self.numbering_separator}{num}"

        # 7. Extension override
        final_ext = self.new_extension if self.new_extension else ext

        return f"{stem}{final_ext}"


def plan_renames(files, engine: RenameEngine):
    """Return list[(old_path, new_path)], applying the engine's conflict mode."""
    planned = []
    used = set()
    for idx, path in enumerate(files):
        new_path = path.parent / engine.compute_new_name(path, idx)
        if new_path == path:
            continue  # nothing to do

        if new_path.exists() or new_path in used:
            if engine.conflict_mode == "skip":
                continue
            elif engine.conflict_mode == "auto_number":
                stem, ext = new_path.stem, new_path.suffix
                n = 1
                candidate = new_path
                while candidate.exists() or candidate in used:
                    candidate = new_path.parent / f"{stem} ({n}){ext}"
                    n += 1
                new_path = candidate
            # "overwrite": fall through, os.replace overwrites

        used.add(new_path)
        planned.append((path, new_path))
    return planned
