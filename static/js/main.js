// MWS MatchFlow — Main JS

// ─── Active sidebar link ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Auto-close flash messages after 4s
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 4000);
  });

  // Checkbox team selection highlight
  document.querySelectorAll('input[type="checkbox"][name="team_ids"]').forEach(cb => {
    cb.addEventListener('change', function () {
      const label = this.closest('label');
      if (this.checked) {
        label.style.borderColor = 'var(--neon)';
        label.style.background = 'rgba(37,99,235,0.08)';
      } else {
        label.style.borderColor = 'var(--border)';
        label.style.background = 'var(--bg-primary)';
      }
    });
  });
});
