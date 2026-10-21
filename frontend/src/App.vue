
<script setup lang="ts">
import { computed, ref } from 'vue'

type Upstream = {
  id: string
  name: string
  url: string
  enabled: boolean
}

type ApiKey = {
  id: string
  user_id: string
  is_revoked: boolean
  created_at: string
  revoked_at: string | null
}

type AuditLog = {
  id: number
  user_id: string
  upstream_name: string
  tool_name: string
  timestamp: string
  duration_seconds: number
  outcome: string
  error_message: string | null
}

const apiKey = ref('')
const upstreams = ref<Upstream[]>([])
const apiKeys = ref<ApiKey[]>([])
const auditLogs = ref<AuditLog[]>([])

const name = ref('')
const url = ref('')

const loading = ref(false)
const keysLoading = ref(false)
const auditLoading = ref(false)
const revokingId = ref('')
const message = ref('')
const auditFilter = ref('all')

type ChatMessage = { role: 'user' | 'assistant'; content: string }
const chatMessages = ref<ChatMessage[]>([
  { role: 'assistant', content: 'Hi! I can help you inspect store products and orders, and run available analytics tools.' },
])
const chatInput = ref('')
const chatLoading = ref(false)
const chatError = ref('')

const apiBase = import.meta.env.VITE_API_BASE || '/api'

const activeKeyCount = computed(
  () => apiKeys.value.filter(key => !key.is_revoked).length,
)

const revokedKeyCount = computed(
  () => apiKeys.value.filter(key => key.is_revoked).length,
)

const filteredAuditLogs = computed(() => {
  if (auditFilter.value === 'all') {
    return auditLogs.value
  }

  return auditLogs.value.filter(log => {
    const outcome = log.outcome.toLowerCase()
    const isSuccess = ['success', 'succeeded', 'ok'].includes(outcome)

    if (auditFilter.value === 'success') return isSuccess
    if (auditFilter.value === 'failure') return !isSuccess

    return true
  })
})

async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey.value.trim(),
      ...options.headers,
    },
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`HTTP ${response.status}: ${detail}`)
  }

  if (response.status === 204) return null

  return response.json()
}

async function sendChatMessage() {
  const messageText = chatInput.value.trim()
  if (!messageText || chatLoading.value) return
  if (!apiKey.value.trim()) {
    chatError.value = 'Enter your gateway API key in Gateway connection first.'
    return
  }

  chatMessages.value.push({ role: 'user', content: messageText })
  chatInput.value = ''
  chatLoading.value = true
  chatError.value = ''

  try {
    const result = await request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message: messageText }),
    }) as { answer: string }
    chatMessages.value.push({ role: 'assistant', content: result.answer })
  } catch (error) {
    chatError.value = errorMessage(
      error,
      'Chat request failed. Confirm the backend chat endpoint and Ollama are running.',
    )
  } finally {
    chatLoading.value = false
  }
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function formatDate(value: string | null) {
  if (!value) return '—'

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString()
}

function isSuccess(outcome: string) {
  return ['success', 'succeeded', 'ok'].includes(outcome.toLowerCase())
}

async function loadUpstreams(): Promise<boolean> {
  if (!apiKey.value.trim()) {
    message.value = 'Enter your gateway API key first.'
    return false
  }

  loading.value = true

  try {
    upstreams.value = await request('/upstreams')
    return true
  } catch (error) {
    message.value = errorMessage(error, 'Failed to load upstreams.')
    return false
  } finally {
    loading.value = false
  }
}

async function loadApiKeys(): Promise<boolean> {
  if (!apiKey.value.trim()) return false

  keysLoading.value = true

  try {
    apiKeys.value = await request('/api-keys')
    return true
  } catch (error) {
    message.value = errorMessage(error, 'Failed to load API keys.')
    return false
  } finally {
    keysLoading.value = false
  }
}

async function loadAuditLogs(): Promise<boolean> {
  if (!apiKey.value.trim()) return false

  auditLoading.value = true

  try {
    auditLogs.value = await request('/audit-logs?limit=100')
    return true
  } catch (error) {
    message.value = errorMessage(error, 'Failed to load audit logs.')
    return false
  } finally {
    auditLoading.value = false
  }
}

