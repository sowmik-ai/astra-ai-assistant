"""
ui.py — Astra Desktop Chat UI
ChatGPT-style window with:
  - Animated face (GIF)
  - Chat bubble history (voice + text)
  - Text input box (type or paste)
  - 📎 Attachment button (any file type)
  - 🎤 Voice button
  - Quick command buttons
  - Thread-safe updates from background
"""

import tkinter as tk
from tkinter import font as tkfont, filedialog
import threading
import os
from PIL import Image, ImageTk, ImageSequence

# ─────────────────────────────────────────────
# COLOURS & CONFIG
# ─────────────────────────────────────────────
BG1          = "#06080f"   # window background
BG2          = "#0a0e18"   # chat area
BG3          = "#0d1017"   # input area
TEAL         = "#00e5a0"   # Astra colour
GREEN        = "#00ff88"   # user colour
CYAN         = "#00ddff"   # speaking colour
MUTED        = "#3a6a5a"   # muted text
BORDER       = "#1a2a3a"   # border colour
USER_BG      = "#0d1a12"   # user bubble bg
ASTRA_BG     = "#0a1318"   # astra bubble bg
ATTACH_COLOR = "#ffaa00"   # attachment button
ALERT_WARN   = "#ffaa00"   # warning alert bubble border
ALERT_CRIT   = "#ff4444"   # critical alert bubble border
ALERT_BG     = "#1a0e00"   # alert bubble background

ASSETS_DIR   = "assets"

# ── Layout constants — 1920×1080 FHD right side panel ────────────────
SCREEN_W     = 1920
SCREEN_H     = 1080
TASKBAR_H    = 40           # Windows taskbar height (approx)

# Panel mode (default — docked to right edge)
PANEL_W      = 520
PANEL_H      = SCREEN_H - TASKBAR_H   # 1040 px
PANEL_X      = SCREEN_W - PANEL_W     # 1400 — snapped to right
PANEL_Y      = 0

# Maximised mode (full screen)
MAX_W        = SCREEN_W
MAX_H        = SCREEN_H - TASKBAR_H
MAX_X        = 0
MAX_Y        = 0

# Minimised mode (compact header-only strip)
MIN_W        = PANEL_W
MIN_H        = 48             # just the header bar
MIN_X        = PANEL_X
MIN_Y        = 0

# Starting values
WINDOW_W     = PANEL_W
WINDOW_H     = PANEL_H

FACE_SIZE    = (260, 260)
FONT         = "Courier"

STATE_FACE   = {"idle":"🤖", "listening":"👂", "speaking":"🗣️"}
STATE_LABEL  = {"idle":"[ STANDBY ]", "listening":"[ LISTENING... ]",
                "speaking":"[ SPEAKING... ]"}
STATE_COLOR  = {"idle": MUTED, "listening": GREEN, "speaking": CYAN}


class AstraUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("A.S.T.R.A")
        self.root.configure(bg=BG1)
        self.root.resizable(True, True)
        # Start in panel mode — right edge of screen
        self.root.geometry(f"{PANEL_W}x{PANEL_H}+{PANEL_X}+{PANEL_Y}")
        self.root.minsize(380, 48)
        # Always on top so ASTRA is visible while working
        self.root.attributes("-topmost", True)
        # Window mode: "panel" | "maximised" | "minimised"
        self._win_mode = "panel"

        self._current_state   = "idle"
        self._gif_frames      = {}
        self._gif_lengths     = {}
        self._static_photos   = {}
        self._after_id        = None
        self._text_callback   = None
        self._file_callback   = None
        self._mic_callback    = None
        self._pending_files   = []   # files queued for analysis

        self._build_ui()
        self._preload_images()
        self._set_state_internal("idle")

    # ─────────────────────────────────────────
    # CALLBACKS — wired from main.py
    # ─────────────────────────────────────────

    def set_text_callback(self, fn):
        """Called when user submits typed text."""
        self._text_callback = fn

    def set_file_callback(self, fn):
        """Called when user attaches a file. fn(file_path, question)"""
        self._file_callback = fn

    def set_mic_callback(self, fn):
        """Called when user toggles mic button."""
        self._mic_callback = fn

    # ─────────────────────────────────────────
    # BUILD UI
    # ─────────────────────────────────────────

    def _build_ui(self):
        title_font  = tkfont.Font(family=FONT, size=13, weight="bold")
        small_font  = tkfont.Font(family=FONT, size=9)
        chat_font   = tkfont.Font(family=FONT, size=11)
        input_font  = tkfont.Font(family=FONT, size=12)
        btn_font    = tkfont.Font(family=FONT, size=10)
        hint_font   = tkfont.Font(family=FONT, size=9)

        # ── Header ──
        header = tk.Frame(self.root, bg=BG2,
                          highlightbackground=BORDER,
                          highlightthickness=1)
        header.pack(fill="x")

        tk.Label(header, text="A . S . T . R . A",
                 font=title_font, fg=TEAL, bg=BG2,
                 padx=16, pady=10).pack(side="left")

        self.conn_label = tk.Label(
            header, text="● ONLINE",
            font=small_font, fg=GREEN, bg=BG2, padx=8
        )
        self.conn_label.pack(side="right")

        # ── Window controls ──────────────────────────────────────────
        ctrl_frame = tk.Frame(header, bg=BG2)
        ctrl_frame.pack(side="right", padx=4)

        # Minimise button — collapses to header strip
        self.min_btn = tk.Button(
            ctrl_frame, text="─",
            font=tkfont.Font(family=FONT, size=10, weight="bold"),
            fg=MUTED, bg=BG2,
            activeforeground=TEAL, activebackground=BG3,
            relief="flat", bd=0, cursor="hand2",
            padx=6, pady=2,
            command=self._minimise
        )
        self.min_btn.pack(side="left")

        # Maximise / restore button
        self.max_btn = tk.Button(
            ctrl_frame, text="□",
            font=tkfont.Font(family=FONT, size=10, weight="bold"),
            fg=MUTED, bg=BG2,
            activeforeground=TEAL, activebackground=BG3,
            relief="flat", bd=0, cursor="hand2",
            padx=6, pady=2,
            command=self._maximise_restore
        )
        self.max_btn.pack(side="left")

        # Panel restore button (back to side panel)
        self.panel_btn = tk.Button(
            ctrl_frame, text="▐",
            font=tkfont.Font(family=FONT, size=10, weight="bold"),
            fg=MUTED, bg=BG2,
            activeforeground=TEAL, activebackground=BG3,
            relief="flat", bd=0, cursor="hand2",
            padx=6, pady=2,
            command=self._restore_panel
        )
        self.panel_btn.pack(side="left")

        # ── Face section ──
        face_frame = tk.Frame(self.root, bg=BG1)
        face_frame.pack(fill="x", padx=16, pady=(10, 4))

        face_inner = tk.Frame(face_frame, bg=BG1)
        face_inner.pack()

        self.face_label = tk.Label(
            face_inner, bg=BG1,
            width=FACE_SIZE[0], height=FACE_SIZE[1]
        )
        self.face_label.pack()

        self.status_label = tk.Label(
            face_inner, text="[ STANDBY ]",
            font=small_font, fg=MUTED, bg=BG1, pady=2
        )
        self.status_label.pack()

        # ── Chat area ──
        chat_outer = tk.Frame(
            self.root, bg=BG2,
            highlightbackground=BORDER, highlightthickness=1
        )
        chat_outer.pack(fill="both", expand=True,
                        padx=10, pady=(4, 4))

        # Scrollable chat
        self.chat_canvas = tk.Canvas(
            chat_outer, bg=BG2, bd=0,
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            chat_outer, orient="vertical",
            command=self.chat_canvas.yview,
            bg=BG2, troughcolor=BG2
        )
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        self.chat_inner = tk.Frame(self.chat_canvas, bg=BG2)
        self.chat_window = self.chat_canvas.create_window(
            (0, 0), window=self.chat_inner, anchor="nw"
        )

        self.chat_inner.bind("<Configure>", self._on_chat_resize)
        self.chat_canvas.bind("<Configure>", self._on_canvas_resize)

        # Welcome bubble
        self._add_bubble_internal(
            "astra",
            "Hi Sowmik! Type a message, attach a file 📎, or say 'Astra' to speak."
        )

        # ── Input area ──
        input_area = tk.Frame(
            self.root, bg=BG3,
            highlightbackground=BORDER, highlightthickness=1
        )
        input_area.pack(fill="x", padx=10, pady=(0, 8))

        # Quick command buttons
        quick_frame = tk.Frame(input_area, bg=BG3)
        quick_frame.pack(fill="x", padx=8, pady=(6, 4))

        quick_cmds = [
            ("health check",    "do health check"),
            ("reminders",       "list reminders"),
            ("skills",          "show skill library"),
            ("learning",        "show learning stats"),
            ("help",            "show commands"),
        ]
        for label, cmd in quick_cmds:
            tk.Button(
                quick_frame, text=label,
                font=hint_font,
                fg=MUTED, bg=BG2,
                activeforeground=TEAL,
                activebackground=BG3,
                relief="flat", bd=0,
                cursor="hand2",
                padx=6, pady=3,
                command=lambda c=cmd: self._quick_send(c)
            ).pack(side="left", padx=2)

        # Attachment preview bar (hidden until file attached)
        self.attach_bar = tk.Frame(input_area, bg=BG3)
        self.attach_label = tk.Label(
            self.attach_bar,
            text="", font=hint_font,
            fg=ATTACH_COLOR, bg=BG3, anchor="w"
        )
        self.attach_label.pack(side="left", padx=8)
        self.clear_attach_btn = tk.Button(
            self.attach_bar, text="✕",
            font=hint_font, fg=MUTED, bg=BG3,
            activeforeground="red",
            relief="flat", bd=0, cursor="hand2",
            command=self._clear_attachment
        )
        self.clear_attach_btn.pack(side="right", padx=4)

        # Input row
        input_row = tk.Frame(input_area, bg=BG3)
        input_row.pack(fill="x", padx=8, pady=(2, 4))

        # 📎 Attach button
        self.attach_btn = tk.Button(
            input_row, text="📎",
            font=tkfont.Font(family=FONT, size=14),
            fg=ATTACH_COLOR, bg=BG3,
            activeforeground="white",
            activebackground=BG3,
            relief="flat", bd=0, cursor="hand2",
            padx=4,
            command=self._open_file_dialog
        )
        self.attach_btn.pack(side="left")

        # Text input
        self.text_input = tk.Text(
            input_row,
            font=input_font,
            fg=TEAL, bg=BG2,
            insertbackground=TEAL,
            relief="flat", bd=0,
            height=2,
            wrap="word",
            padx=8, pady=6,
            highlightthickness=1,
            highlightcolor=TEAL,
            highlightbackground=BORDER
        )
        self.text_input.pack(
            side="left", fill="x", expand=True, padx=(6, 0)
        )
        self.text_input.bind("<Return>",      self._on_enter)
        self.text_input.bind("<Shift-Return>", self._on_shift_enter)

        # Placeholder
        self._placeholder = "Type a message or attach a file..."
        self._show_placeholder()
        self.text_input.bind("<FocusIn>",  self._hide_placeholder)
        self.text_input.bind("<FocusOut>", self._show_placeholder)

        # Send button
        self.send_btn = tk.Button(
            input_row, text="Send",
            font=btn_font,
            fg=TEAL, bg=BG2,
            activeforeground="white",
            activebackground=BG3,
            relief="flat", bd=0, cursor="hand2",
            padx=10, pady=4,
            highlightthickness=1,
            highlightcolor=TEAL,
            highlightbackground=BORDER,
            command=self._submit_text
        )
        self.send_btn.pack(side="left", padx=(6, 0))

        # 🎤 Mic button
        self.mic_btn = tk.Button(
            input_row, text="🎤",
            font=tkfont.Font(family=FONT, size=14),
            fg=GREEN, bg=BG3,
            activeforeground="white",
            activebackground=BG3,
            relief="flat", bd=0, cursor="hand2",
            padx=4,
            command=self._toggle_mic
        )
        self.mic_btn.pack(side="left", padx=(4, 0))

        # Hint label
        self.hint_label = tk.Label(
            input_area,
            text="Enter to send  •  Shift+Enter new line  "
                 "•  📎 attach any file  •  🎤 voice",
            font=hint_font, fg=MUTED, bg=BG3, pady=3
        )
        self.hint_label.pack()

    # ─────────────────────────────────────────
    # ATTACHMENT HANDLING
    # ─────────────────────────────────────────

    def _open_file_dialog(self):
        """Open file picker — any file type allowed."""
        file_types = [
            ("All files",          "*.*"),
            ("Images",             "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("Documents",          "*.pdf *.docx *.xlsx *.xls *.pptx *.txt"),
            ("Code files",         "*.py *.js *.ts *.java *.cpp *.sh *.sql"),
            ("Data files",         "*.csv *.json *.yaml *.yml *.xml"),
            ("Archives",           "*.zip *.tar *.gz"),
        ]
        paths = filedialog.askopenfilenames(
            title="Attach files for Astra to analyse",
            filetypes=file_types,
            initialdir=os.path.expanduser("~")
        )
        if paths:
            self._pending_files = list(paths)
            self._show_attach_preview()

    def _show_attach_preview(self):
        """Show attached file names above input."""
        if not self._pending_files:
            self.attach_bar.pack_forget()
            return

        names = []
        for p in self._pending_files:
            from file_analyzer import get_file_icon
            icon = get_file_icon(p)
            names.append(f"{icon} {os.path.basename(p)}")

        self.attach_label.configure(
            text="  Attached: " + "  |  ".join(names)
        )
        self.attach_bar.pack(fill="x", after=self.hint_label,
                             before=self.hint_label, pady=(0, 2))
        self.attach_bar.pack(fill="x")

    def _clear_attachment(self):
        """Remove attached files."""
        self._pending_files = []
        self.attach_bar.pack_forget()

    # ─────────────────────────────────────────
    # TEXT INPUT HANDLING
    # ─────────────────────────────────────────

    def _on_enter(self, event):
        """Enter submits message."""
        self._submit_text()
        return "break"   # prevent newline

    def _on_shift_enter(self, event):
        """Shift+Enter inserts newline."""
        return None

    def _show_placeholder(self, event=None):
        current = self.text_input.get("1.0", "end-1c")
        if not current.strip():
            self.text_input.delete("1.0", "end")
            self.text_input.insert("1.0", self._placeholder)
            self.text_input.configure(fg=MUTED)

    def _hide_placeholder(self, event=None):
        current = self.text_input.get("1.0", "end-1c")
        if current == self._placeholder:
            self.text_input.delete("1.0", "end")
            self.text_input.configure(fg=TEAL)

    def _get_input_text(self) -> str:
        text = self.text_input.get("1.0", "end-1c").strip()
        if text == self._placeholder:
            return ""
        return text

    def _clear_input(self):
        self.text_input.delete("1.0", "end")
        self._show_placeholder()

    def _submit_text(self):
        text  = self._get_input_text()
        files = list(self._pending_files)

        if not text and not files:
            return

        self._clear_input()
        self._clear_attachment()

        # If files attached — pass to file callback
        if files and self._file_callback:
            for fp in files:
                from file_analyzer import get_file_icon
                icon = get_file_icon(fp)
                display = (f"{icon} {os.path.basename(fp)}"
                           + (f"\n{text}" if text else ""))
                self.add_chat_bubble("user", display)
                threading.Thread(
                    target=self._file_callback,
                    args=(fp, text),
                    daemon=True
                ).start()
        elif text and self._text_callback:
            self.add_chat_bubble("user", text)
            threading.Thread(
                target=self._text_callback,
                args=(text,),
                daemon=True
            ).start()

    def _quick_send(self, text: str):
        if self._text_callback:
            self.add_chat_bubble("user", text)
            threading.Thread(
                target=self._text_callback,
                args=(text,),
                daemon=True
            ).start()

    # ─────────────────────────────────────────
    # WINDOW SIZE CONTROLS
    # ─────────────────────────────────────────

    def _minimise(self):
        """Collapse ASTRA to a slim header-only strip at top-right."""
        self._win_mode = "minimised"
        self.root.geometry(f"{MIN_W}x{MIN_H}+{MIN_X}+{MIN_Y}")
        self.min_btn.configure(text="▲", command=self._restore_panel)
        self.max_btn.configure(text="□", command=self._maximise_restore)
        self.conn_label.configure(text="● MINIMISED", fg=MUTED)

    def _maximise_restore(self):
        """Toggle between maximised (full screen) and panel mode."""
        if self._win_mode == "maximised":
            self._restore_panel()
        else:
            self._win_mode = "maximised"
            self.root.geometry(f"{MAX_W}x{MAX_H}+{MAX_X}+{MAX_Y}")
            self.max_btn.configure(text="❐")   # restore icon
            self.min_btn.configure(text="─", command=self._minimise)
            self.conn_label.configure(text="● ONLINE", fg=GREEN)

    def _restore_panel(self):
        """Restore ASTRA to the default right side panel."""
        self._win_mode = "panel"
        self.root.geometry(f"{PANEL_W}x{PANEL_H}+{PANEL_X}+{PANEL_Y}")
        self.max_btn.configure(text="□", command=self._maximise_restore)
        self.min_btn.configure(text="─", command=self._minimise)
        self.conn_label.configure(text="● ONLINE", fg=GREEN)

    def _toggle_mic(self):
        current = self.mic_btn.cget("fg")
        if current == GREEN:
            self.mic_btn.configure(fg="red", text="⏹")
        else:
            self.mic_btn.configure(fg=GREEN, text="🎤")
        if self._mic_callback:
            self._mic_callback()

    # ─────────────────────────────────────────
    # CHAT BUBBLES
    # ─────────────────────────────────────────

    def add_chat_bubble(self, role: str, text: str):
        """Add a chat bubble. Thread-safe."""
        self.root.after(0, self._add_bubble_internal, role, text)

    def _add_bubble_internal(self, role: str, text: str):
        """Add bubble on main thread. Supports alert bubbles via role='alert' or 'critical'."""
        chat_font  = tkfont.Font(family=FONT, size=10)
        small_font = tkfont.Font(family=FONT, size=8)

        is_user    = (role == "user")
        is_alert   = text.startswith("⚠ ALERT") or text.startswith("🔴 CRITICAL")
        is_critical = text.startswith("🔴 CRITICAL")

        # ── Alert bubble styling ──
        if is_alert:
            border_color = ALERT_CRIT if is_critical else ALERT_WARN
            bubble_bg    = ALERT_BG
            text_color   = ALERT_CRIT if is_critical else ALERT_WARN
            role_text    = "⚠ ASTRA ALERT" if not is_critical else "🔴 CRITICAL ALERT"
            role_color   = ALERT_CRIT if is_critical else ALERT_WARN
        else:
            border_color = None
            bubble_bg    = USER_BG if is_user else ASTRA_BG
            text_color   = GREEN if is_user else TEAL
            role_text    = "You" if is_user else "Astra"
            role_color   = GREEN if is_user else TEAL

        # Outer row
        row = tk.Frame(self.chat_inner, bg=BG2)
        row.pack(fill="x", padx=8, pady=3)

        # Bubble frame
        bubble_frame = tk.Frame(row, bg=BG2)
        if is_user:
            bubble_frame.pack(side="right")
        else:
            bubble_frame.pack(side="left")

        # Role label
        role_label = tk.Label(
            bubble_frame,
            text=role_text,
            font=small_font,
            fg=role_color,
            bg=BG2,
            anchor="e" if is_user else "w"
        )
        role_label.pack(fill="x")

        # Bubble — with optional alert border
        bubble_kwargs = dict(
            text=text,
            font=chat_font,
            fg=text_color,
            bg=bubble_bg,
            wraplength=440,
            justify="left",
            anchor="w",
            padx=12, pady=8,
        )
        if is_alert:
            bubble_kwargs.update(
                relief="solid",
                bd=1,
                highlightbackground=border_color,
                highlightthickness=1,
            )
        else:
            bubble_kwargs.update(relief="flat", bd=0)

        bubble = tk.Label(bubble_frame, **bubble_kwargs)
        bubble.pack(anchor="e" if is_user else "w")

        # Scroll to bottom
        self.chat_inner.update_idletasks()
        self.chat_canvas.configure(
            scrollregion=self.chat_canvas.bbox("all")
        )
        self.chat_canvas.yview_moveto(1.0)

    def _on_chat_resize(self, event):
        self.chat_canvas.configure(
            scrollregion=self.chat_canvas.bbox("all")
        )

    def _on_canvas_resize(self, event):
        self.chat_canvas.itemconfig(
            self.chat_window, width=event.width
        )

    # ─────────────────────────────────────────
    # FACE / STATE
    # ─────────────────────────────────────────

    def _preload_images(self):
        for state in ["idle", "listening", "speaking"]:
            gif_path = os.path.join(ASSETS_DIR, f"{state}.gif")
            png_path = os.path.join(ASSETS_DIR, f"{state}.png")
            if os.path.exists(gif_path):
                try:
                    self._load_gif(state, gif_path)
                    continue
                except Exception:
                    pass
            if os.path.exists(png_path):
                try:
                    img = Image.open(png_path).resize(
                        FACE_SIZE, Image.LANCZOS
                    )
                    self._static_photos[state] = ImageTk.PhotoImage(img)
                except Exception:
                    pass

    def _load_gif(self, state, path):
        gif    = Image.open(path)
        frames = []
        for frame in ImageSequence.Iterator(gif):
            f  = frame.copy().convert("RGBA")
            bg = Image.new("RGBA", f.size, (6, 8, 15, 255))
            bg.paste(f, mask=f.split()[3])
            resized = bg.convert("RGB").resize(FACE_SIZE, Image.LANCZOS)
            frames.append(ImageTk.PhotoImage(resized))
        self._gif_frames[state]  = frames
        self._gif_lengths[state] = len(frames)

    def _set_state_internal(self, state: str):
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

        self._current_state = state
        color = STATE_COLOR.get(state, MUTED)

        self.status_label.configure(
            text=STATE_LABEL.get(state, ""),
            fg=color
        )

        if state in self._gif_frames:
            self._animate_gif(state, 0)
        elif state in self._static_photos:
            self.face_label.configure(
                image=self._static_photos[state]
            )
            self.face_label.image = self._static_photos[state]
        else:
            # Emoji fallback
            self.face_label.configure(
                image="",
                text=STATE_FACE.get(state, "🤖"),
                fg=color, bg=BG1,
                font=tkfont.Font(size=64)
            )

    def _animate_gif(self, state: str, idx: int):
        if self._current_state != state:
            return
        frames = self._gif_frames[state]
        photo  = frames[idx % len(frames)]
        self.face_label.configure(image=photo)
        self.face_label.image = photo
        self._after_id = self.root.after(
            65, self._animate_gif, state, idx + 1
        )

    # ─────────────────────────────────────────
    # PUBLIC API — thread-safe
    # ─────────────────────────────────────────

    def set_face(self, state: str):
        self.root.after(0, self._set_state_internal, state)

    def set_text(self, text: str):
        """Legacy — adds as Astra bubble."""
        if text:
            self.add_chat_bubble("astra", text)

    def clear_text(self):
        pass   # no-op in bubble mode

    def set_status(self, text: str, color: str = TEAL):
        self.root.after(
            0, self.conn_label.configure,
            {"text": text, "fg": color}
        )

    def run(self):
        """Start Tkinter main loop — call from main thread."""
        self.root.mainloop()


# ─────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import time

    ui = AstraUI()

    def demo():
        time.sleep(1)
        ui.add_chat_bubble("astra", "Hi! I am Astra. Type a message or attach a file.")
        time.sleep(2)
        ui.add_chat_bubble("user", "do health check")
        time.sleep(1)
        ui.set_face("idle")
        ui.add_chat_bubble("astra", "All 9 modules healthy. Systems fully operational.")
        time.sleep(2)
        ui.add_chat_bubble("user", "📎 report.csv\nAnalyse this data")
        time.sleep(1)
        ui.add_chat_bubble("astra", "The CSV has 5 columns and 120 rows. Key metric: revenue grew 23% month-on-month.")
        time.sleep(2)
        ui.set_face("listening")
        time.sleep(2)
        ui.set_face("speaking")
        ui.add_chat_bubble("astra", "I heard you say: what time is it. It is Thursday 05 June at 14:30.")
        time.sleep(2)
        ui.set_face("idle")

    threading.Thread(target=demo, daemon=True).start()
    ui.run()
