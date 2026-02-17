// ── State ─────────────────────────────────────────────────────────────
let currentConfig = {};
let heartbeatRunning = false;

// ── Init ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    fetchStatus();
    setupAutoSave();
    setInterval(fetchStatus, 3000); // Poll every 3s
    document.getElementById('settingTemp').addEventListener('input', e => {
        document.getElementById('tempValue').textContent = e.target.value;
    });
});

// ── Tabs ──────────────────────────────────────────────────────────────
function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
        });
    });
}

// ── API Helpers ───────────────────────────────────────────────────────
async function api(path, method = 'GET', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' }, cache: 'no-store' };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    return res.json();
}

function toast(msg) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2500);
}

// ── Fetch Status (polling) ────────────────────────────────────────────
async function fetchStatus() {
    try {
        const data = await api('/api/status');
        currentConfig = data.config || {};
        heartbeatRunning = data.heartbeat_running;

        // Header badges
        const state = data.state || {};
        const statusBadge = document.getElementById('statusBadge');
        const status = state.status || 'ready';
        statusBadge.textContent = '● ' + status.charAt(0).toUpperCase() + status.slice(1);
        statusBadge.className = 'badge badge-' + (status === 'ready' ? 'ready' : status === 'recovering' ? 'recovering' : 'error');

        const providerKey = currentConfig.provider || 'ollama';
        const providerName = (currentConfig.providers || {})[providerKey]?.name || providerKey;
        document.getElementById('providerBadge').textContent = providerName;

        // Dashboard stats
        document.getElementById('statPulses').textContent = data.pulse_count || 0;
        document.getElementById('statStatus').textContent = status;
        document.getElementById('statProvider').textContent = providerName;
        document.getElementById('statModel').textContent = currentConfig.model || '—';

        // Goal
        document.getElementById('currentGoal').textContent = state.goal || '(none)';

        // Progress list
        const progressList = document.getElementById('progressList');
        const progress = state.progress || [];
        if (progress.length > 0) {
            progressList.innerHTML = progress.slice(-8).reverse().map(p =>
                `<div class="progress-item">
                    <div class="progress-action">${escHtml(p.action || '')}</div>
                    <div class="progress-result">→ ${escHtml(p.result || '')}</div>
                </div>`
            ).join('');
        } else {
            progressList.innerHTML = '<div class="empty-state">No activity yet. Set a goal and trigger a pulse.</div>';
        }

        // Activity tab
        document.getElementById('scratchpadView').textContent = data.scratchpad || '(empty)';
        document.getElementById('journalView').textContent = data.journal || '(empty)';

        // Error card
        const errorCard = document.getElementById('errorCard');
        if (state.status === 'recovering' && state.last_error) {
            errorCard.style.display = 'block';
            document.getElementById('errorText').textContent = state.last_error;
        } else {
            errorCard.style.display = 'none';
        }

        // Heartbeat button
        const hbBtn = document.getElementById('btnHeartbeat');
        const hbLabel = document.getElementById('heartbeatLabel');
        if (heartbeatRunning) {
            hbBtn.classList.add('running');
            hbLabel.textContent = 'Stop Heartbeat';
        } else {
            hbBtn.classList.remove('running');
            hbLabel.textContent = 'Start Heartbeat';
        }

        // Settings (populate on first load)
        populateSettings(currentConfig);

        // Footer
        document.getElementById('lastUpdate').textContent = 'Updated: ' + new Date().toLocaleTimeString();
    } catch (e) {
        console.warn('Status fetch failed:', e);
    }
}