async function connectGateway() {
  message.value = ''

  if (!apiKey.value.trim()) {
    message.value = 'Enter your gateway API key first.'
    return
  }

  const upstreamsLoaded = await loadUpstreams()
  if (!upstreamsLoaded) return

  const keysLoaded = await loadApiKeys()
  if (!keysLoaded) return

  const auditLoaded = await loadAuditLogs()

  message.value = auditLoaded
    ? 'Connected successfully. Upstreams, API keys and audit logs loaded.'
    : 'Connected. Upstreams and API keys loaded, but audit logs could not be loaded.'
}

async function addUpstream() {
  if (!name.value.trim() || !url.value.trim()) {
    message.value = 'Enter both a server name and URL.'
    return
  }

  try {
    await request('/upstreams', {
      method: 'POST',
      body: JSON.stringify({
        name: name.value.trim(),
        url: url.value.trim(),
      }),
    })

    name.value = ''
    url.value = ''
    message.value = 'Upstream added.'

    const loaded = await loadUpstreams()
    if (loaded) message.value = 'Upstream added and list refreshed.'
  } catch (error) {
    message.value = errorMessage(error, 'Failed to add upstream.')
  }
}

async function setEnabled(upstream: Upstream, enabled: boolean) {
  try {
    await request(
      `/upstreams/${upstream.id}/${enabled ? 'enable' : 'disable'}`,
      { method: 'PATCH' },
    )

    const loaded = await loadUpstreams()

    message.value = loaded
      ? `${upstream.name} ${enabled ? 'enabled' : 'disabled'}.`
      : 'The server was updated, but the list could not be refreshed.'
  } catch (error) {
    message.value = errorMessage(error, 'Failed to update upstream.')
  }
}

async function revokeApiKey(key: ApiKey) {
  if (key.is_revoked || revokingId.value) return

  const confirmed = window.confirm(
    'Revoke this API key? Applications using it will no longer be able to authenticate.',
  )

  if (!confirmed) return

  revokingId.value = key.id
  message.value = ''

  try {
    await request(`/api-keys/${key.id}/revoke`, {
      method: 'PATCH',
    })

    const loaded = await loadApiKeys()

    message.value = loaded
      ? 'API key revoked successfully.'
      : 'Key revocation was submitted, but the list could not be refreshed.'
  } catch (error) {
    message.value = errorMessage(error, 'Failed to revoke API key.')
  } finally {
    revokingId.value = ''
  }
}
</script>

