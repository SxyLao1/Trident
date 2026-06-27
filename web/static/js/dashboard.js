/* Trident v1.8.0 仪表盘主逻辑 */

/* ============================================================
   Dashboard 全局函数（必须在 dashboard.js 中预定义，因为
   dashboard_content.html 通过 innerHTML 插入时其中的 <script> 不会执行）
   ============================================================ */

function toggleDashboardAudit() {
  var btn = document.getElementById('dash-audit-btn');
  var container = document.getElementById('records-table-container');
  if (!container || !btn) return;
  // 判断当前状态：按钮文本包含 "Normal" 说明当前是 Audit 模式
  var isAuditMode = btn.textContent.indexOf('Normal') !== -1;
  var url = isAuditMode ? '/admin/records?compact=1' : '/admin/records?audit=true&compact=1';
  var nextLabel = isAuditMode ? 'Audit' : '← Normal';
  var nextAuditParam = isAuditMode ? 'false' : 'true';
  fetch(url, { headers: { 'HX-Request': 'true' } })
    .then(function(r){ return r.text(); })
    .then(function(html){
      // 使用 outerHTML 替换容器，避免 records_table.html 最外层 div 嵌套
      var temp = document.createElement('div');
      temp.innerHTML = html;
      var newContainer = temp.firstElementChild;
      if (newContainer) {
        container.replaceWith(newContainer);
        container = document.getElementById('records-table-container');
        if (window.htmx) htmx.process(container);
      }
      btn.textContent = nextLabel;
      // 同步更新 Filter 的 hx-get audit 参数
      var filterInput = document.querySelector('#records-table-container').closest('.card').querySelector('input[name="q"]');
      if (filterInput) {
        filterInput.setAttribute('hx-get', '/admin/search?compact=1&audit=' + nextAuditParam);
      }
    })
    .catch(function(e){
      console.error('Audit toggle failed:', e);
    });
}

/* 当前页面状态（用于Refresh按钮） */
var _currentPath = 'dashboard_content';
var _currentTitle = 'Dashboard';

/* Loading占位HTML */
var _loadingHtml = '<div class="empty-state"><div class="spinner"></div><p>Initializing dashboard...</p></div>';

document.addEventListener('DOMContentLoaded', function() {
  TridentUtils.setupHtmxCsrf();

  // 初始加载dashboard
  setTimeout(function() {
    loadDashboard();
  }, 300);

  // SSE连接
  if (window.TridentSSEManager) {
    TridentSSEManager.getConnection();
  }

  // 导航点击事件
  document.querySelectorAll('.nav-link[data-path]').forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      var path = this.dataset.path;
      var title = this.dataset.title || path;
      loadContent(path, title);
      TridentUtils.highlightNav(path.replace('_content', ''));
    });
  });

  // 登出
  var logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function(e) {
      e.preventDefault();
      TridentUtils.confirm('Confirm logout?', function() {
        if (window.TridentSSEManager) TridentSSEManager.disconnect();
        window.location.href = '/admin/logout';
      });
    });
  }

  // 模态框关闭
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
      e.target.classList.remove('active');
    }
    if (e.target.classList.contains('modal-close')) {
      var overlay = e.target.closest('.modal-overlay');
      if (overlay) overlay.classList.remove('active');
    }
  });

  // 移动端侧边栏
  var sidebarToggle = document.getElementById('sidebar-toggle');
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function() {
      var sidebar = document.querySelector('.app-sidebar');
      var overlay = document.getElementById('sidebar-overlay');
      sidebar.classList.toggle('open');
      overlay.classList.toggle('active');
      this.classList.toggle('active');
    });
  }

  // 移动端导航点击关闭侧边栏
  document.querySelectorAll('.nav-link[data-path]').forEach(function(link) {
    link.addEventListener('click', function() {
      if (window.innerWidth <= 768) {
        closeSidebar();
      }
    });
  });
});

function closeSidebar() {
  var sidebar = document.querySelector('.app-sidebar');
  var overlay = document.getElementById('sidebar-overlay');
  var toggle = document.getElementById('sidebar-toggle');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('active');
  if (toggle) toggle.classList.remove('active');
}

/* ============================================================
   Dashboard加载
   ============================================================ */
function loadDashboard() {
  // v1.7.9: 仅在Dashboard页面自动加载，避免覆盖quarantine/audit等其他页面内容
  // v1.8.0: Overview 是默认首页
  if (window.location.pathname !== '/admin/' && window.location.pathname !== '/admin' && window.location.pathname !== '/admin/overview') {
    return;
  }
  var contentArea = document.getElementById('main-content');
  if (!contentArea) return;

  // 清空 toolbar
  var headerCenter = document.getElementById('header-center');
  if (headerCenter) headerCenter.innerHTML = '';
  var brandSub = document.querySelector('.brand-sub');
  if (brandSub) brandSub.textContent = 'Dashboard';

  // 先显示loading
  contentArea.innerHTML = _loadingHtml;

  fetch('/admin/overview', { headers: { 'HX-Request': 'true' } })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    })
    .then(function(html) {
      // 嵌套防护
      if (html.indexOf('app-header') !== -1 || html.indexOf('app-shell') !== -1) {
        console.error('[Dashboard] Nested page detected, redirecting...');
        window.location.href = '/admin/dashboard';
        return;
      }
      contentArea.innerHTML = html;
      if (window.htmx) {
        htmx.process(contentArea);
        contentArea.querySelectorAll('[hx-trigger*="load"]').forEach(function(el) {
          htmx.trigger(el, 'load');
        });
      }
      setTimeout(loadDashboardPanels, 50);

      // v1.8.4: Auto-scroll live log stream to bottom + MutationObserver
      setTimeout(function() {
        var logStream = document.getElementById('live-log-stream');
        if (logStream) {
          logStream.scrollTop = logStream.scrollHeight;
          // Observe new SSE lines and auto-scroll
          if (!window._logStreamObserver) {
            window._logStreamObserver = new MutationObserver(function() {
              logStream.scrollTop = logStream.scrollHeight;
            });
            window._logStreamObserver.observe(logStream, { childList: true, subtree: false });
          }
        }
      }, 200);

    })
    .catch(function(err) {
      console.error('[Dashboard] Load failed:', err);
      contentArea.innerHTML = '<div class="empty-state"><div style="font-size:32px;margin-bottom:12px;">⚠</div><p>Failed to load dashboard: ' + err.message + '</p></div>';
    });
}

/* ============================================================
   通用内容加载
   ============================================================ */
