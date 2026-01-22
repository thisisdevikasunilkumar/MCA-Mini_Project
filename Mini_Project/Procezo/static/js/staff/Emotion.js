// Message count badge
const messageCount = document.querySelector('.message-count');
if (messageCount) {
  messageCount.style.background =
    `linear-gradient(135deg, ${secondary} 0%, #e53e3e 100%)`;
}

// ------------------------------------------------------
// Reply Functionality
// ------------------------------------------------------
// Toggle reply box
function toggleReply(messageId) {
  document.querySelectorAll('.reply-section').forEach(s => s.classList.remove('active'));
  document.getElementById(`reply-section-${messageId}`).classList.add('active');
  document.getElementById(`reply-textarea-${messageId}`).focus();
}

// Cancel reply
function cancelReply(messageId) {
  const area = document.getElementById(`reply-textarea-${messageId}`);
  area.value = '';
  document.getElementById(`reply-section-${messageId}`).classList.remove('active');
}

// Send reply
function sendReply(messageId) {
  const textarea = document.getElementById(`reply-textarea-${messageId}`);
  const text = textarea.value.trim();

  if (!text) {
    textarea.style.borderColor = '#f56565';
    textarea.placeholder = 'Please enter a message...';
    setTimeout(() => {
      textarea.style.borderColor = '#e2e8f0';
      textarea.placeholder = 'Type your response to admin here...';
    }, 2000);
    return;
  }

  // Send reply to Django
  fetch("/accounts/save-reply/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      message_id: messageId,
      reply_text: text
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        const success = document.getElementById(`success-message-${messageId}`);
        success.classList.add('active');
        textarea.value = '';

        setTimeout(() => {
          success.classList.remove('active');
          document.getElementById(`reply-section-${messageId}`).classList.remove('active');
        }, 3000);
      }
    });
}

// Get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
