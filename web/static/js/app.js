// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert-dismissible').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    }, 5000);
  });

  // Collapsible global navigation sidebar (persisted across pages).
  const wrapper = document.getElementById('wrapper');
  if (wrapper) {
    const KEY = 'cr_sidebar_collapsed';
    if (localStorage.getItem(KEY) === '1') wrapper.classList.add('sidebar-collapsed');
    const setCollapsed = (on) => {
      wrapper.classList.toggle('sidebar-collapsed', on);
      localStorage.setItem(KEY, on ? '1' : '0');
    };
    const close = document.getElementById('sidebar-close');
    const open = document.getElementById('sidebar-open');
    if (close) close.addEventListener('click', () => setCollapsed(true));
    if (open) open.addEventListener('click', () => setCollapsed(false));
  }
});
