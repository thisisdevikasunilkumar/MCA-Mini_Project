document.addEventListener("DOMContentLoaded", function () {
  
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

    // Toggle Dropdown logic modified
    button.addEventListener("click", function (e) {
      e.stopPropagation();
      const isActive = wrapper.classList.contains("active");
      closeAllDropdowns(); // മറ്റുള്ളവ ക്ലോസ് ചെയ്യുക
      if (!isActive) {
        wrapper.classList.add("active"); // നിലവിലുള്ളത് ഓപ്പൺ ചെയ്യുക
      }
    });

    items.forEach(item => {
      item.addEventListener("click", function () {
        const newStatus = item.dataset.value;
        const oldStatus = wrapper.dataset.currentStatus || "Pending";
        const statusText = button.querySelector(".status-text");

        // UI Update
        statusText.textContent = newStatus;
        wrapper.dataset.currentStatus = newStatus;
        wrapper.classList.remove("active");

        // AJAX POST
        // ശ്രദ്ധിക്കുക: URL നിങ്ങളുടെ urls.py-ൽ ഉള്ളതുപോലെ തന്നെ നൽകുക
        fetch("/accounts/update-staff-response/", {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/x-www-form-urlencoded"
          },
          body: `schedule_id=${scheduleId}&response=${encodeURIComponent(newStatus)}`
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
          if (!data.success) {
            revertStatus(statusText, wrapper, oldStatus);
            alert("Error: " + data.error);
          }
        })
        .catch(error => {
          console.error("Fetch Error:", error);
          revertStatus(statusText, wrapper, oldStatus);
          alert("Server error. Please try again.");
        });
      });
    });
  });

  function revertStatus(textElem, wrapElem, oldVal) {
    textElem.textContent = oldVal;
    wrapElem.dataset.currentStatus = oldVal;
  }

  document.addEventListener("click", closeAllDropdowns);
});