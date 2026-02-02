// ======================= TASK DATA ============================
const tasks = [
  { id: 1, completed: false },
  { id: 2, completed: false },
  { id: 3, completed: false }
];

// Helper
function findTask(id) {
  return tasks.find(t => t.id === Number(id));
}

// ======================= UPDATE CHECKBOX UI ============================
function updateTaskCheckboxes() {
  document.querySelectorAll('.task-checkbox').forEach(cb => {
    const id = cb.getAttribute('data-id');
    const task = findTask(id);
    if (!task) return;

    if (task.completed) {
      cb.classList.add('checked');
      cb.innerText = '✓';
      cb.setAttribute('aria-checked', 'true');
      cb.parentElement.setAttribute('aria-checked', 'true');
    } else {
      cb.classList.remove('checked');
      cb.innerText = '';
      cb.setAttribute('aria-checked', 'false');
      cb.parentElement.setAttribute('aria-checked', 'false');
    }
  });
}

// ======================= MENU ACTIVE STATE ============================
document.querySelectorAll('.menu-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
    item.classList.add('active');
  });
});

// ======================= CHECKBOX CLICK ============================
function toggleTaskById(id) {
  const task = findTask(id);
  if (!task) return;
  task.completed = !task.completed;
  updateTaskCheckboxes();
}

document.addEventListener('click', (e) => {
  const cb = e.target.closest('.task-checkbox');
  if (cb) {
    e.stopPropagation();
    toggleTaskById(cb.getAttribute('data-id'));
  }
});

// ======================= ROW CLICK ============================
document.querySelectorAll('.task-item').forEach(row => {
  row.addEventListener('click', () => {
    const id = row.getAttribute('data-id');
    toggleTaskById(id);
  });

  const checkbox = row.querySelector('.task-checkbox');
  if (checkbox) {
    checkbox.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        toggleTaskById(checkbox.getAttribute('data-id'));
      }
    });
  }
});

// ======================= CURRENT DATE TIME ============================
function updateDateTime() {
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });
  const timeStr = now.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit'
  });

  const dateEl = document.getElementById('current-date');
  if (dateEl) {
    dateEl.textContent = dateStr;
  }
  
  const timeEl = document.getElementById('current-time');
  if (timeEl) {
    timeEl.textContent = timeStr;
  }
}

document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('current-date') || document.getElementById('current-time')) {
        updateDateTime();
        setInterval(updateDateTime, 1000);
    }
    
    if (document.querySelector('.task-checkbox')) {
        updateTaskCheckboxes();
    }
});

// ======================= MEETING MODAL ============================
let currentButton = null;

function addMeetingLink(button) {
  currentButton = button;

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal-content">

      <div class="modal-header">
        <h3>Add Meeting Details</h3>
        <p style="margin:0;color:#6b7280;font-size:.95rem;">Fill in the meeting info below</p>
      </div>

      <div class="modal-input-group">
        <label>Job Type</label>
        <select id="job-type-select" class="modal-select-input">
          <option value="">Select Job Type</option>
        </select>
      </div>

      <div class="modal-input-group">
        <label>Meeting Time</label>
        <input type="time" id="meeting-time-input" class="modal-input">
      </div>

      <div class="modal-input-group">
        <label>Meeting Title</label>
        <input type="text" id="meeting-title-input" class="modal-input" placeholder="Team Meeting">
      </div>

      <div class="modal-input-group">
        <label>Description</label>
        <input type="text" id="meeting-desc-input" class="modal-input" placeholder="Meeting description">
      </div>

      <div class="modal-input-group">
        <label>Meeting Link</label>
        <input type="url" id="meeting-link-input" class="modal-input" placeholder="https://meet.google.com/xxx-xxxx-xxx">
      </div>

      <div class="modal-actions">
        <button class="modal-btn modal-btn-cancel" id="modalCancel">Cancel</button>
        <button class="modal-btn modal-btn-save" id="modalSave">Save</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // UNIQUE JOB TYPES
  const jobSelect = modal.querySelector('#job-type-select');
  [...new Set(staffData.map(s => s.job_type))].forEach(job => {
    jobSelect.innerHTML += `<option value="${job}">${job}</option>`;
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  document.getElementById('modalCancel').addEventListener('click', closeModal);
  document.getElementById('modalSave').addEventListener('click', saveMeetingLink);
}

function closeModal() {
  const modal = document.querySelector('.modal-overlay');
  if (modal) modal.remove();
  currentButton = null;
}

// URL validation
function isValidUrl(value) {
  try { new URL(value); return true; }
  catch { return false; }
}

// ======================= SAVE MEETING (AJAX TO DJANGO) ============================
function saveMeetingLink() {
  const jobType = document.getElementById('job-type-select').value.trim();
  const time = document.getElementById('meeting-time-input').value.trim();
  const title = document.getElementById('meeting-title-input').value.trim();
  const desc = document.getElementById('meeting-desc-input').value.trim();
  const link = document.getElementById('meeting-link-input').value.trim();

  if (!jobType || !time || !title || !desc || !link) {
    alert("Please fill all fields");
    return;
  }

  if (!isValidUrl(link)) {
    alert("Enter valid URL");
    return;
  }

  // ================= AJAX SAVE =================
  fetch("/accounts/save-meeting/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      job_type: jobType,
      meet_time: time,
      meet_title: title,
      meet_description: desc,
      meet_link: link
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert("Meeting saved successfully!");
      closeModal();
    } else {
      alert("Failed to save meeting.");
    }
  })
  .catch(err => console.error(err));
}

// CSRF helper
function getCookie(name) {
  let cookieValue = null;
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith(name + "=")) {
      cookieValue = cookie.substring(name.length + 1);
    }
  }
  return cookieValue;
}

document.addEventListener("DOMContentLoaded", function () {
  // 1. EMOTION CHART (Doughnut)
  const canvas = document.getElementById("emotionChart");
  if (!canvas || !window.EMOTION_DATA) return;

  const ctx = canvas.getContext("2d");

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Happy", "Focused", "Neutral", "Angry", "Sad", "Tired"],
      datasets: [{
        data: [
          EMOTION_DATA.happy,
          EMOTION_DATA.focused,
          EMOTION_DATA.neutral,
          EMOTION_DATA.angry,
          EMOTION_DATA.sad,
          EMOTION_DATA.tired
        ],
        backgroundColor: [
          "#008000",  // Happy
          "#19ABB6",  // Focused
          "#9ca3af",  // Neutral
          "#FF0000",  // Angry
          "#6F517A",  // Sad
          "#FF8800"   // Tired
        ],
        borderColor: "#ffffff",
        borderWidth: 3
      }]
    },
    options: {
      responsive: true,
      cutout: "65%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            boxWidth: 18,
            padding: 16,
            font: {
              size: 14
            }
          }
        },
        tooltip: {
          enabled: true
        }
      }
    }
  });
});

document.addEventListener('DOMContentLoaded', function() {
  // 2. PRODUCTIVITY CHART (Line)
  const ctxProd = document.getElementById('productivityChart').getContext('2d');
  new Chart(ctxProd, {
    type: 'line',
    data: {
      labels: window.PRODUCTIVITY_DATA.labels,
      datasets: [{
        label: 'Efficiency %',
        data: window.PRODUCTIVITY_DATA.values,
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79, 70, 229, 0.1)',
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, max: 100 }
      }
    }
  });
});