/* Trident v1.8.0 仪表盘主逻辑 */

/* ============================================================
   Dashboard 全局函数（必须在 dashboard.js 中预定义，因为
   dashboard_content.html 通过 innerHTML 插入时其中的 <script> 不会执行）
   ============================================================ */

function filterLogStream(term) {
  var logStream = document.getElementById('log-stream');
  if (!logStream) return;
  var lines = logStream.querySelectorAll('.log-line');
  var lower = term.toLowerCase();
  lines.forEach(function(line) {
    line.style.display = (!lower || line.textContent.toLowerCase().includes(lower)) ? '' : 'none';
  });
}

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
      // Dashboard特殊处理
      if (path === 'dashboard_content') {
        setTimeout(loadDashboardPanels, 50);
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

var _threatsTabsLoaded = {active: true, quarantine: false, audit: false};

// Auto-load hidden tabs when Threats page loads
document.addEventListener('htmx:afterSettle', function(evt) {
  if (evt.target && evt.target.id === 'main-content') {
    // Check if Threats page just loaded
    if (document.querySelector('.threats-tab')) {
      setTimeout(function() {
        ['quarantine', 'audit'].forEach(function(tab) {
          if (!_threatsTabsLoaded[tab]) {
            _threatsTabsLoaded[tab] = true;
            var urls = { quarantine: '/admin/quarantine?status=quarantined', audit: '/admin/records?audit=true&compact=1' };
            var targets = { quarantine: '#threats-quarantine-container', audit: '#threats-audit-container' };
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
      var urls = { quarantine: '/admin/quarantine?status=quarantined', audit: '/admin/records?audit=true&compact=1' };
      var targets = { quarantine: '#threats-quarantine-container', audit: '#threats-audit-container' };
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
  // Store current page IPs, then trigger Select All across pages via data attribute
  document.querySelectorAll('.ip-checkbox').forEach(function(cb) {
    window._ipSelected.add(cb.value);
  });
  _updateIPUI();
}

function clearIPSelection() {
  window._ipSelected.clear();
  document.querySelectorAll('.ip-checkbox').forEach(function(cb) { cb.checked = false; });
  _updateIPUI();
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

// Restore IP checkboxes after HTMX page swaps
document.addEventListener('htmx:afterSettle', function() { _restoreIPCheckboxes(); });

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
