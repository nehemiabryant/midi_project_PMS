document.addEventListener('DOMContentLoaded', () => {
    initSidebarToggle();
});

function initSidebarToggle() {
    document.querySelectorAll('.nav-toggle').forEach((btn) => {
        btn.addEventListener('click', () => {
            const submenu = btn.nextElementSibling;
            const chevron = btn.querySelector('.chevron');

            document.querySelectorAll('.nav-submenu.open').forEach((openMenu) => {
                if (openMenu !== submenu) {
                    openMenu.classList.remove('open');
                    const otherChevron = openMenu.previousElementSibling?.querySelector('.chevron');
                    if (otherChevron) otherChevron.classList.remove('open');
                }
            });

            submenu?.classList.toggle('open');
            chevron?.classList.toggle('open');
        });
    });
}
