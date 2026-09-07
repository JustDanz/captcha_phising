# captcha-lab — Security Awareness CAPTCHA Simulation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-blue)](https://flask.palletsprojects.com/)

> **AUTHORIZED SECURITY AWARENESS LAB — FOR TRAINING/DEMO USE ONLY**  
> Use only on devices you own, or with participants who have given explicit, informed consent as part of a security-awareness training session.  
> **Do not deploy this outside a controlled lab network.** Do not use it to target people without consent — that would be illegal in most jurisdictions.

---

## 📌 What this demonstrates

A realistic fake "reCAPTCHA" page that, once the participant clicks **"I'm not a robot"**, asks the browser for **camera** and **location** permissions using the standard, user-visible browser permission prompts. If the participant grants them, the demo:

1. Takes **one** photo (front-facing camera for selfie simulation on mobile).
2. Reads the device's GPS coordinates via the Geolocation API.
3. Sends that data back to the local Flask server.
4. Shows results in the operator's terminal in real time.
5. Saves results to `logs/<session_id>.json` and `logs/<session_id>.txt`.
6. Provides a **live operator dashboard** with authentication, audit logs, and a terminal console.
7. Supports **CLI commands** for remote inspection and replay tests.

**This is not credential phishing.** There is no login form, no password field, no OTP/token field, and no cookie/session harvesting anywhere in this project. It only shows what over‑permissive browser grants can expose.

---

## 🚫 What this does NOT do (by design)

- No permission bypass — 100% standard `getUserMedia()` / `getCurrentPosition()` browser prompts that the user must explicitly accept.
- No stealth capture, no background access, no persistence.
- No password/cookie/token/clipboard/file-system access.
- No keylogging.
- No data sent anywhere outside your lab network (server runs locally; there are no external API calls).
- Refuses to start unless `LAB_MODE=true` (the default).

---

## ✨ Features

- **Fake CAPTCHA UI** with loading spinner and visual feedback.
- **Front‑facing camera** capture (ideal for smartphone selfies).
- **Geolocation** (latitude, longitude, accuracy) with browser consent.
- **Session management** – each demo run gets a unique session ID.
- **Real‑time terminal logging** – see everything as it happens.
- **Operator Dashboard** with:
  - Authentication (default `admin` / `labpass123`, configurable via env)
  - List of active sessions with status, permissions, and photo thumbnails
  - **Replay** button to generate a synthetic test image for a session
  - **Terminal console** to run whitelisted CLI commands right in the browser
  - **Audit log** of all actions
  - Clear all data and delete session buttons
- **CLI tool** (`cli.py`) for lab administrators:
  - `sessions` – list all active sessions
  - `status <session_id>` – show detailed info
  - `capture-result <session_id>` – download the captured image as base64
  - `replay <session_id>` – generate a synthetic replay image
- **Security hardening**:
  - Rate limiting on API endpoints
  - File upload validation (MIME type, size limit)
  - Path traversal protection
  - Command allowlisting
  - Audit logging
  - Dashboard authentication

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- `pip` and `virtualenv` (recommended)
- (Optional) QR code libraries if you want to generate QR codes (already in `requirements.txt`)

### Clone and setup

```bash
git clone https://github.com/yourusername/captcha-lab.git
cd captcha-lab
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt`:
```
Flask==3.0.3
Pillow==10.4.0
requests==2.31.0
# qrcode==7.4.2   # optional, for QR generation
```

---

## 🚀 Running the server

```bash
export LAB_MODE=true   # default; can be omitted
python3 app.py
```

On startup the server will:
- Print the lab URL, e.g. `http://127.0.0.1:5000/`
- Print the dashboard login credentials (default `admin` / `labpass123`)
- Print the dashboard URL: `http://127.0.0.1:5000/dashboard`

---

## 📱 Accessing the demo from other devices (e.g. phone)

### 1. Get your host IP

- **WSL2**:  
  ```bash
  ip addr show eth0 | grep inet
  ```
- **Windows**:  
  Open PowerShell and run `ipconfig` – look for the IPv4 address of your Wi‑Fi/Ethernet adapter.

### 2. Port forward (if using WSL2)

In an **elevated PowerShell** on Windows:

```powershell
netsh interface portproxy add v4tov4 listenport=5000 listenaddress=0.0.0.0 connectport=5000 connectaddress=<WSL_IP>
New-NetFirewallRule -DisplayName "CAPTCHA Lab" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

Now test devices on your LAN can reach `http://<WINDOWS_HOST_IP>:5000/`.

**After your demo, remove the rules:**

```powershell
netsh interface portproxy delete v4tov4 listenport=5000 listenaddress=0.0.0.0
Remove-NetFirewallRule -DisplayName "CAPTCHA Lab"
```

