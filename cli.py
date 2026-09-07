#!/usr/bin/env python3
"""
CLI untuk environment lab. Hanya menjalankan perintah whitelist.
Gunakan: python cli.py <command> [args]
"""

import sys
import requests
import json
import base64
from PIL import Image
from io import BytesIO

BASE_URL = "http://127.0.0.1:5000"

def print_help():
    print("""
Usage: python cli.py <command> [arguments]

Commands:
  sessions                     - List all active sessions
  status <session_id>          - Show session details
  capture-result <session_id>  - Show captured image (base64) and save to file
  replay <session_id>          - Generate synthetic replay capture for session
  help                         - Show this help

Examples:
  python cli.py sessions
  python cli.py status LAB-1234
  python cli.py capture-result LAB-1234
  python cli.py replay LAB-1234
""")

def list_sessions():
    resp = requests.get(f"{BASE_URL}/api/dashboard/sessions")
    if resp.status_code == 401:
        print("❌ Unauthorized. Make sure you are logged in via browser or set token.")
        return
    data = resp.json()
    if not data:
        print("No active sessions.")
        return
    print("Active Sessions:")
    for s in data:
        print(f"  {s['session_id']} | {s['status']} | Camera: {s['camera_permission']} | Captcha: {s['captcha_verified']}")

def session_status(sid):
    resp = requests.get(f"{BASE_URL}/api/cli/status/{sid}")
    if resp.status_code == 404:
        print(f"Session {sid} not found.")
        return
    data = resp.json()
    print(json.dumps(data, indent=2))

def capture_result(sid):
    resp = requests.get(f"{BASE_URL}/api/cli/capture-result/{sid}")
    if resp.status_code == 404:
        print(f"Session {sid} not found.")
        return
    data = resp.json()
    if not data.get("ok"):
        print("No photo available for this session.")
        return
    b64 = data["image_base64"]
    # Decode and save
    img_data = base64.b64decode(b64)
    filename = f"capture_{sid}.jpg"
    with open(filename, "wb") as f:
        f.write(img_data)
    print(f"✅ Image saved as {filename}")
    # Tampilkan preview di terminal? Sulit, jadi hanya info.

def replay(sid):
    resp = requests.get(f"{BASE_URL}/api/cli/replay/{sid}")
    if resp.status_code == 404:
        print(f"Session {sid} not found.")
        return
    data = resp.json()
    if data.get("ok"):
        print(f"✅ Replay generated for {sid}. Check dashboard.")
    else:
        print("❌ Replay failed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "help":
        print_help()
    elif cmd == "sessions":
        list_sessions()
    elif cmd == "status" and len(sys.argv) == 3:
        session_status(sys.argv[2])
    elif cmd == "capture-result" and len(sys.argv) == 3:
        capture_result(sys.argv[2])
    elif cmd == "replay" and len(sys.argv) == 3:
        replay(sys.argv[2])
    else:
        print("Unknown command or missing arguments.")
        print_help()
        sys.exit(1)