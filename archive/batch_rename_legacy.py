import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry  # Requires "pip install tkcalendar"
import json

# Supported file formats (excluding RAW files)
PHOTO_EXTENSIONS = [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif", ".webp"]
VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"]
LOG_FILE = "rename_log.json"

def save_log(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

def undo_last_rename():
    log_data = load_log()
    if not log_data:
        messagebox.showinfo("Undo", "No renaming history found.")
        return
    for entry in reversed(log_data):
        try:
            os.rename(entry["new"], entry["old"])
        except Exception as e:
            messagebox.showerror("Error", f"Could not revert {entry['new']}: {e}")
    os.remove(LOG_FILE)
    messagebox.showinfo("Undo", "Rename reverted successfully!")

def rename_files():
    directory = filedialog.askdirectory()
    if not directory:
        return
    
    date = date_entry.get().strip()
    event = event_entry.get().strip()
    photographer = photographer_entry.get().strip()
    user_suffix = user_suffix_entry.get().strip()

    if not date or not event or not photographer:
        messagebox.showerror("Error", "Please fill in all fields.")
        return
    
    prefix = f"{date}_{event}_Photo By {photographer}"
    
    selected_extensions = []
    if photo_var.get():
        selected_extensions.extend(PHOTO_EXTENSIONS)
    if video_var.get():
        selected_extensions.extend(VIDEO_EXTENSIONS)

    if not selected_extensions:
        messagebox.showerror("Error", "Please select at least one file type.")
        return
    
    format_a_pattern = re.compile(r"^_?(\d{3}_?\d{4})\.[a-zA-Z0-9]+$")
    renamed_files = []
    preview_list = []
    
    for filename in os.listdir(directory):
        match = format_a_pattern.match(filename)
        if filename.lower().endswith(tuple(selected_extensions)) and match:
            original_code = match.group(1)  # Extract original numeric code
            name, ext = os.path.splitext(filename)
            
            new_name = f"{prefix}_{original_code}"  # Keep original filename code
            if user_suffix:
                new_name += f"_{user_suffix}"
            new_name += ext
            
            new_path = os.path.join(directory, new_name)
            old_path = os.path.join(directory, filename)
            
            # Ensure no duplicate filenames
            counter = 1
            while os.path.exists(new_path):
                name, ext = os.path.splitext(new_name)
                new_name = f"{name}_{counter}{ext}"
                new_path = os.path.join(directory, new_name)
                counter += 1
            
            preview_list.append(f"{filename} → {new_name}")
            renamed_files.append({"old": old_path, "new": new_path})
    
    if not renamed_files:
        messagebox.showinfo("No Changes", "No files need renaming.")
        return
    
    # Show preview before renaming
    confirm = messagebox.askyesno("Confirm Rename", "Preview:\n" + "\n".join(preview_list[:10]) + ("\n..." if len(preview_list) > 10 else "") + "\nProceed?")
    if not confirm:
        return
    
    # Execute renaming
    log_data = []
    for entry in renamed_files:
        try:
            os.rename(entry["old"], entry["new"])
            log_data.append(entry)
        except Exception as e:
            messagebox.showerror("Error", f"Error renaming {entry['old']}: {e}")
    
    save_log(log_data)
    messagebox.showinfo("Success", "Batch renaming completed!")

# GUI setup
root = tk.Tk()
root.title("Batch Rename Tool")
root.geometry("450x450")

# Date Input
tk.Label(root, text="Select Date:").pack()
date_entry = DateEntry(root, width=12, background='darkblue', foreground='white', date_pattern='yyyy-MM-dd')
date_entry.pack()

# Event Name Input
tk.Label(root, text="Event Name:").pack()
event_entry = tk.Entry(root)
event_entry.pack()

# Photographer Name Input
tk.Label(root, text="Photographer Name:").pack()
photographer_entry = tk.Entry(root)
photographer_entry.pack()

# User-defined suffix Input
tk.Label(root, text="Custom Suffix (optional):").pack()
user_suffix_entry = tk.Entry(root)
user_suffix_entry.pack()

# File Type Selection
tk.Label(root, text="Select File Types:").pack()
photo_var = tk.BooleanVar(value=True)
video_var = tk.BooleanVar(value=True)
frame = tk.Frame(root)
frame.pack()
ttk.Checkbutton(frame, text="Photos", variable=photo_var).pack(side="left")
ttk.Checkbutton(frame, text="Videos", variable=video_var).pack(side="left")

# Buttons
ttk.Button(root, text="Select Folder & Run", command=rename_files).pack(pady=10)
ttk.Button(root, text="Undo Last Rename", command=undo_last_rename).pack(pady=5)

root.mainloop()
