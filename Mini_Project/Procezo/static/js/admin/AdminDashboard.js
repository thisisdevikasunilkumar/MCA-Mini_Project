// ======================= TASK DATA ============================
const tasks = [
  { id: 1, completed: false },
  { id: 2, completed: false },
  { id: 3, completed: false }
];

// Helper: find task by id
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

// ======================= CHECKBOX CLICK HANDLER ============================
function toggleTaskById(id) {
  const task = findTask(id);
  if (!task) return;
  task.completed = !task.completed;
  updateTaskCheckboxes();
}

// Click on checkbox
document.addEventListener('click', (e) => {
  const cb = e.target.closest('.task-checkbox');
  if (cb) {
    e.stopPropagation();
    toggleTaskById(cb.getAttribute('data-id'));
  }
});

// Allow toggling by clicking task-item row
document.querySelectorAll('.task-item').forEach(row => {
  row.addEventListener('click', () => {
    const id = row.getAttribute('data-id');
    toggleTaskById(id);
  });

  // allow keyboard toggle on checkbox with Enter / Space
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

// ======================= SET CURRENT DATE & TIME ============================
function updateDateTime() {
  const now = new Date();
  const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  const dateStr = now.toLocaleDateString('en-US', dateOptions);
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  const dateEl = document.getElementById('current-date');
  const timeEl = document.getElementById('current-time');
  if (dateEl) dateEl.textContent = dateStr;
  if (timeEl) timeEl.textContent = timeStr;
}
updateDateTime();
setInterval(updateDateTime, 1000);

// Initial checkbox update
updateTaskCheckboxes();

// ======================= Meeting link modal & logic ============================
let currentButton = null;

function addMeetingLink(button) {
  currentButton = button;

  // Create modal markup
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
      <div class="modal-header">
        <h3 id="modalTitle">Add Meeting Details</h3>
        <p style="margin:0;color:#6b7280;font-size:.95rem;">Fill in the meeting information below</p>
      </div>
      <div class="modal-input-group" style="margin-top:12px;">
        <label for="meeting-time-input" style="font-weight:700;font-size:.92rem;">Meeting Time</label>
        <input type="text" id="meeting-time-input" class="modal-input" placeholder="09:00 AM">
      </div>
      <div class="modal-input-group" style="margin-top:8px;">
        <label for="meeting-title-input" style="font-weight:700;font-size:.92rem;">Meeting Title</label>
        <input type="text" id="meeting-title-input" class="modal-input" placeholder="Team Meeting">
      </div>
      <div class="modal-input-group" style="margin-top:8px;">
        <label for="meeting-desc-input" style="font-weight:700;font-size:.92rem;">Description</label>
        <input type="text" id="meeting-desc-input" class="modal-input" placeholder="Meeting description">
      </div>
      <div class="modal-input-group" style="margin-top:8px;">
        <label for="meeting-link-input" style="font-weight:700;font-size:.92rem;">Meeting Link</label>
        <input type="url" id="meeting-link-input" class="modal-input" placeholder="https://meet.google.com/xxx-xxxx-xxx">
      </div>
      <div class="modal-actions">
        <button class="modal-btn modal-btn-cancel" type="button" id="modalCancel">Cancel</button>
        <button class="modal-btn modal-btn-save" type="button" id="modalSave">Save Meeting</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // focus first input
  const timeInput = document.getElementById('meeting-time-input');
  if (timeInput) timeInput.focus();

  // close on overlay click
  modal.addEventListener('click', function(e) {
    if (e.target === modal) closeModal();
  });

  // hook up buttons
  document.getElementById('modalCancel').addEventListener('click', closeModal);
  document.getElementById('modalSave').addEventListener('click', saveMeetingLink);
}

function closeModal() {
  const modal = document.querySelector('.modal-overlay');
  if (modal) modal.remove();
  currentButton = null;
}

function isValidUrl(value) {
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}

function saveMeetingLink() {
  const timeInput = document.getElementById('meeting-time-input');
  const titleInput = document.getElementById('meeting-title-input');
  const descInput = document.getElementById('meeting-desc-input');
  const linkInput = document.getElementById('meeting-link-input');

  const time = timeInput ? timeInput.value.trim() : '';
  const title = titleInput ? titleInput.value.trim() : '';
  const desc = descInput ? descInput.value.trim() : '';
  const link = linkInput ? linkInput.value.trim() : '';

  // basic validation
  if (!time || !title || !desc || !link) {
    // short user feedback (could be improved)
    alert('Please fill all fields.');
    return;
  }

  if (!isValidUrl(link)) {
    alert('Please enter a valid URL (include http/https).');
    return;
  }

  if (currentButton) {
    const scheduleItem = currentButton.closest('.schedule-item');
    const detailsDiv = scheduleItem.querySelector('.schedule-details');

    if (detailsDiv) {
      detailsDiv.innerHTML = `
        <div class="schedule-time">${time}</div>
        <div class="schedule-info">
          <p class="schedule-title">${escapeHtml(title)}</p>
          <p class="schedule-desc">${escapeHtml(desc)}</p>
        </div>
      `;
      detailsDiv.classList.add('show');
    }

    const linkElement = document.createElement('a');
    linkElement.href = link;
    linkElement.target = '_blank';
    linkElement.rel = 'noopener noreferrer';
    linkElement.className = 'meet-link-btn has-link';
    linkElement.innerHTML = `
      <svg class="meet-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/>
      </svg>
      Join Meeting
    `;

    currentButton.parentNode.replaceChild(linkElement, currentButton);
  }

  closeModal();
}

// simple HTML escape to prevent injection in inserted text nodes
function escapeHtml(unsafe) {
  return unsafe.replace(/[&<>"'`=\/]/g, function (s) {
    return ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
      '/': '&#x2F;',
      '`': '&#x60;',
      '=': '&#x3D;'
    })[s];
  });
}
