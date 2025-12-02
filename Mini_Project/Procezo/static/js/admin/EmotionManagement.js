// ----------------------------------------
// FEEDBACK HANDLER
// ----------------------------------------
function askFeedback(employeeName, emotion) {
  const feedbackSection = document.getElementById('feedback-section');
  const employeeNameEl = document.getElementById('feedback-employee-name');
  const emotionEl = document.getElementById('feedback-emotion');
  const feedbackResponse = document.getElementById('feedback-response');

  employeeNameEl.textContent = employeeName;

  let emotionIcon = '';
  if (emotion === 'Sad') emotionIcon = '😔';
  else if (emotion === 'Tired') emotionIcon = '😴';
  else if (emotion === 'Angry') emotionIcon = '😠';

  emotionEl.textContent = `${emotionIcon} ${emotion}`;

  feedbackSection.style.display = 'block';
  feedbackResponse.style.display = 'none';
  document.getElementById('feedback-message').value = '';

  feedbackSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function sendFeedbackRequest() {
  const feedbackMessage = document.getElementById('feedback-message').value;
  const feedbackResponse = document.getElementById('feedback-response');

  if (feedbackMessage.trim() === '') {
    return;
  }

  feedbackResponse.style.display = 'block';

  setTimeout(() => {
    feedbackResponse.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

function closeFeedback() {
  document.getElementById('feedback-section').style.display = 'none';
}

// ----------------------------------------
// EMPLOYEE PROBLEM DATA
// ----------------------------------------
const employeeProblems = {
  'Emily Brown': 'Feeling overwhelmed with workload and personal issues',
  'Alex Kumar': 'Not getting enough sleep, too many late night shifts',
  'Lisa Chen': 'Disagreement with team members, unclear project requirements',
  'James Park': 'Working overtime for past 2 weeks, need rest'
};

// ----------------------------------------
// ISSUE REPORT HANDLER
// ----------------------------------------
function reportIssue(employeeName, emotion) {
  const issueSection = document.getElementById('issue-report-section');
  const employeeNameEl = document.getElementById('issue-employee-name');
  const emotionEl = document.getElementById('issue-emotion');
  const currentProblemEl = document.getElementById('issue-current-problem');
  const issueResponse = document.getElementById('issue-response');

  employeeNameEl.textContent = employeeName;

  let emotionIcon = '';
  if (emotion === 'Sad') emotionIcon = '😔';
  else if (emotion === 'Tired') emotionIcon = '😴';
  else if (emotion === 'Angry') emotionIcon = '😠';

  emotionEl.textContent = `${emotionIcon} ${emotion}`;
  currentProblemEl.textContent = employeeProblems[employeeName] || 'No problem description available';

  issueSection.style.display = 'block';
  issueResponse.style.display = 'none';
  document.getElementById('issue-why').value = '';
  document.getElementById('issue-action').value = '';

  issueSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function submitIssueReport() {
  const issueWhy = document.getElementById('issue-why').value;
  const issueAction = document.getElementById('issue-action').value;
  const issueResponse = document.getElementById('issue-response');

  if (issueWhy.trim() === '' || issueAction.trim() === '') {
    return;
  }

  issueResponse.style.display = 'block';

  setTimeout(() => {
    issueResponse.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

function closeIssueReport() {
  document.getElementById('issue-report-section').style.display = 'none';
}