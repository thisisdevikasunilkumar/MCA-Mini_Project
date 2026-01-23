document.addEventListener("DOMContentLoaded", function () {

  // Close all dropdowns
  function closeAllDropdowns() {
    document.querySelectorAll(".status-wrapper").forEach(w => {
      w.classList.remove("active");
    });
  }

  document.querySelectorAll(".status-wrapper").forEach(wrapper => {

    const button = wrapper.querySelector(".status-btn");
    const dropdown = wrapper.querySelector(".status-dropdown");
    const items = dropdown.querySelectorAll("li");

    const taskItem = wrapper.closest(".task-item");
    const scheduleId = taskItem.dataset.id;

    // =============================
    // Toggle Dropdown
    // =============================
    button.addEventListener("click", function (e) {
      e.stopPropagation();
      closeAllDropdowns();
      wrapper.classList.toggle("active");
    });

    // =============================
    // Select Status
    // =============================
    items.forEach(item => {
      item.addEventListener("click", function () {

        const newStatus = item.dataset.value;
        const oldStatus = wrapper.dataset.currentStatus || "Pending";

        // Update UI instantly
        button.childNodes[0].nodeValue = newStatus + " ";
        wrapper.dataset.currentStatus = newStatus;
        wrapper.classList.remove("active");

        // =============================
        // AJAX POST
        // =============================
        fetch("/update-staff-response/", {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/x-www-form-urlencoded"
          },
          body: `schedule_id=${scheduleId}&response=${encodeURIComponent(newStatus)}`
        })
        .then(response => response.json())
        .then(data => {
          if (!data.success) {
            // Revert on failure
            button.childNodes[0].nodeValue = oldStatus + " ";
            wrapper.dataset.currentStatus = oldStatus;
            alert("Status update failed");
          }
        })
        .catch(error => {
          console.error(error);
          button.childNodes[0].nodeValue = oldStatus + " ";
          wrapper.dataset.currentStatus = oldStatus;
          alert("Server error");
        });

      });
    });

  });

  // Close dropdown when clicking outside
  document.addEventListener("click", closeAllDropdowns);

});

// =============================
// CSRF TOKEN HELPER
// =============================
function getCookie(name) {
  let cookieValue = null;

  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");

    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
