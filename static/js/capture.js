/*
 * capture.js
 * AUTHORIZED SECURITY AWARENESS LAB
 *
 * This script ONLY uses standard, user-consented browser APIs:
 *   - navigator.mediaDevices.getUserMedia()  (camera)
 *   - navigator.geolocation.getCurrentPosition() (location)
 *
 * No permission bypass, no stealth capture, no background access.
 * The camera preview is shown to the user, and a photo is only taken
 * when the user explicitly clicks "Capture Photo".
 */

let sessionId = null;
let mediaStream = null;

const verifyBtn = document.getElementById('verify-btn');
const captureBtn = document.getElementById('capture-btn');
const stepInitial = document.getElementById('step-initial');
const stepPermissions = document.getElementById('step-permissions');
const stepDone = document.getElementById('step-done');
const preview = document.getElementById('preview');
const statusEl = document.getElementById('status');

function setStatus(msg) {
  statusEl.textContent = msg;
}

async function startSession() {
  const res = await fetch('/api/new-session', { method: 'POST' });
  const data = await res.json();
  sessionId = data.session_id;
}

async function reportPermission(permission, granted) {
  await fetch('/api/permission-update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, permission, granted })
  });
}

async function requestCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
    preview.srcObject = mediaStream;
    preview.classList.remove('hidden');
    captureBtn.classList.remove('hidden');
    await reportPermission('camera', true);
    setStatus('Camera access granted. Please press "Capture Photo" to continue.');
  } catch (err) {
    await reportPermission('camera', false);
    setStatus('Camera permission was not granted. Verification cannot continue.');
  }
}

function requestLocation() {
  if (!navigator.geolocation) {
    setStatus('Geolocation not supported by this browser.');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      await fetch('/api/location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy
        })
      });
    },
    async (err) => {
      await reportPermission('location', false);
      setStatus('Location permission was not granted.');
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

async function capturePhoto() {
  const canvas = document.createElement('canvas');
  canvas.width = preview.videoWidth;
  canvas.height = preview.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(preview, 0, 0);

  canvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('photo', blob, `${sessionId}.jpg`);

    await fetch('/api/photo', { method: 'POST', body: formData });

    // Stop camera stream immediately after capture — no lingering access.
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
    }

    stepPermissions.classList.add('hidden');
    stepDone.classList.remove('hidden');
  }, 'image/jpeg', 0.9);
}

verifyBtn.addEventListener('click', async () => {
  verifyBtn.disabled = true;
  await startSession();

  stepInitial.classList.add('hidden');
  stepPermissions.classList.remove('hidden');
  setStatus('Requesting camera permission...');

  await requestCamera();
  setStatus('Requesting location permission...');
  requestLocation();
});

captureBtn.addEventListener('click', capturePhoto);