function loadContent(path, title) {
  var contentArea = document.getElementById('main-content');
  if (!contentArea) return;

  // 更新状态
  _currentPath = path;
  _currentTitle = title || path;

  // 更新 header 中的页面标题显示
  var brandSub = document.querySelector('.brand-sub');
  if (brandSub) brandSub.textContent = _currentTitle;
  // 同步更新 page-title（大标题）
  var pageTitle = document.getElementById('page-title');
  if (pageTitle) pageTitle.textContent = _currentTitle;

  // v1.8.0: header-center 留给未来多站点选择器，页面工具栏留在各自内容区
  var headerCenter = document.getElementById('header-center');
  if (headerCenter) headerCenter.innerHTML = '';

  // 先显示loading
  contentArea.innerHTML = _loadingHtml;

  // 使用fetch加载
  fetch('/admin/' + path, { headers: { 'HX-Request': 'true' } })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    })
    .then(function(html) {
      // 嵌套防护
      if (html.indexOf('app-header') !== -1 || html.indexOf('app-shell') !== -1) {
        console.error('[Dashboard] Nested page detected, redirecting...');
        window.location.href = '/admin/dashboard';
        return;
      }

      contentArea.innerHTML = html;
      // 手动处理HTMX属性
      if (window.htmx) {
        htmx.process(contentArea);
        contentArea.querySelectorAll('[hx-trigger*="load"]').forEach(function(el) {
          htmx.trigger(el, 'load');
        });
      }
      // v1.8.2: Load block status if Profiles page
      if (path === 'profiles') {
        setTimeout(function() { if (typeof loadBlockStatus === 'function') loadBlockStatus(); }, 300);
      }
      if (path === 'scanner') {
        setTimeout(function() { if (typeof loadScanHistory === 'function') loadScanHistory(); }, 200);
      }
    })
    .catch(function(err) {
      console.error('[Content] Load failed:', err);
      contentArea.innerHTML = '<div class="empty-state"><div style="font-size:32px;margin-bottom:12px;">⚠</div><p>' + err.message + '</p></div>';
    });
}

/* ============================================================
   v1.8.0: Shared functions (Threats tabs + Log Analyzer)
   Defined here because HTMX innerHTML does not execute <script> tags
   ============================================================ */

var _threatsTabsLoaded = {active: true, quarantine: false, audit: false, clusters: false};

// Auto-load hidden tabs when Threats page loads
document.addEventListener('htmx:afterSettle', function(evt) {
  if (evt.target && evt.target.id === 'main-content') {
    // Check if Threats page just loaded
    if (document.querySelector('.threats-tab')) {
      setTimeout(function() {
        ['quarantine', 'audit', 'clusters'].forEach(function(tab) {
          if (!_threatsTabsLoaded[tab]) {
            _threatsTabsLoaded[tab] = true;
            var urls = { quarantine: '/admin/quarantine?status=quarantined', audit: '/admin/records?audit=true&compact=1', clusters: '/admin/file-clusters' };
            var targets = { quarantine: '#threats-quarantine-container', audit: '#threats-audit-container', clusters: '#threats-clusters-container' };
            if (urls[tab] && window.htmx) htmx.ajax('GET', urls[tab], {target: targets[tab], swap: 'innerHTML'});
          }
        });
      }, 200);
    }
  }
});

function switchThreatsTab(tab) {
  document.querySelectorAll('.threats-tab').forEach(function(t) {
    t.style.color = '#666'; t.style.borderBottomColor = 'transparent'; t.classList.remove('active');
  });
  var at = document.querySelector('.threats-tab[data-tab="' + tab + '"]');
  if (at) { at.style.color = '#00ff41'; at.style.borderBottomColor = '#00ff41'; at.classList.add('active'); }
  document.querySelectorAll('.threats-tab-content').forEach(function(c) { c.style.display = 'none'; });
  var ct = document.getElementById('threats-tab-' + tab);
  if (ct) {
    ct.style.display = 'flex';
    if (!_threatsTabsLoaded[tab]) {
      _threatsTabsLoaded[tab] = true;
      var urls = { quarantine: '/admin/quarantine?status=quarantined', audit: '/admin/records?audit=true&compact=1', clusters: '/admin/file-clusters' };
      var targets = { quarantine: '#threats-quarantine-container', audit: '#threats-audit-container', clusters: '#threats-clusters-container' };
      if (urls[tab] && window.htmx) htmx.ajax('GET', urls[tab], {target: targets[tab], swap: 'innerHTML'});
    }
  }
}

function openLogAnalyzer() {
  var m = document.getElementById('log-analyzer-modal'); if (!m) return;
  m.style.display = 'flex';
  m.style.visibility = 'visible';
  m.style.opacity = '1';
  m.classList.add('active');
  var s = document.getElementById('live-log-stream'), t = document.getElementById('analyzer-log-content');
  if (s && t) { t.innerHTML = s.innerHTML; t.scrollTop = t.scrollHeight; }
  // Mirror live SSE into analyzer
  if (!window._analyzerMirror) {
    window._analyzerMirror = new MutationObserver(function() {
      var src = document.getElementById('live-log-stream');
      var dst = document.getElementById('analyzer-log-content');
      var mod = document.getElementById('log-analyzer-modal');
      if (src && dst && mod && mod.style.display !== 'none') {
        dst.innerHTML = src.innerHTML; dst.scrollTop = dst.scrollHeight;
      }
    });
    if (s) window._analyzerMirror.observe(s, {childList: true, subtree: true});
  }
}

function closeLogAnalyzer() {
  var m = document.getElementById('log-analyzer-modal'); if (!m) return;
  m.style.display = 'none'; m.style.visibility = 'hidden'; m.style.opacity = '0';
  m.classList.remove('active');
}

function analyzerTimePreset() {
  var tr = document.getElementById('analyzer-time-filter')?.value || 'all';
  var custom = document.getElementById('analyzer-custom-time');
  if (custom) custom.style.display = (tr === 'custom') ? '' : 'none';
  filterLogAnalyzer();
}

