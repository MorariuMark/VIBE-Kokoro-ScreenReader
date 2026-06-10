# Environment Isolation Rules

To maintain absolute system safety and consistency, this project enforces strict execution sandbox constraints. 

## Rules

1. **Virtual Environment Isolation:**
   - All third-party Python modules (`pynput`, `onnxruntime`, `customtkinter`, `sounddevice`, `soundfile`, `kokoro-onnx`, etc.) must be installed and run exclusively inside the local virtual environment located at `.\.venv\`.
   - Never run global system pip commands. Always execute using `.\.venv\Scripts\python.exe` or `.\.venv\Scripts\pip.exe`.

2. **Model Weight Storage:**
   - The Kokoro-82M model weights (`kokoro-v1.0.onnx`) and style vectors (`voices-v1.0.bin`) must be stored strictly within `.\models\` inside this project folder.
   - Do not refer to, read, or write to standard system-level global directories like `~/.cache`, `%APPDATA%`, or `%USERPROFILE%`.

3. **Audio Generation Safety:**
   - Speech synthesis must be fully buffered in local memory or a temporary file inside the project workspace before audio playback is initiated.
   - No live-streaming audio chunks directly to playback output device to avoid stuttering under high OS workload.

4. **Self-Contained Executables:**
   - Do not request the user to install external executables or tools on their system.
   - Always prioritize Python bindings that bundle prebuilt DLLs or compile-free bindings (e.g. `espeakng-loader`, `soundfile`, `sounddevice`).
