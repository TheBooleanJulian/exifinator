import sys
import pyperclip
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from PIL.ExifTags import TAGS, GPSTAGS
import geopy.geocoders

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
        return "No EXIF data found."
    
    shutter_speed = exif.get("ExposureTime", "N/A")
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
    
    exif_text = (f"Camera: {camera_make} {camera_model}\n"
                 f"Lens: {lens_model}\n"
                 f"Focal Length: {focal_length}mm\n"
                 f"Shutter Speed: {shutter_speed}\n"
                 f"Aperture: f/{aperture}\n"
                 f"ISO: {iso}\n"
                 f"White Balance: {white_balance}\n"
                 f"Flash: {flash}\n"
                 f"Date Taken: {datetime_original}\n"
                 f"Location: {location}")
    
    return exif_text

def browse_file():
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.tiff;*.bmp")])
    if file_path:
        display_exif(file_path)

def display_exif(image_path):
    exif_text = extract_basic_exif(image_path)
    text_var.set(exif_text)
    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, exif_text)

def copy_to_clipboard():
    text = text_box.get("1.0", tk.END).strip()
    pyperclip.copy(text)

def create_gui():
    global text_var, text_box
    root = tk.Tk()
    root.title("EXIF Extractor")
    root.geometry("400x400")
    
    frame = tk.Frame(root, width=380, height=200, relief=tk.RIDGE, borderwidth=2)
    frame.pack(pady=20)
    
    label = tk.Label(frame, text="Click to Browse Image", wraplength=350)
    label.pack(expand=True)
    
    frame.bind("<Button-1>", lambda e: browse_file())
    
    text_var = tk.StringVar()
    text_box = tk.Text(root, height=10, wrap=tk.WORD)
    text_box.pack(pady=10)
    
    copy_button = tk.Button(root, text="Copy to Clipboard", command=copy_to_clipboard)
    copy_button.pack()
    
    browse_button = tk.Button(root, text="Browse", command=browse_file)
    browse_button.pack()
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()
