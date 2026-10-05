const form = document.getElementById('loginForm');
const errorBox = document.getElementById('loginError');
const btn = document.getElementById('loginBtn');

const demoBtn = document.getElementById('demoBtn');
if (demoBtn) {
  demoBtn.addEventListener('click', async () => {
    errorBox.textContent = '';
    demoBtn.disabled = true;
    try {
      const res = await fetch('/api/auth/demo-login', { method: 'POST' });
      if (!res.ok) throw new Error('Demo login is not available');
      window.location.href = '/';
    } catch (err) {
      errorBox.textContent = err.message;
      demoBtn.disabled = false;
    }
  });
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorBox.textContent = '';
  btn.disabled = true;
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('email').value.trim(),
        password: document.getElementById('password').value,
      }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Sign in failed');
    }
    window.location.href = '/';
  } catch (err) {
    errorBox.textContent = err.message;
    document.getElementById('password').value = '';
  } finally {
    btn.disabled = false;
  }
});
