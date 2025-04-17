import os
import time
import uuid
import threading
import requests
import keyboard
import mss
import ctypes
from PIL import Image
import io

# Folder to store screenshots temporarily
SCREENSHOT_DIR = "screenshots"

# Dummy API endpoint (replace with OpenAI later)
API_URL = "https://httpbin.org/post"

# Make sure the folder exists
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# List to keep track of saved screenshot paths
screenshot_paths = []

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    print("⚠️ Please run this script as Administrator to capture all windows.")
else:
    print("yes")

# Take a screenshot using `mss`
def take_screenshot():
    filename = f"{uuid.uuid4()}.jpg"  # Use JPG for smaller file size
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    with mss.mss() as sct:
        monitor = sct.monitors[2]  # Change to your preferred monitor
        sct_img = sct.grab(monitor)

        # Convert raw screenshot to Pillow Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)

        # Resize (e.g., scale to 50%)
        new_size = (int(img.width * 0.5), int(img.height * 0.5))
        img = img.resize(new_size, Image.LANCZOS)

        # Save with compression (JPEG quality: 30)
        img.save(filepath, "JPEG", quality=60, optimize=True)

    screenshot_paths.append(filepath)
    print(f"[Ctrl+Z] Screenshot saved: {filepath} ({new_size[0]}x{new_size[1]})")

def clear_screenshots():
    if not screenshot_paths:
        print("[Clear] No screenshots to delete.")
        return

    for path in screenshot_paths:
        try:
            os.remove(path)
        except Exception as e:
            print(f"[Clear] Failed to delete {path}: {e}")

    screenshot_paths.clear()
    print("[Clear] All screenshots deleted.")

# Send all stored screenshots to the API
def send_screenshots():
    if not screenshot_paths:
        print("[F2] No screenshots to send.")
        return

    print(f"[F2] Sending {len(screenshot_paths)} screenshot(s) to API...")

    files = []
    for path in screenshot_paths:
        with open(path, 'rb') as f:
            files.append(('files', (os.path.basename(path), f, 'image/png')))

    try:
        response = requests.post(API_URL, files=files)
        print(f"[F2] Response status: {response.status_code}")
        print(f"[F2] Response body: {response.text[:200]}...")

        # Clear screenshots after sending
        for path in screenshot_paths:
            os.remove(path)
        screenshot_paths.clear()
        print("[F2] All screenshots sent and cleared.")

    except Exception as e:
        print(f"[F2] Error sending screenshots: {e}")

# Background listener for F1 and F2
def keyboard_listener():
    print("🎯 Screenshot Sender is running.")
    print("  ⌨️  Ctrl+Z = Take screenshot")
    print("  ⌨️  Ctrl+X = Send screenshots")
    print("  ⌨️  Ctrl+C = Clear screenshots")
    print("  ⌨️  ESC = Quit")

    keyboard.add_hotkey('ctrl+z', take_screenshot)
    keyboard.add_hotkey('ctrl+x', send_screenshots)
    keyboard.add_hotkey('ctrl+c', clear_screenshots)

    keyboard.wait('esc')
    print("❌ Exiting...")

if __name__ == "__main__":
    listener_thread = threading.Thread(target=keyboard_listener)
    listener_thread.start()
