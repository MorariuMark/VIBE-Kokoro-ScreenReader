# VIBE-Kokoro-ScreenReader 🎙️✨

A lightweight, high-performance, background-running Windows system extension that allows you to select text anywhere on your screen, trigger a global hotkey, and read it aloud using the state-of-the-art **Kokoro-82M** Text-to-Speech (TTS) model running locally via ONNX with NVIDIA CUDA GPU acceleration.

---

## 🌟 Key Features

*   **Global Hotkey Activation (`Ctrl + Shift + Space`)**: Highlight any text on your screen (browser, document, PDF, Discord) and trigger reading instantly.
*   **Safe Clipboard Preservation**: Automatically backups your clipboard history, grabs the selected text, and restores your old clipboard content seamlessly.
*   **Media-Style Floating Widget**:
    *   **Zero-CPU Native Pausing**: Toggles pause/play (`⏸`/`▶`) instantly using native sounddevice stream stops, consuming no CPU cycles while paused.
    *   **Vibrant Stop Button (`⏹`)**: Red button cancels the current playback immediately and hides the widget.
    *   **Expandable Speed Slider**: Clicking the speed button dynamically expands the menu to show a slider (`0.5x` to `2.0x`) that adjusts speed for the next reading.
    *   **Voice Profile Cycling**: Cycle through high-quality UK and US English voice styles.
*   **Self-Contained GPU Acceleration**: Runs natively on your dedicated **NVIDIA GeForce GTX 1650** (or higher) GPU using local CUDA/cuDNN packages, achieving speech generation in **under ~0.4 seconds** without needing a global system-wide CUDA Toolkit installation.
*   **DPI-Aware Glassmorphic UI**: Sleek dark slate cards with harmonized HSL color borders (Indigo for Processing, Emerald for Reading, Amber for Paused).

---

## 🚀 Quick Start

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/MorariuMark/VIBE-Kokoro-ScreenReader.git
    cd VIBE-Kokoro-ScreenReader
    ```
2.  **Launch the App**:
    *   Double-click the **`run.bat`** file.
    *   On the first run, the app will automatically setup the isolated `.venv` virtual environment, install package dependencies, and download the lightweight Kokoro ONNX model weights (`~100MB`) programmatically with a modern download manager screen.
3.  **Read Aloud**:
    *   Select text anywhere on the screen and press **`Ctrl + Shift + Space`**.
    *   The app will run in your system tray. Right-click the system tray icon to access global configuration settings, toggle pause state, or exit the extension.

---

## 🛠️ Technology Stack

*   **Core Logic**: Python 3.10+
*   **TTS Engine**: `kokoro-onnx`
*   **Inference Backend**: `onnxruntime-gpu` (utilizing self-contained `nvidia-cuda-runtime-cu12`, `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, `nvidia-cufft-cu12`, `nvidia-curand-cu12`, and `nvidia-nvjitlink-cu12` packages)
*   **System Hook**: `pynput` for keyboard hotkey hooking
*   **UI Toolkit**: `customtkinter` for premium glassmorphic widgets and configuration panels
*   **System Tray Integration**: `pystray`
*   **Audio Output**: `sounddevice` and `soundfile`

---

## 🔒 Environment Isolation & Security

This project enforces strict environment isolation:
*   All dependencies, including the 1.5GB of NVIDIA CUDA runtime libraries, reside strictly within the project's local virtual environment (`.venv`).
*   No system-wide environment variables (`PATH`) or global Windows directories are modified.
*   Model weights and voice binaries are downloaded programmatically into the isolated local `./models/` folder.