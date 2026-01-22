let currentStaffId = null;

/* Get CSRF cookie */
function getCookie(name) {
    let value = null;
    if (document.cookie) {
        document.cookie.split(";").forEach(cookie => {
            cookie = cookie.trim();
            if (cookie.startsWith(name + "=")) {
                value = decodeURIComponent(cookie.substring(name.length + 1));
            }
        });
    }
    return value;
}

/* Open feedback form */
function askFeedback(btn) {
    currentStaffId = btn.dataset.staffId;   // FIXED: now always correct
    console.log("Selected Staff ID:", currentStaffId);

    document.getElementById("feedback-employee-name").textContent = btn.dataset.staffName;

    const icons = {
        "Happy": "😄", "Sad": "😢", "Neutral": "😐",
        "Angry": "😠", "Tired": "😴", "Focused": "🎯"
    };

    const emo = btn.dataset.staffEmotion;
    document.getElementById("feedback-emotion").textContent = emo ? icons[emo] + " " + emo : "";

    document.getElementById("feedback-message").value = "";
    document.getElementById("feedback-response").style.display = "none";

    document.getElementById("feedback-section").style.display = "block";
}

/* Close feedback box */
function closeFeedback() {
    document.getElementById("feedback-section").style.display = "none";
}

/* Send feedback to backend */
function submitInlineFeedback() {
    const message = document.getElementById("feedback-message").value.trim();

    if (!message) {
        alert("Please write your message.");
        return;
    }

    console.log("Sending to backend:", currentStaffId, message);

    fetch("/accounts/ajax/submit-feedback/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({
            staff_id: currentStaffId,
            message: message
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.ok) {
            const box = document.getElementById("feedback-response");
            box.textContent = "Feedback sent successfully!";
            box.style.display = "block";

            setTimeout(() => closeFeedback(), 1000);
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(() => alert("Network Error"));
}

/* Open issue report form */
function reportIssue(btn) {
    currentStaffId = btn.dataset.staffId;
    document.getElementById("issue-employee-name").textContent = btn.dataset.staffName;
    document.getElementById("issue-current-problem").textContent = btn.dataset.staffIssue;
    
    const icons = {
        "Happy": "😄", "Sad": "😢", "Neutral": "😐",
        "Angry": "😠", "Tired": "😴", "Focused": "🎯"
    };
    const emo = btn.dataset.staffEmotion;
    document.getElementById("issue-emotion").textContent = emo ? icons[emo] + " " + emo : "";

    document.getElementById("issue-report-section").style.display = "block";
}

/* Close issue report form */
function closeIssueReport() {
    document.getElementById("issue-report-section").style.display = "none";
}

/* Submit issue report */
function submitIssueReport() {
    const current_problem = document.getElementById("issue-current-problem").textContent;
    const root_cause = document.getElementById("issue-why").value.trim();
    const proposed_action = document.getElementById("issue-action").value.trim();

    if (!root_cause || !proposed_action) {
        alert("Please fill in both the root cause and proposed action.");
        return;
    }

    fetch("/accounts/ajax/submit-issue/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({
            staff_id: currentStaffId,
            current_problem: current_problem,
            root_cause: root_cause,
            proposed_action: proposed_action
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.ok) {
            const responseDiv = document.getElementById("issue-response");
            responseDiv.style.display = "block";
            setTimeout(() => {
                closeIssueReport();
                responseDiv.style.display = "none";
                location.reload(); 
            }, 2000);
        } else {
            alert("Error: " + (data.error || "Unknown error"));
        }
    })
    .catch(err => {
        console.error("Fetch error:", err);
        alert("A network error occurred.");
    });
}
