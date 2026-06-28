/* Trident v1.8.0 SSE连接管理器 */
window.TridentSSEManager = {
  eventSource: null,
  isConnected: false,
  lastActivity: 0,
  HEALTH_CHECK_INTERVAL: 30000,
  reconnectTimer: null,
  reconnectAttempts: 0,
  MAX_RECONNECT_DELAY: 30000,
  healthCheckTimer: null,
  MAX_LOG_LINES: 500,
  historyLoaded: false,

  getConnection() {
    if (this.eventSource && this.eventSource.readyState === EventSource.OPEN) {
      return this.eventSource;
    }
    // 先加载历史日志，再连接SSE
    if (!this.historyLoaded) {
      this.loadHistory();
    }
    return this.createConnection();
  },

  loadHistory() {
    var self = this;
    var logStream = document.getElementById('live-log-stream');
    if (!logStream) {
      // 不设置 historyLoaded，等 DOM 准备好后再加载
      return;
    }
    fetch('/admin/logs/history')
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function(html) {
        if (html && html.trim()) {
          logStream.innerHTML = html;
        }
        self.historyLoaded = true;
      })
      .catch(function(e) {
        console.error('[SSE-MGR] History load failed:', e);
        self.historyLoaded = true;
      });
  },

  createConnection() {
    console.log('[SSE-MGR] Creating new connection...');
    if (this.eventSource) { this.eventSource.close(); }

    const tokenMeta = document.querySelector('meta[name="sse-token"]');
    const token = tokenMeta ? tokenMeta.content : '';
    if (!token) { console.error('[SSE-MGR] Token missing'); return null; }

    this.updateStatus('connecting');
    const sseUrl = '/admin/stream_logs?token=' + encodeURIComponent(token);
    this.eventSource = new EventSource(sseUrl, { withCredentials: true });

    this.eventSource.onopen = () => {
      console.log('[SSE-MGR] Connected');
      this.isConnected = true;
      this.lastActivity = Date.now();
      this.reconnectAttempts = 0;
      this.updateStatus('connected');
      this.startHealthCheck();
    };

    this.eventSource.onerror = (e) => {
      console.error('[SSE-MGR] Error:', e);
      this.isConnected = false;
      this.updateStatus('disconnected');
      this.stopHealthCheck();

      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);

      const baseDelay = Math.min(5000 * Math.pow(2, this.reconnectAttempts), this.MAX_RECONNECT_DELAY);
      const jitter = Math.random() * 2000;
      const delay = baseDelay + jitter;
      this.reconnectAttempts++;

      console.log('[SSE-MGR] Reconnect in ' + Math.round(delay) + 'ms (attempt ' + this.reconnectAttempts + ')');
      this.reconnectTimer = setTimeout(() => this.getConnection(), delay);
    };

    this.eventSource.onmessage = (e) => {
      this.lastActivity = Date.now();
      this.appendLogLine(e.data);
    };

    return this.eventSource;
  },

  appendLogLine(rawData) {
    const logStream = document.getElementById('log-stream');
    if (!logStream) return;

    let logClass = 'info';
    const upper = rawData.toUpperCase();
    if (upper.indexOf('[CRITICAL]') !== -1 || upper.indexOf('CRITICAL') !== -1) {
      logClass = 'critical';
    } else if (upper.indexOf('[ERROR]') !== -1 || upper.indexOf('ERROR') !== -1) {
      logClass = 'error';
    } else if (upper.indexOf('[WARNING]') !== -1 || upper.indexOf('WARN') !== -1) {
      logClass = 'warn';
    } else if (upper.indexOf('[DEBUG]') !== -1 || upper.indexOf('DEBUG') !== -1) {
      logClass = 'debug';
    }

    if (rawData.indexOf('[SSE]') === 0 && (rawData.indexOf('连接') !== -1 || rawData.indexOf('监控') !== -1)) {
      return;
    }

    const line = document.createElement('div');
    line.className = 'log-line ' + logClass;
    line.textContent = rawData;

    const filterInput = document.getElementById('log-search-input');
    const term = filterInput ? filterInput.value.toLowerCase() : '';
    if (term && !rawData.toLowerCase().includes(term)) {
      line.style.display = 'none';
    }

    logStream.appendChild(line);

    while (logStream.children.length > this.MAX_LOG_LINES) {
      logStream.removeChild(logStream.firstChild);
    }

    logStream.scrollTop = logStream.scrollHeight;
  },

  disconnect() {
    this.stopHealthCheck();
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.isConnected = false;
      this.reconnectAttempts = 0;
      this.historyLoaded = false;
      this.updateStatus('disconnected');
      console.log('[SSE-MGR] Disconnected');
    }
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
  },

  startHealthCheck() {
    this.stopHealthCheck();
    this.healthCheckTimer = setInterval(() => {
      const elapsed = Date.now() - this.lastActivity;
      if (elapsed > this.HEALTH_CHECK_INTERVAL * 2) {
        console.warn('[SSE-MGR] Health check failed - no activity for ' + elapsed + 'ms');
        if (this.eventSource) {
          this.eventSource.close();
          this.isConnected = false;
          this.updateStatus('disconnected');
          this.getConnection();
        }
      }
    }, this.HEALTH_CHECK_INTERVAL);
  },

  stopHealthCheck() {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
  },

  updateStatus(state) {
    const el = document.getElementById('sse-status-indicator');
    if (!el) return;
    el.className = 'sse-status ' + state;
    const label = el.querySelector('.status-label');
    if (label) {
      label.textContent = state === 'connected' ? 'LIVE' : state === 'connecting' ? '...' : 'OFF';
    }
  }
};
