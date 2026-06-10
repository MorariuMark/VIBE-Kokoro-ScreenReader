# VIBE-Kokoro-ScreenReader

A background-running Windows system utility that captures selected screen text, triggers text-to-speech, and reads it aloud using a local Kokoro-82M ONNX model. The application features full local GPU acceleration using NVIDIA CUDA.

## Features

* **Global Hotkey (Ctrl + Shift + Space)**: Captures currently selected text from any application, temporarily backing up and restoring the clipboard.
* **Floating Controller Widget**:
    * **Native Pause/Resume**: Uses sounddevice stream stop/start to toggle playback without consuming CPU resources while paused.
    * **Stop Control**: Immediately cancels playback, clears the speech queue, and dismisses the widget.
    * **Settings Menu**: Allows voice profile cycling and exposes a slider to adjust speed rate (from 0.5x to 2.0x) for subsequent reads.
* **Local GPU Acceleration**: Runs inference directly on dedicated NVIDIA GPUs (e.g., GTX 1650) using project-isolated CUDA, cuDNN, and cuFFT dependencies. No system-wide CUDA installation is required.
* **Compact UI**: Minimizes to the Windows system tray and runs as a background process.

## Quick Start

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/MorariuMark/VIBE-Kokoro-ScreenReader.git
   cd VIBE-Kokoro-ScreenReader
   ```

2. **Launch**:
   * Run the `run.bat` script.
   * On first run, it initializes a local virtual environment (`.venv`), installs dependencies, and downloads the ONNX model weights and voice files (~100MB) to the local `models` directory.

3. **Usage**:
   * Highlight text anywhere and press `Ctrl + Shift + Space`.
   * Access configuration options by right-clicking the speaker icon in the system tray.

## Tech Stack

* **Language**: Python 3.10+
* **Inference**: `kokoro-onnx` and `onnxruntime-gpu`
* **GPU Dependencies**: `nvidia-cuda-runtime-cu12`, `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, `nvidia-cufft-cu12`, `nvidia-curand-cu12`, `nvidia-nvjitlink-cu12`
* **GUI & Tray**: `customtkinter` and `pystray`
* **System Hooks**: `pynput` for keyboard interception
* **Audio**: `sounddevice` and `soundfile`