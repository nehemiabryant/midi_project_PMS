document.addEventListener('DOMContentLoaded', () => {
  initPagination();
});

function initPagination() {
  document.querySelectorAll('.dashboard-pagination').forEach((pagination) => {
    pagination.querySelectorAll('.dashboard-page-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        pagination
          .querySelectorAll('.dashboard-page-btn')
          .forEach((button) => button.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  });
}
