#!/usr/bin/env python3
"""
Stream Deck Companion — Linux
────────────────────────────────────────────────────────────────────
Controls:
  POT 0 (A0)  →  Discord app volume
  POT 1 (A1)  →  Global system volume
  POT 2 (A2)  →  Spotify app volume
  BTN 0 (D2)  →  Simulate F10 keypress
  BTN 1 (D3)  →  Simulate F12 keypress

Requirements:
  - PulseAudio or PipeWire (pipewire-pulse) with `pactl` available
  - xdotool (X11) — sudo apt install xdotool
    or ydotool (Wayland) — sudo apt install ydotool

  pip install pyserial

Run:
  python3 stream_deck_companion_linux.py

Change SERIAL_PORT below to match your Arduino (usually /dev/ttyUSB0
or /dev/ttyACM0 — run `ls /dev/tty*` after plugging in to find it).

You may need permission to access the serial port:
  sudo usermod -a -G dialout $USER
  (then log out and back in)
────────────────────────────────────────────────────────────────────
"""

import serial
import subprocess
import shutil
import sys
import time

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION — edit these
# ─────────────────────────────────────────────────────────────────
SERIAL_PORT = "/dev/ttyUSB0"   # or /dev/ttyACM0 — check with: ls /dev/tty*
BAUD_RATE   = 115200

# App names as they appear in `pactl list sink-inputs` (application.name)
DISCORD_APP_NAME = "Discord"
SPOTIFY_APP_NAME = "Spotify"

# Key names for xdotool / ydotool
KEY_BTN0 = "F10"
KEY_BTN1 = "F12"

# ─────────────────────────────────────────────────────────────────
# DETECT KEY-SIMULATION TOOL (xdotool for X11, ydotool for Wayland)
# ─────────────────────────────────────────────────────────────────
KEY_TOOL = None
if shutil.which("xdotool"):
    KEY_TOOL = "xdotool"
elif shutil.which("ydotool"):
    KEY_TOOL = "ydotool"
else:
    print("WARNING: Neither xdotool nor ydotool found.")
    print("  X11:     sudo apt install xdotool")
    print("  Wayland: sudo apt install ydotool   (and run ydotoold as a service)")

if not shutil.which("pactl"):
    print("ERROR: pactl not found. Install PulseAudio or PipeWire-Pulse:")
    print("  sudo apt install pulseaudio-utils")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────
# AUDIO HELPERS (PulseAudio / PipeWire via pactl)
# ─────────────────────────────────────────────────────────────────

def get_sink_input_id(app_name: str):
    """Find the sink-input ID for a running app by matching application.name."""
    try:
        output = subprocess.run(
            ["pactl", "list", "sink-inputs"],
            capture_output=True, text=True, check=True
        ).stdout
    except subprocess.CalledProcessError:
        return None

    current_id = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Sink Input #"):
            current_id = line.split("#")[1]
        elif "application.name" in line and current_id is not None:
            # line looks like: application.name = "Discord"
            name = line.split("=", 1)[1].strip().strip('"')
            if app_name.lower() in name.lower():
                return current_id
    return None


def set_app_volume(app_name: str, volume: float):
    """Set an app's volume (0.0 - 1.0). Silently skips if app isn't playing audio."""
    sink_id = get_sink_input_id(app_name)
    if sink_id is None:
        return
    pct = round(volume * 100)
    subprocess.run(
        ["pactl", "set-sink-input-volume", sink_id, f"{pct}%"],
        capture_output=True
    )


def set_system_volume(volume: float):
    """Set the default sink's master volume (0.0 - 1.0)."""
    pct = round(volume * 100)
    subprocess.run(
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"],
        capture_output=True
    )


# ─────────────────────────────────────────────────────────────────
# KEYPRESS HELPER
# ─────────────────────────────────────────────────────────────────

def press_key(key_name: str):
    """Simulate a key press using xdotool or ydotool."""
    if KEY_TOOL == "xdotool":
        subprocess.run(["xdotool", "key", key_name], capture_output=True)
    elif KEY_TOOL == "ydotool":
        # ydotool uses linux input event key names, e.g. F10 -> key 68
        # ydotool key understands names like "F10" in recent versions
        subprocess.run(["ydotool", "key", key_name], capture_output=True)
    else:
        print(f"  (no key tool available, would press {key_name})")


# ─────────────────────────────────────────────────────────────────
# POT / BTN HANDLERS
# ─────────────────────────────────────────────────────────────────

def handle_pot(index: int, raw: int):
    """Map potentiometer value (0-1023) to a volume action."""
    volume = raw / 1023.0

    if index == 0:
        set_app_volume(DISCORD_APP_NAME, volume)
        print(f"  Discord  -> {round(volume * 100)}%")

    elif index == 1:
        set_system_volume(volume)
        print(f"  System   -> {round(volume * 100)}%")

    elif index == 2:
        set_app_volume(SPOTIFY_APP_NAME, volume)
        print(f"  Spotify  -> {round(volume * 100)}%")


def handle_btn(index: int, pressed: bool):
    """Map button press to a key event."""
    if not pressed:
        return  # only act on press, not release

    if index == 0:
        press_key(KEY_BTN0)
        print(f"  BTN 0  -> {KEY_BTN0}")

    elif index == 1:
        press_key(KEY_BTN1)
        print(f"  BTN 1  -> {KEY_BTN1}")


# ─────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────

def main():
    print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    except serial.SerialException as e:
        print(f"ERROR: Could not open {SERIAL_PORT}: {e}")
        print("Run `ls /dev/tty*` to find the correct port.")
        print("You may also need: sudo usermod -a -G dialout $USER  (then re-login)")
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
