/**
 * WorkSchedule.js - Core Logic for Work Schedule Grid and CRUD Operations
 *
 * This refactored script consolidates logic, fixes bugs, and adds staff-specific filtering.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Global State & Configuration ---
    const API = window.API || {};
    const CSRF_TOKEN = window.CSRF_TOKEN;
    const INITIAL_EVENTS = window.INIT_EVENTS || [];

    let currentDate = new Date();
    let currentView = 'week';
    let currentJobFilter = 'ALL'; // From tabs like 'HR'
    let currentStaffIdFilter = 'ALL'; // From dropdown

    // --- DOM Elements ---
    const calendarGridContainer = document.getElementById('calendar');
    const rangeLabel = document.getElementById('rangeLabel');

    // Controls
    const viewToggleGroup = document.getElementById('viewToggleGroup');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const teamTabsContainer = document.querySelector('.ws-scheduling-area .team-tabs');
    const staffFilterSelect = document.getElementById('staffFilter');

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
    const modalTitleInput = document.getElementById('modalTitleInput');
    const modalDescription = document.getElementById('modalDescription');
    const modalEventType = document.getElementById('modalEventType');
    const modalDate = document.getElementById('modalDate');
    const modalStartTime = document.getElementById('modalStartTime');
    const modalEndTime = document.getElementById('modalEndTime');

    // --- Data Initialization ---
    function normalizeJobType(raw) {
        if (!raw) return '';
        const t = raw.trim().toLowerCase();
        if (t === 'hr' || t === 'human resources' || t === 'human resource') return 'HR';
        if (t === 'finance' || t === 'finance dept' || t === 'accounts') return 'Finance';
        if (t === 'sales' || t === 'sales dept') return 'Sales';
        if (t === 'marketing' || t === 'marketing dept') return 'Marketing';
        if (t === 'operations' || t === 'ops') return 'Operations';
        if (t === 'it' || t === 'it support' || t === 'tech support') return 'IT Support';
        return raw.trim();
    }

    const allStaff = Array.from(document.getElementById('staffList').children).map(el => ({
        id: el.dataset.staff,
        name: el.dataset.name,
        total_time: el.dataset.time || '0h 00m',
        job_type: normalizeJobType(el.dataset.jobType || '')
    }));

    const staffJobTypeMap = allStaff.reduce((acc, s) => {
        acc[s.id] = s.job_type;
        return acc;
    }, {});

    INITIAL_EVENTS.forEach(ev => {
        const staffId = ev.staff || ev.staff_id;
        ev.staff_id = staffId; // normalize
        ev.job_type = normalizeJobType(staffJobTypeMap[staffId] || '');
    });

    // --- UTILITY FUNCTIONS ---
    function formatDateToISO(date) {
        // Format date as YYYY-MM-DD using local timezone (not UTC)
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function getWeekRange(date) {
        let startOfWeek = new Date(date);
        startOfWeek.setHours(0, 0, 0, 0);

        // Loop backwards to find Monday (getDay() === 1)
        for (let i = 0; i < 7; i++) {
            if (startOfWeek.getDay() === 1) {
                break;
            }
            startOfWeek.setDate(startOfWeek.getDate() - 1);
        }

        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(startOfWeek.getDate() + 6);
        endOfWeek.setHours(23, 59, 59, 999);
        return { start: startOfWeek, end: endOfWeek };
    }

    function formatDateRangeLabel(start, end) {
        const startMonth = start.toLocaleString('default', { month: 'short' });
        const endMonth = end.toLocaleString('default', { month: 'short' });

        if (startMonth === endMonth) {
            return `${start.toLocaleString('default', { weekday: 'short' })}, ${startMonth} ${start.getDate()} - ${end.toLocaleString('default', { weekday: 'short' })}, ${end.getDate()}, ${start.getFullYear()}`;
        }
        return `${start.toLocaleString('default', { weekday: 'short' })}, ${startMonth} ${start.getDate()} - ${end.toLocaleString('default', { weekday: 'short' })}, ${endMonth} ${end.getDate()}, ${start.getFullYear()}`;
    }

    function getMonthStartAndEnd(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        
        // Start with the first day of the month
        let startDay = new Date(year, month, 1);

        // Loop backwards until we find a Monday (getDay() === 1)
        for (let i = 0; i < 7; i++) {
            if (startDay.getDay() === 1) {
                break; // Found Monday
            }
            startDay.setDate(startDay.getDate() - 1);
        }
        
        startDay.setHours(0, 0, 0, 0);

        // Create a 6-week (42 days) grid for a consistent layout
        const endDay = new Date(startDay);
        endDay.setDate(startDay.getDate() + 41);
        endDay.setHours(23, 59, 59, 999);

        return { start: startDay, end: endDay, month: month };
    }


    // --- MODAL FUNCTIONS ---
    function showModal() {
        scheduleModal.classList.add('show');
        scheduleModal.setAttribute('aria-hidden', 'false');
    }

    function hideModal() {
        scheduleModal.classList.remove('show');
        scheduleModal.setAttribute('aria-hidden', 'true');
        scheduleForm.reset();
        modalAction.value = 'create';
        modalTitle.textContent = 'Create a schedule';
        deleteScheduleBtn.style.display = 'none';
        modalScheduleId.value = '';
    }

    function openModalForAdd(date, staffId) {
        hideModal();
        modalTitle.textContent = 'Create a schedule';
        modalAction.value = 'create';
        
        // Auto-fill with provided date or today's date
        if (date) {
            modalDate.value = date;
        } else {
            const today = new Date();
            modalDate.value = formatDateToISO(today);
        }
        
        if (staffId) {
            modalStaffSelect.value = staffId;
        } else {
            modalStaffSelect.selectedIndex = 0;
        }
        showModal();
    }

    function openModalForEdit(eventId) {
        hideModal();
        const event = INITIAL_EVENTS.find(e => String(e.id) === String(eventId));
        if (!event) {
            console.error('Event not found:', eventId);
            alert('Error: Could not find event to edit');
            return;
        }

        console.log('Editing event:', event);

        modalTitle.textContent = 'Edit Schedule';
        modalAction.value = 'update';
        modalScheduleId.value = event.id;
        deleteScheduleBtn.style.display = 'inline-block';

        // Populate form fields
        modalTitleInput.value = event.title || '';
        modalDescription.value = event.description || '';
        modalStaffSelect.value = event.staff_id || event.staff || '';
        modalEventType.value = event.event_type || 'Office';
        modalDate.value = event.date || '';
        
        // Handle repeat field if it exists
        const modalRepeat = document.getElementById('modalRepeat');
        if (modalRepeat) {
            modalRepeat.value = event.repeat || 'none';
        }

        showModal();
    }


    // --- API Communication ---
    async function submitSchedule(e) {
        e.preventDefault();
        const formData = new FormData(scheduleForm);
        const data = Object.fromEntries(formData.entries());
        const action = data.action;
        const scheduleId = data.schedule_id;

        console.log('Schedule data being sent:', data);

        let url = API.create;
        if (action === 'update' && scheduleId) {
            url = API.update.replace('__ID__', scheduleId);
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN },
                body: JSON.stringify(data),
            });

            console.log('Response status:', response.status);
            const result = await response.json();
            console.log('Server response:', result);

            if (result.success) {
                // Show success message
                alert(`✓ Schedule "${data.title}" created successfully for ${data.staff}!`);
                // Reload to reflect changes
                location.reload();
            } else {
                alert("Failed: " + (result.error || "Unknown error"));
            }
        } catch (err) {
            console.error('Schedule submission error:', err);
            alert("Error: Could not save schedule. " + err.message);
        }
    }

    async function deleteSchedule() {
        const scheduleId = modalScheduleId.value;
        if (!scheduleId || !confirm("Are you sure you want to delete this schedule?")) return;

        const url = API.delete.replace('__ID__', scheduleId);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN, "Content-Type": "application/json" },
            });
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

            const result = await response.json();
            if (result.success) {
                location.reload(); // Easiest way to reflect change
            } else {
                 alert("Failed to delete: " + (result.error || "Unknown error"));
            }
        } catch (error) {
            console.error('Failed to delete schedule:', error);
            alert(`Error: Could not delete schedule. ${error.message}`);
        }
    }


    // --- RENDERING ---
    function renderWeekView() {
        const { start, end } = getWeekRange(currentDate);
        rangeLabel.textContent = formatDateRangeLabel(start, end);

        // Filter staff based on both job tab and staff dropdown
        const staffToRender = allStaff.filter(staff => {
            const jobMatch = currentJobFilter === 'ALL' || staff.job_type === currentJobFilter;
            const staffMatch = currentStaffIdFilter === 'ALL' || String(staff.id) === currentStaffIdFilter;
            return jobMatch && staffMatch;
        });

        let html = '<div class="schedule-grid">';

        // Render day headers
        const dayNames = ['Sun','Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        html += `<div class="grid-staff-cell header"></div>`; // Placeholder for staff column header
        dayNames.forEach((name, i) => {
            const day = new Date(start);
            day.setDate(start.getDate() + i);
            html += `<div class="grid-header-cell">${name}<br>${day.getDate()}</div>`;
        });

        // Render staff rows and event cells
        staffToRender.forEach(staff => {
            html += `<div class="grid-staff-cell" data-staff-id="${staff.id}">
                        <div class="staff-info-box">
                            <div class="staff-name-tag">${staff.name}</div>
                            <div class="staff-time-info">${staff.total_time}</div>
                        </div>
                    </div>`;

            for (let i = 0; i < 7; i++) {
                const date = new Date(start);
                date.setDate(start.getDate() + i);
                const dayKey = formatDateToISO(date);

                const eventsOnDay = INITIAL_EVENTS.filter(e => e.date === dayKey && String(e.staff_id) === String(staff.id));
                let eventsHtml = eventsOnDay.map(event => {
                    const eventClass = `event-${(event.event_type || 'other').toLowerCase().replace(/\s+/g, '-')}`;
                    return `<div class="event-block ${eventClass}" data-event-id="${event.id}" title="${event.title}">${event.title}</div>`;
                }).join('');

                html += `<div class="grid-event-cell" data-date="${dayKey}" data-staff="${staff.id}">${eventsHtml}</div>`;
            }
        });

        html += '</div>';
        calendarGridContainer.innerHTML = html;
        attachCellEventListeners();
    }

    function renderMonthView() {
        const { start: startDate, end: endDate, month: currentMonth } = getMonthStartAndEnd(currentDate);
        rangeLabel.textContent = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });

        let html = '<div class="schedule-grid month-grid-layout">';
        const dayNames = ['Sun','Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayNames.forEach(name => {
            html += `<div class="grid-header-cell month-day-name">${name}</div>`;
        });

        // Filter events based on dropdown
        const filteredEvents = INITIAL_EVENTS.filter(event =>
            currentStaffIdFilter === 'ALL' || String(event.staff_id) === currentStaffIdFilter
        );

        let day = new Date(startDate);
        while (day <= endDate) {
            const dayKey = formatDateToISO(day);
            const isOutsideMonth = day.getMonth() !== currentMonth;
            const classes = isOutsideMonth ? 'outside-month' : '';

            const eventsOnDay = filteredEvents.filter(e => e.date === dayKey);
            let eventsHtml = eventsOnDay.map(event => {
                const eventClass = `event-${(event.event_type || 'other').toLowerCase().replace(/\s+/g, '-')}`;
                return `<div class="month-event-bubble ${eventClass}" data-event-id="${event.id}" title="${event.title}">${event.title}</div>`;
            }).join('');

            html += `<div class="month-cell grid-event-cell ${classes}" data-date="${dayKey}">
                        <div class="day-number">${day.getDate()}</div>
                        <div class="month-events-container">${eventsHtml}</div>
                    </div>`;
            day.setDate(day.getDate() + 1);
        }

        html += '</div>';
        calendarGridContainer.innerHTML = html;
        attachCellEventListeners();
    }

    function renderCalendar() {
        if (currentView === 'week') {
            renderWeekView();
        } else {
            renderMonthView();
        }
    }


    // --- EVENT HANDLERS ---
    function attachCellEventListeners() {
        // Edit event
        document.querySelectorAll('.event-block, .month-event-bubble').forEach(block => {
            block.addEventListener('click', (e) => {
                e.stopPropagation();
                openModalForEdit(e.target.dataset.eventId);
            });
        });

        // Add event
        document.querySelectorAll('.grid-event-cell').forEach(cell => {
            const hasEvents = cell.querySelector('.event-block, .month-event-bubble');
            if (!hasEvents || currentView === 'month') {
                cell.addEventListener('click', () => {
                    const staffId = cell.dataset.staff; // Might be undefined in month view
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
        const button = e.target.closest('.btn-view');
        if (!button) return;

        currentView = button.dataset.view;
        document.querySelectorAll('.btn-view').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        
        currentDate = new Date(); // Reset to today when toggling view
        renderCalendar();
    }

    function handleJobTabClick(e) {
        const button = e.target.closest('.tab-button');
        if (!button) return;

        currentJobFilter = button.dataset.job || 'ALL';
        teamTabsContainer.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        // When a job tab is clicked, reset the staff dropdown to "All"
        staffFilterSelect.value = 'ALL';
        currentStaffIdFilter = 'ALL';

        renderCalendar();
    }

    function handleStaffFilterChange(e) {
        currentStaffIdFilter = e.target.value;

        // When a specific staff is selected, deactivate job tabs
        teamTabsContainer.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        // And set the job filter to ALL to not conflict
        currentJobFilter = 'ALL';

        renderCalendar();
    }

    // --- INITIALIZATION ---
    function init() {
        // Attach main listeners
        prevBtn.addEventListener('click', () => handleNavigation(-1));
        nextBtn.addEventListener('click', () => handleNavigation(1));
        viewToggleGroup.addEventListener('click', handleViewToggle);
        teamTabsContainer.addEventListener('click', handleJobTabClick);
        staffFilterSelect.addEventListener('change', handleStaffFilterChange);

        // Modal Listeners
        openAddBtn.addEventListener('click', () => openModalForAdd(new Date().toISOString().split('T')[0], null));
        closeModalBtn.addEventListener('click', hideModal);
        cancelModalBtn.addEventListener('click', hideModal);

        // Form Submission
        scheduleForm.addEventListener('submit', submitSchedule);
        deleteScheduleBtn.addEventListener('click', deleteSchedule);

        // Initial Render
        renderCalendar();
    }

    init();
});