// ── Settings Population ───────────────────────────────────────────────
let settingsPopulated = false;
function populateSettings(config) {
    console.log('Populating settings:', config);
    if (settingsPopulated) return;
    settingsPopulated = true;

    // Model select — set current value or add it as option
    const modelSelect = document.getElementById('settingModel');
    const currentModel = config.model || '';
    if (currentModel && !modelSelect.querySelector(`option[value="${currentModel}"]`)) {
        const opt = document.createElement('option');
        opt.value = currentModel;
        opt.textContent = currentModel;
        modelSelect.insertBefore(opt, modelSelect.firstChild);
    }
    modelSelect.value = currentModel;

    document.getElementById('settingTemp').value = config.temperature || 0.1;
    document.getElementById('tempValue').textContent = config.temperature || 0.1;
    document.getElementById('settingCtx').value = config.num_ctx || 2048;
    document.getElementById('settingInterval').value = config.heartbeat_interval || 60;
    document.getElementById('settingMaxTokens').value = config.max_tokens || 0;

    // Thinking toggle sync
    const thinkToggle = document.getElementById('thinkingToggle');
    if (thinkToggle) thinkToggle.checked = config.thinking_enabled !== false;

    // Provider buttons
    const active = config.provider || 'ollama';
    document.getElementById('btnOllama').classList.toggle('active', active === 'ollama');
    document.getElementById('btnLmstudio').classList.toggle('active', active === 'lmstudio');

    // Provider URLs
    const providers = config.providers || {};
    document.getElementById('ollamaUrl').value = providers.ollama?.base_url || '';
    document.getElementById('lmstudioUrl').value = providers.lmstudio?.base_url || '';
    document.getElementById('ollamaKey').value = providers.ollama?.api_key || '';
    document.getElementById('lmstudioKey').value = providers.lmstudio?.api_key || '';

    // Permissions
    const perms = config.permissions || {};
    const grid = document.getElementById('permissionsGrid');
    grid.innerHTML = Object.entries(perms).map(([name, enabled]) =>
        `<div class="perm-item">
            <span class="perm-name">${name}</span>
            <label class="toggle">
                <input type="checkbox" data-perm="${name}" ${enabled ? 'checked' : ''} />
                <span class="slider"></span>
            </label>
        </div>`
    ).join('');
}

// ── Actions ───────────────────────────────────────────────────────────
async function triggerPulse() {
    const btn = document.getElementById('btnPulse');
    btn.disabled = true;
    btn.textContent = 'Running...';
    toast('⚡ Pulse triggered...');
    try {
        await api('/api/pulse', 'POST');
        toast('✓ Pulse completed');
        settingsPopulated = false; // refresh
        fetchStatus();
    } catch (e) {
        toast('✗ Pulse failed');
    }
    btn.disabled = false;
    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Single Pulse';
}

async function toggleHeartbeat() {
    if (heartbeatRunning) {
        await api('/api/heartbeat/stop', 'POST');
        toast('■ Heartbeat stopped');
    } else {
        await api('/api/heartbeat/start', 'POST');
        toast('♥ Heartbeat started');
    }
    fetchStatus();
}

async function setGoal() {
    const input = document.getElementById('goalInput');
    const goal = input.value.trim();
    if (!goal) return;
    await api('/api/goal', 'POST', { goal });
    input.value = '';
    toast('✓ Goal set: ' + goal);
    settingsPopulated = false;
    fetchStatus();
}

async function switchProvider(provider) {
    await api('/api/provider', 'POST', { provider });
    document.getElementById('btnOllama').classList.toggle('active', provider === 'ollama');
    document.getElementById('btnLmstudio').classList.toggle('active', provider === 'lmstudio');
    settingsPopulated = false;
    toast('✓ Switched to ' + (provider === 'ollama' ? 'Ollama' : 'LM Studio'));
    fetchStatus();
}

async function saveSettings() {
    const update = {
        model: document.getElementById('settingModel').value,
        temperature: parseFloat(document.getElementById('settingTemp').value),
        num_ctx: parseInt(document.getElementById('settingCtx').value),
        heartbeat_interval: parseInt(document.getElementById('settingInterval').value),
        max_tokens: parseInt(document.getElementById('settingMaxTokens').value) || 0,
    };
    await api('/api/config', 'POST', update);
    settingsPopulated = false;
    toast('✓ Settings saved');
    fetchStatus();
}

