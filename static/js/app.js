const chat = document.getElementById('chat');
const form = document.getElementById('chatForm');
const question = document.getElementById('question');
const trace = document.getElementById('trace');
const sourceUsed = document.getElementById('sourceUsed');
const userRole = document.body.dataset.role;

const SOURCE_LABELS = {
  private_kb: 'Company knowledge base',
  personal_data: 'Your HR record',
  web_search: 'Web search',
  direct: 'Direct reply',
  insufficient_evidence: 'Not enough evidence',
  blocked: 'Blocked by privacy policy',
};
const sourceLabel = (s) => SOURCE_LABELS[s] || s;

function escapeHtml(s = '') {
  return s.replace(/[&<>'"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
}
function formatText(s = '') { return escapeHtml(s).replace(/\n/g, '<br>'); }

function addMessage(role, text, source = '', citations = []) {
  const blocked = source === 'blocked';
  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;
  const citeHtml = citations.length
    ? `<div class="citations"><strong>Sources</strong><br>${citations
        .map((c) => (c.url
          ? `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.title)}</a>`
          : escapeHtml(c.title)))
        .join('<br>')}</div>`
    : '';
  const sourceHtml = source ? `<div class="answer-source">${blocked ? '🛡 ' : 'Source: '}${escapeHtml(sourceLabel(source))}</div>` : '';
  wrap.innerHTML = `<div class="avatar">AI</div><div class="bubble${blocked ? ' blocked' : ''}">${formatText(text)}${sourceHtml}${citeHtml}</div>`;
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

function renderTrace(items = []) {
  trace.innerHTML = items.length
    ? items.map((x) => `<div class="trace-item${x.includes('BLOCKED') || x.includes('REPLACED') ? ' trace-block' : ''}">${escapeHtml(x)}</div>`).join('')
    : '<div class="empty">No trace.</div>';
}

function goToLogin() { window.location.href = '/login'; }

async function askAgent(q) {
  addMessage('user', q);
  question.value = '';
  renderTrace(['Running LangGraph workflow...']);
  sourceUsed.textContent = 'Running';
  const btn = form.querySelector('button');
  btn.disabled = true;
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    });
    if (res.status === 401) { goToLogin(); return; }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    addMessage('assistant', data.answer, data.source_used, data.citations || []);
    renderTrace(data.trace || []);
    sourceUsed.textContent = sourceLabel(data.source_used);
  } catch (e) {
    addMessage('assistant', `Error: ${e.message}`);
    renderTrace(['Request failed']);
    sourceUsed.textContent = 'Error';
  } finally {
    btn.disabled = false;
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = question.value.trim();
  if (q) askAgent(q);
});
question.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
});
document.querySelectorAll('.example').forEach((b) => b.addEventListener('click', () => askAgent(b.textContent.trim())));

// ---- account controls
document.getElementById('logoutBtn').onclick = async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  goToLogin();
};
// Buttons are only shown to roles that may use them. The server enforces this regardless.
if (userRole === 'admin') document.getElementById('openUpload').classList.remove('hidden');
if (userRole === 'admin' || userRole === 'hr') document.getElementById('adminLink').classList.remove('hidden');

// ---- document upload (admin only)
const modal = document.getElementById('uploadModal');
document.getElementById('openUpload').onclick = () => modal.classList.remove('hidden');
document.getElementById('closeUpload').onclick = () => modal.classList.add('hidden');
document.getElementById('uploadBtn').onclick = async () => {
  const file = document.getElementById('fileInput').files[0];
  const status = document.getElementById('uploadStatus');
  if (!file) { status.textContent = 'Choose a file first.'; return; }
  status.textContent = 'Indexing document...';
  const fd = new FormData();
  fd.append('file', file);
  fd.append('visibility', document.getElementById('visibility').value);
  try {
    const r = await fetch('/api/ingest', { method: 'POST', body: fd });
    if (r.status === 401) { goToLogin(); return; }
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Upload failed');
    status.textContent = `Indexed ${d.file}: ${d.chunks} chunks (visible to: ${d.visibility === 'hr' ? 'HR and Admin' : 'everyone'}).`;
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  }
};
