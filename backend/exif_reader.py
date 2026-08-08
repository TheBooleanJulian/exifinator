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

if __name__ == "__main__":
    print("This is a backend module, not the app. Run: python Exifinator.py")
    raise SystemExit(0)

from backend.metadata_editor import IMAGE_EXTS, find_exiftool

SUPPORTED_EXTS = IMAGE_EXTS

# Tags to pull from exiftool. A trailing "#" forces the raw numeric value
# (needed for math/formatting below); tags without it get exiftool's own
# print-converted text, which for WhiteBalance/LightSource/Flash is often a
# maker-note-specific description (e.g. "Tungsten", "Cloudy", "Fired") richer
# than the generic two-value EXIF spec would otherwise give.
READ_TAGS = [
    "Make", "Model", "LensModel",
    "FocalLength#", "ExposureTime#", "FNumber#", "ISO",
    "WhiteBalance", "LightSource", "ColorTemperature",
    "Flash", "FocusDistance", "SubjectDistance",
    "DateTimeOriginal",
    "GPSLatitude#", "GPSLongitude#", "GPSAltitude#", "GPSAltitudeRef#",
    "ImageWidth", "ImageHeight", "ExifImageWidth", "ExifImageHeight", "Megapixels",
    "Software", "Artist", "Creator", "Copyright", "Rights",
    "ShutterCount",
]


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
    """Read the fields in READ_TAGS for one file via exiftool."""
    exiftool = find_exiftool()
    cmd = [exiftool, "-j"] + [f"-{t}" for t in READ_TAGS] + [str(image_path)]
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


def _first(*values):
    """Return the first non-empty value; flattens single-item XMP lists."""
    for value in values:
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) if value else None
        if value not in (None, ""):
            return value
    return "N/A"


def format_white_balance(exif):
    """Prefer WhiteBalance's maker-note description (e.g. "Tungsten",
    "Cloudy", "Kelvin") over the generic two-value EXIF spec, falling back
    to LightSource, and appending a Kelvin reading when the camera reports
    one (common when WB is set to a manual color temperature)."""
    wb = _first(exif.get("WhiteBalance"), exif.get("LightSource"))
    color_temp = exif.get("ColorTemperature")
    if color_temp:
        return f"{wb} ({color_temp}K)" if wb != "N/A" else f"{color_temp}K"
    return wb


def format_gps_altitude(exif):
    altitude = exif.get("GPSAltitude")
    if altitude is None:
        return "N/A"
    below_sea_level = exif.get("GPSAltitudeRef") == 1
    sign = "-" if below_sea_level else ""
    return f"{sign}{abs(altitude):.1f}m"


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
    white_balance = format_white_balance(exif)
    flash = exif.get("Flash", "N/A")
    focus_distance = _first(exif.get("FocusDistance"), exif.get("SubjectDistance"))
    datetime_original = exif.get("DateTimeOriginal", "N/A")
    location = get_gps_location(exif)
    altitude = format_gps_altitude(exif)

    width = exif.get("ImageWidth") or exif.get("ExifImageWidth")
    height = exif.get("ImageHeight") or exif.get("ExifImageHeight")
    megapixels = exif.get("Megapixels")
    dimensions = f"{width} × {height}" if width and height else "N/A"
    if megapixels:
        dimensions += f"  ({megapixels:.1f} MP)"

    software = exif.get("Software", "N/A")
    artist = _first(exif.get("Artist"), exif.get("Creator"))
    copyright_notice = _first(exif.get("Copyright"), exif.get("Rights"))
    shutter_count = exif.get("ShutterCount", "N/A")

    return (
        f"✦ ───────────────────── ✦\n\n"
        f"\U0001f4f7 Camera:\n   {camera_make} {camera_model}\n\n"
        f"\U0001f52d Lens:\n   {lens_model}\n\n"
        f"\U0001f4cf Focal Length:\n   {focal_length}mm\n\n"
        f"⏱️ Shutter Speed:\n   {shutter_speed}\n\n"
        f"\U0001f317 Aperture:\n   f/{aperture}\n\n"
        f"\U0001f506 ISO:\n   {iso}\n\n"
        f"\U0001f3af Focus Distance:\n   {focus_distance}\n\n"
        f"⚪ White Balance:\n   {white_balance}\n\n"
        f"\U0001f4a1 Flash:\n   {flash}\n\n"
        f"\U0001f550 Date Taken:\n   {datetime_original}\n\n"
        f"\U0001f4cd Location:\n   {location}\n\n"
        f"⛰️ Altitude:\n   {altitude}\n\n"
        f"\U0001f5bc️ Dimensions:\n   {dimensions}\n\n"
        f"\U0001f4bb Software:\n   {software}\n\n"
        f"✒️ Artist:\n   {artist}\n\n"
        f"©️ Copyright:\n   {copyright_notice}\n\n"
        f"\U0001f522 Shutter Count:\n   {shutter_count}\n\n"
        f"✦ ───────────────────── ✦"
    )
