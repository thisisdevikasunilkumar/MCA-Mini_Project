document.addEventListener("DOMContentLoaded", function () {

    function renderCalendar() {
        const calendar = document.getElementById("attendanceCalendar");
        const monthTitle = document.getElementById("monthTitle");

        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth();

        // Month name
        const monthName = today.toLocaleString('default', { month: 'long' });
        monthTitle.textContent = `${monthName} ${year}`;

        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const firstDay = new Date(year, month, 1).getDay();

        calendar.innerHTML = "";

        // Empty slots before 1st day
        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement("div");
            empty.classList.add("calendar-day");
            empty.style.visibility = "hidden";
            calendar.appendChild(empty);
        }

        // Days generation
        for (let d = 1; d <= daysInMonth; d++) {
            const dayBox = document.createElement("div");
            dayBox.classList.add("calendar-day");

            const weekday = new Date(year, month, d).getDay();

            // Add attendance status class from Django → JS data
            if (attendanceData[d]) {
                if (attendanceData[d] === "Active") dayBox.classList.add("present");
                if (attendanceData[d] === "Inactive") dayBox.classList.add("absent");
                if (attendanceData[d] === "Late") dayBox.classList.add("late");
            }

            // Weekend styling
            if (weekday === 0 || weekday === 6) {
                dayBox.classList.add("weekend");
            }

            dayBox.innerHTML = `
                <div class="day-number">${d}</div>
                <div class="day-label">${["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][weekday]}</div>
            `;

            // Animation on click
            dayBox.addEventListener('click', () => {
                dayBox.style.transform = 'scale(1.1)';
                setTimeout(() => dayBox.style.transform = '', 200);
            });

            calendar.appendChild(dayBox);
        }
    }

    renderCalendar();
});
