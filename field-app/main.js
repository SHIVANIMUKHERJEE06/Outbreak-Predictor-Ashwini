// main.js
//
// Two things happen here:
//
// 1. OFFLINE-FIRST SAVING (unchanged in spirit from the original
//    version): every form submission saves straight to localStorage
//    before anything else happens. This never depends on a network
//    call, which is what makes the app genuinely usable with no
//    connection.
//
// 2. BACKEND SYNC (new): "Sync to server" sends the queued entries to
//    the live backend API (see ../backend/main.py) and triggers a
//    recompute of the risk scores. If the server can't be reached,
//    the app tells you plainly and points you to the CSV export
//    instead - it never pretends a sync succeeded when it didn't.

import '@fontsource/space-grotesk/500.css'
import '@fontsource/space-grotesk/700.css'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/ibm-plex-sans/600.css'

// Change VITE_API_BASE_URL in your .env file (or Vercel's environment
// variables) to point at your deployed backend. Falls back to
// localhost for local development if that variable isn't set.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const HEALTH_CHECK_INTERVAL_MS = 10000

const DISTRICT_NAMES = {
  '814112': 'Deoghar',
  '834001': 'Ranchi',
  '826001': 'Dhanbad',
  '827001': 'Bokaro',
  '831001': 'Jamshedpur',
  '833201': 'West Singhbhum',
  '816109': 'Sahibganj',
  '822101': 'Palamu',
}

const STORAGE_KEY = 'asha_pending_entries'

const form = document.getElementById('log-form')
const queueList = document.getElementById('queue-list')
const queueCount = document.getElementById('queue-count')
const syncBtn = document.getElementById('sync-btn')
const exportBtn = document.getElementById('export-btn')
const syncMessage = document.getElementById('sync-message')
const connectionStatus = document.getElementById('connection-status')
const serverStatus = document.getElementById('server-status')
const stampBanner = document.getElementById('stamp-banner')
const stampDetail = document.getElementById('stamp-detail')

let backendReachable = false

// ---------- Local queue (offline-first storage) ----------

function loadQueue() {
  const raw = localStorage.getItem(STORAGE_KEY)
  return raw ? JSON.parse(raw) : []
}

function saveQueue(queue) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queue))
}

function renderQueue() {
  const queue = loadQueue()
  queueCount.textContent = queue.length
  syncBtn.disabled = !backendReachable
  exportBtn.disabled = queue.length === 0

  queueList.innerHTML = ''
  queue.forEach((entry, index) => {
    const li = document.createElement('li')
    li.innerHTML = `
      <span>
        <strong>${DISTRICT_NAMES[entry.district_code]}</strong>
        &mdash; ${entry.disease}, ${entry.case_count} case(s)
        <br /><small>${entry.timestamp}</small>
      </span>
      <button class="remove-btn" data-index="${index}" aria-label="Remove entry">&times;</button>
    `
    queueList.appendChild(li)
  })

  document.querySelectorAll('.remove-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const queue = loadQueue()
      queue.splice(Number(btn.dataset.index), 1)
      saveQueue(queue)
      renderQueue()
    })
  })
}

// ---------- Connection + backend health status ----------

function updateConnectionStatus() {
  if (navigator.onLine) {
    connectionStatus.textContent = 'Online'
    connectionStatus.className = 'status-pill good'
  } else {
    connectionStatus.textContent = 'Offline — saving locally'
    connectionStatus.className = 'status-pill bad'
    backendReachable = false
    serverStatus.textContent = 'Server unreachable'
    serverStatus.className = 'status-pill bad'
  }
  renderQueue()
}

async function checkBackendHealth() {
  if (!navigator.onLine) return

  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)
    const res = await fetch(`${API_BASE_URL}/api/health`, { signal: controller.signal })
    clearTimeout(timeout)

    if (res.ok) {
      backendReachable = true
      serverStatus.textContent = 'Server connected'
      serverStatus.className = 'status-pill good'
    } else {
      throw new Error('Server responded with an error')
    }
  } catch {
    backendReachable = false
    serverStatus.textContent = 'Server unreachable'
    serverStatus.className = 'status-pill bad'
  }
  renderQueue()
}

