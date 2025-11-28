// ===================== Profile Image Upload Preview =====================
const fileInput = document.getElementById("profileUpload");
const previewImg = document.getElementById("previewImg");
const imageLabel = document.getElementById("imageLabel");

fileInput.addEventListener("change", function () {
    const file = this.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function () {
            previewImg.src = reader.result;
            previewImg.classList.remove("camera-icon");
            previewImg.classList.add("preview");
            imageLabel.style.display = "none";
        };
        reader.readAsDataURL(file);
    }
});

// ===================== Reset Image Handler =====================
function resetProfileImage() {
    const defaultImg = previewImg.getAttribute("data-default-img");

    previewImg.src = defaultImg;
    previewImg.className = "camera-icon";
    imageLabel.textContent = "Profile Image";
    imageLabel.style.display = "block";
    fileInput.value = "";
}

// ===================== Intl Tel Input =====================
var phoneInput = document.querySelector("#phone");
window.intlTelInput(phoneInput, {
    utilsScript: "/static/phone/js/utils.js"
});

// ===================== Country / State / City =====================
async function getCountries() {
    const res = await fetch("https://countriesnow.space/api/v0.1/countries/positions");
    const data = await res.json();
    return data.data.map(c => c.name);
}

async function getStates(country) {
    const res = await fetch("https://countriesnow.space/api/v0.1/countries/states", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ country })
    });
    const data = await res.json();
    return data.data.states.map(s => s.name);
}

async function getCities(country, state) {
    const res = await fetch("https://countriesnow.space/api/v0.1/countries/state/cities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ country, state })
    });
    const data = await res.json();
    return data.data;
}

// Initialize dropdowns
(async function () {
    const countryDropdown = document.getElementById("country");
    const stateDropdown = document.getElementById("state");
    const cityDropdown = document.getElementById("city");

    const countries = await getCountries();
    countries.forEach(c => {
        countryDropdown.innerHTML += `<option value="${c}">${c}</option>`;
    });

    countryDropdown.addEventListener("change", async function () {
        stateDropdown.innerHTML = `<option>Loading...</option>`;
        cityDropdown.innerHTML = `<option value="">Select city</option>`;

        const states = await getStates(this.value);
        stateDropdown.innerHTML = `<option value="">Select state</option>`;
        states.forEach(s => {
            stateDropdown.innerHTML += `<option value="${s}">${s}</option>`;
        });
    });

    stateDropdown.addEventListener("change", async function () {
        cityDropdown.innerHTML = `<option>Loading...</option>`;

        const cities = await getCities(countryDropdown.value, this.value);
        cityDropdown.innerHTML = `<option value="">Select city</option>`;
        cities.forEach(c => {
            cityDropdown.innerHTML += `<option value="${c}">${c}</option>`;
        });
    });

})();
