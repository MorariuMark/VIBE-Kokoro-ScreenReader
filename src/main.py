import os
import sys

# Dynamic path resolution to ensure the project packages load correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 60)
    print("  KOKORO-82M LOCAL TTS WINDOWS SYSTEM EXTENSION LAUNCHER")
    print("=" * 60)
    print(f"Python Binary:    {sys.executable}")
    print(f"Root Directory:   {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
    print("=" * 60)

    # Verify virtual environment isolation safety rules
    if ".venv" not in sys.executable:
        print("[WARNING] The application is running outside the isolated virtual environment (.venv)!")
        print("Please execute using the 'run.bat' launcher to maintain environment isolation.")
    else:
        print("[OK] Running in isolated virtual environment (.venv).")

    try:
        # Load and run the UI manager (which handles downloading and minimizing to tray)
        from src.ui_manager import ui_manager
        ui_manager.run_app()
    except KeyboardInterrupt:
        print("[OK] Keyboard interrupt received, exiting...")
    except Exception as e:
        print(f"[FATAL] Application crash during execution: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
