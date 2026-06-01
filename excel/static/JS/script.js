// Toggle menú mobile
function toggleMenu() {
    const navbar = document.querySelector(".responsive-navbar");
    if (navbar) {
        navbar.classList.toggle("active");
    }
}

// Mostrar/ocultar bloques complementarios
document.addEventListener("DOMContentLoaded", () => {
    const toggles = document.querySelectorAll('[id^="toggleComp"]');

    toggles.forEach((toggle) => {
        toggle.addEventListener("change", function () {
            const compBlockId = this.id.replace("toggleComp", "compBlock");
            const compBlock = document.getElementById(compBlockId);

            if (compBlock) {
                if (this.checked) {
                    compBlock.classList.add("visible");
                } else {
                    compBlock.classList.remove("visible");
                }
            }
        });
    });
});

