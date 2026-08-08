"""
Exifinator
----------
A local desktop tool for working with photo metadata — no upload, no
account, nothing leaves your machine (except optional GPS reverse-geocoding
on the Read tab, which needs internet).

Two tabs:
  Read        — open one photo (or a whole folder to cycle through with
                Prev/Next or the arrow keys), see its camera/lens/exposure/
                GPS info.
  Batch Edit  — fix Artist/Copyright/Creator tags across a whole folder of
                photos at once (e.g. after borrowing a camera that still has
                someone else's name baked into every shot).

Run:   python Exifinator.py
Needs: Pillow, geopy — see requirements.txt
       exiftool on PATH, or placed next to this script (both tabs;
       Read tab uses it for tag extraction and RAW previews)
       https://exiftool.org
"""

import io
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from backend import exif_reader
from backend.metadata_editor import (
    COPYRIGHT_FIELDS, FIELD_GROUPS, NAME_FIELDS, FileInfo, apply_edits,
    build_tag_args, find_exiftool, scan_folder,
)

# ---- design tokens -----------------------------------------------------
BG_VOID = "#050508"
BG_PANEL = "#0A0E14"
TEAL = "#00D4C8"
TEAL_DARK = "#009E94"
GOLD = "#F5C842"
TEXT_PRIMARY = "#E8ECEF"
TEXT_MUTED = "#7A8590"
FONT_UI = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 9)
FONT_HEAD = ("Segoe UI Semibold", 12)

READ_FILETYPES = [("Image Files", " ".join(f"*{e}" for e in exif_reader.SUPPORTED_EXTS))]

# Plain-English explanations for the technical tag names, shown as tooltips
# next to each Batch Edit "fields to write" checkbox so a layperson knows
# what they do.
FIELD_DESCRIPTIONS = {
    "EXIF Artist": "The classic camera tag. Almost every photo viewer and OS "
                    "file-properties panel reads this as the author's name.",
    "EXIF Copyright": "The classic camera tag for copyright text. Read by "
                       "most photo viewers and OS file-properties panels.",
    "IPTC By-line (Creator)": "Used by news/stock-photo workflows. Shows up "
                               "as \"Creator\" in Photoshop/Lightroom.",
    "IPTC Copyright Notice": "Shows up as \"Copyright\" in the Photoshop/"
                              "Lightroom IPTC panel.",
    "IPTC Credit": "The \"Credit\" line — often displayed next to captions "
                    "on news/stock sites.",
    "IPTC Source": "The \"Source\" field — usually the agency or publisher "
                    "name, not a personal name.",
    "XMP Creator": "Modern Adobe equivalent of Artist. Read by Lightroom, "
                    "Bridge, and most current photo software.",
    "XMP Rights": "Modern Adobe equivalent of Copyright.",
    "XMP Credit": "XMP \"Credit\" field (Photoshop namespace).",
}


