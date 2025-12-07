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

// ======================= CAMERA TOGGLE FUNCTIONALITY ============================
// Simple and direct approach for camera toggle
const toggleButton = document.getElementById('camera-toggle');
const toggleText = document.getElementById('toggle-text');
const videoElement = document.getElementById('camera-video');

let isCameraOn = true;
let stream = null;

// ======================= START CAMERA ============================
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });

    if (videoElement) {
      videoElement.srcObject = stream;
      videoElement.style.display = 'block';
    }

    const errorElement = document.getElementById('camera-error');
    if (errorElement) {
      errorElement.style.display = 'none';
    }
  } catch (error) {
    console.error('Camera access error:', error);
    const errorElement = document.getElementById('camera-error');
    if (errorElement) {
      errorElement.style.display = 'flex';
      const errorText = errorElement.querySelector('.error-text');
      if (errorText) {
        if (error.name === 'NotAllowedError') {
          errorText.textContent = 'Camera access denied. Please allow camera access.';
        } else if (error.name === 'NotFoundError') {
          errorText.textContent = 'No camera found on this device.';
        } else {
          errorText.textContent = 'Camera access unavailable. Please check your device.';
        }
      }
    }
  }
}

// ======================= STOP CAMERA ============================
function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }
}

// ======================= TOGGLE CAMERA BUTTON CLICK HANDLER ============================
console.log('Toggle button element:', toggleButton);
console.log('Toggle text element:', toggleText);

if (toggleButton && toggleText) {
  toggleButton.addEventListener('click', function(e) {
    e.preventDefault();
    console.log('Button clicked! Current state - isCameraOn:', isCameraOn);
    
    if (isCameraOn) {
      // Turn OFF
      stopCamera();
      isCameraOn = false;
      toggleButton.classList.add('off');
      toggleText.textContent = 'OFF';
      console.log('Changed to OFF');
      if (videoElement) {
        videoElement.style.display = 'none';
      }
    } else {
      // Turn ON
      startCamera();
      isCameraOn = true;
      toggleButton.classList.remove('off');
      toggleText.textContent = 'ON';
      console.log('Changed to ON');
    }
  });
  console.log('Click listener attached to toggle button');
} else {
  console.error('Toggle button or text not found!');
  console.error('toggleButton:', toggleButton);
  console.error('toggleText:', toggleText);
}

// Start camera on page load
startCamera();

// Stop camera on page close
window.addEventListener('beforeunload', stopCamera);
window.addEventListener('visibilitychange', () => {
  if (document.hidden) stopCamera();
  else startCamera();
});


// ======================= CAMERA + SDK CONFIG MODULE ============================
(function () {
  // ======================= CACHE DOM ELEMENTS FOR SDK ============================
  const cameraTitle = document.getElementById('camera-title');
  const timestamp = document.getElementById('timestamp');
  const dashboardHeader = document.querySelector('.staff-header') || document.querySelector('.dashboard-header');
  const cameraScreen = document.querySelector('.camera-screen');
  const homeIcon = document.querySelector('.home-icon');

  // ======================= APPLY CONFIG ============================
  function onConfigChange(config) {
    const cfg = { ...defaultConfig, ...config };

    const baseFont = cfg.font_family || defaultConfig.font_family;
    const baseSize = Number(cfg.font_size || defaultConfig.font_size) || 16;

    const fontStack = `${baseFont}, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`;

    if (dashboardHeader) {
      dashboardHeader.style.background =
        `linear-gradient(135deg, ${cfg.background_color} 0%, ${cfg.primary_action_color} 100%)`;
    }

    if (cameraScreen) {
      cameraScreen.style.backgroundColor = cfg.surface_color;
    }
    if (cameraTitle) {
      cameraTitle.style.color = cfg.text_color;
      cameraTitle.textContent = cfg.camera_label || defaultConfig.camera_label;
      cameraTitle.style.fontSize = `${baseSize * 1.125}px`;
    }

    document.body.style.fontFamily = fontStack;
    if (timestamp) {
      timestamp.style.fontSize = `${baseSize * 0.75}px`;
    }
  }

  // ======================= SDK CAPABILITIES ============================
  function mapToCapabilities(config) {
    const cfg = { ...defaultConfig, ...config };
    return {
      recolorables: [
        { get: () => cfg.background_color, set: v => window.elementSdk?.setConfig({ background_color: v }) },
        { get: () => cfg.surface_color, set: v => window.elementSdk?.setConfig({ surface_color: v }) },
        { get: () => cfg.text_color, set: v => window.elementSdk?.setConfig({ text_color: v }) },
        { get: () => cfg.primary_action_color, set: v => window.elementSdk?.setConfig({ primary_action_color: v }) },
        { get: () => cfg.secondary_action_color, set: v => window.elementSdk?.setConfig({ secondary_action_color: v }) }
      ],
      borderables: [],
      fontEditable: {
        get: () => cfg.font_family,
        set: v => window.elementSdk?.setConfig({ font_family: v })
      },
      fontSizeable: {
        get: () => cfg.font_size,
        set: v => window.elementSdk?.setConfig({ font_size: v })
      }
    };
  }

  // ======================= SDK PANEL VALUES ============================
  function mapToEditPanelValues(config) {
    const cfg = { ...defaultConfig, ...config };
    return new Map([
      ["dashboard_title", cfg.dashboard_title],
      ["camera_label", cfg.camera_label]
    ]);
  }

  // ======================= INIT SDK ============================
  if (window.elementSdk && typeof window.elementSdk.init === "function") {
    window.elementSdk.init({
      defaultConfig,
      onConfigChange,
      mapToCapabilities,
      mapToEditPanelValues
    });
  } else {
    onConfigChange(defaultConfig);
  }

  // ======================= HOME ICON ANIMATION ============================
  if (homeIcon) {
    homeIcon.addEventListener('click', () => {
      homeIcon.style.transform = 'scale(0.95)';
      setTimeout(() => {
        homeIcon.style.transform = 'scale(1)';
      }, 150);
    });
  }

})();