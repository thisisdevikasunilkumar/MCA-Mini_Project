/* JavaScript to Sticky Navbar on Scroll */
$(document).ready(function () {
    $(window).scroll(function () {
        if ($(this).scrollTop() > 550) {
            $('.navbar').addClass('solid');
            $('.back-to-top').addClass('visible');
        } else {
            $('.navbar').removeClass('solid');
            $('.back-to-top').removeClass('visible');
        }
    });
});


/* JavaScript to Smooth Scrolling */
$(document).ready(function () {
    $("a").on('click', function (event) {
        if (this.hash !== "") {
            event.preventDefault();
            var hash = this.hash;
            $('html, body').animate({
                scrollTop: $(hash).offset().top
            }, 800, function () {
                window.location.hash = hash;
            });
        }
    });
});


/* JavaScript to Toggle dropdown on click */
document.addEventListener("DOMContentLoaded", () => {
    const dropdownToggle = document.querySelector(".dropdown-toggle");
    const dropdownMenu = document.querySelector(".dropdown-menu");
    
    dropdownToggle.addEventListener("click", (e) => {
      e.preventDefault();
      dropdownMenu.classList.toggle("show");
    });

    // Close dropdown if clicked outside
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".dropdown")) {
            dropdownMenu.classList.remove("show");
        }
    });
});