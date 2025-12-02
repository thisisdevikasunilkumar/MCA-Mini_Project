// Message count badge
const messageCount = document.querySelector('.message-count');
if (messageCount) {
  messageCount.style.background =
    `linear-gradient(135deg, ${secondary} 0%, #e53e3e 100%)`;
}

// ------------------------------------------------------
// Reply Functionality
// ------------------------------------------------------
function toggleReply(messageId) {
  document
    .querySelectorAll('.reply-section')
    .forEach(s => s.classList.remove('active'));

  const curr = document.getElementById(`reply-section-${messageId}`);
  curr.classList.add('active');

  document.getElementById(`reply-textarea-${messageId}`).focus();
}

function cancelReply(messageId) {
  const area = document.getElementById(`reply-textarea-${messageId}`);
  area.value = '';
  document.getElementById(`reply-section-${messageId}`).classList.remove('active');
}

function sendReply(messageId) {
  const area = document.getElementById(`reply-textarea-${messageId}`);
  const text = area.value.trim();

  if (!text) {
    area.style.borderColor = '#f56565';
    area.placeholder = 'Please enter a message before sending...';

    setTimeout(() => {
      area.style.borderColor = '#e2e8f0';
      area.placeholder = 'Type your response to admin here...';
    }, 2000);

    return;
  }

  const success = document.getElementById(`success-message-${messageId}`);
  success.classList.add('active');
  area.value = '';

  setTimeout(() => {
    success.classList.remove('active');
    document.getElementById(`reply-section-${messageId}`).classList.remove('active');
  }, 3000);
}
