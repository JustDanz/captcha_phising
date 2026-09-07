# captcha-lab — Security Awareness CAPTCHA Simulation

> **AUTHORIZED SECURITY AWARENESS LAB — FOR TRAINING/DEMO USE ONLY**
> Use only on devices you own, or with participants who have given explicit,
> informed consent as part of a security-awareness training session. Do not
> deploy this outside a controlled lab network. Do not use it to target
> people without consent — that would be illegal in most jurisdictions.

## What this demonstrates

A fake "Security Verification" (CAPTCHA-style) page that, once the
participant clicks **"I'm not a robot"**, asks the browser for **camera** and
**location** permissions using the standard, user-visible browser permission
prompts. If the participant grants them, the demo:

1. Takes **one** photo (only after the user clicks "Capture Photo").
2. Reads the device's GPS coordinates via the Geolocation API.
3. Sends that data back to the local Flask server.
4. Shows results in the operator's terminal in real time.
5. Saves results to `logs/<session_id>.json` and `logs/<session_id>.txt`.
6. Shows a live dashboard at `/dashboard`.

**This is not credential phishing.** There is no login form, no password
field, no OTP/token field, and no cookie/session harvesting anywhere in this
project. It only shows what over-permissive browser grants can expose.

## What this does NOT do (by design)

- No permission bypass — 100% standard `getUserMedia()` / `getCurrentPosition()`
  browser prompts that the user must explicitly accept.
- No stealth capture, no background access, no persistence.
- No password/cookie/token/clipboard/file-system access.
- No keylogging.
- No data sent anywhere outside your lab network (server runs locally; there
  are no external API calls).
- Refuses to start unless `LAB_MODE=true` (the default).

---

## 1. Installation (Kali Linux / WSL)

```bash
# From inside your Kali WSL shell:
cd ~
git clone <your-repo-or-copy-this-folder> captcha-lab
cd captcha-lab

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt`:
```
Flask==3.0.3
qrcode==7.4.2
Pillow==10.4.0
```

## 2. Running the server

```bash
export LAB_MODE=true      # default; can be omitted
python3 app.py
```

On startup the server will:
- Print an ASCII QR code directly in the terminal.
- Save a QR code image to `qr/captcha-demo.png`.
- Print the lab URL, e.g. `http://192.168.1.42:5000/`.
- Print the dashboard URL, e.g. `http://192.168.1.42:5000/dashboard`.

## 3. Getting your WSL IP address (for the lab URL)

WSL2 has its own virtual network adapter, so `localhost` on WSL is not always
reachable from other devices (like a test phone) on your LAN. Steps:

```bash
# Inside WSL, get the WSL-internal IP:
ip addr show eth0 | grep inet

# Get your Windows host's LAN IP (the one your phone should actually use):
# Run this in PowerShell on Windows, not inside WSL:
ipconfig
# Look for "IPv4 Address" under your active Wi-Fi/Ethernet adapter.
```

If your test devices are on the same Wi-Fi as your Windows host, you
generally want to reach the server via the **Windows host's LAN IP**, with
traffic forwarded into WSL (see next section).

## 4. Port forwarding (WSL → LAN), lab network only

WSL2's NAT networking means external devices can't directly hit the WSL IP.
Forward the port from Windows to WSL using `netsh` (run as Administrator in
PowerShell on Windows):

```powershell
# Get the current WSL IP first (run inside WSL): ip addr show eth0 | grep inet
# Then, in an elevated PowerShell:
netsh interface portproxy add v4tov4 listenport=5000 listenaddress=0.0.0.0 connectport=5000 connectaddress=<WSL_IP>

# Allow the port through Windows Firewall (also elevated PowerShell):
New-NetFirewallRule -DisplayName "CAPTCHA Lab Demo" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

Now test devices on your LAN can reach `http://<WINDOWS_HOST_LAN_IP>:5000/`.

**Important:** Only do this on an isolated/controlled lab Wi-Fi network for
the duration of the demo. Remove the portproxy rule and firewall rule
afterward:

```powershell
netsh interface portproxy delete v4tov4 listenport=5000 listenaddress=0.0.0.0
Remove-NetFirewallRule -DisplayName "CAPTCHA Lab Demo"
```

If your test device is on the *same* network as WSL is bridged to (e.g. you
use `mirrored` networking mode in `.wslconfig` on newer WSL versions), you
may be able to skip port forwarding entirely — test by browsing to the
printed lab URL directly from your phone first.