async function fetchModels() {
    toast('⏳ Fetching models...');
    try {
        const data = await api('/api/models');
        const select = document.getElementById('settingModel');
        const current = select.value;
        select.innerHTML = '';
        if (data.models && data.models.length > 0) {
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                select.appendChild(opt);
            });
            // Keep current selection if it exists in the list
            if (current && data.models.includes(current)) {
                select.value = current;
            }
            toast('✓ Found ' + data.models.length + ' models');
        } else {
            select.innerHTML = '<option value="">No models found</option>';
            toast('✗ No models found — is the provider running?');
        }
    } catch (e) {
        toast('✗ Failed to fetch models');
    }
}

async function clearJournal() {
    await api('/api/clear/journal', 'POST');
    toast('✓ Journal cleared');
    fetchStatus();
}

async function clearScratchpad() {
    await api('/api/clear/scratchpad', 'POST');
    toast('✓ Scratchpad cleared');
    fetchStatus();
}

async function saveProviderUrls() {
    const config = { ...currentConfig };
    config.providers = config.providers || {};
    config.providers.ollama = {
        ...config.providers.ollama,
        base_url: document.getElementById('ollamaUrl').value,
        api_key: document.getElementById('ollamaKey').value,
    };
    config.providers.lmstudio = {
        ...config.providers.lmstudio,
        base_url: document.getElementById('lmstudioUrl').value,
        api_key: document.getElementById('lmstudioKey').value,
    };
    await api('/api/config', 'POST', { providers: config.providers });
    settingsPopulated = false;
    toast('✓ Provider URLs saved');
    fetchStatus();
}

async function savePermissions() {
    const perms = {};
    document.querySelectorAll('[data-perm]').forEach(el => {
        perms[el.dataset.perm] = el.checked;
    });
    await api('/api/permissions', 'POST', { permissions: perms });
    settingsPopulated = false;
    toast('✓ Permissions saved');
}

function setupAutoSave() {
    const inputs = ['settingModel', 'settingCtx', 'settingInterval', 'settingMaxTokens'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', saveSettings);
    });
    const tempEl = document.getElementById('settingTemp');
    if (tempEl) tempEl.addEventListener('change', saveSettings);
}

// ── Utility ───────────────────────────────────────────────────────────
function escHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

function cleanResponse(text) {
    // Strip <think>...</think> and [THINK]...[/THINK] blocks
    let cleaned = text.replace(/<think>[\s\S]*?<\/think>/gi, '');
    cleaned = cleaned.replace(/\[THINK\][\s\S]*?\[\/THINK\]/gi, '');
    return cleaned.trim();
}

// Enter key on goal input
document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && document.activeElement?.id === 'goalInput') setGoal();
});

// ── Chat System ───────────────────────────────────────────────────────
let chatHistory = [];  // {role, content}
let pendingFiles = []; // {name, type, content}
let currentSessionId = null;

async function toggleThinking() {
    const enabled = document.getElementById('thinkingToggle').checked;
    await api('/api/config', 'POST', { thinking_enabled: enabled });
    toast(enabled ? '🧠 Thinking ON — step-by-step reasoning' : '⚡ Thinking OFF — direct answers');
}

// ── Session Management ────────────────────────────────────────────────
function toggleSidebar() {
    document.getElementById('chatSidebar').classList.toggle('collapsed');
}

async function loadSessionList() {
    try {
        const data = await api('/api/chat/sessions', 'POST', {});
        const container = document.getElementById('sessionList');
        const sessions = data.sessions || [];
        if (sessions.length === 0) {
            container.innerHTML = '<div class="empty-state" style="font-size:11px;padding:16px;text-align:center;opacity:0.5;">No saved sessions yet</div>';
            return;
        }
        container.innerHTML = sessions.map(s => `
            <div class="session-card ${s.id === currentSessionId ? 'active' : ''}" onclick="loadSession('${s.id}')">
                <div class="session-title">${escHtml(s.title)}</div>
                <div class="session-meta">
                    <span>${s.created || ''}</span>
                    <span>${s.message_count || 0} msgs</span>
                </div>
                <span class="session-delete" onclick="event.stopPropagation(); deleteSession('${s.id}')" title="Delete">🗑</span>
            </div>
        `).join('');
    } catch (e) {
        console.warn('Failed to load sessions:', e);
    }
}

