"""
Stream Deck Companion - Windows
────────────────────────────────────────────────────────────────────
Controls:
  POT 0 (A0)  →  Discord app volume
  POT 1 (A1)  →  Global system volume
  POT 2 (A2)  →  Spotify app volume
  BTN 0 (D2)  →  Simulate F10 keypress
  BTN 1 (D3)  →  Simulate F12 keypress

Requirements (install once):
  pip install pyserial pycaw psutil pywin32

Run:
  python stream_deck_companion.py

Change COM_PORT below to match your Arduino (check Device Manager).
────────────────────────────────────────────────────────────────────
"""

import serial
import time
import sys
import ctypes
from ctypes import POINTER, cast

# ── Third-party ───────────────────────────────────────────────────
try:
    import win32api
    import win32con
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
except ImportError:
    print("Missing dependencies. Run:")
    print("  pip install pyserial pycaw psutil pywin32")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION - edit these
# ─────────────────────────────────────────────────────────────────
COM_PORT   = "COM3"      # Windows: COM3, COM4, etc.
                         # Linux/Mac: "/dev/ttyUSB0"
BAUD_RATE  = 115200

# Process names as they appear in Windows (case-insensitive)
DISCORD_PROCESS = "Discord.exe"
SPOTIFY_PROCESS = "Spotify.exe"

# Virtual key codes for F10 / playpause
VK_F10 = 0x79
VK_F12 = 0xB3

# ─────────────────────────────────────────────────────────────────
# AUDIO HELPERS
# ─────────────────────────────────────────────────────────────────

def get_app_session(process_name: str):
    """Return the first audio session matching a process name, or None."""
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        if session.Process and session.Process.name().lower() == process_name.lower():
            return session
    return None


def set_app_volume(process_name: str, volume: float):
    """Set an app's volume (0.0 – 1.0). Silently skips if app not running."""
    session = get_app_session(process_name)
    if session is None:
        return
    interface = session._ctl.QueryInterface(ISimpleAudioVolume)
    interface.SetMasterVolume(volume, None)


def set_system_volume(volume: float):
    """Set the Windows master volume (0.0 – 1.0). Works with all pycaw versions."""
    speakers = AudioUtilities.GetSpeakers()
    # pycaw >= 20231005 wraps the COM device in an AudioDevice object
    # older versions return the COM device directly - handle both
    dev = getattr(speakers, '_dev', speakers)
    interface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    endpoint = cast(interface, POINTER(IAudioEndpointVolume))
    endpoint.SetMasterVolumeLevelScalar(volume, None)


# ─────────────────────────────────────────────────────────────────
# KEYPRESS HELPER
# ─────────────────────────────────────────────────────────────────

def press_key(vk_code: int):
    """Simulate a key press + release."""
    win32api.keybd_event(vk_code, 0, 0, 0)                    # key down
    time.sleep(0.05)
    win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)  # key up


# ─────────────────────────────────────────────────────────────────
# POT → ACTION MAP
# ─────────────────────────────────────────────────────────────────

def handle_pot(index: int, raw: int):
    """Map potentiometer value (0-1023) to a volume action."""
    volume = raw / 1023.0   # 0.0 – 1.0

    if index == 0:
        set_app_volume(DISCORD_PROCESS, volume)
        print(f"  Discord  → {round(volume * 100)}%")

    elif index == 1:
        set_system_volume(volume)
        print(f"  System   → {round(volume * 100)}%")

    elif index == 2:
        set_app_volume(SPOTIFY_PROCESS, volume)
        print(f"  Spotify  → {round(volume * 100)}%")


# ─────────────────────────────────────────────────────────────────
# BTN → ACTION MAP
# ─────────────────────────────────────────────────────────────────

def handle_btn(index: int, pressed: bool):
    """Map button press to a key event."""
    if not pressed:
        return   # only act on press, not release

    if index == 0:
        press_key(VK_F10)
        print("  BTN 0  → F10")

    elif index == 1:
        press_key(VK_F12)
        print("  BTN 1  → Play/Pause")


# ─────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────

def main():
    print(f"Connecting to {COM_PORT} at {BAUD_RATE} baud…")
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
    except serial.SerialException as e:
        print(f"ERROR: Could not open {COM_PORT}: {e}")
        print("Check Device Manager for the correct COM port.")
        sys.exit(1)

    time.sleep(2)  # wait for Arduino to reset after serial connect
    print("Connected! Listening for events. Press Ctrl+C to quit.\n")

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            parts = line.split(":")

            if parts[0] == "POT" and len(parts) == 3:
                handle_pot(int(parts[1]), int(parts[2]))

            elif parts[0] == "BTN" and len(parts) == 3:
                handle_btn(int(parts[1]), parts[2] == "1")

            elif parts[0] == "STREAMDECK":
                print(f"Arduino says: {line}")

        except KeyboardInterrupt:
            print("\nExiting.")
            ser.close()
            sys.exit(0)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.1)


if __name__ == "__main__":
    main()
