// ── State ─────────────────────────────────────────────────────────────
let currentConfig = {};
let heartbeatRunning = false;

// ── Init ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSettings();
    initScrollObserver();
    fetchStatus();
    fetchModels();
    fetchSessions().then(() => {
        const lastSid = localStorage.getItem('lastSessionId');
        if (lastSid) {
            console.log('Restoring last session:', lastSid);
            loadSession(lastSid);
        }
    });

    // Resize textarea automatically
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }
    // Start periodic polling
    setInterval(fetchStatus, 3000);
    setInterval(fetchLogs, 2000);
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

        // Chat header badge
        const modelBadge = document.getElementById('modelBadge');
        if (modelBadge) {
            modelBadge.textContent = currentConfig.model || '—';
        }

        // Goal
        const goalEl = document.getElementById('currentGoal');
        goalEl.textContent = state.goal || '(none)';
        const goalContainer = goalEl.closest('.goal-current');
        if (state.goal && state.goal.toLowerCase() !== 'done') {
            goalContainer.classList.add('busy');
        } else {
            goalContainer.classList.remove('busy');
        }

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

        // Stop Button Visual State
        const btnStop = document.getElementById('btnStop');
        if (btnStop) {
            const isStopped = state.status === 'stopped' || state.goal === 'done';
            btnStop.classList.toggle('working', !isStopped);
            btnStop.textContent = isStopped ? 'STOPPED' : 'STOP';
        }

        // Settings (populate on first load)
        populateSettings(currentConfig);

        // Chat Sync
        const lastReply = state.last_reply;
        const lastReplyTs = state.last_reply_ts || 0;

        if (lastReply && lastReplyTs > (window.lastKnownReplyTs || 0)) {
            window.lastKnownReplyTs = lastReplyTs;

            // Filter out [SILENT_OK] from chat sync
            if (lastReply.includes('[SILENT_OK]')) {
                console.log('Filtered silent reply');
            } else {
                // Avoid duplicates if already shown (check raw and (Background) variant)
                const lastMsg = chatHistory[chatHistory.length - 1];
                const isDuplicate = lastMsg && (lastMsg.content === lastReply || lastMsg.content === `(Background) ${lastReply}`);
                if (!isDuplicate) {
                    // Parse think/content
                    const result = cleanResponse(lastReply);
                    // Only add if there is actual content or thought
                    if (result.content || result.thought) {
                        addChatMessage('assistant', result);
                        chatHistory.push({ role: 'assistant', content: lastReply }); // Store raw
                    } else {
                        console.log('Skipping empty/silent reply');
                        // We still update history to prevent re-processing? 
                        // If we don't push to history, next poll will try again.
                        // So we MUST push to history to mark it as "seen".
                        // BUT we don't call addChatMessage.
                        chatHistory.push({ role: 'assistant', content: lastReply });
                    }
                }
            }
        }

        // Footer
        document.getElementById('lastUpdate').textContent = 'Updated: ' + new Date().toLocaleTimeString();
    } catch (e) {
        // console.warn('Status fetch failed:', e);
        const statusBadge = document.getElementById('statusBadge');
        if (statusBadge) {
            statusBadge.textContent = '● Offline';
            statusBadge.className = 'badge badge-error';
        }
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
        modelSelect.appendChild(opt);
    }
    modelSelect.value = currentModel;

    // Embedding Model select
    const embModelSelect = document.getElementById('settingEmbModel');
    const currentEmbModel = config.embedding_model || '';
    if (currentEmbModel && !embModelSelect.querySelector(`option[value="${currentEmbModel}"]`)) {
        const opt = document.createElement('option');
        opt.value = currentEmbModel;
        opt.textContent = currentEmbModel;
        embModelSelect.insertBefore(opt, embModelSelect.firstChild);
    }
    embModelSelect.value = currentEmbModel;

    document.getElementById('settingTemp').value = config.temperature || 0.1;
    document.getElementById('tempValue').textContent = config.temperature || 0.1;
    document.getElementById('settingCtx').value = config.num_ctx || 2048;
    document.getElementById('settingInterval').value = config.heartbeat_interval || 60;
    document.getElementById('settingMaxTokens').value = config.max_tokens || 0;

    // Thinking toggle sync
    const thinkToggle = document.getElementById('thinkingToggle');
    if (thinkToggle) thinkToggle.checked = config.thinking_enabled !== false;

    // Embedding Provider sync
    const embProvider = config.embedding_provider || 'local';
    document.getElementById('btnEmbLocal')?.classList.toggle('active', embProvider === 'local');
    document.getElementById('btnEmbOllama')?.classList.toggle('active', embProvider === 'ollama');
    document.getElementById('btnEmbLmstudio')?.classList.toggle('active', embProvider === 'lmstudio');

    // Provider buttons (dynamic)
    const providerToggle = document.getElementById('providerToggle');
    if (providerToggle) {
        const active = config.provider || 'ollama';
        const providers = config.providers || {};
        providerToggle.innerHTML = Object.entries(providers).map(([key, p]) => {
            const isActive = key === active;
            let displayUrl = (p.base_url || '').replace(/^https?:\/\//, '').split('/')[0];
            return `
                <button id="btn_${key}" class="provider-btn ${isActive ? 'active' : ''}" onclick="switchProvider('${key}')">
                    <div class="provider-icon">${key === 'ollama' ? '🦙' : key === 'lmstudio' ? '🔬' : '🛠️'}</div>
                    <div class="provider-name">${p.name || key.charAt(0).toUpperCase() + key.slice(1)}</div>
                    <div class="provider-url">${displayUrl}</div>
                </button>
            `;
        }).join('');
    }

    // Dynamic Provider Settings
    renderProviderSettings(config.providers || {});

    // Permissions
    const perms = config.permissions || {};
    const grid = document.getElementById('permissionsGrid');
    if (grid) {
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
}

function renderProviderSettings(providers) {
    const container = document.getElementById('providerSettingsContainer');
    if (!container) return;

    container.innerHTML = Object.entries(providers).map(([key, p]) => {
        const isStandard = ['ollama', 'lmstudio'].includes(key);

        if (isStandard) {
            // Revert to simple "Base URL" format for standard providers
            return `
                <div class="provider-config-block card" style="background: rgba(255,255,255,0.02); border-color: rgba(255,255,255,0.05); margin-bottom: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h4 style="margin:0; font-size: 14px; color: var(--accent);">${p.name || key.charAt(0).toUpperCase() + key.slice(1)}</h4>
                        <button class="btn btn-small" onclick="fetchModels()">Fetch Models</button>
                    </div>
                    <div class="settings-grid">
                        <div class="setting-item" style="grid-column: span 2;">
                            <label>Base URL</label>
                            <input type="text" data-provider-key="${key}" data-field="base_url" value="${p.base_url || ''}" placeholder="http://localhost:..." />
                        </div>
                        <div class="setting-item" style="grid-column: span 2;">
                            <label>API Key</label>
                            <input type="text" data-provider-key="${key}" data-field="api_key" value="${p.api_key || ''}" />
                        </div>
                    </div>
                </div>
            `;
        }

        // Keep granular format only for Custom providers
        let host = 'localhost';
        let port = '';
        let path = '';
        let protocol = 'http';

        try {
            const urlStr = p.base_url.includes('://') ? p.base_url : 'http://' + p.base_url;
            const url = new URL(urlStr);
            host = url.hostname;
            port = url.port;
            path = url.pathname;
            protocol = url.protocol.replace(':', '');
        } catch (e) {
            console.warn('Failed to parse URL for provider:', key, p.base_url);
        }

        return `
            <div class="provider-config-block card" style="background: rgba(255,255,255,0.02); border-color: rgba(255,255,255,0.05); margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h4 style="margin:0; font-size: 14px; color: var(--accent);">${p.name || key.charAt(0).toUpperCase() + key.slice(1)}</h4>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-small" onclick="fetchModels()">Fetch Models</button>
                        <button class="btn btn-small btn-danger" onclick="deleteProvider('${key}')">Remove</button>
                    </div>
                </div>
                <div class="settings-grid">
                    <div class="setting-item">
                        <label>Protocol</label>
                        <select data-provider-key="${key}" data-field="protocol">
                            <option value="http" ${protocol === 'http' ? 'selected' : ''}>http</option>
                            <option value="https" ${protocol === 'https' ? 'selected' : ''}>https</option>
                        </select>
                    </div>
                    <div class="setting-item">
                        <label>Host</label>
                        <input type="text" data-provider-key="${key}" data-field="host" value="${host}" placeholder="localhost" />
                    </div>
                    <div class="setting-item">
                        <label>Port</label>
                        <input type="text" data-provider-key="${key}" data-field="port" value="${port}" placeholder="8000" />
                    </div>
                    <div class="setting-item">
                        <label>Base Path</label>
                        <input type="text" data-provider-key="${key}" data-field="path" value="${path}" placeholder="/v1" />
                    </div>
                    <div class="setting-item">
                        <label>API Key</label>
                        <input type="text" data-provider-key="${key}" data-field="api_key" value="${p.api_key || ''}" />
                    </div>
                    <div class="setting-item">
                        <label>API Format</label>
                        <select data-provider-key="${key}" data-field="api_format">
                            <option value="openai" ${p.api_format === 'openai' ? 'selected' : ''}>OpenAI Compatible</option>
                            <option value="ollama" ${p.api_format === 'ollama' ? 'selected' : ''}>Ollama Native</option>
                        </select>
                    </div>
                    <div class="setting-item">
                        <label>Default Model</label>
                        <input type="text" data-provider-key="${key}" data-field="default_model" value="${p.default_model || ''}" />
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function addProvider() {
    const name = prompt("Enter a name for the new provider (e.g. Ouro):");
    if (!name) return;
    const key = name.toLowerCase().replace(/[^a-z0-9]/g, '_');

    const config = { ...currentConfig };
    config.providers = config.providers || {};
    if (config.providers[key]) {
        alert("A provider with this name already exists.");
        return;
    }

    config.providers[key] = {
        name: name,
        base_url: "http://localhost:8000/v1",
        api_format: "openai",
        api_key: "sk-...",
        default_model: "model-name"
    };

    await api('/api/config', 'POST', { providers: config.providers });
    settingsPopulated = false;
    toast('✓ Added provider: ' + name);
    fetchStatus();
}

async function deleteProvider(key) {
    if (!confirm(`Are you sure you want to remove the provider '${key}'?`)) return;

    const config = { ...currentConfig };
    if (config.provider === key) config.provider = 'ollama';
    delete config.providers[key];

    await api('/api/config', 'POST', { providers: config.providers, provider: config.provider });
    settingsPopulated = false;
    toast('✓ Removed provider: ' + key);
    fetchStatus();
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
    // No need to manually save here, the server-side endpoints will handle config persistence
    fetchStatus();
}

async function stopAgent() {
    const btn = document.getElementById('btnStop');
    btn.disabled = true;
    toast('🛑 Sending stop request...');
    try {
        await api('/api/stop', 'POST');
        toast('✓ Stopping agent loop');
        fetchStatus();
    } catch (e) {
        toast('✗ Stop request failed');
    }
    btn.disabled = false;
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
    settingsPopulated = false;
    toast('✓ Switched LLM Provider to ' + provider);
    fetchStatus();
    // Auto-fetch models for the new provider
    setTimeout(fetchModels, 500);
}

async function switchEmbeddingProvider(provider) {
    await api('/api/embedding_provider', 'POST', { provider });
    document.getElementById('btnEmbLocal')?.classList.toggle('active', provider === 'local');
    document.getElementById('btnEmbOllama')?.classList.toggle('active', provider === 'ollama');
    document.getElementById('btnEmbLmstudio')?.classList.toggle('active', provider === 'lmstudio');
    settingsPopulated = false;
    toast('✓ Switched Embedding Provider to ' + provider);
    fetchStatus();
}

async function saveSettings() {
    const update = {
        model: document.getElementById('settingModel').value,
        embedding_provider: document.querySelector('.provider-toggle.small-toggle .provider-btn.active')?.id.replace('btnEmb', '').toLowerCase() || 'local',
        embedding_model: document.getElementById('settingEmbModel').value,
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

async function fetchEmbeddingModels() {
    toast('⏳ Fetching embedding models...');
    try {
        const data = await api('/api/embedding_models');
        const select = document.getElementById('settingEmbModel');
        const current = select.value;
        select.innerHTML = '';
        if (data.models && data.models.length > 0) {
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                select.appendChild(opt);
            });
            if (current && data.models.includes(current)) {
                select.value = current;
            }
            toast('✓ Found ' + data.models.length + ' embedding models');
        } else {
            select.innerHTML = '<option value="">No models found</option>';
            toast('✗ No models found for embedding provider');
        }
    } catch (e) {
        toast('✗ Failed to fetch embedding models');
    }
}

async function triggerDreaming() {
    toast('✨ Stage 1: Summarizing recent activity...');
    try {
        const res = await api('/api/pulse', 'POST', { type: 'reflect' });
        if (res.ok) {
            toast('🧠 Stage 2: Re-generating episodic embeddings...');
            setTimeout(() => {
                toast('✓ Dreaming complete — memories consolidated.');
                fetchStatus();
            }, 1500);
        } else {
            toast('✗ Dreaming failed: ' + (res.error || 'Unknown error'));
        }
    } catch (e) {
        toast('✗ Dreaming request failed');
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
    const providers = {};

    // Collect all dynamic inputs
    document.querySelectorAll('[data-provider-key]').forEach(input => {
        const key = input.dataset.providerKey;
        const field = input.dataset.field;
        providers[key] = providers[key] || {};
        providers[key][field] = input.value;
    });

    // Re-combine URLs
    Object.entries(providers).forEach(([key, p]) => {
        const isStandard = ['ollama', 'lmstudio'].includes(key);

        if (!isStandard) {
            const proto = p.protocol || 'http';
            const host = p.host || 'localhost';
            const port = p.port ? `:${p.port}` : '';
            const path = p.path || '';

            let cleanPath = path;
            if (cleanPath && !cleanPath.startsWith('/')) cleanPath = '/' + cleanPath;

            p.base_url = `${proto}://${host}${port}${cleanPath}`;

            delete p.protocol;
            delete p.host;
            delete p.port;
            delete p.path;
        }
    });

    await api('/api/config', 'POST', { providers });
    settingsPopulated = false;
    toast('✓ Provider configurations saved');
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

function initSettings() {
    const inputs = ['settingModel', 'settingEmbModel', 'settingCtx', 'settingInterval', 'settingMaxTokens'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', saveSettings);
    });
    const tempEl = document.getElementById('settingTemp');
    if (tempEl) {
        tempEl.addEventListener('change', saveSettings);
        tempEl.addEventListener('input', e => {
            document.getElementById('tempValue').textContent = e.target.value;
        });
    }
    document.getElementById('thinkingToggle')?.addEventListener('change', toggleThinking);
    document.getElementById('btnFetchModels')?.addEventListener('click', fetchModels);
    document.getElementById('btnSaveProviderUrls')?.addEventListener('click', saveProviderUrls);
    document.getElementById('permissionsGrid')?.addEventListener('change', e => {
        if (e.target.matches('[data-perm]')) savePermissions();
    });
}

