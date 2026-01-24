document.addEventListener("DOMContentLoaded", function () {
    const calendar = document.getElementById("attendanceCalendar");
    const monthSelect = document.getElementById("monthSelect");
    const yearSelect = document.getElementById("yearSelect");

    const today = new Date();
    let currentMonth = today.getMonth(); 
    let currentYear = today.getFullYear();

    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    function initSelectors() {
        monthNames.forEach((name, index) => {
            const opt = document.createElement("option");
            opt.value = index;
            opt.textContent = name;
            if (index === currentMonth) opt.selected = true;
            monthSelect.appendChild(opt);
        });

        for (let y = 2020; y <= 2030; y++) {
            const opt = document.createElement("option");
            opt.value = y;
            opt.textContent = y;
            if (y === currentYear) opt.selected = true;
            yearSelect.appendChild(opt);
        }
    }

    function renderCalendar(month, year) {
        calendar.innerHTML = "";

        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const firstDay = new Date(year, month, 1).getDay();

        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement("div");
            empty.classList.add("calendar-day");
            empty.style.visibility = "hidden";
            calendar.appendChild(empty);
        }

        for (let d = 1; d <= daysInMonth; d++) {
            const dayBox = document.createElement("div");
            dayBox.classList.add("calendar-day");

            const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            const status = attendanceData[formattedDate];

            if (status === "Active") {
                dayBox.classList.add("present");
            } else if (status === "Inactive") {
                dayBox.classList.add("absent");
            } else if (status === "Late") {
                dayBox.classList.add("late");
            }

            const dateObj = new Date(year, month, d);
            const weekday = dateObj.getDay();

            if ((weekday === 0 || weekday === 6) && !status) {
                dayBox.classList.add("weekend");
            }

            dayBox.innerHTML = `
                <div class="day-number">${d}</div>
                <div class="day-label">${["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][weekday]}</div>
            `;

            calendar.appendChild(dayBox);
        }
    }

    monthSelect.addEventListener("change", () => {
        currentMonth = parseInt(monthSelect.value);
        renderCalendar(currentMonth, currentYear);
    });

    yearSelect.addEventListener("change", () => {
        currentYear = parseInt(yearSelect.value);
        renderCalendar(currentMonth, currentYear);
    });

    initSelectors();
    renderCalendar(currentMonth, currentYear);
});