function filterLogAnalyzer() {
  var kw = (document.getElementById('analyzer-filter-input')?.value || '').toLowerCase();
  var lv = document.getElementById('analyzer-level-filter')?.value || 'all';
  var md = document.getElementById('analyzer-module-filter')?.value || 'all';
  var tr = document.getElementById('analyzer-time-filter')?.value || 'all';
  var c = document.getElementById('analyzer-log-content'); if (!c) return;

  // Time range: relative presets
  var now = Date.now(), minTime = 0, maxTime = 0;
  if (tr === '1h') minTime = now - 3600000;
  else if (tr === '6h') minTime = now - 21600000;
  else if (tr === '24h') minTime = now - 86400000;
  else if (tr === '7d') minTime = now - 604800000;
  else if (tr === '30d') minTime = now - 2592000000;
  else if (tr === 'custom') {
    // Custom absolute range: date + time inputs
    var fd = document.getElementById('analyzer-time-from-date');
    var ft = document.getElementById('analyzer-time-from-time');
    var td = document.getElementById('analyzer-time-to-date');
    var tt = document.getElementById('analyzer-time-to-time');
    if (fd && fd.value) { var fv = fd.value; if (ft && ft.value) fv += 'T' + ft.value; else fv += 'T00:00'; minTime = new Date(fv).getTime(); }
    if (td && td.value) { var tv = td.value; if (tt && tt.value) tv += 'T' + tt.value; else tv += 'T23:59'; maxTime = new Date(tv).getTime(); }
  }

  var v = 0;
  c.querySelectorAll('.log-line').forEach(function(el) {
    var tx = el.textContent; var s = true;
    if (kw && tx.toLowerCase().indexOf(kw) < 0) s = false;
    // Level: match ' CRITICAL ', '[CRITICAL]', or 'CRITICAL -'
    if (lv !== 'all') {
      var up = tx.toUpperCase();
      if (up.indexOf(' ' + lv + ' ') < 0 && up.indexOf('[' + lv + ']') < 0 && up.indexOf(lv + ' -') < 0) s = false;
    }
    if (md !== 'all' && tx.indexOf('[' + md + ']') < 0) s = false;
    // Time range
    if (minTime > 0 || maxTime > 0) {
      var m = tx.match(/\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
      if (m) {
        var ts = new Date(m[1].replace(' ', 'T')).getTime();
        if (minTime > 0 && ts < minTime) s = false;
        if (maxTime > 0 && ts > maxTime) s = false;
      }
    }
    el.style.display = s ? '' : 'none'; if (s) v++;
  });
  var ce = document.getElementById('analyzer-count'); if (ce) ce.textContent = v + ' lines';
}

function filterLogStream() {
  var kw = (document.getElementById('log-filter-input')?.value || '').toLowerCase();
  var c = document.getElementById('live-log-stream'); if (!c) return;
  c.querySelectorAll('.log-line').forEach(function(el) {
    el.style.display = (kw && el.textContent.toLowerCase().indexOf(kw) < 0) ? 'none' : '';
  });
}

// v1.8.0: Moved from dashboard.html for consistency
function closeRecordDetail() {
  var overlay = document.getElementById('record-detail-modal-overlay');
  var modal = document.getElementById('record-detail-modal');
  if (overlay) { overlay.style.display = 'none'; overlay.classList.remove('active'); }
  if (modal) { modal.style.display = 'none'; modal.classList.remove('active'); modal.innerHTML = ''; }
}

// v1.8.0: Auto-show record detail modal when content is swapped in
document.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'record-detail-modal') {
    showRecordDetail();
  }
});

// v1.8.0: System modal (Settings page)
var _systemUrls = {
  registry: '/admin/system/registry_panel',
  wal: '/admin/system/wal_panel',
  session: '/admin/system/session_panel?per_page=6',
  config: '/admin/system/config_panel'
};
var _systemTitles = {
  registry: 'Registry Status', wal: 'WAL Management',
  session: 'Session Management', config: 'Config Reload'
};
var _systemActions = {
  registry: '<button class=\"btn btn-ghost btn-sm\" hx-post=\"/admin/system/registry/compact\" hx-target=\"#system-modal-body\" hx-swap=\"innerHTML\">Compact</button>',
  wal: '<button class=\"btn btn-ghost btn-sm\" hx-post=\"/admin/system/wal/replay\" hx-target=\"#system-modal-body\" hx-swap=\"innerHTML\">Replay</button>',
  session: '<button class=\"btn btn-ghost btn-sm\" hx-post=\"/admin/system/session/cleanup\" hx-target=\"#system-modal-body\" hx-swap=\"innerHTML\">Cleanup</button>',
  config: '<button class=\"btn btn-ghost btn-sm\" hx-post=\"/admin/system/config/reload\" hx-confirm=\"Reload config?\" hx-target=\"#system-modal-body\" hx-swap=\"innerHTML\">Reload</button>'
};
function openSystemModal(type) {
  var m = document.getElementById('system-modal');
  var t = document.getElementById('system-modal-title');
  var b = document.getElementById('system-modal-body');
  var a = document.getElementById('system-modal-actions');
  if (!m || !b) return;
  m.style.display = 'flex'; m.style.visibility = 'visible'; m.style.opacity = '1';
  m.classList.add('active');
  if (t) t.textContent = _systemTitles[type] || type;
  if (a) a.innerHTML = _systemActions[type] || '';
  b.innerHTML = '<div class=\"empty-state\"><div class=\"spinner\"></div><p>Loading...</p></div>';
  if (_systemUrls[type]) htmx.ajax('GET', _systemUrls[type], {target: '#system-modal-body', swap: 'innerHTML'});
}
function closeSystemModal() {
  var m = document.getElementById('system-modal'); if (!m) return;
  m.style.display = 'none'; m.style.visibility = 'hidden'; m.style.opacity = '0';
  m.classList.remove('active');
}

// v1.8.1: IP cross-page selection (profile detail page)
window._ipSelected = window._ipSelected || new Set();
window._ipTotal = window._ipTotal || 0;

function _restoreIPCheckboxes() {
  document.querySelectorAll('.ip-checkbox').forEach(function(cb) {
    cb.checked = window._ipSelected.has(cb.value);
  });
  _updateIPUI();
}

function toggleIPRow(row) {
  var cb = row.querySelector('.ip-checkbox'); cb.checked = !cb.checked;
  if (cb.checked) window._ipSelected.add(cb.value); else window._ipSelected.delete(cb.value);
  _updateIPUI();
}

function toggleAllIPs(m) {
  document.querySelectorAll('.ip-checkbox').forEach(function(cb) {
    cb.checked = m.checked;
    if (m.checked) window._ipSelected.add(cb.value); else window._ipSelected.delete(cb.value);
  });
  _updateIPUI();
}

function selectAllIPs() {
  document.querySelectorAll('.ip-checkbox').forEach(function(cb) {
    cb.checked = true; window._ipSelected.add(cb.value);
  });
  _updateIPUI();
}

function selectAllIPsAll() {
  // Select all IPs across all pages — read full list from data attribute
  var section = document.getElementById('ip-table-section');
  if (section && section.dataset.allIps) {
    try {
      var allIps = JSON.parse(section.dataset.allIps);
      allIps.forEach(function(ip) { window._ipSelected.add(ip); });
    } catch(e) { console.error('Failed to parse all IPs:', e); }
  }
  // Also check visible checkboxes
  document.querySelectorAll('.ip-checkbox').forEach(function(cb) {
    cb.checked = true;
    window._ipSelected.add(cb.value);
  });
  _updateIPUI();
}

function clearIPSelection() {
  window._ipSelected.clear();
  document.querySelectorAll('.ip-checkbox').forEach(function(cb) { cb.checked = false; });
  _updateIPUI();
}

