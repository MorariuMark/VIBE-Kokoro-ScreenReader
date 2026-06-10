import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

DEFAULT_CONFIG = {
    "voice": "af_sarah",
    "speed": 1.0,
    "hotkey": "<ctrl>+<shift>+<space>",
    "paused": False
}

class AppConfig:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Loads configuration from config.json. Falls back to defaults if missing or corrupted."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge loaded keys to handle potential future config expansions gracefully
                    for k, v in loaded.items():
                        self.config[k] = v
            except Exception as e:
                print(f"[Config] Error loading config, using defaults: {e}")
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.save()

    def save(self):
        """Saves current configuration to config.json."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set a configuration value and save immediately."""
        self.config[key] = value
        self.save()

# Global config instance
config = AppConfig()
