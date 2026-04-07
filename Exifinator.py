import sys
import pyperclip
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from PIL.ExifTags import TAGS, GPSTAGS
import geopy.geocoders
from fractions import Fraction

def format_shutter_speed(speed):
    """Convert shutter speed to human-readable format (fractions for < 1s)"""
    if speed == "N/A":
        return "N/A"
    
    try:
        # Handle Fraction objects
        if isinstance(speed, Fraction):
            speed_value = float(speed)
        else:
            speed_value = float(speed)
        
        # For speeds below 1 second, express as 1/x
        if speed_value < 1:
            denominator = round(1 / speed_value)
            return f"1/{denominator}"
        else:
            # For speeds >= 1 second, express as "x" or "x.x"
            if speed_value == int(speed_value):
                return f"{int(speed_value)}s"
            else:
                return f"{speed_value:.1f}s"
    except (ValueError, TypeError, ZeroDivisionError):
        return str(speed)

def get_exif(image_path):
    with Image.open(image_path) as img:
        exif_data = img._getexif()
        if not exif_data:
            return None
        
        exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
        return exif

def get_gps_location(gps_info):
    if not gps_info:
        return "N/A"
    
    gps_tags = {GPSTAGS.get(tag, tag): value for tag, value in gps_info.items()}
    
    if 'GPSLatitude' in gps_tags and 'GPSLongitude' in gps_tags:
        lat = gps_tags['GPSLatitude']
        lon = gps_tags['GPSLongitude']
        lat_ref = gps_tags.get('GPSLatitudeRef', 'N')
        lon_ref = gps_tags.get('GPSLongitudeRef', 'E')
        
        latitude = (lat[0] + lat[1] / 60 + lat[2] / 3600) * (-1 if lat_ref == 'S' else 1)
        longitude = (lon[0] + lon[1] / 60 + lon[2] / 3600) * (-1 if lon_ref == 'W' else 1)
        
        geolocator = geopy.geocoders.Nominatim(user_agent="exif_reader")
        location = geolocator.reverse((latitude, longitude), language='en')
        if location:
            return f"{location.raw.get('address', {}).get('state', 'Unknown')}, {location.raw.get('address', {}).get('country', 'Unknown')}"
    
    return "N/A"

def extract_basic_exif(image_path):
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
    gps_info = exif.get("GPSInfo", None)
    location = get_gps_location(gps_info)
    
    exif_text = (f"✦ ━━━━━━━━━━━━━━━━━━━━━ ✦\n\n"
                 f"📷 Camera:\n   {camera_make} {camera_model}\n\n"
                 f"🔭 Lens:\n   {lens_model}\n\n"
                 f"📏 Focal Length:\n   {focal_length}mm\n\n"
                 f"⏱️  Shutter Speed:\n   {shutter_speed}\n\n"
                 f"🌗 Aperture:\n   f/{aperture}\n\n"
                 f"🔆 ISO:\n   {iso}\n\n"
                 f"⚪ White Balance:\n   {white_balance}\n\n"
                 f"💡 Flash:\n   {flash}\n\n"
                 f"🕐 Date Taken:\n   {datetime_original}\n\n"
                 f"📍 Location:\n   {location}\n\n"
                 f"✦ ━━━━━━━━━━━━━━━━━━━━━ ✦")
    
    return exif_text

def browse_file():
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.tiff;*.bmp")])
    if file_path:
        display_exif(file_path)

def display_exif(image_path):
    global current_image_path, thumbnail_label
    
    # Load and display thumbnail
    try:
        img = Image.open(image_path)
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        thumbnail_label.config(image=photo)
        thumbnail_label.image = photo  # Keep a reference
        current_image_path = image_path
    except Exception as e:
        thumbnail_label.config(text=f"❌ Error loading thumbnail\n{str(e)}")
    
    # Display EXIF data
    exif_text = extract_basic_exif(image_path)
    text_var.set(exif_text)
    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, exif_text)

def copy_to_clipboard():
    text = text_box.get("1.0", tk.END).strip()
    pyperclip.copy(text)