function toggleIPCheckbox(cb) {
  if (cb.checked) window._ipSelected.add(cb.value);
  else window._ipSelected.delete(cb.value);
  _updateIPUI();
}
function updateBlockBtn() { _updateIPUI(); }

/* ============================================================
   v1.9.0: Records batch selection + toolbar (class-based, no dup IDs)
   ============================================================ */
window._recSelected = window._recSelected || new Set();

function _recUpdateUI() {
  var c = window._recSelected.size;
  document.querySelectorAll('.rec-count').forEach(function(el) { el.textContent = c + ' selected'; });
  document.querySelectorAll('.rec-batch-btn').forEach(function(b) { b.disabled = c === 0; });
}
function _restoreRecCheckboxes() {
  document.querySelectorAll('.rec-checkbox').forEach(function(cb) {
    cb.checked = window._recSelected.has(cb.value);
  });
  _recUpdateUI();
}
function toggleRecCb(cb) {
  if (cb.checked) window._recSelected.add(cb.value);
  else window._recSelected.delete(cb.value);
  _recUpdateUI();
}
function selRecPage(btn) {
  var row = btn.closest('[id^="records-table-container"]');
  (row||document).querySelectorAll('.rec-checkbox').forEach(function(cb) {
    cb.checked = true; window._recSelected.add(cb.value);
  });
  _recUpdateUI();
}
function selRecAll(btn) {
  var row = btn.closest('[data-all-paths]');
  if (row && row.dataset.allPaths) {
    try { JSON.parse(row.dataset.allPaths).forEach(function(p) { window._recSelected.add(p); }); } catch(e) {}
  }
  (row||document).querySelectorAll('.rec-checkbox').forEach(function(cb) {
    cb.checked = true; window._recSelected.add(cb.value);
  });
  _recUpdateUI();
}
function clearRecSel(btn) {
  window._recSelected.clear();
  var row = btn.closest('[id^="records-table-container"]');
  (row||document).querySelectorAll('.rec-checkbox').forEach(function(cb) { cb.checked = false; });
  _recUpdateUI();
}
function batchRecAction(action) {
  var paths = Array.from(window._recSelected);
  if (!paths.length) return;
  var labels = {quarantine:'Quarantine', false_positive:'Mark as FP', delete:'Delete'};
  if (!confirm(labels[action] + ' ' + paths.length + ' records?')) return;
  var csrf = document.querySelector('meta[name="csrf-token"]');
  var token = csrf ? csrf.content : '';
  var body = 'action=' + action;
  paths.forEach(function(fp) { body += '&file_paths[]=' + encodeURIComponent(fp); });
  fetch('/admin/records/batch', {
    method: 'POST',
    headers: {'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':token},
    body: body
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    alert('Done: ' + (d.success||0) + ' success, ' + (d.skipped||0) + ' skipped, ' + (d.failed||0) + ' failed');
    window._recSelected.clear();
    var container = document.querySelector('[id^="records-table-container"]');
    if (container && window.htmx) {
      htmx.ajax('GET', '/admin/records?compact=1' + (container.id.indexOf('audit')!==-1?'&audit=true':''), {target:'#'+container.id,swap:'outerHTML'});
    }
  })
  .catch(function(e) { alert('Batch failed: ' + e.message); });
}

/* ============================================================
   v1.9.0: Quarantine batch selection (class-based)
   ============================================================ */
window._qSelected = window._qSelected || new Set();

function _qUpdateUI() {
  var c = window._qSelected.size;
  document.querySelectorAll('.q-count').forEach(function(el) { el.textContent = c + ' selected'; });
  document.querySelectorAll('.q-batch-btn').forEach(function(b) { b.disabled = c === 0; });
}
function _restoreQCheckboxes() {
  document.querySelectorAll('.q-checkbox').forEach(function(cb) {
    cb.checked = window._qSelected.has(cb.value);
  });
  _qUpdateUI();
}
function toggleQCheckbox(cb) {
  if (cb.checked) window._qSelected.add(cb.value);
  else window._qSelected.delete(cb.value);
  _qUpdateUI();
}
function selQPage(btn) {
  var row = btn.closest('#quarantine-list-container');
  (row||document).querySelectorAll('.q-checkbox').forEach(function(cb) {
    cb.checked = true; window._qSelected.add(cb.value);
  });
  _qUpdateUI();
}
function selQAll(btn) {
  var row = btn.closest('[data-all-qids]');
  if (row && row.dataset.allQids) {
    try { JSON.parse(row.dataset.allQids).forEach(function(id) { window._qSelected.add(id); }); } catch(e) {}
  }
  (row||document).querySelectorAll('.q-checkbox').forEach(function(cb) {
    cb.checked = true; window._qSelected.add(cb.value);
  });
  _qUpdateUI();
}
function clearQSel(btn) {
  window._qSelected.clear();
  var row = btn.closest('#quarantine-list-container');
  (row||document).querySelectorAll('.q-checkbox').forEach(function(cb) { cb.checked = false; });
  _qUpdateUI();
}
function batchQAction(action) {
  var ids = Array.from(window._qSelected);
  if (!ids.length) return;
  var labels = {restore:'Restore', delete:'Delete'};
  if (!confirm(labels[action] + ' ' + ids.length + ' quarantine records?')) return;
  var csrf = document.querySelector('meta[name="csrf-token"]');
  var token = csrf ? csrf.content : '';
  var body = 'action=' + action;
  ids.forEach(function(id) { body += '&qids[]=' + encodeURIComponent(id); });
  fetch('/admin/quarantine/batch', {
    method: 'POST',
    headers: {'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':token},
    body: body
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    alert('Done: ' + (d.success||0) + ' success, ' + (d.failed||0) + ' failed');
    window._qSelected.clear();
    var container = document.getElementById('quarantine-list-container');
    if (container && window.htmx) {
      htmx.ajax('GET', '/admin/quarantine?status=quarantined', {target:'#quarantine-list-container', swap:'outerHTML'});
    }
  })
  .catch(function(e) { alert('Batch failed: ' + e.message); });
}

function _updateIPUI() {
  var count = window._ipSelected.size;
  var countEl = document.getElementById('ip-selected-count');
  if (countEl) countEl.textContent = count + ' selected';
  var btn = document.getElementById('block-ips-btn');
  if (btn) { btn.disabled = count === 0; btn.textContent = 'Block ' + (count > 0 ? count : 'Selected') + ' IP' + (count !== 1 ? 's' : ''); }
}

function copyIP(ip) { navigator.clipboard.writeText(ip); }

function copySelectedIPs() {
  var ips = window._ipSelected.size > 0 ? Array.from(window._ipSelected) :
    Array.from(document.querySelectorAll('.ip-addr')).map(function(el) { return el.textContent.trim(); });
  navigator.clipboard.writeText(ips.join('\n'));
}

