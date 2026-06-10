import os
import sys
import threading
import time

# Try importing dependencies; they are installed in the venv
try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pass

from src.config import config
from src.tts_engine import tts_engine, MODEL_PATH, VOICES_PATH
from src.input_handler import input_handler

class FloatingMenu(ctk.CTkToplevel):
    def __init__(self, parent, owner):
        super().__init__(parent)
        self.owner = owner
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Transparent chroma-keying for perfect rounded corners
        self.configure(fg_color="#000001")
        self.wm_attributes("-transparentcolor", "#000001")

        self.card = ctk.CTkFrame(
            self, 
            fg_color="#0F172A", 
            border_color="#4F46E5", 
            border_width=1.5, 
            corner_radius=10
        )
        self.card.pack(fill="both", expand=True, padx=1, pady=1)

        # Replay Button
        self.replay_btn = ctk.CTkButton(
            self.card, 
            text="🔄  Replay Selection", 
            anchor="w",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color="transparent",
            hover_color="#1E293B",
            text_color="white",
            height=26,
            command=self.owner.replay_text
        )
        self.replay_btn.pack(fill="x", padx=6, pady=(6, 2))

        # Speed Button (Toggles Slider Dropdown)
        self.speed_btn = ctk.CTkButton(
            self.card, 
            text="⚡  Speed: 1.0x", 
            anchor="w",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color="transparent",
            hover_color="#1E293B",
            text_color="white",
            height=26,
            command=self.toggle_speed_slider
        )
        self.speed_btn.pack(fill="x", padx=6, pady=2)

        # Speed Slider Frame (starts hidden)
        self.slider_visible = False
        self.slider_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        
        self.speed_slider = ctk.CTkSlider(
            self.slider_frame,
            from_=0.5,
            to=2.0,
            number_of_steps=15,
            height=14,
            width=130,
            fg_color="#1E293B",
            progress_color="#4F46E5",
            button_color="#6366F1",
            button_hover_color="#4F46E5",
            command=self.on_slider_change
        )
        self.speed_slider.set(config.get("speed", 1.0))
        self.speed_slider.pack(pady=(2, 6), padx=6)

        # Voice Cycle Button
        self.voice_btn = ctk.CTkButton(
            self.card, 
            text="🗣️  Voice: US-F", 
            anchor="w",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color="transparent",
            hover_color="#1E293B",
            text_color="white",
            height=26,
            command=self.owner.cycle_voice
        )
        self.voice_btn.pack(fill="x", padx=6, pady=2)

        # Cancel Button
        self.cancel_btn = ctk.CTkButton(
            self.card, 
            text="❌  Stop & Close", 
            anchor="w",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color="transparent",
            hover_color="#1E293B",
            text_color="#F87171",
            height=26,
            command=self.owner.cancel_playback
        )
        self.cancel_btn.pack(fill="x", padx=6, pady=(2, 6))

        # Bind hover states directly to prevent menu from closing when mouse enters it
        self.bind("<Enter>", lambda e: self.owner.on_mouse_enter(), add="+")
        self.bind("<Leave>", lambda e: self.owner.on_mouse_leave(), add="+")
        self.card.bind("<Enter>", lambda e: self.owner.on_mouse_enter(), add="+")
        self.card.bind("<Leave>", lambda e: self.owner.on_mouse_leave(), add="+")

        self.withdraw()

    def toggle_speed_slider(self):
        """Toggles the visibility of the speed slider inside the menu."""
        if self.slider_visible:
            self.slider_frame.pack_forget()
            self.slider_visible = False
            # Repack buttons to ensure voice and cancel are placed cleanly
            self.voice_btn.pack_forget()
            self.cancel_btn.pack_forget()
            self.voice_btn.pack(fill="x", padx=6, pady=2)
            self.cancel_btn.pack(fill="x", padx=6, pady=(2, 6))
            
            # Shrink menu window height to 126px
            w = self.winfo_width()
            x = self.winfo_x()
            y = self.winfo_y()
            self.geometry(f"{w}x126+{x}+{y}")
        else:
            # Show slider frame right under speed button
            self.voice_btn.pack_forget()
            self.cancel_btn.pack_forget()
            
            self.slider_frame.pack(fill="x", padx=6, pady=2)
            self.voice_btn.pack(fill="x", padx=6, pady=2)
            self.cancel_btn.pack(fill="x", padx=6, pady=(2, 6))
            self.slider_visible = True
            
            # Expand menu window height to 162px
            w = self.winfo_width()
            x = self.winfo_x()
            y = self.winfo_y()
            self.geometry(f"{w}x162+{x}+{y}")

    def on_slider_change(self, value):
        """Callback when speed slider value is changed in the widget menu."""
        rounded_speed = round(value, 1)
        config.set("speed", rounded_speed)
        self.speed_btn.configure(text=f"⚡  Speed: {rounded_speed}x")
        self.owner.speed_lbl.configure(text=f"Speed: {rounded_speed}x")

    def show(self, x, y):
        # Update speed text and slider
        speed = config.get("speed", 1.0)
        self.replay_btn.focus_force() # Clean focus
        self.speed_btn.configure(text=f"⚡  Speed: {speed}x")
        self.speed_slider.set(speed)
        
        # Reset slider visibility to collapsed on every show to be clean and predictable
        if self.slider_visible:
            self.slider_frame.pack_forget()
            self.slider_visible = False
            self.voice_btn.pack_forget()
            self.cancel_btn.pack_forget()
            self.voice_btn.pack(fill="x", padx=6, pady=2)
            self.cancel_btn.pack(fill="x", padx=6, pady=(2, 6))
        
        # Update voice text
        voice = config.get("voice", "af_sarah")
        voice_map = {
            "af_sarah": "US Female",
            "am_adam": "US Male",
            "bf_emma": "UK Female",
            "bm_george": "UK Male"
        }
        voice_name = voice_map.get(voice, voice)
        self.voice_btn.configure(text=f"🗣️  Voice: {voice_name}")
        
        self.geometry(f"150x126+{x}+{y}")
        self.deiconify()
        self.lift()

    def hide(self):
        self.withdraw()