// ── Utility ───────────────────────────────────────────────────────────
function escHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

function cleanResponse(text) {
    // Return object { content, thought }
    let thoughts = [];
    let content = text || '';

    // 1. Extract ALL [THINK] blocks
    const thinkRegex = /\[THINK\]([\s\S]*?)\[\/THINK\]/gi;
    let match;
    while ((match = thinkRegex.exec(content)) !== null) {
        thoughts.push(match[1].trim());
    }
    // Remove ALL [THINK] blocks from content
    content = content.replace(thinkRegex, '');

    // 2. Extract <think> (Ollama / DeepSeek style)
    const xmlRegex = /<think>([\s\S]*?)<\/think>/gi;
    while ((match = xmlRegex.exec(content)) !== null) {
        const t = match[1].trim();
        // Avoid adding if same thought already captured via [THINK] (common in nested cases)
        if (!thoughts.includes(t)) {
            thoughts.push(t);
        }
    }
    content = content.replace(xmlRegex, '');

    // 3. Final cleanup of joined thoughts - remove nested tags that might have leaked
    let finalThought = thoughts.join('\n---\n').trim();
    finalThought = finalThought.replace(/\[\/?THINK\]/gi, '');
    finalThought = finalThought.replace(/<think>|<\/think>/gi, '');

    // Check if a tool was used (to provide a placeholder if content is empty)
    const hasTool = /\[TOOL\]/gi.test(content);

    // Strip [TOOL] blocks from the final chat display
    const toolRegex = /\[TOOL\]([\s\S]*?)\[\/TOOL\]/gi;
    content = content.replace(toolRegex, '');

    // Strip [SILENT_OK]
    content = content.replace(/\[SILENT_OK\]/gi, '');

    content = content.trim();

    // FAIL-SAFE: If content is empty but something happened (thought or tool),
    // provide a representative placeholder so the bubble isn't empty.
    if (!content) {
        if (hasTool) {
            content = "*Performing action...*";
        } else if (finalThought) {
            content = "*Thinking...*";
        }
    }

    return { content, thought: finalThought.trim() };
}