function copyAllIPs() {
  var ips = Array.from(document.querySelectorAll('.ip-addr')).map(function(el) { return el.textContent.trim(); });
  navigator.clipboard.writeText(ips.join('\n'));
}

function blockSelectedIPs() {
  var ips = Array.from(window._ipSelected);
  if (ips.length === 0) return;
  if (!confirm('Block ' + ips.length + ' IPs?\n\n' + ips.slice(0, 10).join('\n') + (ips.length > 10 ? '\n... and ' + (ips.length - 10) + ' more' : ''))) return;
  fetch('/api/v1/blocklist/add', {
    method: 'POST', headers: {'Content-Type':'application/json','X-CSRFToken':document.querySelector('meta[name="csrf-token"]')?.content||''},
    body: JSON.stringify({ips:ips})
  }).then(function(r){return r.json()}).then(function(d){alert(d.message||'Blocked')});
}

// v1.8.2: Block status panel (Profiles page)
function loadBlockStatus() {
  fetch('/admin/block/status')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var panel = document.getElementById('block-status-panel');
      if (!panel) return;
      document.getElementById('bs-auto').textContent = 'Auto: ' + (d.auto_block_enabled ? 'ON (>' + (d.auto_block_min_score*100) + '%)' : 'OFF');
      document.getElementById('bs-devices').textContent = 'Devices: ' + d.device_count;
      document.getElementById('bs-queue').textContent = 'Queue: ' + (d.retry_queue?.pending || 0);
      document.getElementById('bs-blocked').textContent = 'Blocked: ' + (d.blocklist?.length || 0);

      // Render queue detail
      var qlist = document.getElementById('block-queue-list');
      if (qlist && d.retry_queue?.items?.length > 0) {
        var html = '';
        d.retry_queue.items.forEach(function(item) {
          html += '<div style="padding:2px 0; border-bottom:1px solid #111;">' +
            '<code style="color:#ffaa00;">' + item.ip + '</code>' +
            ' retry ' + item.attempts + '/' + item.max_attempts +
            ' next: ' + item.next_retry_at +
            ' <span style="color:#666;">' + (item.last_error || '') + '</span></div>';
        });
        qlist.innerHTML = html;
      } else if (qlist) {
        qlist.innerHTML = '<span style="color:#666;">No pending retries</span>';
      }

      // History
      if (d.history?.length > 0) {
        var hlist = document.getElementById('block-queue-list');
        if (hlist && !d.retry_queue?.items?.length) {
          var hhtml = '<div style="color:#888;margin-top:4px;">Recent:</div>';
          d.history.slice(-10).reverse().forEach(function(h) {
            hhtml += '<div style="font-size:10px; color:' + (h.success ? '#888' : '#ff4444') + ';">' +
              h.device + ': ' + h.ip + ' — ' + h.message + '</div>';
          });
          hlist.innerHTML = hhtml;
        }
      }
    });
}

function toggleBlockDetail() {
  var d = document.getElementById('block-detail');
  if (d) d.style.display = d.style.display === 'none' ? '' : 'none';
}

// Load block status when Profiles page loads
document.addEventListener('htmx:afterSettle', function(evt) {
  _restoreIPCheckboxes();
  _restoreRecCheckboxes();
  _restoreQCheckboxes();
  if (document.getElementById('block-status-panel')) loadBlockStatus();
});

/* ============================================================
   v1.9.0: Manual Scanner (defined globally — innerHTML doesn't exec <script>)
   ============================================================ */

var _scanSSE = null;
var _scanFindings = [];
var _scanResultsTab = 'new';
var _scanStartTime = 0;
var _scanComplete = false;
var _scanLastId = '';

function startScan() {
  var dir = document.getElementById('scan-target-dir');
  if (!dir) return;
  dir = dir.value.trim();
  if (!dir) { alert('Please enter a target directory.'); return; }

  var recursive = document.getElementById('scan-recursive')?.checked ? '1' : '0';
  var extensions = document.getElementById('scan-extensions')?.value?.trim() || '';

  // Reset state
  _scanFindings = [];
  _scanComplete = false;
  _scanStartTime = Date.now();
  var tbody = document.getElementById('results-tbody');
  if (tbody) tbody.innerHTML = '';

  // Show/hide cards
  var configCard = document.getElementById('scan-config-card');
  var progressCard = document.getElementById('scan-progress-card');
  var resultsCard = document.getElementById('scan-results-card');
  var reportBtn = document.getElementById('scan-report-btn');
  if (configCard) configCard.style.display = 'none';
  if (progressCard) progressCard.style.display = 'flex';
  if (resultsCard) resultsCard.style.display = 'none';
  if (reportBtn) reportBtn.style.display = 'none';

  // Reset stats
  ['stat-new','stat-known','stat-clean','stat-errors'].forEach(function(id) {
    var el = document.getElementById(id); if (el) el.textContent = '0';
  });
  ['tab-new-count','tab-known-count','tab-all-count'].forEach(function(id) {
    var el = document.getElementById(id); if (el) el.textContent = '0';
  });
  document.getElementById('scan-progress-bar')?.style && (document.getElementById('scan-progress-bar').style.width = '0%');
  var pt = document.getElementById('scan-progress-text'); if (pt) pt.textContent = '0 / ?';

  // Open SSE
  var token = window._sseToken || '';
  var tokenParam = token ? '&token=' + encodeURIComponent(token) : '';
  var url = '/admin/scanner/run?target_dir=' + encodeURIComponent(dir)
          + '&recursive=' + recursive + tokenParam;

  _scanSSE = new EventSource(url, { withCredentials: true });

  _scanSSE.onmessage = function(event) {
    try { var data = JSON.parse(event.data); handleScanEvent(data); }
    catch(e) { console.error('SSE parse error:', e); }
  };

  _scanSSE.onerror = function() {
    if (!_scanComplete) {
      var tb = document.getElementById('results-tbody');
      if (tb) tb.innerHTML += '<tr><td colspan="6" style="color:#ff4444;padding:12px;">SSE connection lost.</td></tr>';
    }
    if (_scanSSE) { _scanSSE.close(); _scanSSE = null; }
  };
}