async function saveSession() {
    if (chatHistory.length === 0) return null;
    const sid = currentSessionId || `chat_${Date.now()}`;
    await api('/api/chat/save', 'POST', {
        id: sid,
        messages: chatHistory,
    });
    currentSessionId = sid;
    loadSessionList();
    return sid;
}

async function newChat() {
    // Auto-save current session if it has messages
    if (chatHistory.length > 0) {
        await saveSession();
        toast('💾 Session saved');
    }
    // Reset state
    chatHistory = [];
    pendingFiles = [];
    currentSessionId = null;
    renderAttachments();
    document.getElementById('chatMessages').innerHTML = `
        <div class="chat-welcome">
            <div class="chat-welcome-icon">🤖</div>
            <div class="chat-welcome-text">Start a conversation with your model. You can also attach files.</div>
        </div>`;
    loadSessionList();
    toast('📝 New chat started');
}

async function loadSession(sid) {
    // Auto-save current if different
    if (chatHistory.length > 0 && currentSessionId !== sid) {
        await saveSession();
    }
    try {
        const data = await api('/api/chat/load', 'POST', { id: sid });
        if (data.error) {
            toast('✗ ' + data.error);
            return;
        }
        currentSessionId = data.id;
        chatHistory = data.messages || [];
        pendingFiles = [];
        renderAttachments();

        // Render messages
        const container = document.getElementById('chatMessages');
        container.innerHTML = '';
        for (const msg of chatHistory) {
            addChatMessage(msg.role, msg.content);
        }
        if (chatHistory.length === 0) {
            container.innerHTML = `
                <div class="chat-welcome">
                    <div class="chat-welcome-icon">🤖</div>
                    <div class="chat-welcome-text">Start a conversation with your model.</div>
                </div>`;
        }
        loadSessionList();
        toast('📂 Loaded: ' + (data.title || 'Session'));
    } catch (e) {
        toast('✗ Failed to load session');
    }
}

async function deleteSession(sid) {
    await api('/api/chat/delete', 'POST', { id: sid });
    if (currentSessionId === sid) {
        currentSessionId = null;
        chatHistory = [];
        document.getElementById('chatMessages').innerHTML = `
            <div class="chat-welcome">
                <div class="chat-welcome-icon">🤖</div>
                <div class="chat-welcome-text">Start a conversation with your model.</div>
            </div>`;
    }
    loadSessionList();
    toast('🗑 Session deleted');
}

// ── File Attachments ──────────────────────────────────────────────────
function handleFileAttach(event) {
    const files = event.target.files;
    if (!files.length) return;

    Array.from(files).forEach(file => {
        const reader = new FileReader();
        const isText = file.type.startsWith('text/') ||
            /\.(md|json|js|py|html|css|csv|xml|yaml|yml|toml|ini|cfg|log|txt|sh|bat|ps1|sql|ts|jsx|tsx|c|cpp|h|hpp|java|rb|go|rs|php|pl|lua|r|swift|kt)$/i.test(file.name);

        if (isText) {
            reader.onload = () => {
                pendingFiles.push({ name: file.name, type: file.type || 'text/plain', content: reader.result });
                renderAttachments();
            };
            reader.readAsText(file);
        } else {
            pendingFiles.push({ name: file.name, type: file.type, content: `[Binary file: ${file.name}]` });
            renderAttachments();
        }
    });

    event.target.value = '';
}