class FloatingWidget(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)  # Remove window borders and title bars
        self.attributes("-topmost", True)  # Floating topmost overlay
        
        # Windows-specific transparent color chroma key to eliminate black corners!
        self.configure(fg_color="#000001")
        self.wm_attributes("-transparentcolor", "#000001")

        # Sleek Frame with glowing thin border, with corners perfectly rounded
        self.card = ctk.CTkFrame(
            self, 
            fg_color="#0F172A",  # Sleek dark Tailwind slate
            border_color="#6366F1", 
            border_width=1.5, 
            corner_radius=12
        )
        self.card.pack(fill="both", expand=True, padx=1, pady=1)

        # Custom animated loading / wave icon label
        self.icon_label = ctk.CTkLabel(
            self.card, 
            text="⠋", 
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color="#6366F1",
            width=28
        )
        self.icon_label.pack(side="left", padx=(10, 2))

        # Status text frame
        self.text_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.text_frame.pack(side="left", fill="both", expand=True, pady=4, padx=(2, 8))

        self.status_lbl = ctk.CTkLabel(
            self.text_frame, 
            text="Processing...", 
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            text_color="white",
            anchor="w"
        )
        self.status_lbl.pack(anchor="w", pady=(2, 0))

        self.speed_lbl = ctk.CTkLabel(
            self.text_frame, 
            text="Speed: 1.0x", 
            font=ctk.CTkFont(family="Inter", size=8),
            text_color="#818CF8",
            anchor="w"
        )
        self.speed_lbl.pack(anchor="w", pady=(0, 2))

        # Action Buttons frame (Pause/Play, Stop, & Gear), appears on hover
        self.actions_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.actions_visible = False

        # Play/Pause circular button (Sleek Indigo)
        self.play_pause_btn = ctk.CTkButton(
            self.actions_frame, 
            text="⏸", 
            width=22, 
            height=22, 
            corner_radius=11, 
            font=ctk.CTkFont(family="Inter", size=9, weight="bold"),
            fg_color="#4F46E5",
            hover_color="#4338CA",
            text_color="white",
            command=self.toggle_play_pause
        )
        self.play_pause_btn.pack(side="left", padx=1)

        # Stop circular button (Solid Red)
        self.stop_btn = ctk.CTkButton(
            self.actions_frame, 
            text="⏹", 
            width=22, 
            height=22, 
            corner_radius=11, 
            font=ctk.CTkFont(family="Inter", size=9, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="white",
            command=self.cancel_playback
        )
        self.stop_btn.pack(side="left", padx=1)

        # Gear (menu) circular button (Sleek Slate)
        self.gear_btn = ctk.CTkButton(
            self.actions_frame, 
            text="⚙", 
            width=22, 
            height=22, 
            corner_radius=11, 
            font=ctk.CTkFont(family="Segoe UI Symbol", size=12),
            fg_color="#475569",
            hover_color="#334155",
            text_color="white",
            command=self.toggle_menu
        )
        self.gear_btn.pack(side="left", padx=1)

        # Drag coordinates offsets
        self.x_offset = 0
        self.y_offset = 0

        # Enable dragging by clicking and dragging anywhere on safe non-button elements
        for w in [self.card, self.icon_label, self.status_lbl, self.speed_lbl, self.text_frame]:
            w.bind("<Button-1>", self.start_drag, add="+")
            w.bind("<B1-Motion>", self.drag_motion, add="+")

        # Enable action buttons hover effects directly without click-hijacking recursion
        self.bind("<Enter>", lambda e: self.on_mouse_enter(), add="+")
        self.bind("<Leave>", lambda e: self.on_mouse_leave(), add="+")
        self.card.bind("<Enter>", lambda e: self.on_mouse_enter(), add="+")
        self.card.bind("<Leave>", lambda e: self.on_mouse_leave(), add="+")

        # Instantiate secondary custom dropdown menu
        self.menu_window = FloatingMenu(self, self)

        # Animation sequence definitions
        self.widget_state = "idle"  # Renamed from state to avoid DPI scaling collision
        self.anim_frame = 0
        # Subtle animations: spinner (every 150ms), sound wave (every 450ms)
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.wave_frames = ["🔊", "🔉", "🔈", "🔉"]  # Clean wave loops with equal char length!

        self.withdraw()  # Start hidden

    # Drag and hover bindings are handled directly on containers to prevent event hijacking

    def on_mouse_enter(self):
        """Reveals action buttons and expands widget on hover."""
        self.show_action_buttons()

    def on_mouse_leave(self):
        """Gracefully verifies coordinates before hiding buttons to prevent flickering."""
        self.after(60, self._check_mouse_leave)

    def _check_mouse_leave(self):
        x, y = self.winfo_pointerxy()
        
        # Check main widget boundary (expanded width)
        wx = self.winfo_rootx()
        wy = self.winfo_rooty()
        ww = self.winfo_width()
        wh = self.winfo_height()
        inside_widget = (wx <= x <= wx + ww and wy <= y <= wy + wh)
        
        # Check menu boundary
        inside_menu = False
        if self.menu_window and self.menu_window.winfo_viewable():
            mx = self.menu_window.winfo_rootx()
            my = self.menu_window.winfo_rooty()
            mw = self.menu_window.winfo_width()
            mh = self.menu_window.winfo_height()
            inside_menu = (mx <= x <= mx + mw and my <= y <= my + mh)
            
        if not inside_widget and not inside_menu:
            self.hide_action_buttons()
            self.hide_menu()

    def show_action_buttons(self):
        if not self.actions_visible:
            # Dynamically expand width to 240px to show buttons
            x = self.winfo_x()
            y = self.winfo_y()
            self.geometry(f"240x42+{x}+{y}")
            
            self.actions_frame.pack(side="right", padx=(0, 6))
            self.actions_visible = True

    def hide_action_buttons(self):
        if self.actions_visible:
            self.actions_frame.pack_forget()
            self.actions_visible = False
            
            # Dynamically contract width back to 180px
            x = self.winfo_x()
            y = self.winfo_y()
            self.geometry(f"180x42+{x}+{y}")

    def start_drag(self, event):
        """Stores original mouse click coordinates relative to the window."""
        self.x_offset = event.x
        self.y_offset = event.y
        self.hide_menu()  # Instantly dismiss menu during dragging

    def drag_motion(self, event):
        """Calculates and updates window coordinates dynamically on mouse drag."""
        x = self.winfo_x() - self.x_offset + event.x
        y = self.winfo_y() - self.y_offset + event.y
        self.geometry(f"+{x}+{y}")

    def position_randomly(self):
        """Calculates a random coord on screen to project the overlay safely."""
        import random
        
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        
        # Unexpanded startup size dimensions
        w = 180
        h = 42
        
        # Safely constrain within random range leaving 15% to 75% margins
        x = random.randint(int(sw * 0.15), max(int(sw * 0.15) + 50, int(sw * 0.75) - w))
        y = random.randint(int(sh * 0.15), max(int(sh * 0.15) + 50, int(sh * 0.75) - h))
        
        self.geometry(f"{w}x{h}+{x}+{y}")

    def set_processing(self):
        """Sets spinner state to processing and runs loaders."""
        self.widget_state = "processing"
        self.status_lbl.configure(text="Processing...")
        self.play_pause_btn.configure(text="⏸")  # Start in playing/active state
        
        active_speed = config.get("speed", 1.0)
        self.speed_lbl.configure(text=f"Speed: {active_speed}x", text_color="#818CF8")
        
        self.card.configure(border_color="#6366F1")  # Indigo border
        self.deiconify()
        self.lift()
        self.anim_frame = 0
        self.animate()

    def set_reading(self):
        """Transitions overlay text and borders to green reading wave."""
        self.widget_state = "reading"
        self.status_lbl.configure(text="Reading Aloud...")
        self.play_pause_btn.configure(text="⏸")
        
        active_speed = config.get("speed", 1.0)
        self.speed_lbl.configure(text=f"Speed: {active_speed}x", text_color="#34D399")
        
        self.card.configure(border_color="#10B981")  # Emerald border
        self.anim_frame = 0

    def hide(self):
        """Hides the borderless overlay and ends graphics loops."""
        self.widget_state = "idle"
        self.hide_menu()
        self.hide_action_buttons()
        self.withdraw()

    def animate(self):
        """Animate characters dynamically via Tkinter recursive callback loops."""
        if self.widget_state == "idle":
            return
            
        if self.widget_state == "processing":
            self.anim_frame = (self.anim_frame + 1) % len(self.spinner_chars)
            self.icon_label.configure(text=self.spinner_chars[self.anim_frame], text_color="#6366F1")
            self.after(150, self.animate)  # Subtle slower speed (150ms)
        elif self.widget_state == "reading":
            self.anim_frame = (self.anim_frame + 1) % len(self.wave_frames)
            self.icon_label.configure(text=self.wave_frames[self.anim_frame], text_color="#10B981")
            self.after(450, self.animate)  # Subtle slower sound wave pulsing (450ms)

    def toggle_play_pause(self):
        """Pauses or resumes current active selection cleanly without reprocessing."""
        if self.widget_state == "reading":
            # Playback is active, let's pause it!
            tts_engine.pause()
            self.widget_state = "paused"
            self.play_pause_btn.configure(text="▶")
            self.status_lbl.configure(text="Paused")
            self.card.configure(border_color="#F59E0B")  # Yellow pause border
        elif self.widget_state == "paused":
            # Currently paused, let's resume it!
            tts_engine.resume()
            self.widget_state = "reading"
            self.play_pause_btn.configure(text="⏸")
            self.status_lbl.configure(text="Reading Aloud...")
            self.card.configure(border_color="#10B981")  # Green playing border

    def toggle_menu(self):
        """Opens or closes the floating sub-menu under the widget."""
        if self.menu_window.winfo_viewable():
            self.hide_menu()
        else:
            self.show_menu()

    def show_menu(self):
        """Displays menu window directly below the widget card."""
        x = self.winfo_x() + (self.winfo_width() - 150) // 2
        y = self.winfo_y() + self.winfo_height() + 4
        self.menu_window.show(x, y)

    def hide_menu(self):
        if self.menu_window:
            self.menu_window.hide()

    def replay_text(self):
        self.hide_menu()
        if tts_engine.current_text:
            self.widget_state = "reading"
            tts_engine.speak(tts_engine.current_text)

    def cancel_playback(self):
        self.hide_menu()
        tts_engine.stop()
        self.hide()

    def cycle_speed(self):
        speeds = [0.8, 1.0, 1.2, 1.5, 1.8, 2.0]
        current = config.get("speed", 1.0)
        try:
            idx = speeds.index(current)
            new_speed = speeds[(idx + 1) % len(speeds)]
        except ValueError:
            new_speed = 1.0
        
        config.set("speed", new_speed)
        self.menu_window.speed_btn.configure(text=f"⚡  Speed: {new_speed}x")
        self.speed_lbl.configure(text=f"Speed: {new_speed}x")

    def cycle_voice(self):
        voices = ["af_sarah", "am_adam", "bf_emma", "bm_george"]
        voice_names = {
            "af_sarah": "US Female",
            "am_adam": "US Male",
            "bf_emma": "UK Female",
            "bm_george": "UK Male"
        }
        current = config.get("voice", "af_sarah")
        try:
            idx = voices.index(current)
            new_voice = voices[(idx + 1) % len(voices)]
        except ValueError:
            new_voice = "af_sarah"
            
        config.set("voice", new_voice)
        self.menu_window.voice_btn.configure(text=f"🗣️  Voice: {voice_names[new_voice]}")

class UIManager:
    def __init__(self):
        self.root = None
        self.settings_window = None
        self.loading_window = None
        self.floating_widget = None  # Floating state indicator widget
        self.tray_icon = None
        self.progress_bar = None
        self.progress_label = None
        
        # Determine the assets path
        self.icon_path = self._generate_default_icon()

    def _generate_default_icon(self):
        """Generates a default temporary .ico icon programmatically if none exists, to avoid missing asset errors."""
        import tempfile
        from PIL import Image, ImageDraw

        temp_dir = tempfile.gettempdir()
        icon_path = os.path.join(temp_dir, "tts_app_icon.ico")
        
        # Draw a beautiful speaker icon into a temporary file
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Accent background circle (dark purple/blue gradient vibe)
        draw.ellipse([4, 4, 60, 60], fill=(79, 70, 229, 255))
        # White speaker shape
        draw.rectangle([16, 24, 28, 40], fill=(255, 255, 255, 255))
        draw.polygon([(28, 24), (44, 12), (44, 52), (28, 40)], fill=(255, 255, 255, 255))
        # Sound wave arcs
        draw.arc([36, 18, 52, 46], start=-45, end=45, fill=(255, 255, 255, 255), width=3)
        
        img.save(icon_path, format="ICO")
        return icon_path

    def run_app(self):
        """Starts the Tkinter main loop on the main thread."""
        import customtkinter as ctk
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.withdraw() # Keep the main root window hidden
        
        # Check if assets are missing. If so, show beautiful download progress screen first
        model_exists = os.path.exists(MODEL_PATH)
        voices_exists = os.path.exists(VOICES_PATH)
        
        if not model_exists or not voices_exists:
            self._show_loading_screen()
            # Start downloader thread
            threading.Thread(target=self._run_downloader_thread, daemon=True).start()
        else:
            # Models already exist, start the background tray immediately
            self.start_tray()
            self._show_ready_notification()

        self.root.mainloop()

    def _show_loading_screen(self):
        """Creates and shows the initial assets downloader interface."""
        import customtkinter as ctk

        self.loading_window = ctk.CTkToplevel(self.root)
        self.loading_window.title("Kokoro-82M Download manager")
        self.loading_window.geometry("450x230")
        self.loading_window.resizable(False, False)
        
        # Center the loading screen
        self.loading_window.update_idletasks()
        width = self.loading_window.winfo_width()
        height = self.loading_window.winfo_height()
        x = (self.loading_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.loading_window.winfo_screenheight() // 2) - (height // 2)
        self.loading_window.geometry(f"+{x}+{y}")
        
        # Window attributes
        self.loading_window.protocol("WM_DELETE_WINDOW", self.exit_app) # Exit app if they close loading
        self.loading_window.focus_force()

        # UI elements
        title_lbl = ctk.CTkLabel(
            self.loading_window, 
            text="Setting Up Kokoro TTS Engine", 
            font=ctk.CTkFont(family="Outfit", size=18, weight="bold")
        )
        title_lbl.pack(pady=(20, 5))

        desc_lbl = ctk.CTkLabel(
            self.loading_window, 
            text="Downloading lightweight local models (approx. 100MB total).\nThis runs entirely in your isolated environment on first startup.", 
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="gray"
        )
        desc_lbl.pack(pady=5)

        self.progress_label = ctk.CTkLabel(
            self.loading_window, 
            text="Starting downloads...", 
            font=ctk.CTkFont(family="Inter", size=12, weight="bold")
        )
        self.progress_label.pack(pady=(15, 2))

        self.progress_bar = ctk.CTkProgressBar(self.loading_window, width=380)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

    def _run_downloader_thread(self):
        """Thread worker that downloads assets and switches to Tray once finished."""
        try:
            def on_progress(file_name, percent):
                # Update progress bar safely on UI thread
                self.root.after(0, lambda: self._update_download_ui(file_name, percent))

            tts_engine.check_and_download_models(progress_callback=on_progress)
            
            # Download completed successfully, initialize the tray in the main thread
            self.root.after(0, self._on_download_complete)
        except Exception as e:
            print(f"[UI] Download error: {e}")
            self.root.after(0, lambda: self._on_download_failed(str(e)))

    def _update_download_ui(self, file_name, percent):
        """Updates the download progress widgets safely."""
        if self.progress_bar and self.progress_label:
            self.progress_bar.set(percent / 100.0)
            self.progress_label.configure(text=f"Downloading {file_name}: {percent}%")

    def _on_download_complete(self):
        """Closes the loading screen, starts the tray, and alerts user."""
        if self.loading_window:
            self.loading_window.destroy()
            self.loading_window = None
        
        self.start_tray()
        self._show_ready_notification()

    def _on_download_failed(self, error_msg):
        """Displays error window if download fails."""
        import customtkinter as ctk
        from tkinter import messagebox
        
        messagebox.showerror(
            "Setup Error", 
            f"Failed to download required Kokoro TTS models:\n{error_msg}\n\nPlease check your internet connection and restart the app."
        )
        self.exit_app()

    def _show_ready_notification(self):
        """Sends a modern Windows notification showing the app is active."""
        if self.tray_icon:
            self.tray_icon.notify(
                "TTS System Extension is running in the background!\nHighlight text anywhere and press Ctrl+Shift+Space to read it aloud.",
                "Kokoro TTS Ready"
            )

    def start_tray(self):
        """Initializes and runs the pystray background System Tray icon."""
        from PIL import Image
        
        # Load the tray icon
        img = Image.open(self.icon_path)
        
        # Tray Menu
        menu = pystray.Menu(
            item('Settings', self.show_settings_window, default=True),
            item('Paused', self.toggle_pause, checked=lambda item: config.get("paused")),
            pystray.Menu.SEPARATOR,
            item('Exit', self.exit_app)
        )
        
        self.tray_icon = pystray.Icon("kokoro_tts", img, "Kokoro Local TTS", menu)
        
        # Run tray in a separate background thread so the Tkinter thread keeps running
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        # Start TTS background workers and input listeners
        tts_engine.start_worker()
        input_handler.start()

        # Bind callbacks for floating widget state
        tts_engine.on_processing_start = self.on_processing_start
        tts_engine.on_reading_start = self.on_reading_start
        tts_engine.on_reading_end = self.on_reading_end

        # Automatically pop up the beautiful settings configuration GUI on launch
        self.show_settings_window()

    def show_settings_window(self):
        """Shows or restores the CustomTkinter GUI panel thread-safely."""
        self.root.after(0, self._create_or_restore_settings)

    def _create_or_restore_settings(self):
        """Creates or restores the settings dialog on the main thread."""
        import customtkinter as ctk

        if self.settings_window is not None:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self.settings_window = ctk.CTkToplevel(self.root)
        self.settings_window.title("Kokoro TTS Settings")
        self.settings_window.geometry("450x380")
        self.settings_window.resizable(False, False)
        
        # Center the window
        self.settings_window.update_idletasks()
        width = self.settings_window.winfo_width()
        height = self.settings_window.winfo_height()
        x = (self.settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.settings_window.winfo_screenheight() // 2) - (height // 2)
        self.settings_window.geometry(f"+{x}+{y}")

        # Minimize instead of closing when they click X
        self.settings_window.protocol("WM_DELETE_WINDOW", self.hide_settings_window)

        # Style & Layout
        # Title
        title_lbl = ctk.CTkLabel(
            self.settings_window, 
            text="Local ONNX TTS Configuration", 
            font=ctk.CTkFont(family="Outfit", size=18, weight="bold")
        )
        title_lbl.pack(pady=(20, 15))

        # Main settings card frame
        card = ctk.CTkFrame(self.settings_window)
        card.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        # Voice Selector
        voice_lbl = ctk.CTkLabel(card, text="Voice & Speaker Profile", font=ctk.CTkFont(family="Inter", size=13, weight="bold"))
        voice_lbl.pack(anchor="w", padx=20, pady=(15, 2))

        voices = [
            "af_sarah (US Female - Soft)",
            "af_bella (US Female - Crisp)",
            "af_nicole (US Female - Clear)",
            "af_sky (US Female - Modern)",
            "am_adam (US Male - Deep)",
            "am_michael (US Male - Natural)",
            "bf_emma (UK Female - British Soft)",
            "bf_isabella (UK Female - British Natural)",
            "bm_george (UK Male - British Deep)",
            "bm_lewis (UK Male - British Clear)"
        ]
        
        # Get active voice and find its display name
        active_voice = config.get("voice", "af_sarah")
        active_display = next((v for v in voices if v.startswith(active_voice)), voices[0])

        self.voice_dropdown = ctk.CTkComboBox(
            card, 
            values=voices, 
            width=360,
            command=self._on_voice_selected
        )
        self.voice_dropdown.set(active_display)
        self.voice_dropdown.pack(pady=(0, 15), padx=20)

        # Speed Slider
        speed_lbl_frame = ctk.CTkFrame(card, fg_color="transparent")
        speed_lbl_frame.pack(fill="x", padx=20)
        
        speed_title = ctk.CTkLabel(speed_lbl_frame, text="Speech Speed Rate", font=ctk.CTkFont(family="Inter", size=13, weight="bold"))
        speed_title.pack(side="left")
        
        active_speed = config.get("speed", 1.0)
        self.speed_val_lbl = ctk.CTkLabel(speed_lbl_frame, text=f"{active_speed}x", font=ctk.CTkFont(family="Inter", size=12, weight="bold"), text_color="indigo")
        self.speed_val_lbl.pack(side="right")

        self.speed_slider = ctk.CTkSlider(
            card, 
            from_=0.5, 
            to=2.0, 
            number_of_steps=15, 
            width=360,
            command=self._on_speed_changed
        )
        self.speed_slider.set(active_speed)
        self.speed_slider.pack(pady=(0, 20), padx=20)

        # Test Button
        self.test_btn = ctk.CTkButton(
            card, 
            text="Play Test Phrase", 
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=self._test_speech,
            fg_color="#4F46E5", # Custom Premium Indigo color
            hover_color="#4338CA"
        )
        self.test_btn.pack(pady=(5, 10), padx=20, fill="x")

        # Info Footer
        footer_lbl = ctk.CTkLabel(
            card, 
            text="Shortcut: Highlight text and press Ctrl + Shift + Space", 
            font=ctk.CTkFont(family="Inter", size=11, slant="italic"),
            text_color="gray"
        )
        footer_lbl.pack(pady=(5, 10))

    def _on_voice_selected(self, selected_display):
        """Saves voice change."""
        # The actual voice ID is the first token (e.g. 'af_sarah')
        voice_id = selected_display.split()[0]
        config.set("voice", voice_id)
        print(f"[UI] Selected voice style updated to: {voice_id}")

    def _on_speed_changed(self, value):
        """Updates speed slider label and saves speed change."""
        rounded_speed = round(value, 1)
        self.speed_val_lbl.configure(text=f"{rounded_speed}x")
        config.set("speed", rounded_speed)

    def _test_speech(self):
        """Plays a default test phrase to verify configuration changes."""
        test_text = "This is a test of the Kokoro ONNX Text to Speech engine."
        tts_engine.speak(test_text)

    def hide_settings_window(self):
        """Hides the settings window safely without destroying it."""
        if self.settings_window:
            self.settings_window.withdraw()

    def toggle_pause(self, icon_item=None):
        """Toggles global hooking state between paused and active."""
        current_paused = config.get("paused", False)
        new_paused = not current_paused
        config.set("paused", new_paused)
        print(f"[UI] App paused state updated to: {new_paused}")
        
        # Stop any active voice immediately if pausing
        if new_paused:
            tts_engine.stop()
            
        # Redraw tray menu to check/uncheck Pause
        if self.tray_icon:
            self.tray_icon.update_menu()

    def on_processing_start(self):
        """Called programmatically from background thread when audio generation begins."""
        if self.root:
            self.root.after(0, self._show_processing_widget)

    def _show_processing_widget(self):
        """Instantiates or restores the floating widget in a random spot, showing processing."""
        if not self.floating_widget:
            self.floating_widget = FloatingWidget(self.root)
        
        # Position at a random spot
        self.floating_widget.position_randomly()
        self.floating_widget.set_processing()

    def on_reading_start(self):
        """Called programmatically from background thread when audio playback starts."""
        if self.root:
            self.root.after(0, self._show_reading_widget)

    def _show_reading_widget(self):
        """Transitions the floating widget to reading mode."""
        if self.floating_widget:
            self.floating_widget.set_reading()

    def on_reading_end(self):
        """Called programmatically from background thread when playback finishes or interrupts."""
        if self.root:
            self.root.after(0, self._hide_floating_widget)

    def _hide_floating_widget(self):
        """Hides the floating widget completely."""
        if self.floating_widget and self.floating_widget.widget_state != "paused":
            self.floating_widget.hide()

    def exit_app(self, icon_item=None):
        """Gracefully shuts down the background listeners, tray, and loops."""
        print("[UI] Gracefully exiting application...")
        
        # Stop hook listeners
        input_handler.stop()
        
        # Stop speech thread
        tts_engine.stop()
        
        # Destroy floating widget
        if self.floating_widget:
            try:
                self.floating_widget.destroy()
            except Exception:
                pass
        
        # Stop system tray icon
        if self.tray_icon:
            self.tray_icon.stop()
            
        # Terminate tkinter loop
        if self.root:
            self.root.quit()
            self.root.destroy()
            
        sys.exit(0)

# Create global instance
ui_manager = UIManager()