function handleScanEvent(data) {
  switch (data.event) {
    case 'init':
      var pt = document.getElementById('scan-progress-text');
      if (pt) pt.textContent = '0 / ' + (data.total_files || '?');
      break;
    case 'progress':
      var pct = data.total > 0 ? Math.round(data.scanned / data.total * 100) : 0;
      var pb = document.getElementById('scan-progress-bar');
      if (pb) pb.style.width = pct + '%';
      var pt2 = document.getElementById('scan-progress-text');
      if (pt2) pt2.textContent = data.scanned + ' / ' + data.total;
      var el = document.getElementById('scan-elapsed');
      if (el) el.textContent = Math.round((Date.now() - _scanStartTime) / 1000) + 's';
      var sn = document.getElementById('stat-new'); if (sn) sn.textContent = data.new_findings || 0;
      var sk = document.getElementById('stat-known'); if (sk) sk.textContent = data.known_findings || 0;
      var sc = document.getElementById('stat-clean'); if (sc) sc.textContent = data.clean || 0;
      var se = document.getElementById('stat-errors'); if (se) se.textContent = data.errors || 0;
      break;
    case 'finding':
      _scanFindings.push(data);
      addResultRow(data);
      updateResultCounts();
      break;
    case 'complete':
      _scanComplete = true;
      _scanLastId = data.scan_id;
      var pb2 = document.getElementById('scan-progress-bar');
      if (pb2) pb2.style.width = '100%';
      var pt3 = document.getElementById('scan-progress-text');
      if (pt3) pt3.textContent = data.scanned_files + ' / ' + data.total_files;
      var el2 = document.getElementById('scan-elapsed');
      if (el2) el2.textContent = data.duration + 's';
      var sn2 = document.getElementById('stat-new'); if (sn2) sn2.textContent = data.new_findings;
      var sk2 = document.getElementById('stat-known'); if (sk2) sk2.textContent = data.known_findings;
      var sc2 = document.getElementById('stat-clean'); if (sc2) sc2.textContent = data.clean;
      var se2 = document.getElementById('stat-errors'); if (se2) se2.textContent = data.errors;
      if (data.new_findings > 0 || data.known_findings > 0) {
        var rb = document.getElementById('scan-report-btn');
        if (rb) rb.style.display = '';
      }
      if (_scanSSE) { _scanSSE.close(); _scanSSE = null; }
      break;
    case 'error':
      var tb2 = document.getElementById('results-tbody');
      if (tb2) tb2.innerHTML += '<tr><td colspan="6" style="color:#ff4444;padding:12px;">Error: ' + (data.message || 'Unknown') + '</td></tr>';
      if (_scanSSE) { _scanSSE.close(); _scanSSE = null; }
      break;
  }
}

function addResultRow(finding) {
  var resultsCard = document.getElementById('scan-results-card');
  if (resultsCard && resultsCard.style.display === 'none') resultsCard.style.display = 'flex';

  var isNew = finding.classification === 'new';
  var badgeCls = isNew ? 'badge-danger' : 'badge-warning';
  var badgeText = isNew ? 'NEW' : 'KNOWN';
  var rowClass = isNew ? 'result-new' : 'result-known';
  var esc = _escJs;

  var actions = '';
  if (isNew) {
    actions = '<span style="display:inline-flex;gap:3px;white-space:nowrap;">'
            + '<button class="btn btn-ghost btn-sm" style="font-size:9px;padding:2px 5px;" onclick="openFileViewerByPath(\'' + esc(finding.file_path) + '\')">View</button>'
            + '<button class="btn btn-danger btn-sm quarantine-btn" style="font-size:9px;padding:2px 5px;" onclick="quarantineScanFile(\'' + esc(finding.file_path) + '\', this)">Quarantine</button>'
            + '</span>';
  } else {
    actions = '<span style="display:inline-flex;gap:3px;white-space:nowrap;">'
            + '<button class="btn btn-ghost btn-sm" style="font-size:9px;padding:2px 5px;" onclick="openFileViewerByPath(\'' + esc(finding.file_path) + '\')">View</button>'
            + '<span style="color:#888;font-size:9px;">Known</span>'
            + '</span>';
  }

  var row = '<tr class="' + rowClass + '" data-file-path="' + _escHtml(finding.file_path) + '" style="border-bottom:1px solid #111;">'
    + '<td style="padding:3px 8px;"><code style="color:#ccc;font-size:10px;">' + _escHtml(finding.file_name) + '</code></td>'
    + '<td style="padding:3px 8px;color:#555;font-size:9px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + _escHtml(finding.file_path) + '">' + _escHtml(finding.file_path) + '</td>'
    + '<td style="padding:3px 8px;color:#888;font-size:10px;">' + _escHtml(finding.engine || '') + '</td>'
    + '<td style="padding:3px 8px;font-size:10px;">' + (finding.features || []).map(function(f) { return '<span class="badge badge-blue">' + _escHtml(f) + '</span>'; }).join(' ') + '</td>'
    + '<td style="padding:3px 8px;text-align:center;"><span class="badge ' + badgeCls + '" style="font-size:9px;">' + badgeText + '</span></td>'
    + '<td style="padding:3px 8px;text-align:right;white-space:nowrap;">' + actions + '</td>'
    + '</tr>';

  var tbody = document.getElementById('results-tbody');
  if (tbody) tbody.insertAdjacentHTML('beforeend', row);
  applyTabFilter();
}

function switchResultsTab(tab) {
  _scanResultsTab = tab;
  ['tab-new','tab-known','tab-all'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) { el.style.color = '#888'; el.style.borderBottomColor = 'transparent'; }
  });
  var active = document.getElementById('tab-' + tab);
  if (active) { active.style.color = '#00ff41'; active.style.borderBottom = '2px solid #00ff41'; }
  applyTabFilter();
}

function applyTabFilter() {
  var rows = document.querySelectorAll('#results-tbody tr');
  rows.forEach(function(row) {
    if (_scanResultsTab === 'all') { row.style.display = ''; return; }
    if (_scanResultsTab === 'new' && row.classList.contains('result-new')) row.style.display = '';
    else if (_scanResultsTab === 'known' && row.classList.contains('result-known')) row.style.display = '';
    else row.style.display = 'none';
  });
}

function updateResultCounts() {
  var newCount = _scanFindings.filter(function(f) { return f.classification === 'new'; }).length;
  var knownCount = _scanFindings.filter(function(f) { return f.classification === 'known'; }).length;
  var nc = document.getElementById('tab-new-count'); if (nc) nc.textContent = newCount;
  var kc = document.getElementById('tab-known-count'); if (kc) kc.textContent = knownCount;
  var ac = document.getElementById('tab-all-count'); if (ac) ac.textContent = _scanFindings.length;
}

function quarantineScanFile(filePath, btn) {
  if (!confirm('Quarantine ' + filePath.split(/[\\/]/).pop() + '?')) return;
  var csrf = document.querySelector('meta[name="csrf-token"]');
  var token = csrf ? csrf.content : '';
  fetch('/admin/scanner/quarantine', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': token },
    body: 'file_path=' + encodeURIComponent(filePath)
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.success) {
      btn.outerHTML = '<span class="badge badge-success" style="font-size:9px;">Quarantined</span>';
    } else {
      alert('Quarantine failed: ' + (d.error || 'unknown'));
    }
  });
}

