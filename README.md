# Exifinator

A lightweight desktop tool for extracting and copying EXIF metadata from photos. Built with Python and Tkinter — no browser, no upload, fully local.

---

## What it does

Open any photo and instantly see its shooting data:

- **Camera** — make and model
- **Lens** — model name
- **Focal length, aperture, shutter speed, ISO**
- **White balance and flash status**
- **Date/time** the shot was taken
- **Location** — reverse-geocoded from GPS coordinates to a readable place name

Hit **Copy to Clipboard** to grab the output as formatted text.

---

## Requirements

```
Python 3.8+
Pillow
pyperclip
geopy
tkinter (included with standard Python on Windows/macOS)
```

Install dependencies:

```bash
pip install Pillow pyperclip geopy
```

---

## Usage

```bash
python Exifinator.py
```

1. Click **Browse** or the image preview area to open a photo
2. EXIF data appears in the text box
3. Click **Copy to Clipboard** to copy the formatted output

---

## Supported formats

`.jpg` `.jpeg` `.png` `.tiff` `.bmp`

> Note: GPS reverse-geocoding requires an internet connection (via OpenStreetMap/Nominatim). All other features work fully offline.

---

## Output example

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

---

## Known limitations

- RAW formats (`.NEF`, `.CR2`, `.ARW`) are not currently supported — EXIF is read from rendered/JPEG-embedded data only
- GPS lookup depends on Nominatim's uptime and rate limits; heavy batch use may throttle results
- `_getexif()` is a Pillow internal method and may behave differently across library versions

---

## License

MIT
