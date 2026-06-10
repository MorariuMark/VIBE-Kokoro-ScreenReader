import time
import threading

# Try importing dependencies
try:
    import pyperclip
    from pynput import keyboard
    from pynput.keyboard import Controller, Key
except ImportError:
    pass

from src.config import config

class InputHandler:
    def __init__(self):
        self.listener = None
        self.keyboard_controller = None
        self._lock = threading.Lock()

    def start(self):
        """Starts the global hotkey listener in a background thread."""
        with self._lock:
            if self.listener is not None:
                return

            try:
                from pynput.keyboard import Controller
                self.keyboard_controller = Controller()
            except Exception as e:
                print(f"[Input] Error initializing keyboard controller: {e}")
                return

            hotkey_str = config.get("hotkey", "<ctrl>+<shift>+<space>")
            print(f"[Input] Registering global hotkey: {hotkey_str}")

            try:
                from pynput import keyboard
                self.listener = keyboard.GlobalHotKeys({
                    hotkey_str: self._on_hotkey_trigger
                })
                self.listener.start()
                print("[Input] Hotkey listener started successfully.")
            except Exception as e:
                print(f"[Input] Error starting hotkey listener: {e}")

    def stop(self):
        """Stops the global hotkey listener."""
        with self._lock:
            if self.listener is not None:
                try:
                    self.listener.stop()
                    print("[Input] Hotkey listener stopped.")
                except Exception as e:
                    print(f"[Input] Error stopping listener: {e}")
                self.listener = None

    def restart(self):
        """Restarts the listener to apply a new hotkey from config."""
        print("[Input] Restarting hotkey listener...")
        self.stop()
        self.start()

    def _on_hotkey_trigger(self):
        """Callback fired when the global hotkey combo is pressed."""
        if config.get("paused", False):
            print("[Input] Hotkey ignored: Extension is paused.")
            return

        # Run clipboard capture in a separate thread so we don't block the OS keyboard hook
        threading.Thread(target=self._capture_and_speak, daemon=True).start()

    def _capture_and_speak(self):
        """Simulates Ctrl+C, captures selection, restores clipboard, and triggers TTS."""
        try:
            import pyperclip
            from pynput.keyboard import Key
        except ImportError:
            return

        print("[Input] Hotkey triggered! Capturing screen selection...")

        # Helper function to read clipboard with retries in case of temporary lock
        def safe_paste():
            for _ in range(3):
                try:
                    return pyperclip.paste()
                except Exception:
                    time.sleep(0.01)
            return ""

        # Helper function to write clipboard with retries
        def safe_copy(txt):
            for _ in range(3):
                try:
                    pyperclip.copy(txt)
                    return True
                except Exception:
                    time.sleep(0.01)
            return False

        # 1. Backup the current clipboard contents
        old_clipboard = safe_paste()

        # 2. Clear clipboard so we can easily check when the copy finishes
        safe_copy("")

        # 3. Release modifier keys that the user is physically holding
        # This prevents active modifiers (like Shift) from turning Ctrl+C into Ctrl+Shift+C
        try:
            self.keyboard_controller.release(Key.shift)
            self.keyboard_controller.release(Key.ctrl)
            self.keyboard_controller.release(Key.alt)
            self.keyboard_controller.release(Key.cmd)
            # Crucial: sleep a tiny bit so Windows registers the modifier release events
            time.sleep(0.04)
        except Exception as e:
            print(f"[Input] Error releasing modifiers: {e}")

        # 4. Simulate Ctrl + C (with small hardware-friendly delays)
        try:
            self.keyboard_controller.press(Key.ctrl)
            time.sleep(0.02)
            self.keyboard_controller.press('c')
            time.sleep(0.02)
            self.keyboard_controller.release('c')
            time.sleep(0.02)
            self.keyboard_controller.release(Key.ctrl)
        except Exception as e:
            print(f"[Input] Keystroke simulation error: {e}")
            # Try to restore clipboard even on error
            safe_copy(old_clipboard)
            return

        # 5. Poll the clipboard waiting for the copy operation to complete (up to 350ms)
        selected_text = ""
        for _ in range(12):
            time.sleep(0.03)
            clip_content = safe_paste()
            if clip_content and clip_content.strip():
                selected_text = clip_content
                break

        # 6. Restore original clipboard content immediately
        safe_copy(old_clipboard)

        # 7. Route the captured text to the speech engine
        if selected_text and selected_text.strip():
            text_to_speak = selected_text.strip()
            print(f"[Input] Captured selection (len={len(text_to_speak)}): '{text_to_speak[:50]}...'")
            
            # Speak using the global tts_engine instance
            from src.tts_engine import tts_engine
            tts_engine.speak(text_to_speak)
        else:
            print("[Input] No text highlighted or clipboard copy failed.")

# Create global instance
input_handler = InputHandler()
