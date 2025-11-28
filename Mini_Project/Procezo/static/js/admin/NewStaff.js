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
    const defaultImageSrc = previewImg.getAttribute("data-default-img");
    previewImg.src = defaultImageSrc;
    previewImg.className = "camera-icon";
    imageLabel.textContent = "Profile Image";
    imageLabel.style.display = "block";
    fileInput.value = "";
}
