document.addEventListener('DOMContentLoaded', () => {
    // --- Global State & Configuration ---
    const API = window.API || {};
    const CSRF_TOKEN = window.CSRF_TOKEN;
    const INITIAL_EVENTS = window.INIT_EVENTS || [];

    let currentDate = new Date();
    let currentView = 'week'; 
    let currentJobFilter = 'ALL';
    let currentStaffIdFilter = 'ALL';

    // --- DOM Elements ---
    const calendarGridContainer = document.getElementById('calendar');
    const rangeLabel = document.getElementById('rangeLabel');
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

    // --- Data Pre-processing ---
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
        ev.staff_id = staffId; 
        ev.job_type = normalizeJobType(staffJobTypeMap[staffId] || '');
    });

    // --- Helper Functions ---
    function formatDateToISO(date) {
        let d = new Date(date);
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    }

    function getWeekRange(date) {
        let start = new Date(date);
        start.setDate(date.getDate() - date.getDay()); // Sunday logic
        start.setHours(0,0,0,0);
        let end = new Date(start);
        end.setDate(start.getDate() + 6);
        return { start, end };
    }

    function getMonthStartAndEnd(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        let firstDay = new Date(year, month, 1);
        let startDay = new Date(firstDay);
        startDay.setDate(firstDay.getDate() - firstDay.getDay()); // Sunday logic
        let endDay = new Date(startDay);
        endDay.setDate(startDay.getDate() + 41); 
        return { start: startDay, end: endDay, month: month };
    }

    // --- Modal Logic ---
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
        modalDate.value = date || formatDateToISO(new Date());
        if (staffId) modalStaffSelect.value = staffId;
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

        modalTitleInput.value = event.title || '';
        modalDescription.value = event.description || '';
        modalStaffSelect.value = event.staff_id || '';
        modalEventType.value = event.event_type || 'Office';
        modalDate.value = event.date || '';
        showModal();
    }

    // --- Rendering Logic ---
    function renderWeekView() {
        const { start, end } = getWeekRange(currentDate);
        rangeLabel.textContent = `${start.toLocaleDateString()} - ${end.toLocaleDateString()}`;

        const staffToRender = allStaff.filter(s => {
            const jobMatch = currentJobFilter === 'ALL' || s.job_type === currentJobFilter;
            const staffMatch = currentStaffIdFilter === 'ALL' || String(s.id) === currentStaffIdFilter;
            return jobMatch && staffMatch;
        });

        let html = '<div class="schedule-grid">';
        const days = ['Sun','Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        
        html += `<div class="grid-header-cell">Staff Members</div>`;
        days.forEach((name, i) => {
            let d = new Date(start);
            d.setDate(start.getDate() + i);
            html += `<div class="grid-header-cell">${name}<br>${d.getDate()}</div>`;
        });

        staffToRender.forEach(staff => {
            html += `<div class="grid-staff-cell">
                <div class="staff-info-box">
                    <div class="staff-name-tag">${staff.name}</div>
                    <div class="staff-time-info">${staff.total_time}</div>
                </div>
            </div>`;

            for (let i = 0; i < 7; i++) {
                let d = new Date(start);
                d.setDate(start.getDate() + i);
                const key = formatDateToISO(d);
                const dayEvents = INITIAL_EVENTS.filter(e => e.date === key && String(e.staff_id) === String(staff.id));
                
                let evHtml = dayEvents.map(e => {
                    const cls = `event-${(e.event_type || 'other').toLowerCase().replace(/\s+/g, '-')}`;
                    return `<div class="event-block ${cls}" data-event-id="${e.id}">${e.title}</div>`;
                }).join('');

                html += `<div class="grid-event-cell" data-date="${key}" data-staff="${staff.id}">${evHtml}</div>`;
            }
        });
        html += '</div>';
        calendarGridContainer.innerHTML = html;
        attachCellListeners();
    }

    function renderMonthView() {
        const { start, month } = getMonthStartAndEnd(currentDate);
        rangeLabel.textContent = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });

        let html = '<div class="month-grid-layout">';
        ['Sun','Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(day => {
            html += `<div class="grid-header-cell">${day}</div>`;
        });

        let d = new Date(start);
        for (let i = 0; i < 42; i++) {
            const key = formatDateToISO(d);
            const isOutside = d.getMonth() !== month;
            const dayEvents = INITIAL_EVENTS.filter(e => e.date === key && 
                (currentStaffIdFilter === 'ALL' || String(e.staff_id) === currentStaffIdFilter));

            let evHtml = dayEvents.map(e => {
                const cls = `event-${(e.event_type || 'other').toLowerCase().replace(/\s+/g, '-')}`;
                return `<div class="event-block ${cls}" data-event-id="${e.id}">${e.title}</div>`;
            }).join('');

            html += `<div class="grid-event-cell month-cell ${isOutside ? 'outside-month' : ''}" data-date="${key}">
                <div class="day-number">${d.getDate()}</div>
                <div class="event-container">${evHtml}</div>
            </div>`;
            d.setDate(d.getDate() + 1);
        }
        html += '</div>';
        calendarGridContainer.innerHTML = html;
        attachCellListeners();
    }

    function renderCalendar() {
        if (currentView === 'week') renderWeekView();
        else renderMonthView();
    }

    // --- API Interactions ---
    async function submitSchedule(e) {
        e.preventDefault();
        const formData = new FormData(scheduleForm);
        const data = Object.fromEntries(formData.entries());
        let url = data.action === 'update' ? API.update.replace('__ID__', data.schedule_id) : API.create;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN },
                body: JSON.stringify(data),
            });
            const result = await response.json();
            if (result.success) location.reload();
            else alert("Error: " + (result.error || "Unknown error"));
        } catch (err) {
            alert("Submission failed: " + err.message);
        }
    }

    async function deleteSchedule() {
        const scheduleId = modalScheduleId.value;
        if (!scheduleId || !confirm("Are you sure?")) return;
        try {
            const response = await fetch(API.delete.replace('__ID__', scheduleId), {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN, "Content-Type": "application/json" },
            });
            const result = await response.json();
            if (result.success) location.reload();
        } catch (error) {
            alert("Delete failed.");
        }
    }

    // --- Event Handlers ---
    function attachCellListeners() {
        // Edit event
        document.querySelectorAll('.event-block').forEach(block => {
            block.onclick = (e) => {
                e.stopPropagation();
                openModalForEdit(e.target.dataset.eventId);
            };
        });

        // Add event
        document.querySelectorAll('.grid-event-cell').forEach(cell => {
            cell.onclick = () => openModalForAdd(cell.dataset.date, cell.dataset.staff);
        });
    }

    // --- Initialize Listeners ---
    prevBtn.onclick = () => {
        if (currentView === 'week') currentDate.setDate(currentDate.getDate() - 7);
        else currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    };

    nextBtn.onclick = () => {
        if (currentView === 'week') currentDate.setDate(currentDate.getDate() + 7);
        else currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    };

    document.querySelectorAll('.btn-view').forEach(btn => {
        btn.onclick = (e) => {
            document.querySelectorAll('.btn-view').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentView = e.target.dataset.view;
            renderCalendar();
        };
    });

    teamTabsContainer.addEventListener('click', (e) => {
        const button = e.target.closest('.tab-button');
        if (!button) return;
        currentJobFilter = button.dataset.job || 'ALL';
        teamTabsContainer.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        staffFilterSelect.value = 'ALL';
        currentStaffIdFilter = 'ALL';
        renderCalendar();
    });

    staffFilterSelect.addEventListener('change', (e) => {
        currentStaffIdFilter = e.target.value;
        currentJobFilter = 'ALL';
        teamTabsContainer.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        renderCalendar();
    });

    closeModalBtn.onclick = hideModal;
    cancelModalBtn.onclick = hideModal;
    scheduleForm.onsubmit = submitSchedule;
    deleteScheduleBtn.onclick = deleteSchedule;
    openAddBtn.onclick = () => openModalForAdd(formatDateToISO(new Date()), null);

    renderCalendar();
});