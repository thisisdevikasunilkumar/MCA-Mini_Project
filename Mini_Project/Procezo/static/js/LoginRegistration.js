/* -------------------- Form Toggle (Register / Login) -------------------- */
const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

if (registerBtn) registerBtn.addEventListener('click', () => container.classList.add('active'));
if (loginBtn) loginBtn.addEventListener('click', () => container.classList.remove('active'));

// ------------------------ AUTO FILL STAFF DETAILS ------------------------
document.getElementById("reg-staff-id").addEventListener("blur", function () {
    let staffID = this.value.trim();
    if (!staffID) return;

    fetch(`/accounts/get_staff_details/?staff_ID=${encodeURIComponent(staffID)}`)
        .then(res => res.json())
        .then(data => {
            if (data.exists) {
                // Auto-fill fields
                document.getElementById("reg-name").value = data.name || "";
                document.getElementById("reg-email").value = data.email || "";
                document.getElementById("reg-role").value = data.role || "";
                document.getElementById("reg-job").value = data.job_type || "";
            } else {
                // Clear fields
                document.getElementById("reg-name").value = "";
                document.getElementById("reg-email").value = "";
                document.getElementById("reg-role").value = "";
                document.getElementById("reg-job").value = "";

                // ❗ Show alert when ID is invalid
                alert("❌ Invalid Staff ID. Please enter a valid one.");
            }
        })
        .catch(err => console.log("Auto-fill error:", err));
});


/* -------------------- Elements for camera modal and capture -------------------- */ 
const cameraBox = document.getElementById("camera-box");
const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const captureBtn = document.getElementById("camera-capture-Image");
const closeBtn = document.getElementById("camera-close");
const openCameraBtnRegister = document.getElementById('open-camera-btn-register');
const openCameraBtnLogin = document.getElementById('open-camera-btn-login');

let currentMode = null; // "register" or "login"
let streamRef = null;
let isFaceCaptured = false;
let redirectUrl = null;

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Open camera and start video stream
function openCamera(mode) {
    currentMode = mode;
    cameraBox.style.display = 'block';

    // prefer smaller resolution to speed up processing
    const constraints = {
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false
    };

    navigator.mediaDevices.getUserMedia(constraints)
        .then(stream => {
            streamRef = stream;
            video.srcObject = stream;
            video.play();
        })
        .catch(err => {
            alert("Camera access required: " + err.message);
        });
}

// Close camera and stop video stream
function closeCamera() {
    cameraBox.style.display = 'none';
    if (streamRef) {
        streamRef.getTracks().forEach(t => t.stop());
        streamRef = null;
    }

    // Reset state on close
    isFaceCaptured = false;
    redirectUrl = null;
    if (captureBtn) {
        captureBtn.textContent = 'Capture Image';
        video.style.display = 'block';
        canvas.style.display = 'none';
    }
}

// Open camera buttons  
if (openCameraBtnRegister) openCameraBtnRegister.addEventListener('click', () => openCamera('register'));
if (openCameraBtnLogin) openCameraBtnLogin.addEventListener('click', () => openCamera('login'));
if (closeBtn) closeBtn.addEventListener('click', closeCamera);

// Capture button handler
if (captureBtn) captureBtn.addEventListener('click', () => {
    // This button is now only for capturing, not for the second-step login.
    if (isFaceCaptured) {
        // This state should ideally not be reached as the button is in a modal
        // that closes. But as a safeguard:
        return; 
    }

    if (!video.videoWidth) {
        alert("Camera not ready");
        return;
    }

    // force a square or moderate size for reliability
    const targetWidth = 480;
    const targetHeight = Math.round(targetWidth * video.videoHeight / video.videoWidth);

    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // compress quality to reduce payload if needed (0.8)
    const dataURL = canvas.toDataURL('image/jpeg', 0.8);

    // quick debug
    console.log("Captured length:", dataURL.length);

    fetch('/accounts/api/check-face/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ image: dataURL })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert("Face API error: " + data.error);
            return;
        }
        const count = data.face_count || 0;
        if (count !== 1) {
            alert("❌ Please ensure exactly face is visible. Detected: " + count);
            return;
        }

        // Registration flow
        if (currentMode === 'register') {

            const staffID = document.getElementById('reg-staff-id')?.value || "";
            const name = document.getElementById('reg-name')?.value || "";
            const email = document.getElementById('reg-email')?.value || "";
            const role = document.getElementById('reg-role')?.value || "";
            const job_type = document.getElementById('reg-job')?.value || "";
            const profile_image = document.getElementById('profile-image-input')?.value || "";

            fetch('/accounts/register/', {
                method: 'POST',
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie('csrftoken'),
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify({
                    staff_ID: staffID,
                    name: name,
                    email: email,
                    role: role,
                    job_type: job_type,
                    image: dataURL,             // live captured
                    profile_image: profile_image // uploaded profile image
                })
            })
            .then(res => res.json())
            .then(resp => {
                
                // Face mismatch / other backend errors
                if (!resp.success) {
                    alert(resp.error || "❌ Face mismatch detected!");
                    return;
                }

                // Success
                alert("😎 Face captured successfully! Now click the REGISTER button.");
                document.getElementById("captured-image-input").value = dataURL;
                closeCamera();
            });
        }

        // Login flow
        else if (currentMode === 'login') {
            const email = (document.getElementById('login-email') || {}).value || '';
            fetch('/accounts/api/face-login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ image: dataURL, email: email })
            })
            .then(r => r.json())
            .then(resp => {
                if (resp.success) {
                    redirectUrl = resp.redirect;
                    isFaceCaptured = true;
                    alert(`🎉 Welcome back, ${resp.name}! Now submit the login button. Redirecting to your dashboard...`);
                    // keep camera modal hidden but keep state for final submit
                    cameraBox.style.display = 'none';
                    if (streamRef) {
                        streamRef.getTracks().forEach(t => t.stop());
                        streamRef = null;
                    }
                } else {
                    alert("Login failed: " + (resp.error || 'Unknown'));
                    closeCamera();
                }
            })
            .catch(e => {
                alert("Login error: " + e);
                closeCamera();
            });
        }
    })
    .catch(err => {
        alert("Face check request failed: " + err);
    });
});

// Normal password login form submit handler (with face 2nd step) 
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();

        // Check if this is the second step of face login
        if (isFaceCaptured && redirectUrl) {
            window.location.href = redirectUrl;
            return;
        }

        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password') ? document.getElementById('login-password').value : '';
        fetch('/accounts/api_login_with_password/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: `email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`
        })
        .then(r => r.json())
        .then(resp => {
            if (resp.success) {
                if (resp.face_required) {
                    // This is a staff member with a correct password.
                    alert("⚠ Staff must complete face recognition to log in!");
                    // The email field is already filled, so we can open the camera.
                    openCamera('login'); 
                } else if (resp.redirect) {
                    // This is a successful admin login.
                    window.location.href = resp.redirect;
                }
            } else {
                alert("Login failed: " + (resp.error || 'Unknown'));
            }
        })
        .catch(err => alert("Login error: " + err));
    });
}