<template>
  <main class="dashboard">
    <header>
      <p class="eyebrow">URUMI · MCP PLATFORM</p>
      <h1>Gateway Dashboard</h1>
      <p class="subtitle">
        Manage connected MCP servers, API keys and tool-call activity.
      </p>
    </header>

    <!-- Store assistant chatbot -->
    <section class="panel chat-panel">
      <div class="section-heading">
        <div>
          <h2>Store assistant</h2>
          <p class="subtitle">Ask about products, orders, and store analytics using your MCP tools.</p>
        </div>
        <span class="chat-badge">LLM · MCP tools</span>
      </div>

      <div class="chat-transcript" aria-live="polite" aria-label="Chat conversation">
        <article
          v-for="(item, index) in chatMessages"
          :key="index"
          :class="['chat-message', item.role === 'user' ? 'chat-user' : 'chat-assistant']"
        >
          <span class="chat-role">{{ item.role === 'user' ? 'You' : 'Urumi assistant' }}</span>
          <p>{{ item.content }}</p>
        </article>
        <p v-if="chatLoading" class="chat-thinking">Thinking and checking available tools…</p>
      </div>

      <form class="chat-composer" @submit.prevent="sendChatMessage">
        <label class="sr-only" for="chat-input">Message the store assistant</label>
        <textarea
          id="chat-input"
          v-model="chatInput"
          rows="2"
          maxlength="2000"
          placeholder="Ask: List the latest 5 products…"
          :disabled="chatLoading"
          @keydown.enter.exact.prevent="sendChatMessage"
        />
        <button type="submit" :disabled="chatLoading || !chatInput.trim()">
          {{ chatLoading ? 'Working…' : 'Send' }}
        </button>
      </form>
      <p v-if="chatError" class="chat-error">{{ chatError }}</p>
      <p class="hint">Uses the gateway API key above. Chat requests require the backend <code>POST /chat</code> endpoint.</p>
    </section>

    <!-- Gateway connection -->
    <section class="panel">
      <h2>Gateway connection</h2>

      <label for="api-key">Admin API key</label>

      <div class="connection">
        <input
          id="api-key"
          v-model="apiKey"
          type="password"
          placeholder="Enter your gateway API key"
          autocomplete="off"
        />

        <button
          :disabled="loading || keysLoading || auditLoading"
          @click="connectGateway"
        >
          {{
            loading || keysLoading || auditLoading
              ? 'Loading...'
              : 'Connect'
          }}
        </button>
      </div>

      <p v-if="message" class="message" role="status">
        {{ message }}
      </p>
    </section>

    <!-- Upstream servers -->
    <section class="panel">
      <div class="section-heading">
        <div>
          <h2>Upstream servers</h2>
          <p class="subtitle">
            Configure the MCP servers available to the gateway.
          </p>
        </div>

        <span class="count">{{ upstreams.length }} servers</span>
      </div>

      <div v-if="upstreams.length" class="server-list">
        <article
          v-for="server in upstreams"
          :key="server.id"
          class="server"
        >
          <div class="server-info">
            <strong>{{ server.name }}</strong>
            <span class="server-url">{{ server.url }}</span>

            <span
              :class="[
                'status',
                server.enabled ? 'active' : 'inactive',
              ]"
            >
              {{ server.enabled ? 'Enabled' : 'Disabled' }}
            </span>
          </div>

          <button
            class="secondary"
            @click="setEnabled(server, !server.enabled)"
          >
            {{ server.enabled ? 'Disable' : 'Enable' }}
          </button>
        </article>
      </div>

      <p v-else class="empty">
        No upstreams loaded. Connect to view configured servers.
      </p>
    </section>

    <!-- API key management -->
    <section class="panel">
      <div class="section-heading">
        <div>
          <h2>API key management</h2>
          <p class="subtitle">
            Review keys and revoke access when necessary.
          </p>
        </div>

        <button
          class="secondary"
          :disabled="keysLoading || !apiKey.trim()"
          @click="loadApiKeys"
        >
          {{ keysLoading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>

      <div class="key-summary">
        <div class="summary-card">
          <span class="summary-label">Active keys</span>
          <strong>{{ activeKeyCount }}</strong>
        </div>

        <div class="summary-card">
          <span class="summary-label">Revoked keys</span>
          <strong>{{ revokedKeyCount }}</strong>
        </div>
      </div>

      <p v-if="keysLoading" class="empty">Loading API keys...</p>

      <div v-else-if="apiKeys.length" class="key-list">
        <article
          v-for="key in apiKeys"
          :key="key.id"
          class="key-card"
        >
          <div class="key-info">
            <div class="key-title">
              <strong>Key {{ key.id.slice(0, 8) }}...</strong>

              <span
                :class="[
                  'status',
                  key.is_revoked ? 'inactive' : 'active',
                ]"
              >
                {{ key.is_revoked ? 'Revoked' : 'Active' }}
              </span>
            </div>

            <p><span>User ID:</span> {{ key.user_id }}</p>
            <p><span>Created:</span> {{ formatDate(key.created_at) }}</p>
            <p><span>Revoked:</span> {{ formatDate(key.revoked_at) }}</p>
          </div>

          <button
            v-if="!key.is_revoked"
            class="danger"
            :disabled="!!revokingId"
            @click="revokeApiKey(key)"
          >
            {{ revokingId === key.id ? 'Revoking...' : 'Revoke key' }}
          </button>
        </article>
      </div>

      <p v-else class="empty">
        No API keys loaded. Connect using an admin API key.
      </p>

      <p class="hint">
        Only key metadata is displayed. Secret API keys are not shown here.
        Revocation cannot be undone for that key.
      </p>
    </section>

    <!-- Audit logs -->
    <section class="panel">
      <div class="section-heading">
        <div>
          <h2>Audit logs</h2>
          <p class="subtitle">
            Review tool calls, outcomes and execution times.
          </p>
        </div>

        <button
          class="secondary"
          :disabled="auditLoading || !apiKey.trim()"
          @click="loadAuditLogs"
        >
          {{ auditLoading ? 'Refreshing...' : 'Refresh logs' }}
        </button>
      </div>

      <div class="audit-controls">
        <label for="audit-filter">Filter by outcome</label>

        <select id="audit-filter" v-model="auditFilter">
          <option value="all">All outcomes</option>
          <option value="success">Success</option>
          <option value="failure">Failure / other</option>
        </select>
      </div>

      <p v-if="auditLoading" class="empty">
        Loading audit logs...
      </p>

      <p v-else-if="filteredAuditLogs.length === 0" class="empty">
        No audit records match this filter.
      </p>

      <div v-else class="audit-list">
        <article
          v-for="log in filteredAuditLogs"
          :key="log.id"
          class="audit-card"
        >
          <div class="audit-heading">
            <strong>{{ log.tool_name }}</strong>

            <span
              :class="[
                'status',
                isSuccess(log.outcome) ? 'active' : 'inactive',
              ]"
            >
              {{ log.outcome }}
            </span>
          </div>

          <p><span>User:</span> {{ log.user_id }}</p>
          <p><span>Upstream:</span> {{ log.upstream_name }}</p>
          <p><span>Time:</span> {{ formatDate(log.timestamp) }}</p>
          <p>
            <span>Duration:</span>
            {{ Number(log.duration_seconds).toFixed(3) }} seconds
          </p>

          <div v-if="log.error_message" class="audit-error">
            <strong>Error details</strong>
            <p>{{ log.error_message }}</p>
          </div>
        </article>
      </div>

      <p class="hint">
        Showing up to 100 recent records. Access is restricted to admins.
      </p>
    </section>

    <!-- Add upstream -->
    <section class="panel">
      <h2>Add an upstream</h2>

      <form @submit.prevent="addUpstream">
        <label for="server-name">Server name</label>
        <input
          id="server-name"
          v-model.trim="name"
          required
          placeholder="e.g. docs"
        />

        <label for="server-url">Streamable HTTP URL</label>
        <input
          id="server-url"
          v-model.trim="url"
          type="url"
          required
          placeholder="http://127.0.0.1:8004/mcp"
        />

        <button type="submit">Add server</button>
      </form>

      <p class="hint">
        Your API key is used for requests and is not saved by this page.
      </p>
    </section>
  </main>