function parseMarkdown(text) {
    if (!text) return '';

    // 0. Clean Protocol Tags
    // Strip [TOOL] blocks entirely from user view
    let out = text.replace(/\[TOOL\][\s\S]*?\[\/TOOL\]/gi, '');

    // Strip [SILENT_OK]
    out = out.replace(/\[SILENT_OK\]/gi, '');

    // Strip [THINK] blocks if they leaked (should be handled by separate parser, but safety first)
    out = out.replace(/\[THINK\][\s\S]*?\[\/THINK\]/gi, '');

    // Trim extra whitespace caused by removals
    out = out.trim();

    // If message is empty after stripping (e.g. only tool use), return empty string
    // The UI should handle empty messages gracefully (e.g. show nothing or a subtle indicator)
    if (!out) return '';

    // 1. Escape HTML first
    out = out.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    // 2. Code Blocks
    out = out.replace(/```(\w*)([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre class="md-code-block"><div class="md-code-header">${lang || 'code'}</div><code>${code.trim()}</code></pre>`;
    });

    // 3. Inline Code
    out = out.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

    // 4. Bold
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 5. Italic
    out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 6. Headers
    out = out.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    out = out.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    out = out.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    return out; // Newlines are handled by CSS white-space: pre-wrap
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

async function fetchSessions() {
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
                <span class="session-delete" onclick="event.stopPropagation(); deleteSession('${s.id}')" title="Delete" style="color: #ef4444; opacity: 0.9;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </span>
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
    fetchSessions();
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
    localStorage.removeItem('lastSessionId');

    // Reset backend goal
    try {
        await api('/api/goal', 'POST', { goal: '' });
        console.log('Backend goal cleared');
    } catch (err) {
        console.error('Failed to clear backend goal:', err);
    }

    renderAttachments();
    document.getElementById('chatMessages').innerHTML = `
        <div class="chat-welcome">
            <div class="chat-welcome-icon">🤖</div>
            <div class="chat-welcome-text">Start a conversation with your model. You can also attach files.</div>
        </div>`;
    fetchSessions();
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
        localStorage.setItem('lastSessionId', currentSessionId);
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
        fetchSessions();
        toast('📂 Loaded: ' + (data.title || 'Session'));
    } catch (e) {
        toast('✗ Failed to load session');
    }
}