class Tooltip:
    """Small hover tooltip for a widget, used to explain jargon inline."""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, justify="left", background="#1C232D",
                 foreground=TEXT_PRIMARY, relief="solid", borderwidth=1,
                 font=FONT_UI, padx=8, pady=4, wraplength=260).pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class ExifinatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("✦ 初音ミク ♪ Exifinator")
        self.geometry("1200x800")
        self.configure(bg=BG_VOID)
        self.minsize(800, 560)
        self._set_window_icon()

        # Read tab state
        self.current_image_path: str | None = None
        self.thumbnail_photo = None
        self.read_files: list[Path] = []
        self.read_index: int = -1

        # Batch Edit tab state
        self.folder: Path | None = None
        self.files: list[FileInfo] = []
        self.field_vars: dict[str, tk.BooleanVar] = {}

        self._build_style()
        self._build_layout()
        self._check_exiftool()

    # -- setup -------------------------------------------------------
    def _logo_path(self) -> Path:
        here = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        return here / "assets" / "exifinator-icon.png"

    def _set_window_icon(self):
        logo_path = self._logo_path()
        if not logo_path.exists():
            return
        self._icon_photo = ImageTk.PhotoImage(Image.open(logo_path))
        self.iconphoto(True, self._icon_photo)

    def _check_exiftool(self):
        try:
            find_exiftool()
        except FileNotFoundError as e:
            messagebox.showwarning("exiftool not found — Batch Edit tab won't work", str(e))

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=BG_VOID)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG_VOID, foreground=TEXT_PRIMARY, font=FONT_UI)
        style.configure("Muted.TLabel", background=BG_VOID, foreground=TEXT_MUTED, font=FONT_UI)
        style.configure("Head.TLabel", background=BG_VOID, foreground=TEAL, font=FONT_HEAD)
        style.configure("Panel.TLabel", background=BG_PANEL, foreground=TEXT_PRIMARY, font=FONT_UI)
        style.configure("PanelMuted.TLabel", background=BG_PANEL, foreground=TEXT_MUTED, font=FONT_UI)

        style.configure("TCheckbutton", background=BG_VOID, foreground=TEXT_PRIMARY, font=FONT_UI)
        style.map("TCheckbutton", background=[("active", BG_VOID)])
        style.configure("Panel.TCheckbutton", background=BG_PANEL, foreground=TEXT_PRIMARY, font=FONT_UI)
        style.map("Panel.TCheckbutton", background=[("active", BG_PANEL)])

        style.configure("Accent.TButton", background=TEAL, foreground="#00201E",
                         font=("Segoe UI Semibold", 10), padding=8, borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#0FE8DB"), ("disabled", "#1C3532")])

        style.configure("Ghost.TButton", background=BG_PANEL, foreground=TEXT_PRIMARY,
                         font=FONT_UI, padding=6, borderwidth=1)
        style.map("Ghost.TButton", background=[("active", "#131A24")])

        style.configure("Treeview", background=BG_PANEL, fieldbackground=BG_PANEL,
                         foreground=TEXT_PRIMARY, rowheight=24, font=FONT_UI, borderwidth=0)
        style.configure("Treeview.Heading", background="#111721", foreground=GOLD,
                         font=("Segoe UI Semibold", 9), borderwidth=0)
        style.map("Treeview", background=[("selected", "#132420")])

        style.configure("TEntry", fieldbackground=BG_PANEL, foreground=TEXT_PRIMARY,
                         insertcolor=TEAL, borderwidth=1)

        style.configure("Panel.TLabelframe", background=BG_PANEL, foreground=TEXT_PRIMARY,
                         font=FONT_UI, borderwidth=1)
        style.configure("Panel.TLabelframe.Label", background=BG_PANEL, foreground=TEXT_MUTED,
                         font=FONT_UI)

        style.configure("TNotebook", background=BG_VOID, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=TEXT_MUTED,
                         font=("Segoe UI Semibold", 10), padding=(16, 8))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_VOID)],
                  foreground=[("selected", TEAL)])

    # -- top-level layout ----------------------------------------------
    def _build_layout(self):
        header = ttk.Frame(self, padding=(16, 16, 16, 8))
        header.pack(fill="x")
        logo_path = self._logo_path()
        if logo_path.exists():
            logo_img = Image.open(logo_path)
            logo_img.thumbnail((28, 28), Image.Resampling.LANCZOS)
            self._header_logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(header, image=self._header_logo_photo, bg=BG_VOID,
                     borderwidth=0, highlightthickness=0).pack(side="left", padx=(0, 8))
        ttk.Label(header, text="✦ Exifinator", style="Head.TLabel").pack(side="left")
        ttk.Label(header, text="  ·  read one photo's EXIF, or batch-fix Artist/Copyright across a folder",
                  style="Muted.TLabel").pack(side="left")

        self.notebook = notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        read_tab = ttk.Frame(notebook, padding=16)
        batch_tab = ttk.Frame(notebook, padding=16)
        notebook.add(read_tab, text="🔍  Read")
        notebook.add(batch_tab, text="✏️  Batch Edit")

        self._build_read_tab(read_tab)
        self._build_batch_tab(batch_tab)

        # Left/Right cycle through the current folder on the Read tab, as
        # long as the user isn't typing into a text field somewhere.
        self.bind_all("<Left>", lambda e: self._on_nav_key(-1))
        self.bind_all("<Right>", lambda e: self._on_nav_key(1))

        footer = ttk.Frame(self, padding=(16, 0, 16, 10))
        footer.pack(fill="x")
        ttk.Label(footer, text="✦ Built by TheBooleanJulian ♪",
                  style="Muted.TLabel", font=("Segoe UI", 8)).pack()

    # ==================================================================
    #  Read tab — single photo EXIF viewer
    # ==================================================================
    def _build_read_tab(self, root: ttk.Frame):
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # thumbnail
        thumb_col = ttk.Frame(root)
        thumb_col.grid(row=0, column=0, sticky="n", padx=(0, 16))
        ttk.Label(thumb_col, text="🖼️  Preview", font=("Segoe UI Semibold", 11)).pack(
            anchor="w", pady=(0, 8))

        thumb_frame = tk.Frame(thumb_col, width=240, height=240, bg=BG_PANEL,
                                highlightthickness=0)
        thumb_frame.pack()
        thumb_frame.pack_propagate(False)
        self.thumb_label = tk.Label(thumb_frame, text="📤 Click or Browse\nto load a photo",
                                     font=FONT_UI, bg=BG_PANEL, fg=TEAL, justify="center")
        self.thumb_label.pack(expand=True)
        thumb_frame.bind("<Button-1>", lambda _e: self.browse_photo())
        self.thumb_label.bind("<Button-1>", lambda _e: self.browse_photo())

        # folder filmstrip nav — hidden (via disabled state) until a folder
        # of photos is loaded, either via Open Folder or by browsing to a
        # single file (which auto-loads its parent folder for cycling)
        nav_row = ttk.Frame(thumb_col)
        nav_row.pack(fill="x", pady=(8, 0))
        self.prev_btn = ttk.Button(nav_row, text="◀ Prev", style="Ghost.TButton",
                                    command=self.show_prev_photo, state="disabled")
        self.prev_btn.pack(side="left")
        self.next_btn = ttk.Button(nav_row, text="Next ▶", style="Ghost.TButton",
                                    command=self.show_next_photo, state="disabled")
        self.next_btn.pack(side="right")
        self.nav_label = ttk.Label(thumb_col, text="", style="Muted.TLabel",
                                    anchor="center")
        self.nav_label.pack(fill="x", pady=(4, 0))

        # EXIF text
        data_col = ttk.Frame(root)
        data_col.grid(row=0, column=1, sticky="nsew")
        data_col.rowconfigure(1, weight=1)
        data_col.columnconfigure(0, weight=1)
        ttk.Label(data_col, text="📊  EXIF Data", font=("Segoe UI Semibold", 11)).grid(
            row=0, column=0, sticky="w", pady=(0, 8))

        self.exif_text = tk.Text(data_col, wrap="word", bg=BG_PANEL, fg=TEXT_PRIMARY,
                                  font=FONT_MONO, borderwidth=0, insertbackground=TEAL)
        self.exif_text.grid(row=1, column=0, sticky="nsew")
        exif_vsb = ttk.Scrollbar(data_col, orient="vertical", command=self.exif_text.yview)
        exif_vsb.grid(row=1, column=1, sticky="ns")
        self.exif_text.configure(yscrollcommand=exif_vsb.set)

        buttons = ttk.Frame(data_col)
        buttons.grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="🔍 Browse Photo…", style="Accent.TButton",
                   command=self.browse_photo).pack(side="left")
        ttk.Button(buttons, text="📁 Open Folder…", style="Ghost.TButton",
                   command=self.open_read_folder).pack(side="left", padx=8)
        ttk.Button(buttons, text="📋 Copy to Clipboard", style="Ghost.TButton",
                   command=self.copy_exif_text).pack(side="left")

    def browse_photo(self):
        path = filedialog.askopenfilename(title="Choose a photo", filetypes=READ_FILETYPES)
        if not path:
            return
        self._load_read_folder(Path(path).parent, select=Path(path))

    def open_read_folder(self):
        folder = filedialog.askdirectory(title="Choose a folder of photos")
        if folder:
            self._load_read_folder(Path(folder))

    def _load_read_folder(self, folder: Path, select: Path | None = None):
        files = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in exif_reader.SUPPORTED_EXTS
        )
        if not files:
            messagebox.showinfo("No images found", f"No supported image files in {folder}")
            return
        self.read_files = files
        self.read_index = files.index(select) if select in files else 0
        self._update_nav_state()
        self.display_exif(str(self.read_files[self.read_index]))

    def _update_nav_state(self):
        total = len(self.read_files)
        if total:
            self.nav_label.configure(
                text=f"{self.read_index + 1} / {total}  ·  {self.read_files[self.read_index].name}")
        else:
            self.nav_label.configure(text="")
        self.prev_btn.configure(state="normal" if self.read_index > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.read_index < total - 1 else "disabled")

    def show_prev_photo(self):
        if self.read_index > 0:
            self.read_index -= 1
            self._update_nav_state()
            self.display_exif(str(self.read_files[self.read_index]))

    def show_next_photo(self):
        if self.read_index < len(self.read_files) - 1:
            self.read_index += 1
            self._update_nav_state()
            self.display_exif(str(self.read_files[self.read_index]))

    def _on_nav_key(self, direction: int):
        if self.notebook.index(self.notebook.select()) != 0:
            return  # only cycle when the Read tab is active
        focus = self.focus_get()
        if isinstance(focus, (tk.Entry, ttk.Entry, tk.Text)):
            return  # don't hijack arrow keys while typing
        if direction < 0:
            self.show_prev_photo()
        else:
            self.show_next_photo()

    def display_exif(self, image_path: str):
        try:
            try:
                img = Image.open(image_path)
                img.load()
            except Exception:
                # Pillow can't decode most RAW formats directly — fall back
                # to the embedded preview/thumbnail exiftool can pull out.
                preview = exif_reader.get_preview_image_bytes(image_path)
                if not preview:
                    raise
                img = Image.open(io.BytesIO(preview))
            img.thumbnail((220, 220), Image.Resampling.LANCZOS)
            self.thumbnail_photo = ImageTk.PhotoImage(img)
            self.thumb_label.configure(image=self.thumbnail_photo, text="")
            self.current_image_path = image_path
        except Exception as e:
            self.thumbnail_photo = None
            self.thumb_label.configure(image="", text=f"❌ Error loading preview\n{e}")

        try:
            exif_summary = exif_reader.extract_basic_exif(image_path)
        except Exception as e:
            exif_summary = f"❌ Couldn't read EXIF data.\n{e}"

        self.exif_text.delete("1.0", "end")
        self.exif_text.insert("end", exif_summary)

    def copy_exif_text(self):
        text = self.exif_text.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    # ==================================================================
    #  Batch Edit tab — folder-wide Artist/Copyright/Creator writer
    # ==================================================================
    def _build_batch_tab(self, root: ttk.Frame):
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)

        # left: folder controls + file table
        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        controls = ttk.Frame(left)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(controls, text="Choose Folder…", style="Accent.TButton",
                   command=self.choose_folder).pack(side="left")
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Include subfolders", variable=self.recursive_var,
                         command=self.rescan).pack(side="left", padx=12)
        self.folder_label = ttk.Label(controls, text="No folder selected", style="Muted.TLabel")
        self.folder_label.pack(side="left", padx=8)

        table_frame = ttk.Frame(left)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("select", "filename", "model", "date", "artist", "copyright")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="none")
        # (heading, display width, minimum width) — minwidth stops a column
        # from being silently squeezed to nothing when the window narrows;
        # the horizontal scrollbar below takes over once columns hit that floor.
        headings = {
            "select": ("✓", 34, 34), "filename": ("File", 150, 90), "model": ("Camera", 120, 80),
            "date": ("Date", 110, 90), "artist": ("Current Artist", 140, 110),
            "copyright": ("Current Copyright", 200, 140),
        }
        for c, (text, width, minwidth) in headings.items():
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, minwidth=minwidth, anchor="w",
                              stretch=(c not in ("select",)))
        self.tree.column("select", anchor="center", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.bind("<Button-1>", self._on_tree_click)

        sel_row = ttk.Frame(left)
        sel_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(sel_row, text="Select All", style="Ghost.TButton",
                   command=lambda: self._set_all_selected(True)).pack(side="left")
        ttk.Button(sel_row, text="Select None", style="Ghost.TButton",
                   command=lambda: self._set_all_selected(False)).pack(side="left", padx=8)
        self.count_label = ttk.Label(sel_row, text="0 files", style="Muted.TLabel")
        self.count_label.pack(side="right")

        # right: settings (scrollable, so nothing is ever fully hidden) on
        # top, log pinned below with a guaranteed minimum height — a vertical
        # PanedWindow keeps the log visible instead of letting it get
        # squeezed out when the window is short.
        right_pane = tk.PanedWindow(root, orient="vertical", bg=BG_VOID, bd=0,
                                     sashwidth=6, sashrelief="flat", sashpad=2)
        right_pane.grid(row=0, column=1, sticky="nsew")

        settings_outer = ttk.Frame(right_pane, style="Panel.TFrame")
        log_container = ttk.Frame(right_pane, style="Panel.TFrame", padding=(16, 8, 16, 16))
        right_pane.add(settings_outer, stretch="always", minsize=200)
        right_pane.add(log_container, stretch="always", minsize=110)

        settings_outer.rowconfigure(0, weight=1)
        settings_outer.columnconfigure(0, weight=1)
        settings_canvas = tk.Canvas(settings_outer, bg=BG_PANEL, highlightthickness=0)
        settings_canvas.grid(row=0, column=0, sticky="nsew")
        settings_vsb = ttk.Scrollbar(settings_outer, orient="vertical", command=settings_canvas.yview)
        settings_vsb.grid(row=0, column=1, sticky="ns")
        settings_canvas.configure(yscrollcommand=settings_vsb.set)

        panel = ttk.Frame(settings_canvas, style="Panel.TFrame", padding=16)
        panel_window = settings_canvas.create_window((0, 0), window=panel, anchor="nw")
        panel.columnconfigure(0, weight=1)

        def _sync_scrollregion(_event=None):
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))

        def _sync_panel_width(event):
            settings_canvas.itemconfigure(panel_window, width=event.width)

        panel.bind("<Configure>", _sync_scrollregion)
        settings_canvas.bind("<Configure>", _sync_panel_width)

        def _on_mousewheel(event):
            settings_canvas.yview_scroll(-1 * (event.delta // 120), "units")

        settings_canvas.bind("<Enter>", lambda _e: settings_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        settings_canvas.bind("<Leave>", lambda _e: settings_canvas.unbind_all("<MouseWheel>"))

        ttk.Label(panel, text="New values", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 11)).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ttk.Label(panel, text="Name (Artist / Creator / By-line)", style="Panel.TLabel").grid(
            row=1, column=0, sticky="w")
        self.name_entry = ttk.Entry(panel, font=FONT_UI)
        self.name_entry.grid(row=2, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(panel, text="Copyright notice", style="Panel.TLabel").grid(row=3, column=0, sticky="w")
        self.copyright_entry = ttk.Entry(panel, font=FONT_UI)
        self.copyright_entry.grid(row=4, column=0, sticky="ew", pady=(2, 4))
        ttk.Label(panel, text="e.g.  © 2026 Julian Cheung / Accurova", style="PanelMuted.TLabel").grid(
            row=5, column=0, sticky="w", pady=(0, 12))

        ttk.Separator(panel, orient="horizontal").grid(row=6, column=0, sticky="ew", pady=8)

        ttk.Label(panel, text="Fields to write", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 11)).grid(row=7, column=0, sticky="w", pady=(0, 2))
        ttk.Label(panel, text="Different apps read different tags. Hover the ⓘ if you're not "
                              "sure — the top item in each group is the safest default.",
                  style="PanelMuted.TLabel", wraplength=260, justify="left").grid(
            row=8, column=0, sticky="w", pady=(0, 8))

        name_box = ttk.Labelframe(panel, text="Name / Creator fields", style="Panel.TLabelframe")
        name_box.grid(row=9, column=0, sticky="ew", pady=(0, 10))
        name_box.columnconfigure(0, weight=1)
        copyright_box = ttk.Labelframe(panel, text="Copyright fields", style="Panel.TLabelframe")
        copyright_box.grid(row=10, column=0, sticky="ew")
        copyright_box.columnconfigure(0, weight=1)

        name_groups = [g for g in FIELD_GROUPS if g in NAME_FIELDS]
        copyright_groups = [g for g in FIELD_GROUPS if g in COPYRIGHT_FIELDS]
        for box, groups in ((name_box, name_groups), (copyright_box, copyright_groups)):
            for i, group in enumerate(groups):
                var = tk.BooleanVar(value=True)
                self.field_vars[group] = var
                row = ttk.Frame(box, style="Panel.TFrame")
                row.grid(row=i, column=0, sticky="ew", pady=2, padx=6)
                ttk.Checkbutton(row, text=group, variable=var,
                                 style="Panel.TCheckbutton").pack(side="left")
                info = ttk.Label(row, text=" ⓘ", style="PanelMuted.TLabel", cursor="question_arrow")
                info.pack(side="left")
                Tooltip(info, FIELD_DESCRIPTIONS.get(group, ""))

        ttk.Separator(panel, orient="horizontal").grid(row=11, column=0, sticky="ew", pady=12)

        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="Keep original files as backup (_original)",
                         variable=self.backup_var, style="Panel.TCheckbutton").grid(
            row=12, column=0, sticky="w", pady=(0, 12))

        ttk.Button(panel, text="Preview Changes (dry run)", style="Ghost.TButton",
                   command=self.preview_changes).grid(row=13, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(panel, text="Apply Changes", style="Accent.TButton",
                   command=self.apply_changes).grid(row=14, column=0, sticky="ew")

        # log — its own pane below, always at least partly visible
        log_container.rowconfigure(1, weight=1)
        log_container.columnconfigure(0, weight=1)
        ttk.Label(log_container, text="Log", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 10)).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.log_text = tk.Text(log_container, height=6, bg="#050810", fg=TEXT_MUTED,
                                 font=FONT_MONO, borderwidth=0, wrap="word")
        self.log_text.grid(row=1, column=0, sticky="nsew")
        log_vsb = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        log_vsb.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_vsb.set)
        self.log_text.configure(state="disabled")

    # -- batch edit logic ----------------------------------------------
    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose a folder of photos")
        if not folder:
            return
        self.folder = Path(folder)
        self.folder_label.configure(text=str(self.folder))
        self.rescan()

    def rescan(self):
        if not self.folder:
            return
        self.log(f"Scanning {self.folder} …")
        try:
            self.files = scan_folder(self.folder, recursive=self.recursive_var.get())
        except Exception as e:
            messagebox.showerror("Scan failed", str(e))
            return
        self._populate_table()
        self.log(f"Found {len(self.files)} image file(s).")

    def _populate_table(self):
        self.tree.delete(*self.tree.get_children())
        for i, f in enumerate(self.files):
            iid = str(i)
            self.tree.insert("", "end", iid=iid, values=(
                "☑", f.filename, f.model, f.date, f.artist, f.copyright,
            ))
        self._update_count()

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if region == "cell" and col == "#1" and row:
            idx = int(row)
            self.files[idx].selected = not self.files[idx].selected
            mark = "☑" if self.files[idx].selected else "☐"
            vals = list(self.tree.item(row, "values"))
            vals[0] = mark
            self.tree.item(row, values=vals)
            self._update_count()

    def _set_all_selected(self, value: bool):
        mark = "☑" if value else "☐"
        for i, f in enumerate(self.files):
            f.selected = value
            vals = list(self.tree.item(str(i), "values"))
            vals[0] = mark
            self.tree.item(str(i), values=vals)
        self._update_count()

    def _update_count(self):
        n = sum(1 for f in self.files if f.selected)
        self.count_label.configure(text=f"{n} of {len(self.files)} selected")

    def _selected_paths(self) -> list[Path]:
        return [f.path for f in self.files if f.selected]

    def _active_groups(self) -> list[str]:
        return [g for g, v in self.field_vars.items() if v.get()]

    def preview_changes(self):
        paths = self._selected_paths()
        if not paths:
            messagebox.showinfo("Nothing selected", "Select at least one file first.")
            return
        name_value = self.name_entry.get().strip()
        copyright_value = self.copyright_entry.get().strip()
        groups = self._active_groups()
        tag_args = build_tag_args(name_value, copyright_value, groups)
        if not tag_args:
            self.log("⚠ Nothing to preview — select at least one field, and fill in "
                      "the Name and/or Copyright box above.")
            return

        lines = [f"Preview only — nothing written yet. {len(paths)} file(s) would be updated:", ""]
        for arg in tag_args:
            tag, _, value = arg.lstrip("-").partition("=")
            lines.append(f"  {tag}  →  \"{value}\"")
        lines.append("")
        shown = paths[:6]
        lines.append("Files:")
        lines.extend(f"  • {p.name}" for p in shown)
        if len(paths) > len(shown):
            lines.append(f"  … and {len(paths) - len(shown)} more")
        if not self.backup_var.get():
            lines.append("")
            lines.append("⚠ Originals will NOT be backed up — this overwrites the files in place.")
        self.log("\n".join(lines))

    def apply_changes(self):
        paths = self._selected_paths()
        if not paths:
            messagebox.showinfo("Nothing selected", "Select at least one file first.")
            return
        if not messagebox.askyesno(
            "Confirm", f"Write metadata to {len(paths)} file(s)?"
            f"{'' if self.backup_var.get() else chr(10) + 'Originals will NOT be backed up.'}"
        ):
            return

        name_value = self.name_entry.get().strip()
        copyright_value = self.copyright_entry.get().strip()
        groups = self._active_groups()

        def work():
            ok, msg = apply_edits(paths, name_value, copyright_value, groups,
                                   keep_backup=self.backup_var.get(), dry_run=False)
            self.after(0, lambda: self._on_apply_done(ok, msg))

        self.log("Applying changes…")
        threading.Thread(target=work, daemon=True).start()

    def _on_apply_done(self, ok: bool, msg: str):
        self.log(msg if ok else f"⚠ {msg}")
        if ok:
            messagebox.showinfo("Done", "Metadata updated.")
            self.rescan()
        else:
            messagebox.showerror("Failed", msg)


if __name__ == "__main__":
    app = ExifinatorApp()
    app.mainloop()
