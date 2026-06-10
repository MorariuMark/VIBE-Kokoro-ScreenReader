import os
import sys
import threading
import queue
import urllib.request
import numpy as np

# Try importing dependencies; they are installed in the venv
try:
    import sounddevice as sd
    from kokoro_onnx import Kokoro
except ImportError:
    # If not installed yet, we will import them dynamically when needed
    pass

from src.config import config

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

MODEL_PATH = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")
VOICES_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")

class TTSEngine:
    def __init__(self):
        self.kokoro = None
        self._playback_thread = None
        self._task_queue = queue.Queue()
        self._current_playback_id = 0
        self._generation_lock = threading.Lock()
        self.is_downloading = False
        self.download_progress_callback = None
        self.is_initialized = False
        # State callbacks for UI floating widgets
        self.on_processing_start = None
        self.on_reading_start = None
        self.on_reading_end = None
        self.current_text = ""

        # Dynamic Audio OutputStream properties
        self.playback_samples = None
        self.playback_index = 0
        self.playback_active = False
        self.playback_paused = False
        self.playback_stream = None
        self._stream_lock = threading.Lock()

    def check_and_download_models(self, progress_callback=None):
        """Checks if models are present and downloads them if not."""
        self.download_progress_callback = progress_callback
        if not os.path.exists(MODELS_DIR):
            os.makedirs(MODELS_DIR)

        needed_downloads = []
        if not os.path.exists(MODEL_PATH):
            needed_downloads.append(("Model weights", MODEL_URL, MODEL_PATH))
        if not os.path.exists(VOICES_PATH):
            needed_downloads.append(("Voice styles", VOICES_URL, VOICES_PATH))

        if needed_downloads:
            self.is_downloading = True
            try:
                for name, url, path in needed_downloads:
                    self._download_file(name, url, path)
            finally:
                self.is_downloading = False
        
        self.initialize_model()

    def _download_file(self, name, url, destination):
        """Downloads a file with progress reporting."""
        print(f"[TTS] Downloading {name} from {url}...")
        
        # Temporary file path during download to prevent corrupted loads
        temp_destination = destination + ".tmp"
        
        def reporthook(blocknum, blocksize, totalsize):
            if totalsize > 0 and self.download_progress_callback:
                percent = min(100, int(blocknum * blocksize * 100 / totalsize))
                self.download_progress_callback(name, percent)
                # Keep printing to logs
                if blocknum % 100 == 0:
                    print(f"[TTS] Download {name}: {percent}%")

        try:
            urllib.request.urlretrieve(url, temp_destination, reporthook)
            if os.path.exists(destination):
                os.remove(destination)
            os.rename(temp_destination, destination)
            print(f"[TTS] Successfully downloaded {name} to {destination}.")
        except Exception as e:
            if os.path.exists(temp_destination):
                os.remove(temp_destination)
            print(f"[TTS] Failed to download {name}: {e}")
            raise e

    def initialize_model(self):
        """Initializes the ONNX runtime model in memory once, enabling CUDA GPU acceleration if supported."""
        if self.is_initialized:
            return
        
        if not os.path.exists(MODEL_PATH) or not os.path.exists(VOICES_PATH):
            print("[TTS] Cannot initialize model: files are missing.")
            return

        try:
            # Query and add local virtual environment NVIDIA runtime DLL paths to Windows DLL search path
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            site_packages = os.path.join(project_dir, ".venv", "Lib", "site-packages")
            
            cuda_paths = [
                os.path.join(site_packages, "nvidia", "cuda_runtime", "bin"),
                os.path.join(site_packages, "nvidia", "cublas", "bin"),
                os.path.join(site_packages, "nvidia", "cudnn", "bin"),
                os.path.join(site_packages, "nvidia", "cuda_nvrtc", "bin"),
                os.path.join(site_packages, "nvidia", "cufft", "bin"),
                os.path.join(site_packages, "nvidia", "curand", "bin"),
                os.path.join(site_packages, "nvidia", "nvjitlink", "bin"),
            ]
            
            for path in cuda_paths:
                if os.path.exists(path):
                    try:
                        os.add_dll_directory(path)
                        os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
                        print(f"[TTS] Registered CUDA DLL path: {path}")
                    except Exception as e:
                        print(f"[TTS] Warning: Could not register DLL directory {path}: {e}")

            # We import here to avoid loading on module import
            from kokoro_onnx import Kokoro
            import onnxruntime as ort
            
            # Query and prioritize CUDA GPU Execution Provider, explicitly avoiding buggy DirectML
            available_providers = ort.get_available_providers()
            active_provider = "CPUExecutionProvider"
            
            if "CUDAExecutionProvider" in available_providers:
                os.environ["ONNX_PROVIDER"] = "CUDAExecutionProvider"
                active_provider = "CUDAExecutionProvider"
            
            print(f"[TTS] Loading model {MODEL_PATH} into memory with environment prioritized provider: {active_provider}...")
            self.kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
            
            # Retrieve the active provider from the internal InferenceSession for transparency
            active = "CPUExecutionProvider"
            if hasattr(self.kokoro, "sess") and hasattr(self.kokoro.sess, "get_providers"):
                try:
                    active = self.kokoro.sess.get_providers()[0]
                except Exception:
                    pass
            
            self.is_initialized = True
            print(f"[TTS] Model loaded successfully. Active Execution Provider: {active}")
            if active != "CPUExecutionProvider":
                print(f"[TTS] ONNX GPU acceleration successfully enabled via {active}!")
            else:
                print("[TTS] Running ONNX model on CPU. (To accelerate with GPU, ensure you have onnxruntime-gpu installed with matching NVIDIA CUDA Toolkit)")
        except Exception as e:
            print(f"[TTS] Error loading ONNX model: {e}")
            raise e

    def start_worker(self):
        """Starts the background worker thread for processing speak requests."""
        # Pre-load the ONNX model in a background thread if the files are already downloaded.
        # This keeps the system tray startup instantaneous while ensuring the model starts loading.
        if not self.is_initialized and os.path.exists(MODEL_PATH) and os.path.exists(VOICES_PATH):
            print("[TTS] Pre-loading Kokoro ONNX model in background...")
            threading.Thread(target=self.initialize_model, daemon=True).start()

        if self._playback_thread is None or not self._playback_thread.is_alive():
            self._playback_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._playback_thread.start()
            print("[TTS] Background worker thread started.")

    def _audio_callback(self, outdata, frames, time_info, status):
        """Callback for sounddevice OutputStream to support millisecond-accurate pause/resume."""
        with self._stream_lock:
            if not self.playback_active:
                outdata.fill(0)
                raise sd.CallbackStop()

            if self.playback_paused:
                outdata.fill(0)
                return

            start = self.playback_index
            end = start + frames

            if start >= len(self.playback_samples):
                outdata.fill(0)
                self.playback_active = False
                raise sd.CallbackStop()

            chunk = self.playback_samples[start:end]
            if len(chunk) < frames:
                # Fill remaining buffer with zero
                outdata[:len(chunk), 0] = chunk
                outdata[len(chunk):].fill(0)
                self.playback_index = len(self.playback_samples)
                self.playback_active = False
                raise sd.CallbackStop()
            else:
                outdata[:, 0] = chunk
                self.playback_index = end

    def _stop_stream(self):
        """Cleans up the active audio output stream."""
        with self._stream_lock:
            self.playback_active = False
            self.playback_paused = False
            if self.playback_stream:
                try:
                    self.playback_stream.stop()
                    self.playback_stream.close()
                except Exception:
                    pass
                self.playback_stream = None

    def pause(self):
        """Pauses the active playback stream."""
        with self._stream_lock:
            self.playback_paused = True
            if self.playback_stream:
                try:
                    self.playback_stream.stop()
                except Exception as e:
                    print(f"[TTS] Error pausing stream: {e}")
            print("[TTS] Playback stream paused.")

    def resume(self):
        """Resumes the active playback stream."""
        with self._stream_lock:
            self.playback_paused = False
            if self.playback_stream:
                try:
                    self.playback_stream.start()
                except Exception as e:
                    print(f"[TTS] Error resuming stream: {e}")
            print("[TTS] Playback stream resumed.")

    def _worker_loop(self):
        """Background loop that processes the audio generation and playback queue."""
        while True:
            try:
                # Wait for a speak command
                text, req_id = self._task_queue.get()
                
                # Check if this request is still valid (not cancelled)
                if req_id != self._current_playback_id:
                    self._task_queue.task_done()
                    continue

                if config.get("paused", False):
                    self._task_queue.task_done()
                    continue

                # Trigger processing callback in UI
                if self.on_processing_start:
                    self.on_processing_start()

                # Run audio generation under lock to prevent simultaneous model queries
                with self._generation_lock:
                    # Self-healing lazy-load if not initialized yet but files exist
                    if not self.is_initialized:
                        if os.path.exists(MODEL_PATH) and os.path.exists(VOICES_PATH):
                            print("[TTS] Lazy-loading ONNX model on demand...")
                            try:
                                self.initialize_model()
                            except Exception as e:
                                print(f"[TTS] Lazy-loading failed: {e}")

                    if not self.is_initialized:
                        print("[TTS] Error: TTS Engine is not initialized. Model files may be missing or corrupted.")
                        self._task_queue.task_done()
                        continue
                    
                    voice = config.get("voice", "af_sarah")
                    speed = config.get("speed", 1.0)
                    
                    # Deduce language code from voice name prefix
                    if voice.startswith("bf_") or voice.startswith("bm_"):
                        lang = "en-gb"
                    elif voice.startswith("jf_"):
                        lang = "ja"
                    elif voice.startswith("zf_"):
                        lang = "zh"
                    elif voice.startswith("ef_") or voice.startswith("em_"):
                        lang = "es" # Spanish
                    else:
                        lang = "en-us" # US English default

                    print(f"[TTS] Generating speech (ID: {req_id}) | Voice: {voice} | Speed: {speed}x | Lang: {lang} | Text: '{text[:40]}...'")
                    
                    try:
                        samples, sample_rate = self.kokoro.create(
                            text,
                            voice=voice,
                            speed=speed,
                            lang=lang
                        )
                    except Exception as e:
                        print(f"[TTS] Speech synthesis failed: {e}")
                        self._task_queue.task_done()
                        continue

                # If another request arrived during generation, discard this playback
                if req_id != self._current_playback_id:
                    self._task_queue.task_done()
                    continue

                # Play the generated audio completely
                print(f"[TTS] Playing audio (ID: {req_id})...")
                try:
                    self._stop_stream()

                    self.playback_samples = samples
                    self.playback_index = 0
                    self.playback_active = True
                    self.playback_paused = False

                    # Start dynamic stream
                    import sounddevice as sd
                    self.playback_stream = sd.OutputStream(
                        samplerate=sample_rate,
                        channels=1,
                        callback=self._audio_callback
                    )
                    self.playback_stream.start()
                    
                    if self.on_reading_start:
                        self.on_reading_start()

                    # Wait for playback to finish OR for the request to be cancelled/interrupted
                    while self.playback_active:
                        if req_id != self._current_playback_id or config.get("paused", False):
                            self._stop_stream()
                            print(f"[TTS] Playback interrupted (ID: {req_id}).")
                            break
                        threading.Event().wait(0.05) # Tiny sleep to prevent high CPU polling
                        
                except Exception as e:
                    print(f"[TTS] Audio playback error: {e}")
                
                if self.on_reading_end:
                    self.on_reading_end()

                self._task_queue.task_done()
            except Exception as e:
                print(f"[TTS] Error in worker loop: {e}")
                threading.Event().wait(1.0)

    def speak(self, text):
        """Triggers TTS read out of text, interrupting any active playback."""
        if not text or not text.strip():
            return

        self.current_text = text

        # 1. Stop any currently playing audio immediately
        self._stop_stream()

        # 2. Increment request ID to invalidate any pending or currently playing tasks
        self._current_playback_id += 1
        current_id = self._current_playback_id

        # 3. Clear the queue
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
                self._task_queue.task_done()
            except queue.Empty:
                break

        # 4. Queue the new text
        self._task_queue.put((text, current_id))

    def stop(self):
        """Stops any active playback immediately."""
        self._current_playback_id += 1
        self._stop_stream()

# Create global instance
tts_engine = TTSEngine()