async function deleteSession(sid) {
    if (!confirm('Are you sure you want to delete this session?')) return;
    await api('/api/chat/delete', 'POST', { id: sid });
    if (currentSessionId === sid) {
        currentSessionId = null;
        localStorage.removeItem('lastSessionId');
        newChat();
    }
    fetchSessions();
    toast('🗑 Session deleted');
}

async function deleteAllSessions() {
    if (!confirm('⚠️ Are you sure you want to delete ALL chat history? This cannot be undone.')) return;
    await api('/api/chat/delete_all', 'POST', {});
    currentSessionId = null;
    localStorage.removeItem('lastSessionId');
    newChat();
    fetchSessions();
    toast('🗑 All history cleared');
}

// ── File Attachments ──────────────────────────────────────────────────
function handleFileAttach(event) {
    const files = event.target.files;
    if (!files.length) return;

    Array.from(files).forEach(file => {
        // Warning for large files (> 5MB)
        if (file.size > 5 * 1024 * 1024) {
            toast(`⚠️ Large file(${(file.size / 1024 / 1024).toFixed(1)}MB). Browser may slow down.`);
        }

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

// ── Scroll Management ────────────────────────────────────────────────
let isUserAtBottom = true;

function initScrollObserver() {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    // Detect manual scrolling
    container.addEventListener('scroll', () => {
        const threshold = 150;
        isUserAtBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + threshold;
    });

    // Use MutationObserver to watch for content changes
    // ChildList: for new messages, Subtree: for markdown rendering inside messages
    const observer = new MutationObserver(() => {
        if (isUserAtBottom) {
            // Double-tick strategy to wait for next paint cycle
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    container.scrollTop = container.scrollHeight;
                });
            });
        }
    });

    observer.observe(container, { childList: true, subtree: true, characterData: true });
}

