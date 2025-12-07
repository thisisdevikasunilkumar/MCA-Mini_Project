// ------------------------ INITIALIZATION AND SETUP ------------------------

const attendanceModal = document.getElementById("attendanceModal");
const staffTableBody = document.getElementById("staffListTable")?.querySelector("tbody"); 
const cancelButton = document.getElementById("cancelAttendanceBtn");
const saveButton = document.getElementById("saveAttendanceBtn"); 
const saveUrl = document.getElementById("saveAttendanceUrl")?.value;

document.addEventListener('DOMContentLoaded', initializeApp);

function initializeApp() {
    if (!staffTableBody) {
        console.error("Staff table body not found!");
        return;
    }
    if (!saveUrl) {
        console.error("Django URL for saving attendance is missing!");
    }
    setupModals();
}

function setupModals() {
    staffTableBody.addEventListener('click', handleStaffTableClick);
    cancelButton.addEventListener('click', () => closeModal('attendanceModal'));
    saveButton.addEventListener('click', saveAttendanceToStaff); 
    window.addEventListener('click', handleWindowClick);
}

// ---------------------------
// Helper Function: Convert 24h time string (HH:MM) to HH:MM AM/PM
// ---------------------------
function convertToAmPm(timeStr) {
    if (!timeStr) return '';
    
    // Check if the input is already AM/PM or invalid (in case it's called with existing table content)
    if (!/^\d{2}:\d{2}$/.test(timeStr)) return timeStr; 

    let [hour, minute] = timeStr.split(':').map(Number);
    let ampm = hour >= 12 ? 'PM' : 'AM';
    hour = hour % 12;
    if (hour === 0) hour = 12; // 0 hour becomes 12 AM

    // Format: 09:00 AM (Ensure two digits for hour and minute)
    const formattedHour = hour.toString().padStart(2, '0');
    const formattedMinute = minute.toString().padStart(2, '0');
    
    return `${formattedHour}:${formattedMinute} ${ampm}`;
}

// ---------------------------
// Handlers (Modal opening logic)
// ---------------------------
function handleStaffTableClick(event) {
    if (event.target && event.target.id === 'markAttendanceBtn') {
        const row = event.target.closest('tr');
        if (row) {
            const staffID = row.cells[0].textContent.trim();
            const staffName = row.cells[1].textContent.trim();
            const staffRole = row.cells[2].textContent.trim();
            const staffJobType = row.cells[3].textContent.trim();
            
            openAttendanceModal(staffID, staffName, staffRole, staffJobType);
        }
    }
}

function openAttendanceModal(staffID, name, role, jobType) {
    document.getElementById("attendanceStaffId").value = staffID;
    document.getElementById("attendanceName").value = name;
    document.getElementById("attendanceRole").value = role;
    document.getElementById("attendanceJobType").value = jobType;
    document.getElementById("checkInTime").value = "";
    document.getElementById("checkOutTime").value = ""; 
    
    attendanceModal.style.display = "block"; 
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = "none";
    document.querySelector(`#${modalId} form`)?.reset();
}

function handleWindowClick(event) {
    if (event.target === attendanceModal) {
        closeModal('attendanceModal');
    }
}

// ---------------------------
// SAVE TO STAFF TABLE (Django)
// ---------------------------
function saveAttendanceToStaff(e) {
    e.preventDefault(); 

    const staffId = document.getElementById("attendanceStaffId").value;
    // Get time in 24h format (HH:MM) which is suitable for Django TimeField
    const checkIn24h = document.getElementById("checkInTime").value; 
    const checkOut24h = document.getElementById("checkOutTime").value;
    
    if (!saveUrl || (!checkIn24h && !checkOut24h)) {
         if (!checkIn24h && !checkOut24h) alert("Please enter a Check In or Check Out time.");
         return;
    }

    fetch(saveUrl, { 
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken()
        },
        body: JSON.stringify({
            staffId,
            // Send the standard 24h format to Django
            checkIn: checkIn24h, 
            checkOut: checkOut24h
        })
    })
    .then(res => {
        console.log(`Fetch Response Status: ${res.status}`); 
        if (!res.ok) {
            throw new Error(`HTTP Error Status: ${res.status}`); 
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            // Update the table row using the new AM/PM format
            updateStaffTableRow(staffId, checkIn24h, checkOut24h); 
            closeModal('attendanceModal'); 
            alert("Attendance Time ⏱ saved successfully!");
        } else {
            alert(`Error saving attendance: ${data.error || 'Unknown error from Django'}`);
        }
    })
    .catch(error => {
        console.error('Fetch error:', error);
        alert("An error occurred while communicating with the server. Please check the console for details.");
    });
}

// ---------------------------
// UPDATE STAFF TABLE ROW (Frontend)
// ---------------------------
function updateStaffTableRow(staffId, checkIn24h, checkOut24h) {
    const rows = document.querySelectorAll("#staffListTable tbody tr");
    
    // Convert the 24h times to AM/PM for display
    const checkInAmPm = convertToAmPm(checkIn24h);
    const checkOutAmPm = convertToAmPm(checkOut24h);

    rows.forEach(row => {
        if (row.cells[0].textContent.trim() === staffId) {
            const checkInCell = row.querySelector(".check-in-cell");
            const checkOutCell = row.querySelector(".check-out-cell");

            // Use AM/PM strings for display
            if (checkInCell) checkInCell.textContent = checkInAmPm || "--:--"; 
            if (checkOutCell) checkOutCell.textContent = checkOutAmPm || "--:--"; 
        }
    });
}

// ---------------------------
// CSRF TOKEN HELPER
// ---------------------------
function getCSRFToken() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
}