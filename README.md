<div align="center">

# Exifinator

**A lightweight local desktop tool for extracting EXIF metadata from photos — no browser, no upload.**

![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-00D4C8.svg)

</div>

---

## What it does

Exifinator is a local desktop app that reads EXIF metadata from photos and presents it in a clean, copyable format. Open a photo, instantly see camera model, lens, focal length, aperture, shutter speed, ISO, flash, white balance, date taken, and reverse-geocoded GPS location. Everything runs on your machine — no upload, no account, no cloud.

## Features

- Reads camera make/model, lens, focal length, aperture, shutter speed, ISO, white balance, flash, and date taken
- Formats shutter speeds below 1s as fractions (e.g. `1/800`)
- Reverse-geocodes GPS coordinates to a readable place name via OpenStreetMap/Nominatim
- Image thumbnail preview displayed alongside EXIF output
- One-click **Copy to Clipboard** for formatted output
- Cyberpunk-themed dark UI with teal accents (Segoe UI / Consolas)
- Fully offline except for GPS lookup; no data leaves your machine

## Tech Stack

| Layer | Choice |
|---|---|
| Desktop UI | Python + Tkinter |
| Image / EXIF | Pillow |
| Clipboard | pyperclip |
| Geocoding | geopy (Nominatim / OpenStreetMap) |

## Quick Start

```bash
git clone https://github.com/TheBooleanJulian/exifinator
cd exifinator
pip install Pillow pyperclip geopy
python Exifinator.py
```

> `tkinter` is included with the standard Python distribution on Windows and macOS.

## Usage

1. Click **Browse** or the image preview area to open a photo
2. EXIF data populates in the text box
3. Click **Copy to Clipboard** to grab the formatted output

**Supported formats:** `.jpg` `.jpeg` `.png` `.tiff` `.bmp`

> GPS reverse-geocoding requires an internet connection. All other features work fully offline.

## Output Example

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
```

## Known Limitations

- RAW formats (`.NEF`, `.CR2`, `.ARW`) are not supported — EXIF is read from JPEG-embedded data only
- GPS lookup depends on Nominatim uptime and rate limits; heavy batch use may throttle results
- `_getexif()` is a Pillow internal method and may behave differently across library versions

## Status / Roadmap

- [x] EXIF extraction and clipboard copy
- [x] GPS reverse-geocoding to readable place name
- [x] Image thumbnail preview
- [x] Shutter speed fraction formatting
- [x] Cyberpunk dark-theme UI
- [ ] RAW format support (NEF, CR2, ARW)
- [ ] Batch processing / folder scan

## Changelog

- **April 2026** — UI polish: replaced Courier New with Segoe UI / Consolas per branding guidelines; applied cyberpunk dark theme with teal accents and emoji icons
- **April 2026** — Added image thumbnail preview alongside EXIF metadata display
- **April 2026** — Shutter speeds below 1s now display as fractions (e.g. `1/800`)
- **April 2026** — Initial release: EXIF extraction, GPS reverse-geocoding, clipboard copy

## License

MIT

---

<div align="center">
<sub>Built by <a href="https://github.com/TheBooleanJulian">@TheBooleanJulian</a></sub>
</div>