function scrollToBottom(force = false) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    if (force) {
        isUserAtBottom = true;
        container.scrollTop = container.scrollHeight;
    }
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
            return `< div class="chat-file-badge" > ${icon} ${escHtml(f.name)}</div > `;
        }).join('');
    }

    // Handle content object {content, thought} or string
    let msgText = '';
    let thoughtHtml = '';

    if (typeof content === 'object' && content !== null && (content.content !== undefined || content.thought !== undefined)) {
        msgText = content.content || '';
        if (content.thought) {
            thoughtHtml = `
            <details class="chat-thought">
                <summary>Thinking Process</summary>
                <div class="thought-content">${escHtml(content.thought)}</div>
            </details>`;
        }
    } else {
        msgText = content || '';
    }

    // Role-based rendering
    let bubbleContent = '';
    if (role === 'assistant') {
        bubbleContent = parseMarkdown(msgText);
    } else {
        bubbleContent = escHtml(msgText);
    }

    const msgHtml = `
        <div class="chat-msg ${role}">
            <div class="chat-avatar">${avatar}</div>
            <div class="chat-content-wrapper">
                ${thoughtHtml}
                <div class="chat-bubble" style="word-break: break-word;">
                    ${bubbleContent}
                    ${filesBadges}
                </div>
                <div class="chat-timestamp">${time}</div>
            </div>
        </div>`;

    // Simplified insertion - ResizeObserver handles the scroll
    const msgDiv = document.createElement('div');
    msgDiv.innerHTML = msgHtml;
    container.appendChild(msgDiv.firstElementChild);
    if (role === 'user') {
        scrollToBottom(true);
    }
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const html = `<div id="typingIndicator" class="chat-msg assistant">
        <div class="chat-avatar">🤖</div>
        <div class="chat-typing">
            <div class="dot"></div><div class="dot"></div><div class="dot"></div>
        </div>
    </div>`;

    // Check if we should auto-scroll for the indicator
    const threshold = 150;
    const wasAtBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + threshold;

    container.insertAdjacentHTML('beforeend', html);
    if (wasAtBottom) {
        isUserAtBottom = true;
        scrollToBottom(true);
    }
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
            const rawReply = data.reply || '(empty response)';
            const result = cleanResponse(rawReply);
            addChatMessage('assistant', result);
            chatHistory.push({ role: 'assistant', content: rawReply }); // Store raw

            // If the agent was stopped/done, its successful reply signifies it's back in action
            if (state.goal === 'done' || state.status === 'stopped') {
                console.log('Agent responded to new chat, resetting status...');
                // Optionally trigger a status reset on server if needed, 
                // but usually server handles this when /api/chat is called if we want it to.
                // For now, let's just make sure UI state is updated on next fetch.
            }
        }
    } catch (e) {
        removeTypingIndicator();
        addChatMessage('assistant', '⚠ Failed to reach the server. Is it running?');
    }

    sendBtn.disabled = false;
    input.focus();

    // Auto-save session periodically
    // Save on 1st message to ensure it appears in sidebar, then every 2 messages
    if (chatHistory.length === 1 || chatHistory.length % 2 === 0) {
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
    if (window.innerWidth < 768) {
        document.getElementById('chatSidebar')?.classList.add('collapsed');
    }
});