function stopScan() {
  if (_scanSSE) { _scanSSE.close(); _scanSSE = null; }
  fetch('/admin/scanner/cancel', { method: 'POST' });
  var pt = document.getElementById('scan-progress-text');
  if (pt) pt.textContent = 'Stopped';
}

function generateReport() {
  if (_scanLastId) window.open('/admin/scanner/report?scan_id=' + _scanLastId, '_blank');
}

function loadScanHistory() {
  var el = document.getElementById('scan-history-list');
  if (!el) return;
  el.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>Loading history...</p></div>';
  fetch('/admin/scanner/history')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.scans || d.scans.length === 0) {
        el.innerHTML = '<p style="color:#555;text-align:center;padding:12px;">No scan history yet.</p>';
        return;
      }
      var html = '';
      d.scans.forEach(function(s) {
        var statusColor = s.status === 'completed' ? '#00ff41' : s.status === 'error' ? '#ff4444' : '#ffaa00';
        var dateStr = s.start_time ? new Date(s.start_time * 1000).toLocaleString() : 'N/A';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;border-bottom:1px solid #111;font-size:10px;">'
          + '<div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;">'
          + '<span style="color:' + statusColor + ';">●</span>'
          + '<code style="color:#00ff41;font-size:9px;">' + s.scan_id.substring(0, 8) + '</code>'
          + '<span style="color:#888;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px;" title="' + _escHtml(s.target_dir) + '">' + _escHtml(s.target_dir) + '</span>'
          + '<span style="color:#ccc;">' + s.scanned_files + '/' + s.total_files + ' files</span>'
          + '<span style="color:#ff4444;font-size:9px;">' + s.new_findings + ' new</span>'
          + '<span style="color:#ffaa00;font-size:9px;">' + s.known_findings + ' known</span>'
          + '<span style="color:#555;">' + dateStr + '</span>'
          + '<span style="color:#888;">' + (s.duration || '?') + 's</span>'
          + '</div>'
          + '<div style="display:flex;gap:4px;flex-shrink:0;">'
          + '<button class="btn btn-ghost btn-sm" style="font-size:9px;padding:1px 5px;" onclick="viewScanResults(\'' + s.scan_id + '\')">View</button>'
          + '<button class="btn btn-ghost btn-sm" style="font-size:9px;padding:1px 5px;" onclick="window.open(\'/admin/scanner/report?scan_id=' + s.scan_id + '\',\'_blank\')">Report</button>'
          + '</div>'
          + '</div>';
      });
      el.innerHTML = html;
    })
    .catch(function() {
      el.innerHTML = '<p style="color:#ff4444;text-align:center;padding:12px;">Failed to load history.</p>';
    });
}

function viewScanResults(scanId) {
  // Load full scan results from disk and render in the results card
  var tbody = document.getElementById('results-tbody');
  var card = document.getElementById('scan-results-card');
  if (!tbody || !card) return;
  tbody.innerHTML = '<tr><td colspan="6" style="padding:12px;text-align:center;"><div class="spinner"></div><p>Loading results...</p></td></tr>';
  card.style.display = 'flex';
  _scanFindings = [];
  fetch('/admin/scanner/results?scan_id=' + encodeURIComponent(scanId))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.error) { tbody.innerHTML = '<tr><td colspan="6" style="color:#ff4444;padding:12px;">Error: ' + d.error + '</td></tr>'; return; }
      tbody.innerHTML = '';
      _scanFindings = d.findings || [];
      _scanFindings.forEach(function(f) { addResultRow(f); });
      updateResultCounts();
      _scanLastId = d.scan_id;
      document.getElementById('scan-report-btn').style.display = '';
      document.getElementById('scan-progress-card').style.display = 'none';
    })
    .catch(function() { tbody.innerHTML = '<tr><td colspan="6" style="color:#ff4444;padding:12px;">Failed to load.</td></tr>'; });
}

function _escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function _escJs(str) {
  if (!str) return '';
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

// ESC key closes modals
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeRecordDetail();
    closeLogAnalyzer();
    closeSystemModal();
  }
});

/* ============================================================
   刷新当前页面（Refresh按钮调用）
   ============================================================ */
function refreshCurrent() {
  if (_currentPath === 'dashboard_content') {
    loadDashboard();
  } else {
    loadContent(_currentPath, _currentTitle);
  }
}

/* ============================================================
   手动加载Dashboard各面板数据
   ============================================================ */
function loadDashboardPanels() {
  // Metrics面板
  var metricsPanel = document.getElementById('metrics-panel');
  if (metricsPanel) {
    fetch('/admin/metrics/data', { headers: { 'HX-Request': 'true' } })
      .then(function(r) { return r.text(); })
      .then(function(html) {
        metricsPanel.innerHTML = html;
        if (window.htmx) htmx.process(metricsPanel);
      })
      .catch(function(e) { console.error('Metrics load failed:', e); });
  }

  // YARA规则面板（compact模式，使用outerHTML避免嵌套）
  var yaraContainer = document.getElementById('yara-rules-container');
  if (yaraContainer) {
    fetch('/admin/yara/rules?compact=1', { headers: { 'HX-Request': 'true' } })
      .then(function(r) { return r.text(); })
      .then(function(html) {
        var temp = document.createElement('div');
        temp.innerHTML = html;
        var newContainer = temp.firstElementChild;
        if (newContainer) {
          yaraContainer.replaceWith(newContainer);
          if (window.htmx) htmx.process(newContainer);
        }
      })
      .catch(function(e) { console.error('YARA load failed:', e); });
  }

  // Records面板（compact模式，使用outerHTML避免嵌套）
  var recordsContainer = document.getElementById('records-table-container');
  if (recordsContainer) {
    fetch('/admin/records?compact=1', { headers: { 'HX-Request': 'true' } })
      .then(function(r) { return r.text(); })
      .then(function(html) {
        var temp = document.createElement('div');
        temp.innerHTML = html;
        var newContainer = temp.firstElementChild;
        if (newContainer) {
          recordsContainer.replaceWith(newContainer);
          if (window.htmx) htmx.process(newContainer);
        }
      })
      .catch(function(e) { console.error('Records load failed:', e); });
  }
}

function showYaraEditModal(filename) {
  TridentUtils.modal.show('yara-edit-modal');
}

function confirmDelete(filename) {
  TridentUtils.confirm('Delete rule file: ' + filename + ' ?', function() {
    var btn = document.querySelector('[data-delete-file="' + filename + '"]');
    if (btn) btn.click();
  });
}


// v1.7.9-Patch: 修复 Record Detail Modal 显示
function showRecordDetail() {
    const modal = document.getElementById('record-detail-modal');
    const overlay = document.getElementById('record-detail-modal-overlay');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
    }
    if (overlay) {
        overlay.style.display = 'block';
        overlay.classList.add('active');
    }
}

