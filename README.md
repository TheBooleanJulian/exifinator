<div align="center">

<img src="assets/exifinator-logo.png" alt="Exifinator logo" width="240">

# Exifinator

**A lightweight local desktop tool for reading *and* batch-editing photo metadata — no browser, no upload.**

![Version](https://img.shields.io/badge/version-2.1.0-00D4C8.svg)
![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-AGPLv3%20%2B%20Commercial-00D4C8.svg)

![Exifinator](assets/hero-v1.png)

</div>

---

## What it does

Exifinator is a local desktop app for working with photo metadata, in two tabs:

- **Read** — open one photo (including RAW), instantly see camera model, lens, focal length, aperture, shutter speed, ISO, flash, white balance, date taken, GPS location/altitude, dimensions, software, Artist/Copyright, and shutter count.
- **Batch Edit** — fix **Artist / Copyright / Creator** tags across a whole folder of photos at once (e.g. after borrowing a camera that still has someone else's name baked into every shot). Edits EXIF, IPTC, and XMP fields together or individually, lets you preview before writing, and keeps `_original` backups by default.

Everything runs on your machine — no account, no cloud. The only thing that touches the internet is optional GPS reverse-geocoding on the Read tab.

## Features

**Read tab**
- Reads camera make/model, lens, focal length, aperture, shutter speed, ISO, white balance, flash, date taken, image dimensions/megapixels, software, Artist, Copyright, and shutter count
- Supports RAW formats (CR2/CR3, NEF, ARW, DNG, RAF, ORF, RW2) as well as JPEG/PNG/TIFF/HEIC — reads via exiftool, same backend as Batch Edit
- Thumbnail preview for RAW files falls back to the embedded preview image when Pillow can't decode the file directly
- Formats shutter speeds below 1s as fractions (e.g. `1/800`)
- Reverse-geocodes GPS coordinates (and altitude) to a readable place name via OpenStreetMap/Nominatim
- One-click **Copy to Clipboard** for formatted output

**Batch Edit tab**
- Scans a folder (optionally including subfolders) and shows every photo's *current* Artist/Copyright at a glance
- Writes Name/Creator and Copyright values across nine EXIF/IPTC/XMP fields, grouped with plain-English tooltips so you don't need to know the tag names
- **Preview (dry run)** shows exactly what would be written, in readable form, before anything touches disk
- Per-file checkboxes plus Select All / Select None
- Keeps `_original` backup copies by default
- Camera serial number and similar hardware-identifying fields are intentionally not exposed — they identify the physical body, not authorship

**Both tabs**
- Cyberpunk-themed dark UI with teal accents (Segoe UI / Consolas)
- Fully offline except for GPS lookup; no data leaves your machine

## Tech Stack

| Layer | Choice |
|---|---|
| Desktop UI | Python + Tkinter |
| Image / thumbnail display | Pillow |
| EXIF/IPTC/XMP read (Read tab) & read/write (Batch Edit tab) | [exiftool](https://exiftool.org) (external binary) |
| Clipboard | Tkinter (built-in) |
| Geocoding | geopy (Nominatim / OpenStreetMap) |

## Quick Start

```bash
git clone https://github.com/TheBooleanJulian/exifinator
cd exifinator
pip install -r requirements.txt
python Exifinator.py
```

> `tkinter` is included with the standard Python distribution on Windows and macOS.

Both tabs need **exiftool** on your machine:
- Windows: https://exiftool.org → download the `.zip`, extract, rename `exiftool(-k).exe` to `exiftool.exe`, and place it in the **same folder** as `Exifinator.py` (or anywhere on your PATH)
- macOS: `brew install exiftool`
- Linux: `sudo apt install libimage-exiftool-perl`

## Usage

### Read tab
1. Click **Browse Photo…** or the preview area to open a photo
2. EXIF data populates in the text box
3. Click **Copy to Clipboard** to grab the formatted output

**Supported formats:** `.jpg` `.jpeg` `.png` `.tif` `.tiff` `.heic` `.heif` `.cr2` `.cr3` `.nef` `.arw` `.dng` `.raf` `.orf` `.rw2`

> GPS reverse-geocoding requires an internet connection. All other Read-tab features work fully offline.

### Batch Edit tab
1. **Choose Folder…** — pick the folder of photos (tick "Include subfolders" if needed)
2. The table shows every image with its **current** Artist/Copyright, so you can see at a glance whose name is still on the borrowed camera's shots
3. Uncheck any files you don't want touched (☑/☐ in the first column, or use Select All / Select None)
4. Fill in **Name** and **Copyright notice** on the right, and tick which of the fields to write — hover the ⓘ next to each if you're not sure what it does
5. Click **Preview Changes (dry run)** to see exactly what will be written, without touching any files
6. Click **Apply Changes** to write it for real. Leave "Keep original files as backup" ticked unless you're sure — it saves a `filename.jpg_original` copy next to each edited file

## Output Example

**Read tab:**
```
Camera: NIKON CORPORATION NIKON D850
Lens: AF-S NIKKOR 85mm f/1.4G
Focal Length: 85mm
Shutter Speed: 1/500
Aperture: f/1.4
ISO: 200
White Balance: Auto
Flash: Not Fired
Date Taken: 2025:11:02 14:33:21
Location: New South Wales, Australia
Altitude: 58.2m
Dimensions: 5440 × 3616  (19.7 MP)
Software: Ver.1.30
Artist: Julian Cheung/Accurova
Copyright: Julian Cheung/Accurova
Shutter Count: 230363
```

**Batch Edit preview:**
```
Preview only — nothing written yet. 42 file(s) would be updated:

  EXIF:Artist  →  "Julian Cheung"
  IPTC:By-line  →  "Julian Cheung"
  XMP-dc:Creator  →  "Julian Cheung"
  EXIF:Copyright  →  "© 2026 Julian Cheung / Accurova"
```

## Turning it into a standalone .exe (optional)

If you want a double-clickable executable instead of running via `python`:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-binary "exiftool.exe;." Exifinator.py
```

Run this **on the target OS** (e.g. on Windows to get a Windows `.exe`) — PyInstaller doesn't cross-compile. The `--add-binary` flag bundles exiftool into the executable itself so end users don't need to install anything separately for either tab. The output lands in `dist/Exifinator.exe`.

## Known Limitations

- Both tabs require exiftool to be installed separately (not bundled), unless you build the standalone .exe with `--add-binary`
- GPS lookup depends on Nominatim uptime and rate limits; heavy use may throttle results
- Shutter Count is only populated for cameras whose maker notes expose it (mainly Canon/Nikon/Pentax/some Sony bodies) — most files will show `N/A`
- RAW thumbnail previews use the file's embedded preview/thumbnail image, not a full raw decode, so preview quality/orientation may differ slightly from the original

## Status / Roadmap

- [x] EXIF extraction and clipboard copy
- [x] GPS reverse-geocoding to readable place name
- [x] Image thumbnail preview
- [x] Shutter speed fraction formatting
- [x] Cyberpunk dark-theme UI
- [x] Batch processing / folder scan (Batch Edit tab)
- [x] RAW format support on the Read tab (NEF, CR2/CR3, ARW, DNG, RAF, ORF, RW2)

## Future Roadmap

- [ ] Export Read-tab EXIF to CSV / JSON for archiving or spreadsheet import
- [ ] Drag-and-drop file support instead of Browse-only
- [ ] Editable/removable EXIF fields on the Read tab (privacy scrubbing before sharing photos)
- [ ] Offline reverse-geocoding option (bundled dataset) to remove the Nominatim dependency
- [ ] Packaged standalone executable (PyInstaller) so Python isn't required to run it
- [ ] Recent files list / drag history
- [ ] Dark/light theme toggle

## Changelog

Versioning follows `major.minor.patch`: **major** for a new release line, **minor** for new features, **patch** for fixes/polish/docs.

- **v2.1.0** — 2026-08-09 — Read tab now reads via exiftool instead of Pillow, adding RAW support (CR2/CR3, NEF, ARW, DNG, RAF, ORF, RW2) with embedded-preview thumbnails, plus new fields (GPS altitude, dimensions/megapixels, Software, Artist, Copyright, Shutter Count); app window now uses the Exifinator logo as its icon; backend modules (`exif_reader.py`, `metadata_editor.py`) moved into a `backend/` package so `Exifinator.py` is the only entry point at the project root; removed unused `pyperclip` dependency
- **v2.0.0** — 2026-08-09 — Merged in the standalone Camera Metadata Batch Editor as a second **Batch Edit** tab (folder-wide Artist/Copyright/Creator writing via exiftool, with dry-run preview and plain-English field tooltips); app is now a single `Exifinator.py` entry point with a tabbed UI instead of two separate tools
- **v1.3.2** — 2026-07-18 — Revamped README with badges, feature table, roadmap, and changelog (`3be2659`)
- **v1.3.1** — 2026-04-08 — Modernized fonts: replaced Courier New with Segoe UI / Consolas per branding guidelines (`9c23c93`)
- **v1.3.0** — 2026-04-08 — Added image thumbnail preview alongside EXIF metadata display (`ef64d4d`)
- **v1.2.0** — 2026-04-08 — Beautified UI/UX with cyberpunk branding — teal accents, dark theme, emoji icons (`c3279cb`)
- **v1.1.0** — 2026-04-08 — Shutter speeds below 1s now display as fractions, e.g. `1/800` (`62ffd2e`)
- **v1.0.0** — 2026-04-08 — Initial release: EXIF extraction, GPS reverse-geocoding, clipboard copy (`38ce1e6`)

## License

This project is dual licensed.

- Community Edition — [GNU Affero General Public License v3 (AGPLv3)](LICENSE). Free to use, modify, and self-host. If you distribute a modified version or run it as a network service, you must make the corresponding source available.
- Commercial License — for organisations that want to embed, modify, or distribute this software without AGPLv3's obligations. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

---

<div align="center">
<sub>Built by <a href="https://github.com/TheBooleanJulian">@TheBooleanJulian</a></sub>
</div>
