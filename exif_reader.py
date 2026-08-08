"""
exif_reader.py
Backend logic for the "Read" tab — extracts EXIF data from a single photo
and formats it for display. Kept separate from the GUI so it can be tested
or reused headlessly, same split as metadata_editor.py for the batch editor.

Uses the exiftool CLI (via metadata_editor.find_exiftool) rather than Pillow
so RAW formats (NEF, ARW, CR2/CR3, DNG, RAF, ORF, RW2, ...) are readable too,
not just JPEG/PNG/TIFF.
"""

import json
import subprocess
from fractions import Fraction

from metadata_editor import IMAGE_EXTS, find_exiftool

SUPPORTED_EXTS = IMAGE_EXTS


def format_shutter_speed(speed):
    """Convert shutter speed to human-readable format (fractions for < 1s)"""
    if speed == "N/A":
        return "N/A"

    try:
        speed_value = float(speed) if isinstance(speed, Fraction) else float(speed)
        if speed_value < 1:
            denominator = round(1 / speed_value)
            return f"1/{denominator}"
        if speed_value == int(speed_value):
            return f"{int(speed_value)}s"
        return f"{speed_value:.1f}s"
    except (ValueError, TypeError, ZeroDivisionError):
        return str(speed)


def get_exif(image_path):
    """Read all EXIF/IPTC/XMP/maker-note tags exiftool can find for one file.
    -n keeps values numeric (not print-converted) so downstream formatting
    logic can treat FNumber/ExposureTime/WhiteBalance/Flash/GPS consistently."""
    exiftool = find_exiftool()
    cmd = [exiftool, "-j", "-n", str(image_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode not in (0, 1):  # exiftool returns 1 on minor warnings
        raise RuntimeError(f"exiftool read failed: {result.stderr.strip()}")

    records = json.loads(result.stdout or "[]")
    if not records:
        return None
    return records[0]


def get_preview_image_bytes(image_path):
    """Extract an embedded preview/thumbnail image (as JPEG bytes) from a
    RAW file via exiftool, for formats Pillow can't decode directly."""
    exiftool = find_exiftool()
    for tag in ("-PreviewImage", "-JpgFromRaw", "-ThumbnailImage"):
        result = subprocess.run(
            [exiftool, "-b", tag, str(image_path)],
            capture_output=True,
        )
        if result.returncode in (0, 1) and result.stdout:
            return result.stdout
    return None


def get_gps_location(exif):
    """Reverse-geocode GPS coordinates to a readable place name via Nominatim.
    Requires internet access; every other field in this module is offline."""
    if not exif:
        return "N/A"

    lat = exif.get("GPSLatitude")
    lon = exif.get("GPSLongitude")
    if lat is None or lon is None:
        return "N/A"

    import geopy.geocoders

    geolocator = geopy.geocoders.Nominatim(user_agent="exif_reader")
    location = geolocator.reverse((lat, lon), language="en")
    if location:
        address = location.raw.get("address", {})
        return f"{address.get('state', 'Unknown')}, {address.get('country', 'Unknown')}"

    return "N/A"


def extract_basic_exif(image_path) -> str:
    """Return a formatted, human-readable EXIF summary for one photo."""
    exif = get_exif(image_path)
    if not exif:
        return "❌ No EXIF data found."

    shutter_speed = format_shutter_speed(exif.get("ExposureTime", "N/A"))
    aperture = exif.get("FNumber", "N/A")
    iso = exif.get("ISO", "N/A")
    camera_model = exif.get("Model", "N/A")
    camera_make = exif.get("Make", "N/A")
    lens_model = exif.get("LensModel", "N/A")
    focal_length = exif.get("FocalLength", "N/A")
    white_balance = "Auto" if exif.get("WhiteBalance") == 0 else "Manual"
    flash = "Fired" if int(exif.get("Flash", 0) or 0) & 1 else "Not Fired"
    datetime_original = exif.get("DateTimeOriginal", "N/A")
    location = get_gps_location(exif)

    return (
        f"✦ ───────────────────── ✦\n\n"
        f"\U0001f4f7 Camera:\n   {camera_make} {camera_model}\n\n"
        f"\U0001f52d Lens:\n   {lens_model}\n\n"
        f"\U0001f4cf Focal Length:\n   {focal_length}mm\n\n"
        f"⏱️  Shutter Speed:\n   {shutter_speed}\n\n"
        f"\U0001f317 Aperture:\n   f/{aperture}\n\n"
        f"\U0001f506 ISO:\n   {iso}\n\n"
        f"⚪ White Balance:\n   {white_balance}\n\n"
        f"\U0001f4a1 Flash:\n   {flash}\n\n"
        f"\U0001f550 Date Taken:\n   {datetime_original}\n\n"
        f"\U0001f4cd Location:\n   {location}\n\n"
        f"✦ ───────────────────── ✦"
    )
