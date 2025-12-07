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