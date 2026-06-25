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

  // 清空 header toolbar（避免上一个页面的 toolbar 残留）
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

      // 提取 toolbar（如果有的话）
      var toolbarMatch = html.match(/<div class="page-toolbar"[^>]*>([\s\S]*?)<\/div>/);
      if (toolbarMatch && headerCenter) {
        headerCenter.innerHTML = toolbarMatch[1];
        // 从内容中移除 toolbar HTML（避免重复渲染）
        html = html.replace(toolbarMatch[0], '');
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
