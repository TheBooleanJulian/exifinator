"""
exif_reader.py
Backend logic for the "Read" tab — extracts EXIF data from a single photo
and formats it for display. Kept separate from the GUI so it can be tested
or reused headlessly, same split as metadata_core.py for the batch editor.
"""

from fractions import Fraction

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".bmp"}


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
    with Image.open(image_path) as img:
        exif_data = img._getexif()
        if not exif_data:
            return None
        return {TAGS.get(tag, tag): value for tag, value in exif_data.items()}


def get_gps_location(gps_info):
    """Reverse-geocode GPS coordinates to a readable place name via Nominatim.
    Requires internet access; every other field in this module is offline."""
    if not gps_info:
        return "N/A"

    gps_tags = {GPSTAGS.get(tag, tag): value for tag, value in gps_info.items()}

    if "GPSLatitude" in gps_tags and "GPSLongitude" in gps_tags:
        import geopy.geocoders

        lat = gps_tags["GPSLatitude"]
        lon = gps_tags["GPSLongitude"]
        lat_ref = gps_tags.get("GPSLatitudeRef", "N")
        lon_ref = gps_tags.get("GPSLongitudeRef", "E")

        latitude = (lat[0] + lat[1] / 60 + lat[2] / 3600) * (-1 if lat_ref == "S" else 1)
        longitude = (lon[0] + lon[1] / 60 + lon[2] / 3600) * (-1 if lon_ref == "W" else 1)

        geolocator = geopy.geocoders.Nominatim(user_agent="exif_reader")
        location = geolocator.reverse((latitude, longitude), language="en")
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
    iso = exif.get("ISOSpeedRatings", "N/A")
    camera_model = exif.get("Model", "N/A")
    camera_make = exif.get("Make", "N/A")
    lens_model = exif.get("LensModel", "N/A")
    focal_length = exif.get("FocalLength", "N/A")
    white_balance = "Auto" if exif.get("WhiteBalance") == 0 else "Manual"
    flash = "Fired" if exif.get("Flash", 0) & 1 else "Not Fired"
    datetime_original = exif.get("DateTimeOriginal", "N/A")
    location = get_gps_location(exif.get("GPSInfo", None))

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