function renderAttachments() {
    const container = document.getElementById('chatAttachments');
    container.innerHTML = pendingFiles.map((f, i) => {
        const icon = f.type.startsWith('image/') ? '🖼️' :
            f.type.startsWith('video/') ? '🎬' :
                f.type.startsWith('audio/') ? '🎵' : '📄';
        return `<div class="attach-chip">
            <span class="attach-icon">${icon}</span>
            <span>${escHtml(f.name)}</span>
            <span class="remove-attach" onclick="removeAttachment(${i})">×</span>
        </div>`;
    }).join('');
}

function removeAttachment(index) {
    pendingFiles.splice(index, 1);
    renderAttachments();
}

// ── Message Display ───────────────────────────────────────────────────
function addChatMessage(role, content, files = []) {
    const container = document.getElementById('chatMessages');
    const welcome = container.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const avatar = role === 'user' ? '👤' : '🤖';

    let filesBadges = '';
    if (files.length > 0) {
        filesBadges = files.map(f => {
            const icon = f.type?.startsWith('image/') ? '🖼️' :
                f.type?.startsWith('video/') ? '🎬' :
                    f.type?.startsWith('audio/') ? '🎵' : '📄';
            return `<div class="chat-file-badge">${icon} ${escHtml(f.name)}</div>`;
        }).join('');
    }

    const msgHtml = `
        <div class="chat-msg ${role}">
            <div class="chat-avatar">${avatar}</div>
            <div>
                <div class="chat-bubble">${escHtml(content)}${filesBadges}</div>
                <div class="chat-timestamp">${time}</div>
            </div>
        </div>`;
    container.insertAdjacentHTML('beforeend', msgHtml);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const html = `<div id="typingIndicator" class="chat-msg assistant">
        <div class="chat-avatar">🤖</div>
        <div class="chat-typing">
            <div class="dot"></div><div class="dot"></div><div class="dot"></div>
        </div>
    </div>`;
    container.insertAdjacentHTML('beforeend', html);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

// ── Send Chat ─────────────────────────────────────────────────────────
async function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg && pendingFiles.length === 0) return;

    const sendBtn = document.getElementById('chatSendBtn');
    sendBtn.disabled = true;

    const displayMsg = msg || `(${pendingFiles.length} file${pendingFiles.length > 1 ? 's' : ''} attached)`;
    addChatMessage('user', displayMsg, pendingFiles);

    const payload = {
        message: msg,
        files: pendingFiles.map(f => ({ name: f.name, type: f.type, content: f.content })),
        history: chatHistory,
    };

    chatHistory.push({ role: 'user', content: msg + pendingFiles.map(f => `\n[File: ${f.name}]`).join('') });

    input.value = '';
    input.style.height = 'auto';
    pendingFiles = [];
    renderAttachments();
    showTypingIndicator();

    try {
        const data = await api('/api/chat', 'POST', payload);
        removeTypingIndicator();

        if (data.error) {
            addChatMessage('assistant', '⚠ Error: ' + data.error);
        } else {
            const reply = cleanResponse(data.reply || '(empty response)');
            addChatMessage('assistant', reply || '(empty response)');
            chatHistory.push({ role: 'assistant', content: reply });
        }
    } catch (e) {
        removeTypingIndicator();
        addChatMessage('assistant', '⚠ Failed to reach the server. Is it running?');
    }

    sendBtn.disabled = false;
    input.focus();

    // Auto-save session periodically (every 4 messages)
    if (chatHistory.length % 4 === 0) {
        saveSession();
    }
}

function chatKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat();
    }
    requestAnimationFrame(() => {
        const ta = e.target;
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    });
}

// ── Init: load sessions on tab switch ─────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Load sessions when chat tab is first opened
    const chatTab = document.querySelector('[data-tab="chat"]');
    if (chatTab) {
        chatTab.addEventListener('click', () => loadSessionList());
    }
    // Collapse sidebar by default on mobile
    if (window.innerWidth < 768) {
        document.getElementById('chatSidebar')?.classList.add('collapsed');
    }
});