// ── Terminal ──────────────────────────────────────────────────────────
let terminalOpen = false;
let lastLogCount = 0;

function toggleTerminal() {
    const el = document.getElementById('terminal');
    terminalOpen = !terminalOpen;
    el.classList.toggle('collapsed', !terminalOpen);
    if (terminalOpen) {
        fetchLogs();
        setTimeout(scrollToBottom, 50);
    }
}

function clearTerminal() {
    document.getElementById('terminalContent').innerHTML = '';
    lastLogCount = 0; // Reset count (warning: if server buffer not cleared, might duplicate on restart. But server buffer is persistent per session)
}

async function fetchLogs() {
    if (!terminalOpen) return;
    try {
        const data = await api('/api/logs');
        const logs = data.logs || [];

        // If logs array is shorter than last count, it was reset
        if (logs.length < lastLogCount) {
            lastLogCount = 0;
            document.getElementById('terminalContent').innerHTML = '';
        }

        if (logs.length > lastLogCount) {
            const container = document.getElementById('terminalContent');

            // Clear the "Initializing terminal connection..." message on first success
            if (lastLogCount === 0) {
                container.innerHTML = '';
            }

            const newLogs = logs.slice(lastLogCount);
            const frag = document.createDocumentFragment();

            newLogs.forEach(line => {
                const div = document.createElement('div');
                div.className = 'log-line';

                // Colorize logic
                if (line.includes('ERROR') || line.includes('Exception') || line.includes('Error:')) div.classList.add('error');
                else if (line.includes('WARNING')) div.classList.add('warn');
                else if (line.includes('INFO')) div.classList.add('info');
                else if (line.includes('DEBUG')) div.classList.add('debug');
                else if (line.includes('[THINK]')) div.style.color = '#a78bfa'; // Purple
                else if (line.includes('[TOOL]')) div.style.color = '#34d399';  // Green
                else if (line.includes('PULSE ▶')) div.style.color = '#fb923c'; // Orange
                else if (line.includes('SILENT REPLY')) div.style.color = '#94a3b8'; // Slate (dim)

                div.textContent = line;
                frag.appendChild(div);
            });

            container.appendChild(frag);
            lastLogCount = logs.length;
            scrollToBottom();
        } else if (logs.length === 0 && lastLogCount === 0) {
            // No logs yet
            document.getElementById('terminalContent').innerHTML = '<div class="log-line system">Waiting for system output...</div>';
        }
    } catch (e) {
        document.getElementById('terminalContent').innerHTML = `<div class="log-line error">Connection Error: ${e.message}</div>`;
    }
}

function scrollToBottom() {
    const el = document.getElementById('terminalContent');
    el.scrollTop = el.scrollHeight;
}

//  Terminal Resize -
document.addEventListener('DOMContentLoaded', () => {
    const tHandle = document.querySelector('.terminal-resize-handle');
    const tPanel = document.getElementById('terminal');
    let isResizing = false;

    if (tHandle && tPanel) {
        tHandle.addEventListener('mousedown', e => {
            isResizing = true;
            tHandle.classList.add('active');
            document.body.style.cursor = 'ns-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', e => {
            if (!isResizing) return;
            const newHeight = window.innerHeight - e.clientY;
            if (newHeight > 100 && newHeight < window.innerHeight - 50) {
                tPanel.style.height = newHeight + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                tHandle.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }
});

async function stopAgent() {
    console.log('Stopping agent...');
    try {
        const res = await api('/api/stop', 'POST');
        if (res.ok) {
            toast('🛑 Agent Stopped');
            fetchStatus();
        }
    } catch (e) {
        toast('✗ Failed to stop agent');
    }
}
