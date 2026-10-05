const userRole = document.body.dataset.role;

function escapeHtml(s = '') {
  return String(s ?? '').replace(/[&<>'"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
}

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) { window.location.href = '/login'; throw new Error('Signed out'); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

document.getElementById('logoutBtn').onclick = async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
};

// ---- tabs
if (userRole === 'admin') document.querySelectorAll('.admin-only').forEach((el) => el.classList.remove('hidden'));
document.querySelectorAll('.tab').forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t === tab));
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));
    document.getElementById(`tab-${tab.dataset.tab}`).classList.remove('hidden');
    if (tab.dataset.tab === 'users') loadUsers();
  };
});

// ---- audit log
async function loadAudit() {
  const blockedOnly = document.getElementById('blockedOnly').checked;
  const rows = await api('GET', `/api/admin/audit?limit=200${blockedOnly ? '&blocked_only=true' : ''}`);
  document.getElementById('auditCount').textContent = `${rows.length} most recent`;
  document.getElementById('auditBody').innerHTML = rows.map((r) => {
    const blocked = r.guardrail_result === 'block';
    const outcome = blocked
      ? `<span class="badge badge-block">blocked</span> <span class="muted small">${escapeHtml(r.blocked_reason)}</span>`
      : `<span class="badge">${escapeHtml(r.source_used)}</span>`;
    const who = r.email ? `${escapeHtml(r.email)} <span class="muted small">(${escapeHtml(r.role)})</span>` : '<span class="muted">—</span>';
    return `<tr class="${blocked ? 'row-block' : ''}">
      <td class="nowrap">${escapeHtml(r.created_at.replace('T', ' ').slice(0, 19))}</td>
      <td>${who}</td>
      <td class="q">${escapeHtml(r.question)}</td>
      <td>${outcome}</td>
      <td class="small muted">${r.trace.map(escapeHtml).join('<br>')}</td></tr>`;
  }).join('') || '<tr><td colspan="5" class="muted">Nothing logged yet.</td></tr>';
}
document.getElementById('refreshAudit').onclick = loadAudit;
document.getElementById('blockedOnly').onchange = loadAudit;

// ---- accounts (admin only)
async function loadUsers() {
  const users = await api('GET', '/api/admin/users');
  document.getElementById('usersBody').innerHTML = users.map((u) => `<tr>
    <td>${escapeHtml(u.email)}</td><td>${escapeHtml(u.employee_id)}</td><td>${escapeHtml(u.role)}</td>
    <td>${u.active ? '<span class="badge">active</span>' : '<span class="badge badge-block">disabled</span>'}</td>
    <td class="actions">
      <button class="secondary-btn small-btn" data-act="toggle" data-id="${u.id}" data-active="${u.active}">${u.active ? 'Disable' : 'Enable'}</button>
      <button class="secondary-btn small-btn" data-act="password" data-id="${u.id}">Reset password</button>
    </td></tr>`).join('');
}

document.getElementById('usersBody').onclick = async (e) => {
  const btn = e.target.closest('button[data-act]');
  if (!btn) return;
  const msg = document.getElementById('userMsg');
  msg.className = 'small';
  try {
    if (btn.dataset.act === 'toggle') {
      await api('PATCH', `/api/admin/users/${btn.dataset.id}/active`, { active: btn.dataset.active !== 'true' });
    } else {
      const pw = window.prompt('New temporary password (min 8 characters):');
      if (!pw) return;
      await api('POST', `/api/admin/users/${btn.dataset.id}/password`, { password: pw });
      msg.textContent = 'Password updated.';
    }
    await loadUsers();
  } catch (err) { msg.textContent = err.message; msg.className = 'small form-error'; }
};

document.getElementById('newUserForm').onsubmit = async (e) => {
  e.preventDefault();
  const msg = document.getElementById('userMsg');
  try {
    const u = await api('POST', '/api/admin/users', {
      employee_id: document.getElementById('nuEmployee').value.trim(),
      role: document.getElementById('nuRole').value,
      password: document.getElementById('nuPassword').value,
    });
    msg.textContent = `Created ${u.email}`;
    msg.className = 'small';
    e.target.reset();
    await loadUsers();
  } catch (err) { msg.textContent = err.message; msg.className = 'small form-error'; }
};

loadAudit();