// ---------- Form submission ----------

form.addEventListener('submit', (e) => {
  e.preventDefault()

  const entry = {
    district_code: document.getElementById('district').value,
    disease: document.getElementById('disease').value,
    case_count: Number(document.getElementById('case-count').value),
    notes: document.getElementById('notes').value,
    timestamp: new Date().toISOString(),
  }

  const queue = loadQueue()
  queue.push(entry)
  saveQueue(queue)
  renderQueue()

  form.reset()
})

// ---------- Sync to backend ----------

syncBtn.addEventListener('click', async () => {
  const queue = loadQueue()

  syncBtn.disabled = true
  syncBtn.textContent = 'Syncing...'
  syncMessage.textContent = ''
  stampBanner.hidden = true

  const failedEntries = []

  for (const entry of queue) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ? JSON.stringify(body.detail) : `HTTP ${res.status}`)
      }
    } catch (err) {
      failedEntries.push({ entry, error: err.message })
    }
  }

  const succeededCount = queue.length - failedEntries.length

  // Clear successfully-posted entries from the local queue RIGHT NOW,
  // regardless of what happens with recompute next. This matters:
  // those entries are already saved on the server, so leaving them in
  // the queue would mean sending duplicates if the user syncs again.
  if (succeededCount > 0) {
    saveQueue(failedEntries.map((f) => f.entry))
    renderQueue()
  }

  // Attempt recompute if new entries were just sent, OR if the queue
  // was already empty (meaning the user is explicitly retrying a
  // recompute that failed last time, with nothing new to send).
  const shouldRecompute = succeededCount > 0 || queue.length === 0

  if (shouldRecompute) {
    try {
      const recomputeRes = await fetch(`${API_BASE_URL}/api/recompute`, { method: 'POST' })

      if (!recomputeRes.ok) {
        const body = await recomputeRes.json().catch(() => ({}))
        const detail = body.detail || `HTTP ${recomputeRes.status}`
        throw new Error(detail)
      }

      stampBanner.hidden = false
      stampDetail.textContent = succeededCount > 0
        ? `${succeededCount} entr${succeededCount === 1 ? 'y' : 'ies'} sent, risk scores updated`
        : 'Risk scores updated'
    } catch (err) {
      syncMessage.textContent = succeededCount > 0
        ? `${succeededCount} entr${succeededCount === 1 ? 'y' : 'ies'} saved on the server, but the recompute step failed: ` +
          `${err.message} — your data is safe, tap "Sync to server" again to retry just the recompute.`
        : `Recompute failed: ${err.message} — tap "Sync to server" again to retry.`
    }
  }

  if (failedEntries.length > 0) {
    syncMessage.textContent =
      `${failedEntries.length} entr${failedEntries.length === 1 ? 'y' : 'ies'} could not be sent. ` +
      `They're still saved on this device — try again, or use the CSV export below as a backup.`
  }

  syncBtn.textContent = 'Sync to server'
  renderQueue()
})

// ---------- CSV export (manual backup path) ----------

exportBtn.addEventListener('click', () => {
  const queue = loadQueue()
  if (queue.length === 0) return

  const header = 'timestamp,district_code,district_name,disease,case_count,notes\n'
  const rows = queue
    .map((e) =>
      [e.timestamp, e.district_code, DISTRICT_NAMES[e.district_code], e.disease, e.case_count, `"${e.notes.replace(/"/g, '""')}"`].join(',')
    )
    .join('\n')

  const blob = new Blob([header + rows], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `asha_field_log_backup_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
})

// ---------- Init ----------

window.addEventListener('online', () => {
  updateConnectionStatus()
  checkBackendHealth()
})
window.addEventListener('offline', updateConnectionStatus)

updateConnectionStatus()
checkBackendHealth()
setInterval(checkBackendHealth, HEALTH_CHECK_INTERVAL_MS)
renderQueue()