def create_gui():
    global text_var, text_box, thumbnail_label, current_image_path
    current_image_path = None
    root = tk.Tk()
    root.title("✦ Exifinator")
    root.geometry("850x750")
    root.resizable(True, True)
    
    # TheBooleanJulian Branding Colors
    BG_DARK = "#060910"
    BG_CARD = "#0c1018"
    TEAL_PRIMARY = "#00d4c8"
    TEAL_DARK = "#009e94"
    TEXT_WHITE = "#e8eaf0"
    TEXT_MUTED = "#6b7280"
    
    root.configure(bg=BG_DARK)
    
    # Title Section
    title_frame = tk.Frame(root, bg=BG_DARK)
    title_frame.pack(pady=(20, 10), fill=tk.X, padx=20)
    
    title_label = tk.Label(
        title_frame,
        text="✦ 初音ミク ♪ Exifinator",
        font=("Courier New", 24, "bold"),
        bg=BG_DARK,
        fg=TEAL_PRIMARY
    )
    title_label.pack()
    
    subtitle_label = tk.Label(
        title_frame,
        text="Extract EXIF metadata with cyberpunk vibes",
        font=("Courier New", 10),
        bg=BG_DARK,
        fg=TEXT_MUTED
    )
    subtitle_label.pack()
    
    # Main Content Frame (Thumbnail + EXIF Data side by side)
    content_frame = tk.Frame(root, bg=BG_DARK)
    content_frame.pack(pady=15, padx=20, fill=tk.BOTH, expand=True)
    
    # Thumbnail Section
    thumbnail_section = tk.Frame(content_frame, bg=BG_DARK)
    thumbnail_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 15))
    
    thumbnail_title = tk.Label(
        thumbnail_section,
        text="🖼️ Preview",
        font=("Courier New", 11, "bold"),
        bg=BG_DARK,
        fg=TEAL_PRIMARY
    )
    thumbnail_title.pack(pady=(0, 10))
    
    # Thumbnail Display
    thumbnail_frame = tk.Frame(thumbnail_section, width=220, height=220, bg=BG_CARD, relief=tk.FLAT, borderwidth=2)
    thumbnail_frame.pack(fill=tk.BOTH, expand=False)
    thumbnail_frame.pack_propagate(False)
    
    thumbnail_label = tk.Label(
        thumbnail_frame,
        text="📤 Click or Browse\nto load image",
        font=("Courier New", 10),
        bg=BG_CARD,
        fg=TEAL_PRIMARY,
        relief=tk.FLAT
    )
    thumbnail_label.pack(expand=True)
    
    thumbnail_frame.bind("<Button-1>", lambda e: browse_file())
    thumbnail_label.bind("<Button-1>", lambda e: browse_file())
    
    # Right Section (EXIF Data)
    right_section = tk.Frame(content_frame, bg=BG_DARK)
    right_section.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # EXIF Data Display
    data_label = tk.Label(
        right_section,
        text="📊 EXIF Data:",
        font=("Courier New", 11, "bold"),
        bg=BG_DARK,
        fg=TEAL_PRIMARY
    )
    data_label.pack(anchor=tk.W, pady=(0, 8))
    
    text_var = tk.StringVar()
    text_box = tk.Text(
        right_section,
        height=16,
        wrap=tk.WORD,
        bg=BG_CARD,
        fg=TEXT_WHITE,
        font=("Courier New", 8),
        borderwidth=1,
        relief=tk.FLAT,
        insertbackground=TEAL_PRIMARY
    )
    text_box.pack(fill=tk.BOTH, expand=True)
    
    # Button Frame
    button_frame = tk.Frame(root, bg=BG_DARK)
    button_frame.pack(pady=12, padx=20, fill=tk.X)
    
    browse_button = tk.Button(
        button_frame,
        text="🔍 Browse Image",
        command=browse_file,
        font=("Courier New", 11, "bold"),
        bg=TEAL_PRIMARY,
        fg=BG_DARK,
        activebackground=TEAL_DARK,
        activeforeground=BG_DARK,
        relief=tk.FLAT,
        padx=15,
        pady=10,
        cursor="hand2"
    )
    browse_button.pack(side=tk.LEFT, padx=5)
    
    copy_button = tk.Button(
        button_frame,
        text="📋 Copy to Clipboard",
        command=copy_to_clipboard,
        font=("Courier New", 11, "bold"),
        bg=TEAL_PRIMARY,
        fg=BG_DARK,
        activebackground=TEAL_DARK,
        activeforeground=BG_DARK,
        relief=tk.FLAT,
        padx=15,
        pady=10,
        cursor="hand2"
    )
    copy_button.pack(side=tk.LEFT, padx=5)
    
    # Footer
    footer_frame = tk.Frame(root, bg=BG_DARK, height=40)
    footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(10, 10))
    
    footer_label = tk.Label(
        footer_frame,
        text="✦ Built by TheBooleanJulian ♪ | always watching, always running",
        font=("Courier New", 8),
        bg=BG_DARK,
        fg=TEXT_MUTED
    )
    footer_label.pack()
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()