// ═══════════════════════════════════════════════════════════════
// v1.8.4: 安全文件内容查看器
// ═══════════════════════════════════════════════════════════════

var _fvLineWrap = false;

// 危险关键词高亮规则
var _dangerPatterns = [
  {re: /(eval)\s*\(/gi, cls: 'kw-danger'},
  {re: /(assert)\s*\(/gi, cls: 'kw-danger'},
  {re: /(system)\s*\(/gi, cls: 'kw-danger'},
  {re: /(exec)\s*\(/gi, cls: 'kw-danger'},
  {re: /(passthru)\s*\(/gi, cls: 'kw-danger'},
  {re: /(shell_exec)\s*\(/gi, cls: 'kw-danger'},
  {re: /(popen)\s*\(/gi, cls: 'kw-danger'},
  {re: /(proc_open)\s*\(/gi, cls: 'kw-danger'},
  {re: /\b(base64_decode)\s*\(/gi, cls: 'kw-warn'},
  {re: /\b(gzinflate)\s*\(/gi, cls: 'kw-warn'},
  {re: /\b(str_rot13)\s*\(/gi, cls: 'kw-warn'},
  {re: /\b(gzuncompress)\s*\(/gi, cls: 'kw-warn'},
  {re: /\b(file_get_contents)\s*\(/gi, cls: 'kw-info'},
  {re: /\b(file_put_contents)\s*\(/gi, cls: 'kw-info'},
  {re: /\b(move_uploaded_file)\s*\(/gi, cls: 'kw-info'},
  {re: /\b(\$_GET)\b/gi, cls: 'kw-var'},
  {re: /\b(\$_POST)\b/gi, cls: 'kw-var'},
  {re: /\b(\$_REQUEST)\b/gi, cls: 'kw-var'},
  {re: /\b(\$_SERVER)\b/gi, cls: 'kw-var'},
  {re: /\b(\$_FILES)\b/gi, cls: 'kw-var'},
  {re: /\b(\$_COOKIE)\b/gi, cls: 'kw-var'},
];

function _highlightDangerKeywords(html) {
  // 只在非 HTML 标签的部分做高亮（保护已转义的内容）
  var result = html;
  _dangerPatterns.forEach(function(p) {
    result = result.replace(p.re, function(match) {
      return '<span class="' + p.cls + '">' + match + '</span>';
    });
  });
  return result;
}

function openFileViewerByPath(filePath) {
  if (!filePath) return;
  _showFileViewerLoading(filePath);
  fetch('/admin/file/content?path=' + encodeURIComponent(filePath), {
    headers: { 'HX-Request': 'true' }
  })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.error || 'HTTP ' + r.status); });
      return r.json();
    })
    .then(_renderFileViewer)
    .catch(function(e) {
      var content = document.getElementById('fv-content');
      if (content) content.innerHTML = '<span style="color:#ff4444;">Error: ' + e.message + '</span>';
      document.getElementById('fv-file-size').textContent = 'ERROR';
    });
}

function openFileViewerByQid(qid) {
  if (!qid) return;
  _showFileViewerLoading('Quarantine: ' + qid);
  fetch('/admin/file/content?qid=' + encodeURIComponent(qid), {
    headers: { 'HX-Request': 'true' }
  })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.error || 'HTTP ' + r.status); });
      return r.json();
    })
    .then(_renderFileViewer)
    .catch(function(e) {
      var content = document.getElementById('fv-content');
      if (content) content.innerHTML = '<span style="color:#ff4444;">Error: ' + e.message + '</span>';
      document.getElementById('fv-file-size').textContent = 'ERROR';
    });
}

function _showFileViewerLoading(label) {
  var m = document.getElementById('file-viewer-modal');
  if (!m) {
    // Modal template not yet in DOM — load it from server
    var container = document.body;
    var div = document.createElement('div');
    div.innerHTML = '<div id="file-viewer-modal" class="modal-overlay" style="display:flex; z-index:3000;"><div style="margin:auto; color:#00ff41;"><div class="spinner"></div><p>Loading viewer...</p></div></div>';
    // Replace the temp div with actual content
    document.body.appendChild(div.firstElementChild);
    m = document.getElementById('file-viewer-modal');
  }
  m.style.display = 'flex';
  m.style.visibility = 'visible';
  m.style.opacity = '1';
  m.classList.add('active');
  document.getElementById('fv-file-path').textContent = label;
  document.getElementById('fv-file-size').textContent = 'Loading...';
  document.getElementById('fv-content').innerHTML = '';
}

function _renderFileViewer(data) {
  document.getElementById('fv-file-path').textContent = data.path || '';
  var sizeStr = data.size > 1024 ? (data.size / 1024).toFixed(1) + ' KB' : data.size + ' B';
  if (data.truncated) sizeStr += ' [TRUNCATED >512KB]';
  document.getElementById('fv-file-size').textContent = sizeStr + ' | ' + data.lines + ' lines';

  var html = _highlightDangerKeywords(data.content);
  document.getElementById('fv-content').innerHTML = html;

  // Apply wrap if active
  if (_fvLineWrap) {
    document.getElementById('fv-content').style.whiteSpace = 'pre-wrap';
  } else {
    document.getElementById('fv-content').style.whiteSpace = 'pre';
  }
}

function closeFileViewer() {
  var m = document.getElementById('file-viewer-modal');
  if (!m) return;
  m.style.display = 'none';
  m.style.visibility = 'hidden';
  m.style.opacity = '0';
  m.classList.remove('active');
}

function copyFileContent() {
  var pre = document.getElementById('fv-content');
  if (!pre) return;
  // Get raw text (not innerHTML with highlight spans)
  var text = pre.textContent || pre.innerText || '';
  navigator.clipboard.writeText(text).then(function() {
    var btn = document.querySelector('#file-viewer-modal .btn-ghost');
    if (btn && btn.textContent === 'Copy') {
      var orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(function() { btn.textContent = orig; }, 1500);
    }
  });
}

function toggleLineWrap() {
  _fvLineWrap = !_fvLineWrap;
  var pre = document.getElementById('fv-content');
  if (!pre) return;
  pre.style.whiteSpace = _fvLineWrap ? 'pre-wrap' : 'pre';
  var btn = document.querySelector('#file-viewer-modal .btn-ghost:nth-child(2)');
  if (btn) btn.textContent = _fvLineWrap ? 'Unwrap' : 'Wrap';
}

// Extend ESC key handler
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var fv = document.getElementById('file-viewer-modal');
    if (fv && fv.style.display !== 'none') {
      closeFileViewer();
      e.stopPropagation();
    }
  }
});