</template>

<style>
:root {
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  color: #e8edf6;
  background: #0b1020;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
}

button,
input,
select {
  font: inherit;
}

.dashboard {
  max-width: 1000px;
  margin: 0 auto;
  padding: 48px 24px 64px;
}

header {
  margin-bottom: 32px;
}

.eyebrow {
  color: #8ea4ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 2px;
}

h1 {
  margin: 8px 0;
  font-size: clamp(30px, 5vw, 44px);
}

h2 {
  margin: 0 0 18px;
  font-size: 19px;
}

.subtitle,
.hint {
  color: #9ba8bf;
}

.panel {
  margin: 20px 0;
  padding: 24px;
  border: 1px solid #29334b;
  border-radius: 16px;
  background: #131b2e;
}

label {
  display: block;
  margin: 14px 0 8px;
  color: #c4cee0;
  font-size: 13px;
}

input,
select {
  width: 100%;
  min-width: 0;
  padding: 12px 14px;
  color: #f2f5fb;
  background: #0b1020;
  border: 1px solid #35415d;
  border-radius: 9px;
}

input:focus,
select:focus {
  outline: 2px solid #8398ff;
  outline-offset: 1px;
}

.connection {
  display: flex;
  gap: 10px;
}

button {
  padding: 11px 16px;
  color: white;
  background: #526cf5;
  border: 0;
  border-radius: 9px;
  cursor: pointer;
  font-weight: 650;
}

button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.secondary {
  background: #26334d;
  white-space: nowrap;
}

