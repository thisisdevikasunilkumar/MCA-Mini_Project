function handleCheckOut() {
    const logoutButton = document.getElementById('logout-button');
    const logoutUrl = logoutButton.dataset.logoutUrl;
    const loginUrl = logoutButton.dataset.loginUrl;

    // 1. Get the email value from the hidden input (which now has the email)
    const userEmailInput = document.getElementById('userEmail'); 
    const userEmail = userEmailInput ? userEmailInput.value : null;

    // 2. Get the CSRF token
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const logoutData = {
        email: userEmail
    };
    
    if (!confirm("Are you sure you want to Check Out?")) {
        return;
    }

    fetch(logoutUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify(logoutData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Extract overtime message cleanly
            const overtimeMessage = data.message.includes('Overtime: ') ? 
                                    data.message.split('Overtime: ')[1] : '0.00 hours';
            
            alert("Check Out Successful! Overtime: " + overtimeMessage);
            
            // Redirect to the login/register page after successful logout
            window.location.href = loginUrl;
        } else {
            alert("Check Out Failed: " + data.error);
            console.error('Logout Error:', data.error);
        }
    })
    .catch(error => {
        alert("An error occurred during check out.");
        console.error('Fetch error:', error);
    });
}

// ======================= CACHE DOM ELEMENTS & CONFIG ============================
const toggleButton = document.getElementById('camera-toggle');
const toggleText = document.getElementById('toggle-text');
const videoElement = document.getElementById('camera-video');
const canvas = document.getElementById('emotion-canvas');
const context = canvas ? canvas.getContext('2d') : null;

let isCameraOn = true;
let stream = null;
let captureIntervalId = null;
const CAPTURE_INTERVAL_MS = 5000; // 5 seconds interval for emotion detection
const API_URL = '/accounts/record-emotion/'; // **Adjust this URL path as per your Django setup**


// ======================= CSRF TOKEN HELPER (for Django POST requests) ============================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');


// ======================= EMOTION CAPTURE FUNCTIONS ============================

async function sendFrameForEmotionDetection(base64Image) {
    if (!base64Image) return;

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken, 
            },
            body: JSON.stringify({ image: base64Image })
        });

        const data = await response.json();
        console.log('Emotion Detection Response:', data);

    } catch (error) {
        console.error('Error sending frame to API:', error);
    }
}

function captureAndSendFrame() {
    // Safety check: Ensure camera is on and ready
    if (!isCameraOn || !videoElement || videoElement.videoWidth === 0 || !context || !canvas) {
        return;
    }

    // Set canvas dimensions to match video
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;

    // Draw the current video frame onto the canvas
    context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    // Get the image data as a Base64 string (JPEG format)
    const base64Image = canvas.toDataURL('image/jpeg', 0.8);

    // Send the data to the Django API
    sendFrameForEmotionDetection(base64Image);
}

function startEmotionCapture() {
    if (captureIntervalId) {
        clearInterval(captureIntervalId);
    }
    captureIntervalId = setInterval(captureAndSendFrame, CAPTURE_INTERVAL_MS);
    console.log('Emotion capture started.');
}

function stopEmotionCapture() {
    if (captureIntervalId) {
        clearInterval(captureIntervalId);
        captureIntervalId = null;
    }
    console.log('Emotion capture stopped.');
}


// ======================= CAMERA START/STOP ============================

async function startCamera() {
    try {
        // Request media access with constraints
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false
        });

        if (videoElement) {
            videoElement.srcObject = stream;
            videoElement.style.display = 'block';
            
            // Start emotion capture after the video metadata is loaded
            videoElement.onloadedmetadata = () => {
                 startEmotionCapture();
                 videoElement.onloadedmetadata = null; 
            };
        }

        const errorElement = document.getElementById('camera-error');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    } catch (error) {
        console.error('Camera access error:', error);
        stopEmotionCapture(); 
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    stopEmotionCapture(); // Stop emotion detection
}


// ======================= TOGGLE HANDLER & LIFECYCLE ============================
if (toggleButton && toggleText) {
    toggleButton.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (isCameraOn) {
            // Turn OFF
            stopCamera();
            isCameraOn = false;
            toggleButton.classList.add('off');
            toggleText.textContent = 'OFF';
            if (videoElement) {
                videoElement.style.display = 'none';
            }
        } else {
            // Turn ON
            startCamera();
            isCameraOn = true;
            toggleButton.classList.remove('off');
            toggleText.textContent = 'ON';
        }
    });
} 

// Start camera on page load
startCamera();

// Handle tab close/switch/navigation
window.addEventListener('beforeunload', stopCamera);


// *** പ്രധാന മാറ്റം: background/minimize ചെയ്യുമ്പോൾ ക്യാമറ നിർത്തുന്നത് ഒഴിവാക്കുന്നു ***
window.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // ബ്രൗസർ ടൈമറുകൾ കുറയ്ക്കാൻ സാധ്യതയുണ്ട്, പക്ഷെ ക്യാമറ സ്റ്റോപ്പ് ചെയ്യുന്നില്ല.
        console.log("Tab hidden. Attempting to continue detection in background...");
    } 
    
    // ടാബ് വീണ്ടും foreground-ൽ വരുമ്പോൾ:
    if (!document.hidden && isCameraOn) {
        console.log("Tab returned to foreground. Re-starting camera if paused.");
        // ക്യാമറ സ്ട്രീം ബ്രൗസർ നിർത്തിയിട്ടുണ്ടെങ്കിൽ വീണ്ടും startCamera() വിളിക്കുന്നത് അതിനെ ഉണർത്തും.
        startCamera(); 
    }
});