## 5. Scanning the QR Code

- Run `python3 app.py` — the terminal will render an ASCII QR code and also
  save `qr/captcha-demo.png`.
- Display the terminal or open the PNG file, and have the **authorized test
  device** scan it with its camera app.
- Alternatively, project `qr/captcha-demo.png` on a screen during your
  presentation.

## 6. Project structure

```
captcha-lab/
├── app.py
├── requirements.txt
├── templates/
│   ├── captcha.html
│   └── dashboard.html
├── static/
│   ├── css/style.css
│   └── js/capture.js
├── captures/         # captured photos land here
├── logs/             # per-session .json and .txt logs
├── qr/               # generated QR code image
└── README.md
```

## 7. Data collected (and only this)

| Field | Description |
|---|---|
| `session_id` | Random per-session demo ID (e.g. `DEMO-8F21A`) |
| `timestamp` | ISO timestamp |
| `ip_address` | Requesting device's IP (from the HTTP request) |
| `user_agent` | Browser User-Agent string |
| `camera_permission` | true/false — whether camera was granted |
| `location_permission` | true/false — whether location was granted |
| `latitude` / `longitude` / `accuracy` | From Geolocation API, post-consent |
| `captured_image` | Filename of the single photo taken |

No passwords, cookies, tokens, clipboard contents, file listings, or other
personal data are ever collected.

## 8. Troubleshooting camera / geolocation permissions

- **Browser blocks camera/geolocation over plain HTTP on a non-localhost
  address**: Most modern browsers only allow `getUserMedia()` and
  `getCurrentPosition()` on `https://` or `http://localhost`. Since this demo
  uses a LAN IP over HTTP, you have two options:
  1. On Chrome/Edge (desktop, for a quick demo), you can add your lab IP to
     the insecure-origins allowlist for testing:
     `chrome://flags/#unsafely-treat-insecure-origin-as-secure` → add
     `http://<lab-ip>:5000` → relaunch.
  2. For a more realistic/portable demo, put a self-signed TLS certificate in
     front of Flask (e.g. via `flask run --cert=adhoc` using `pyOpenSSL`, or
     a local reverse proxy like `mkcert` + Caddy/nginx) and use `https://`.
- **Permission prompt never appears**: Check that the site isn't already
  blocked from a previous test (browser site settings → reset permissions
  for the lab URL).
- **Camera preview is black**: Some laptops need the physical camera
  privacy shutter opened, or another app (e.g. Zoom, Teams) may be holding
  the camera device — close other apps using the camera.
- **Location accuracy is very low / inaccurate**: Indoor GPS is often
  imprecise; `accuracy` (in meters) reflects this, which itself is a good
  talking point about how Wi-Fi/GPS-based location can vary in quality.
- **Server unreachable from phone**: Re-check the port-forwarding step and
  confirm both devices are on the same lab network, and that Windows
  Firewall/Kali's `ufw` (if enabled) isn't blocking port 5000.

## 9. Demo script (~4 minutes)

| Time | Action |
|---|---|
| 00:00 | Run `python3 app.py` on Kali/WSL. Explain this is a controlled, consent-based simulation. |
| 00:30 | Show the QR code (terminal ASCII or `qr/captcha-demo.png`) and the printed lab URL. |
| 01:00 | Participant scans the QR code with their test device. |
| 01:30 | The fake CAPTCHA ("Security Verification" / "I'm not a robot") appears — point out there's no login form. |
| 02:00 | Participant clicks the button; browser prompts for camera and location permissions. Emphasize these are the browser's own real prompts. |
| 02:30 | Participant clicks "Capture Photo"; the image is sent to the server. |
| 03:00 | Latitude/longitude/accuracy appear in the operator terminal in real time. |
| 03:30 | Show the saved `logs/<id>.json` / `.txt` files and the live `/dashboard` view with the photo thumbnail and Google Maps link. |
| 04:00 | Wrap-up: discuss social-engineering risk — why users should scrutinize *why* a page wants camera/location, and how attackers exploit trust in familiar UI patterns like CAPTCHAs. |

## 10. Consent & ethics checklist before running

- [ ] All participants know in advance they'll take part in a security-awareness demo.
- [ ] Only your own devices or devices of consenting participants are used.
- [ ] The server only runs on an isolated/controlled lab network.
- [ ] `LAB_MODE=true` is set (default).
- [ ] Captured photos/logs are deleted after the training session concludes.
- [ ] You have permission from your organization/venue to run this demo.
