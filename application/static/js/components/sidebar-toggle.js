document.addEventListener("DOMContentLoaded", function() {
    // Ambil semua elemen dengan class nav-toggle
    const toggles = document.querySelectorAll(".nav-toggle");

    toggles.forEach(toggle => {
        toggle.addEventListener("click", function() {
            const chevron = this.querySelector(".chevron");
            if (chevron) chevron.classList.toggle("open");

            const submenu = this.nextElementSibling;
            if (submenu && submenu.classList.contains("nav-submenu")) {
                submenu.classList.toggle("open");
            }
        });
    });
});