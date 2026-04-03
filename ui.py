"""
ui.py — Astra Face UI (Tkinter)
Supports both animated GIF and static PNG face images.
States: idle | listening | speaking
Must run on the main thread — audio loop must be a daemon thread.
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import os
from PIL import Image, ImageTk, ImageSequence

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ASSETS_DIR       = "assets"
FACE_SIZE        = (380, 380)
WINDOW_TITLE     = "A.S.T.R.A"
BACKGROUND_COLOR = "#0a0a0f"
TEXT_COLOR       = "#00e5a0"
STATUS_COLOR     = "#3a6a5a"
FONT_FAMILY      = "Courier"

STATE_LABELS = {
    "idle":      "[ STANDBY ]",
    "listening": "[ LISTENING... ]",
    "speaking":  "[ SPEAKING... ]",
}

STATE_TEXT_COLORS = {
    "idle":      "#3a6a5a",
    "listening": "#00ff88",
    "speaking":  "#00ddff",
}


# ─────────────────────────────────────────────
# UI CLASS
# ─────────────────────────────────────────────

class AstraUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.configure(bg=BACKGROUND_COLOR)
        self.root.resizable(False, False)

        self._current_state = "idle"
        self._gif_frames    = {}   # state -> list of PhotoImage frames
        self._static_photos = {}   # state -> single PhotoImage (PNG fallback)
        self._gif_lengths   = {}   # state -> number of frames
        self._after_id      = None # current animation callback id

        self._build_ui()
        self._preload_images()
        self._set_state_internal("idle")

    # ─────────────────────────────────────────
    # UI LAYOUT
    # ─────────────────────────────────────────
    def _build_ui(self):
        # Top title
        title_font = tkfont.Font(family=FONT_FAMILY, size=13, weight="bold")
        self.title_label = tk.Label(
            self.root, text="A . S . T . R . A",
            font=title_font, fg=TEXT_COLOR, bg=BACKGROUND_COLOR, pady=8
        )
        self.title_label.pack()

        # Face canvas
        self.face_label = tk.Label(
            self.root, bg=BACKGROUND_COLOR,
            width=FACE_SIZE[0], height=FACE_SIZE[1]
        )
        self.face_label.pack(padx=16, pady=2)

        # Status line
        status_font = tkfont.Font(family=FONT_FAMILY, size=9)
        self.status_label = tk.Label(
            self.root, text="",
            font=status_font, fg=STATUS_COLOR, bg=BACKGROUND_COLOR, pady=3
        )
        self.status_label.pack()

        # Conversation text
        text_font = tkfont.Font(family=FONT_FAMILY, size=10)
        self.text_label = tk.Label(
            self.root, text="",
            font=text_font, fg=TEXT_COLOR, bg=BACKGROUND_COLOR,
            wraplength=400, justify="center", pady=6
        )
        self.text_label.pack(padx=16, pady=(0, 14))

    # ─────────────────────────────────────────
    # IMAGE LOADING
    # ─────────────────────────────────────────
    def _preload_images(self):
        """Try GIF first, fall back to PNG for each state."""
        for state in ["idle", "listening", "speaking"]:
            gif_path = os.path.join(ASSETS_DIR, f"{state}.gif")
            png_path = os.path.join(ASSETS_DIR, f"{state}.png")

            if os.path.exists(gif_path):
                try:
                    self._load_gif(state, gif_path)
                    print(f"[UI] Loaded GIF: {gif_path}")
                    continue
                except Exception as e:
                    print(f"[UI] GIF load failed ({e}), trying PNG")

            if os.path.exists(png_path):
                try:
                    img = Image.open(png_path).resize(FACE_SIZE, Image.LANCZOS)
                    self._static_photos[state] = ImageTk.PhotoImage(img)
                    print(f"[UI] Loaded PNG: {png_path}")
                except Exception as e:
                    print(f"[UI] PNG load failed: {e}")
            else:
                print(f"[UI] No image found for state '{state}' — using fallback")

    def _load_gif(self, state: str, path: str):
        """Extract all frames from an animated GIF."""
        gif = Image.open(path)
        frames = []
        for frame in ImageSequence.Iterator(gif):
            f = frame.copy().convert("RGBA")
            # Composite on dark background
            bg = Image.new("RGBA", f.size, (10, 10, 15, 255))
            bg.paste(f, mask=f.split()[3])
            resized = bg.convert("RGB").resize(FACE_SIZE, Image.LANCZOS)
            frames.append(ImageTk.PhotoImage(resized))
        self._gif_frames[state]  = frames
        self._gif_lengths[state] = len(frames)

    # ─────────────────────────────────────────
    # STATE MANAGEMENT
    # ─────────────────────────────────────────
    def _set_state_internal(self, state: str):
        """Apply state change — called on main thread via root.after()."""
        # Cancel any running animation
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

        self._current_state = state
        color = STATE_TEXT_COLORS.get(state, TEXT_COLOR)
        self.status_label.configure(
            text=STATE_LABELS.get(state, ""),
            fg=color
        )

        if state in self._gif_frames:
            # Start GIF animation loop
            self._animate_gif(state, 0)
        elif state in self._static_photos:
            self.face_label.configure(image=self._static_photos[state])
            self.face_label.image = self._static_photos[state]
        else:
            # Fallback coloured rectangle
            colours = {
                "idle":      "#0a1a14",
                "listening": "#0a1a0a",
                "speaking":  "#0a0d1a"
            }
            self.face_label.configure(
                bg=colours.get(state, "#0a0a14"),
                image="", text=state.upper(), fg=color,
                width=FACE_SIZE[0], height=FACE_SIZE[1]
            )

    def _animate_gif(self, state: str, frame_idx: int):
        """Advance GIF to next frame — self-scheduling."""
        if self._current_state != state:
            return   # State changed, stop this animation
        frames = self._gif_frames[state]
        photo = frames[frame_idx % len(frames)]
        self.face_label.configure(image=photo)
        self.face_label.image = photo
        self._after_id = self.root.after(
            65,  # ms per frame (~15fps)
            self._animate_gif, state, frame_idx + 1
        )

    # ─────────────────────────────────────────
    # PUBLIC API (thread-safe)
    # ─────────────────────────────────────────
    def set_face(self, state: str):
        """Change face state. Safe to call from any thread."""
        self.root.after(0, self._set_state_internal, state)

    def set_text(self, text: str):
        """Update conversation text. Safe to call from any thread."""
        self.root.after(0, self.text_label.configure, {"text": text})

    def clear_text(self):
        self.set_text("")

    def run(self):
        """Start Tkinter main loop. Must be called from the main thread."""
        self.root.mainloop()


# ─────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import time

    ui = AstraUI()

    def demo():
        demos = [
            ("idle",      "A.S.T.R.A online. Standing by..."),
            ("listening", "You: Astra, what is today's date?"),
            ("speaking",  "Astra: Today is Wednesday, April 1st 2026."),
            ("idle",      ""),
        ]
        while True:
            for state, text in demos:
                time.sleep(2.5)
                ui.set_face(state)
                ui.set_text(text)

    threading.Thread(target=demo, daemon=True).start()
    ui.run()
