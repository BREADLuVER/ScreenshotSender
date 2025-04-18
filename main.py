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
from dotenv import load_dotenv
import overlay_popup
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
conversation_history = []
DEFAULT_PROMPT = "solve the coding question"

# Folder to store screenshots temporarily
SCREENSHOT_DIR = "screenshots"

# Dummy API endpoint (replace with OpenAI later)
API_URL = "https://httpbin.org/post"

# Make sure the folder exists
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# List to keep track of saved screenshot paths
screenshot_paths: list[str] = [] 

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

overlay = overlay_popup.OverlayManager(
    conversation_history=conversation_history,
    openai=openai,
    log_response=log_response,
    screenshot_paths=screenshot_paths
)

overlay.start()

# Register toggle
keyboard.add_hotkey("F2", overlay.toggle)

# Use this anywhere:
overlay.show_message("This is a very long message from GPT. " * 1)

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
            model="gpt-4o",
            messages=conversation_history,
            max_tokens=100,
            temperature=0.5
        )

        reply = response.choices[0].message.content
        overlay.show_message(reply)
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
    # 1) Hide overlay completely so no capture ever sees it
    if overlay.window:
        overlay.window.hide()

    # 2) Give DWM time to recompose without your window
    time.sleep(0.2)

    # 3) Do the mss grab as before
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    with mss.mss() as sct:
        monitor = sct.monitors[2]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        img = img.resize((int(img.width * 0.7), int(img.height * 0.7)), Image.LANCZOS)
        img.save(filepath, "JPEG", quality=90, optimize=True)

    # 4) Restore your overlay immediately
    if overlay.window:
        overlay.window.show()

    screenshot_paths.append(filepath)
    print(f"[Ctrl+Z] Screenshot saved: {filepath} ({img.width}x{img.height})")
    
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
    keyboard.add_hotkey('ctrl+shift+c', clear_screenshots)

    keyboard.wait('ctrl+shift+k')
    print("❌ Exiting...")

if __name__ == "__main__":
    listener_thread = threading.Thread(target=keyboard_listener)
    listener_thread.start()