> **Note:** For HTTPS testing, consider using `mkcert` + a reverse proxy or Flask's `--cert=adhoc` (requires `pyOpenSSL`).

---

## 🖥️ Operator Dashboard

Login at `http://<lab-ip>:5000/dashboard` with the credentials set in your environment (or the default).

### Dashboard Features

- **Sessions table** – see all active sessions with status, camera/location permissions, photo thumbnails, and a **Replay** button.
- **Terminal console** – run whitelisted CLI commands directly:
  - `sessions`
  - `status <session_id>`
  - `capture-result <session_id>`
  - `replay <session_id>`
- **Audit log** – every action is recorded with timestamps.
- **Clear All Data** – resets the entire lab.

---

## 🧰 CLI Tool (`cli.py`)

Use the command-line interface for quick inspection and automation.

```bash
python cli.py help
```

Available commands:

| Command | Description |
|---------|-------------|
| `sessions` | List all active sessions |
| `status <session_id>` | Show detailed session info |
| `capture-result <session_id>` | Download the captured image (saves as `capture_<session_id>.jpg`) |
| `replay <session_id>` | Generate a synthetic replay image for the session |

Example:

```bash
python cli.py status LAB-abc123
python cli.py capture-result LAB-abc123   # saves image locally
```

---

## 🔐 Security & Configuration

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `LAB_MODE` | `true` | Disables the application if set to `false` (safety gate) |
| `ADMIN_USER` | `admin` | Dashboard username |
| `ADMIN_PASS` | `labpass123` | Dashboard password (change in production!) |
| `PORT` | `5000` | Port the Flask server listens on |

> **⚠️ IMPORTANT:** For any real training environment, **change the default password** and use HTTPS.

---

## 📁 Project Structure

```
captcha-lab/
├── app.py                # Main Flask application
├── cli.py                # Command-line interface tool
├── requirements.txt
├── settings.json         # (optional) for VSCode Live Server
├── templates/
│   ├── captcha.html      # The CAPTCHA page
│   ├── dashboard.html    # Operator dashboard
│   └── login.html        # Dashboard login page
├── static/
│   ├── css/
│   │   └── style.css
│   └── images/
│       └── recaptcha.png
├── data/
│   └── captures/         # Captured images are stored here
└── logs/                 # Per‑session JSON and TXT logs (auto‑generated)
```

---

## 🔧 API Endpoints (for developers)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/captcha/verify` | POST | Simulates CAPTCHA verification (delay 0.5–1.5s) |
| `/api/photo` | POST | Receives the captured photo (validates MIME/size) |
| `/api/location` | POST | Receives GPS coordinates |
| `/api/permission_denied` | POST | Logs when a permission is denied |
| `/api/dashboard/sessions` | GET | (Auth) List all sessions |
| `/api/dashboard/logs` | GET | (Auth) Fetch audit log |
| `/api/dashboard/replay` | POST | (Auth) Generate synthetic replay for a session |
| `/api/cli/status/<sid>` | GET | Get session details (for CLI) |
| `/api/cli/capture-result/<sid>` | GET | Get base64-encoded image (for CLI) |
| `/api/cli/replay/<sid>` | GET | Trigger replay (for CLI) |
| `/api/clear_all` | POST | (Auth) Delete all sessions and files |
| `/api/delete` | POST | (Auth) Delete current session |

All public endpoints have **rate limiting** (max 30 requests per minute per IP).

---

## 🧪 Testing & Troubleshooting

### Camera / geolocation not working over HTTP on a LAN IP?

Most browsers block these APIs on non‑HTTPS origins except `localhost`.  
**Workarounds**:
- Use Chrome's `--unsafely-treat-insecure-origin-as-secure` flag (for testing).
- Use a self‑signed certificate with Flask (add `--cert=adhoc` if you have `pyOpenSSL`).
- Use `ngrok` or a local HTTPS reverse proxy.

### Permission prompt never appears?

Check browser site settings → reset permissions for the lab URL.

### Camera preview is black?

- Ensure no other app is using the camera (close Teams, Zoom, etc.).
- On laptops, open the physical privacy shutter.

### Location accuracy is low?

Indoor GPS is often imprecise – this is a good talking point for the demo.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.  
Keep in mind that this is a **security‑awareness tool** – all contributions must respect the ethical guidelines and not introduce any bypass or data‑harvesting features.

---

## ⚠️ Important Disclaimer

**This software is provided for educational and training purposes only.**  
The authors assume no liability for any misuse or damage caused by this software. You are solely responsible for complying with all applicable laws and regulations in your jurisdiction. Always obtain explicit, informed consent from participants before running any simulation.