.danger {
  background: #a9364b;
  white-space: nowrap;
}

.section-heading,
.server {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.count {
  color: #bdc9ff;
  font-size: 13px;
}

.server-list,
.key-list,
.audit-list {
  display: grid;
  gap: 12px;
}

.server,
.key-card,
.audit-card {
  padding: 16px;
  border: 1px solid #29334b;
  border-radius: 12px;
}

.server-info,
.key-info {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.server-url {
  color: #9ba8bf;
  overflow-wrap: anywhere;
  font-size: 13px;
}

.status {
  width: fit-content;
  padding: 4px 8px;
  border-radius: 20px;
  font-size: 12px;
}

.active {
  color: #82e2b2;
  background: #153c31;
}

.inactive {
  color: #f4c17b;
  background: #44321d;
}

.empty,
.hint {
  color: #9ba8bf;
  font-size: 13px;
}

.message {
  color: #bdc9ff;
  overflow-wrap: anywhere;
}

form {
  display: grid;
  gap: 8px;
}

form button {
  margin-top: 10px;
  justify-self: start;
}

.key-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}

.summary-card {
  padding: 16px;
  border: 1px solid #29334b;
  border-radius: 12px;
  display: grid;
  gap: 8px;
}

.summary-label {
  color: #9ba8bf;
  font-size: 13px;
}

.summary-card strong {
  font-size: 26px;
}

.key-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.key-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.key-info p,
.audit-card > p {
  margin: 0;
  font-size: 13px;
  overflow-wrap: anywhere;
  color: #c4cee0;
}

.key-info p span,
.audit-card > p span {
  color: #9ba8bf;
}

.audit-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 0;
  flex-wrap: wrap;
}

.audit-controls label {
  margin: 0;
}

.audit-controls select {
  width: auto;
  min-width: 180px;
}

.audit-card {
  display: grid;
  gap: 9px;
  min-width: 0;
}

.audit-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.audit-error {
  padding: 12px;
  border: 1px solid #70404b;
  border-radius: 9px;
  background: #301b28;
  overflow-wrap: anywhere;
}

.audit-error p {
  margin-bottom: 0;
  white-space: pre-wrap;
}

@media (max-width: 600px) {
  .dashboard {
    padding: 28px 14px;
  }

  .panel {
    padding: 18px;
  }

  .connection,
  .server,
  .key-card {
    align-items: stretch;
    flex-direction: column;
  }

  .connection button,
  .server button,
  .key-card button {
    width: 100%;
  }

  .section-heading {
    align-items: flex-start;
  }

  .audit-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .audit-controls select {
    width: 100%;
  }
}


/* Chatbot */
.chat-panel { gap: 18px; }
.chat-badge { border: 1px solid #344565; border-radius: 999px; padding: 6px 10px; color: #b8c8e6; font-size: 12px; white-space: nowrap; }
.chat-transcript { display: grid; gap: 12px; max-height: 420px; overflow-y: auto; padding: 14px; border: 1px solid #27334c; border-radius: 12px; background: #090e1b; }
.chat-message { max-width: 88%; padding: 12px 14px; border-radius: 12px; overflow-wrap: anywhere; }
.chat-message p { margin: 6px 0 0; white-space: pre-wrap; line-height: 1.55; }
.chat-user { justify-self: end; background: #243a61; border: 1px solid #365581; }
.chat-assistant { justify-self: start; background: #151e30; border: 1px solid #2a3852; }
.chat-role { font-size: 11px; color: #a9bddf; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.chat-thinking { margin: 0; color: #a9bddf; font-size: 13px; }
.chat-composer { display: flex; align-items: stretch; gap: 10px; }
.chat-composer textarea { flex: 1; resize: vertical; min-width: 0; border: 1px solid #34415b; border-radius: 10px; background: #0c1323; color: #e8edf6; padding: 12px; font: inherit; }
.chat-composer button { align-self: stretch; }
.chat-error { margin: 0; color: #ff9ca8; overflow-wrap: anywhere; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 600px) { .chat-composer { flex-direction: column; } .chat-composer button { width: 100%; } .chat-message { max-width: 100%; } }

</style>
