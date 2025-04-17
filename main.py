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
import openai
import base64
from pathlib import Path
from datetime import datetime


openai.api_key = os.getenv("OPENAI_API_KEY")
conversation_history = []
DEFAULT_PROMPT = "Describe this image in 1 sentence"

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

LOG_FILE = "gpt_responses_log.txt"

def log_response(image_path, prompt, reply):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = os.path.basename(image_path)

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"[{timestamp}] Screenshot: {filename}\n")
        log.write(f"Prompt: {prompt}\n")
        log.write(f"Response:\n{reply}\n")
        log.write("-" * 40 + "\n\n")
        
def send_to_openai(image_path, prompt=DEFAULT_PROMPT):
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        # Append user message (image + text) to the conversation
        conversation_history.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}",
                        "detail": "low"
                    }
                }
            ]
        })

        response = openai.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=conversation_history,
            max_tokens=100,
            temperature=0.5
        )

        reply = response.choices[0].message.content
        print(f"[OpenAI] Response: {reply}")

        # Append assistant reply to conversation
        conversation_history.append({
            "role": "assistant",
            "content": reply
        })

        log_response(image_path, prompt, reply)

    except Exception as e:
        print(f"[OpenAI] Error: {e}")

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
        print("[Ctrl+X] No screenshots to send.")
        return

    print(f"[Ctrl+X] Sending {len(screenshot_paths)} screenshot(s)...")

    for path in screenshot_paths:
        send_to_openai(path)

    # Optionally clear after sending
    for path in screenshot_paths:
        os.remove(path)
    screenshot_paths.clear()
    print("[Ctrl+X] Sent and cleared.")

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
