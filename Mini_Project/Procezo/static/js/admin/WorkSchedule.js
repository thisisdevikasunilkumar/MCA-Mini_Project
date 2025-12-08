/**
 * WorkSchedule.js - Core Logic for Work Schedule Grid and CRUD Operations
 *
 * NOTE: The rendering functions (getWeekRange, renderWeekView, etc.) are crucial 
 * and assumed to be correctly implemented to use INITIAL_EVENTS.
 */

// --- Global Variables (Declared ONCE) ---
const INITIAL_EVENTS = window.INIT_EVENTS || [];
const API = window.API || {};
const CSRF_TOKEN = window.CSRF_TOKEN;

let currentDate = new Date(); 
let currentView = 'week'; 
let currentJobFilter = 'ALL'; 

// --- DOM Elements ---
const calendarGridContainer = document.getElementById('calendar');
const viewToggleGroup = document.getElementById('viewToggleGroup');
const rangeLabel = document.getElementById('rangeLabel');
const teamTabsContainer = document.querySelector('.ws-scheduling-area .team-tabs');
const staffDataList = document.getElementById('staffList').children; 

// Modal Elements
const scheduleModal = document.getElementById('scheduleModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelModalBtn = document.getElementById('cancelModalBtn');
const openAddBtn = document.getElementById('openAddBtn');
const deleteScheduleBtn = document.getElementById('deleteScheduleBtn');
const scheduleForm = document.getElementById('scheduleForm');

// Form Inputs
const modalTitle = document.getElementById('modalTitle');
const modalScheduleId = document.getElementById('modalScheduleId');
const modalAction = document.getElementById('modalAction');
const modalStaffSelect = document.getElementById('modalStaffSelect');
const modalTitleInput = document.getElementById('modalTitleInput'); // Used for title
const modalEventType = document.getElementById('modalEventType');
const modalDate = document.getElementById('modalDate');
const modalStartTime = document.getElementById('modalStartTime');
const modalEndTime = document.getElementById('modalEndTime');

let fullStaffList = Array.from(staffDataList).map(el => ({
    id: el.dataset.staff,
    name: el.dataset.name,
    total_time: el.dataset.time || '0h 00m',
    job_type: el.dataset.jobType || 'Other' 
}));

let currentStaffList = fullStaffList; 


// --- UTILITY FUNCTIONS ---

function getWeekRange(date) { /* ... implementation ... */
    const startOfWeek = new Date(date);
    const day = date.getDay();
    startOfWeek.setDate(date.getDate() - (day === 0 ? 6 : day - 1));
    startOfWeek.setHours(0, 0, 0, 0);

    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    return { start: startOfWeek, end: endOfWeek };
}

function formatDateRangeLabel(start, end) { /* ... implementation ... */
    const startMonth = start.toLocaleString('default', { month: 'short' });
    const endMonth = end.toLocaleString('default', { month: 'short' });
    
    if (startMonth === endMonth) {
        return `${start.toLocaleString('default', { weekday: 'short' })}, ${startMonth} ${start.getDate()} - ${end.toLocaleString('default', { weekday: 'short' })}, ${end.getDate()}, ${start.getFullYear()}`;
    }
    return `${start.toLocaleString('default', { weekday: 'short' })}, ${startMonth} ${start.getDate()} - ${end.toLocaleString('default', { weekday: 'short' })}, ${endMonth} ${end.getDate()}, ${start.getFullYear()}`;
}

function getMonthStartAndEnd(date) { /* ... implementation ... */
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstOfMonth = new Date(year, month, 1);
    const startDay = new Date(firstOfMonth);
    startDay.setDate(startDay.getDate() - startDay.getDay()); 
    const endOfMonth = new Date(year, month + 1, 0);
    const endDay = new Date(endOfMonth);
    endDay.setDate(endDay.getDate() + (6 - endDay.getDay())); 
    return { start: startDay, end: endDay, month: month };
}

// --- MODAL FUNCTIONS ---

function showModal() {
    scheduleModal.classList.add('show');
}

function hideModal() {
    scheduleModal.classList.remove('show');
    scheduleForm.reset();
    modalAction.value = 'create';
    modalTitle.textContent = 'Create a schedule';
    deleteScheduleBtn.style.display = 'none';
    modalScheduleId.value = '';
    modalTitleInput.value = ''; // Ensure title is cleared
}

function openModalForAdd(date, staffId) {
    hideModal(); 
    
    // Set default date and staff 
    modalDate.value = date;
    
    if (staffId) {
        modalStaffSelect.value = staffId;
    } else {
        // Default to the first staff member if staffId is null
        modalStaffSelect.selectedIndex = 0; 
    }

    showModal();
}

function openModalForEdit(eventId) {
    hideModal();
    
    const event = INITIAL_EVENTS.find(e => String(e.id) === String(eventId));
    if (!event) return;

    modalTitle.textContent = 'Edit Schedule';
    modalAction.value = 'update';
    modalScheduleId.value = event.id;
    deleteScheduleBtn.style.display = 'inline-block';

    // Populate the form fields with event data
    modalTitleInput.value = event.title || '';
    modalStaffSelect.value = event.staff || event.staff_id || ''; 
    modalEventType.value = event.event_type || 'Office';
    modalDate.value = event.date || '';
    modalStartTime.value = event.start || '09:00';
    modalEndTime.value = event.end || '17:00';
    
    showModal();
}


// --- API Communication Functions ---

async function submitSchedule(e) {
    e.preventDefault(); 
    
    const formData = new FormData(scheduleForm);
    const action = modalAction.value;
    const scheduleId = modalScheduleId.value;
    
    const data = Object.fromEntries(formData.entries());
    delete data.csrfmiddlewaretoken; 
    
    let url = API.create;

    if (action === 'update' && scheduleId) {
        url = API.update.replace('{id}', scheduleId);
    } 

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
             const errorData = await response.json();
             throw new Error(errorData.error || `Server error: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (result.success) {
            
            // --- Crucial: Update the local data array (INITIAL_EVENTS) and re-render ---
            if (action === 'create' && result.created) {
                result.created.forEach(new_event => {
                    INITIAL_EVENTS.push({
                        id: new_event.id,
                        title: new_event.title,
                        staff: new_event.staff_id, 
                        date: new_event.date,
                        start: new_event.start,
                        end: new_event.end,
                        event_type: new_event.event_type,
                    });
                });
            } else if (action === 'update') {
                const eventIndex = INITIAL_EVENTS.findIndex(e => String(e.id) === String(scheduleId));
                if (eventIndex !== -1) {
                    INITIAL_EVENTS[eventIndex] = { 
                        ...INITIAL_EVENTS[eventIndex], 
                        title: data.title,
                        staff: data.staff, 
                        date: data.date,
                        start: data.start, 
                        end: data.end,
                        event_type: data.event_type,
                    };
                }
            }
            
            // Re-render the calendar to display the new or updated event
            renderCalendar();
            hideModal();
        } else if (result.error) {
            alert(`Failed to save schedule: ${result.error}`);
        }

    } catch (error) {
        console.error('Failed to save schedule:', error);
        alert(`Error: Could not save schedule. ${error.message}`);
    }
}

async function deleteSchedule() {
    const scheduleId = modalScheduleId.value;
    if (!scheduleId || !confirm("Are you sure you want to delete this schedule?")) return;

    const url = API.delete.replace('{id}', scheduleId);

    try {
        const response = await fetch(url, {
            method: 'POST', 
            headers: {
                'X-CSRFToken': CSRF_TOKEN,
            },
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            // Remove the event from the local list
            const eventIndex = INITIAL_EVENTS.findIndex(e => String(e.id) === String(scheduleId));
            if (eventIndex !== -1) {
                INITIAL_EVENTS.splice(eventIndex, 1);
            }
            
            renderCalendar();
            hideModal();
        }
    } catch (error) {
        console.error('Failed to delete schedule:', error);
        alert(`Error: Could not delete schedule. ${error.message}`);
    }
}

// --- RENDERING FUNCTIONS (The part that displays the title) ---

function renderWeekView() {
    const { start, end } = getWeekRange(currentDate);
    rangeLabel.textContent = formatDateRangeLabel(start, end);
    
    let html = '<div class="schedule-grid">';

    // 1. Day Headers (omitted for brevity)

    // 2. Generate Staff Rows and Event Cells
    currentStaffList.forEach(staff => {
        html += `<div class="grid-staff-cell" data-staff-id="${staff.id}">
                    <div class="staff-info-box">
                        <div class="staff-name-tag">${staff.name}</div>
                        <div class="staff-time-info">${staff.total_time} / 0s</div>
                    </div>
                </div>`;

        const days = [];
        for (let i = 0; i < 7; i++) {
            const date = new Date(start);
            date.setDate(start.getDate() + i);
            days.push(date);
        }

        days.forEach(day => {
            const dayKey = day.toISOString().split('T')[0];
            
            const eventsOnDay = INITIAL_EVENTS.filter(e => 
                e.date === dayKey && String(e.staff || e.staff_id) === String(staff.id)
            );
            
            let eventsHtml = eventsOnDay.map(event => {
                const eventClass = `event-${(event.event_type || 'other').toLowerCase()}`;
                const titleToDisplay = event.title || 'Untitled'; // **Displays the title on the calendar**
                const tooltip = `${titleToDisplay} (${event.start || ''} - ${event.end || ''})`;

                return `
                    <div class="event-block ${eventClass}" 
                         data-event-id="${event.id}" 
                         title="${tooltip}">
                        ${titleToDisplay}
                    </div>
                `;
            }).join('');

            // This is the empty box or the box with events
            html += `<div class="grid-event-cell" data-date="${dayKey}" data-staff="${staff.id}">${eventsHtml}</div>`;
        });
    });

    html += '</div>'; 
    calendarGridContainer.innerHTML = html;
    
    attachEventListeners(); 
}

function renderMonthView() { /* ... similar logic to display event title ... */
    const { start: startDate, end: endDate, month: currentMonth } = getMonthStartAndEnd(currentDate);
    rangeLabel.textContent = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });
    
    let html = '<div class="schedule-grid month-grid-layout">';
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dayNames.forEach(name => {
        html += `<div class="grid-header-cell month-day-name">${name}</div>`;
    });
    
    let day = new Date(startDate);
    while (day <= endDate) {
        const dayKey = day.toISOString().split('T')[0];
        const isOutsideMonth = day.getMonth() !== currentMonth;
        const classes = isOutsideMonth ? 'outside-month' : '';

        const eventsOnDay = INITIAL_EVENTS.filter(e => e.date === dayKey);
        
        let eventsHtml = eventsOnDay.map(event => {
            const eventClass = `event-${(event.event_type || 'other').toLowerCase()}`;
            const titleToDisplay = event.title || 'Untitled';
            
            return `
                <div class="month-event-bubble ${eventClass}" 
                     data-event-id="${event.id}" 
                     title="${titleToDisplay}">
                    ${titleToDisplay}
                </div>
            `;
        }).join('');

        html += `
            <div class="month-cell grid-event-cell ${classes}" data-date="${dayKey}">
                <div class="day-number">${day.getDate()}</div>
                ${eventsHtml}
            </div>
        `;
        
        day.setDate(day.getDate() + 1);
    }

    html += '</div>'; 
    calendarGridContainer.innerHTML = html;

    attachEventListeners();
}

function renderCalendar() {
    if (currentView === 'week') {
        renderWeekView();
    } else {
        renderMonthView();
    }
}


// --- EVENT HANDLERS ---

function attachEventListeners() {
    // 1. EDIT: Click on existing event block (displays list title and moves to edit)
    document.querySelectorAll('.event-block, .month-event-bubble').forEach(block => {
        block.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevents cell click from firing
            openModalForEdit(e.target.dataset.eventId);
        });
    });
    
    // 2. ADD: Click on empty calendar box (displays the add form)
    document.querySelectorAll('.grid-event-cell').forEach(cell => {
        // Only attach listener if no events are present in week view, or always in month view
        const hasEvents = cell.querySelector('.event-block, .month-event-bubble');

        if (!hasEvents || currentView === 'month') {
             cell.addEventListener('click', (e) => {
                const staffId = cell.dataset.staff; 
                const date = cell.dataset.date;
                if (date) {
                    openModalForAdd(date, staffId);
                }
            });
        }
    });
}

function handleNavigation(direction) {
    if (currentView === 'week') {
        currentDate.setDate(currentDate.getDate() + (direction * 7));
    } else {
        currentDate.setMonth(currentDate.getMonth() + direction);
    }
    renderCalendar();
}

function handleViewToggle(e) {
    if (!e.target.classList.contains('btn-view')) return;
    
    const newView = e.target.dataset.view;
    if (newView === currentView) return;

    currentView = newView;
    document.querySelectorAll('.btn-view').forEach(btn => btn.classList.remove('active'));
    e.target.classList.add('active');
    
    currentDate = new Date(); 
    renderCalendar();
}

function handleJobTabClick(e) {
    const button = e.target.closest('.tab-button');
    if (!button) return;

    const newJob = button.dataset.job;
    // ... filtering logic ...
    renderCalendar();
}

// --- INITIALIZATION ---
function init() {
    // Attach main listeners
    document.getElementById('prevBtn').addEventListener('click', () => handleNavigation(-1));
    document.getElementById('nextBtn').addEventListener('click', () => handleNavigation(1));
    viewToggleGroup.addEventListener('click', handleViewToggle);
    teamTabsContainer.addEventListener('click', handleJobTabClick);
    
    // MODAL LISTENERS: Global Add button and close buttons
    openAddBtn.addEventListener('click', () => openModalForAdd(new Date().toISOString().split('T')[0], null));
    closeModalBtn.addEventListener('click', hideModal);
    cancelModalBtn.addEventListener('click', hideModal);
    
    // CRUD Listeners
    scheduleForm.addEventListener('submit', submitSchedule);
    deleteScheduleBtn.addEventListener('click', deleteSchedule);

    renderCalendar();
}

init();


// WorkSchedule.js

document.addEventListener('DOMContentLoaded', function() {
    // 1. DOM Element Selectors
    const teamTabs = document.querySelectorAll('.team-tabs .tab-button');
    const staffListContainer = document.getElementById('staffList'); // Assuming this is the main staff list container

    // 2. Function to Render the Staff List
    function renderStaffList(staffData) {
        // Clear the current list displayed on the left sidebar/overview
        // NOTE: This assumes 'staffList' is the UL element for the staff overview.
        const staffOverviewUl = document.querySelector('.ws-card.ws-staff-list-card ul#stafflist');

        if (!staffOverviewUl) return; // Exit if the container isn't found
        
        staffOverviewUl.innerHTML = ''; // Clear previous entries

        if (staffData && staffData.length > 0) {
            staffData.forEach(staff => {
                const li = document.createElement('li');
                li.setAttribute('data-staff', staff.id);
                li.classList.add('staff-item');

                li.innerHTML = `
                    <span class="staff-name">${staff.name}</span>
                    <span class="staff-id">(${staff.id})</span>
                    <span class="staff-job-type">${staff.job_type || 'N/A'}</span>
                    `;
                staffOverviewUl.appendChild(li);
            });
        } else {
            staffOverviewUl.innerHTML = '<li class="no-results">No staff found for this category.</li>';
        }
    }

    // 3. Function to Fetch Staff Data via AJAX
        // Get the base URL from your Django setup (must be defined in your template's window.API)
    // WorkSchedule.js (Updated fetchStaffData function)

function fetchStaffData(jobType) {
    
    // --- 1. FILTER STAFF LIST ---
    if (jobType === 'ALL') {
        currentVisibleStaff = window.ALL_STAFF_DATA;
    } else {
        // Filter the staff list based on the selected job type
        currentVisibleStaff = window.ALL_STAFF_DATA.filter(staff => staff.job_type === jobType);
    }
    
    // Get the IDs of the staff currently visible
    const visibleStaffIds = new Set(currentVisibleStaff.map(s => s.id));

    // --- 2. FILTER EVENTS ---
    // Filter the schedules to include only those belonging to the visible staff
    currentVisibleEvents = window.ALL_EVENTS.filter(event => 
        visibleStaffIds.has(String(event.staff_id)) // Ensure staff_id types match (string vs. number)
    );

    // --- 3. RENDER UI COMPONENTS ---
    
    // A. Update the Staff Sidebar (using the function from the previous response)
    renderStaffList(currentVisibleStaff);

    // B. Rerender the Calendar Grid (to only show rows for visible staff)
    drawCalendarGrid(currentVisibleStaff); // Pass the filtered staff to draw the rows

    // C. Display the Filtered Events
    displayEvents(currentVisibleEvents);
}


// You must ensure your drawCalendarGrid function accepts the staff list
// and uses it to generate the calendar rows:

function drawCalendarGrid(staffList) {
    const calendarGrid = document.getElementById('calendar');
    calendarGrid.innerHTML = ''; // Clear the grid
    
    // Example: Loop through the visible staff and create a row for each
    staffList.forEach(staff => {
        // 1. Create staff row header (for the name/time)
        // 2. Create 7 day cells for the week
        // 3. Append the row to the calendarGrid element
        // ... (your existing calendar drawing code goes here) ...
    });
}


// WorkSchedule.js (Global/Initial Setup)

// Store the full staff list fetched from Django template (using the hidden-staff-list div)
// This is used to map events to names/job types.
window.ALL_STAFF_DATA = Array.from(document.querySelectorAll('#staffList > div')).map(el => ({
    id: el.getAttribute('data-staff'),
    name: el.getAttribute('data-name'),
    job_type: el.getAttribute('data-job-type') // Ensure this is correctly set in your HTML
}));

// Store all schedules fetched from the template
window.ALL_EVENTS = window.INIT_EVENTS || [];

// Variable to hold the currently visible staff list and events
let currentVisibleStaff = [];
let currentVisibleEvents = [];

// Function declarations for drawing (must already exist in your file)
function drawCalendarGrid() { /* ... draws the calendar structure ... */ }
function displayEvents(eventsToDisplay) { /* ... places events on the grid ... */ }
// ... and the staff list render function from the previous response:
function renderStaffList(staffData) { /* ... updates the sidebar staff list ... */ }})


// WorkSchedule.js (Tab Listener)

const teamTabs = document.querySelectorAll('.team-tabs .tab-button');

teamTabs.forEach(tab => {
    tab.addEventListener('click', function() {
        // ... (remove/add active class) ...
        teamTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        const jobType = this.getAttribute('data-job');

        // This call now handles filtering staff, events, and updating both the sidebar AND the calendar.
        fetchStaffData(jobType); 
    });
});