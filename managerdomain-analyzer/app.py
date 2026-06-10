import asyncio
import re
from flask import Flask, request, jsonify, render_template_string
from analyzer import analyze_domains

app = Flask(__name__)


def clean_domain(d: str) -> str:
    d = d.strip()
    d = re.sub(r'^https?://', '', d)
    d = d.rstrip('/')
    return d


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json() or {}
    raw = data.get('domains', [])
    domains = list(dict.fromkeys(clean_domain(d) for d in raw if d.strip()))[:250]
    domains = [d for d in domains if d]
    results = asyncio.run(analyze_domains(domains))
    return jsonify(results)


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MANAGERDOMAIN Analyzer</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0C0D10; --surface: #13151A; --surface2: #1A1D24; --border: #252830;
    --accent: #E63946; --accent2: #4A9EFF; --text: #E8EAF0; --muted: #5A5F70;
    --green: #2ECC71; --warn: #F4A623;
    --mono: 'DM Mono', monospace; --sans: 'Syne', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }
  body::before {
    content: ''; position: fixed; inset: 0;
    background-image: linear-gradient(rgba(74,158,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(74,158,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px; pointer-events: none; z-index: 0;
  }
  .layout { position: relative; z-index: 1; max-width: 960px; margin: 0 auto; padding: 40px 24px; }
  header { display: flex; align-items: center; gap: 16px; margin-bottom: 40px; }
  .logo-mark {
    width: 44px; height: 44px; background: var(--accent); border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; font-weight: 800; color: #fff; font-family: var(--sans); flex-shrink: 0;
  }
  .header-text h1 { font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }
  .header-text p { font-size: 12px; color: var(--muted); font-family: var(--mono); margin-top: 2px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 28px; margin-bottom: 20px; }
  .card-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: var(--muted); margin-bottom: 16px; font-family: var(--mono); }
  textarea {
    width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
    padding: 12px 14px; color: var(--text); font-size: 13px; font-family: var(--mono);
    outline: none; resize: vertical; min-height: 180px; line-height: 1.7; transition: border-color 0.15s;
  }
  textarea:focus { border-color: var(--accent2); }
  .counter-row { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; gap: 12px; }
  .counter { font-size: 12px; font-family: var(--mono); color: var(--muted); }
  .counter.warn { color: var(--warn); }
  .btn {
    padding: 11px 28px; border-radius: 8px; font-size: 13px; font-weight: 700;
    cursor: pointer; border: none; font-family: var(--sans); transition: all 0.15s; white-space: nowrap;
  }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover:not(:disabled) { background: #cc2f3b; }
  .btn-primary:disabled { background: var(--muted); cursor: not-allowed; }
  .btn-secondary {
    background: var(--surface2); color: var(--text); border: 1px solid var(--border);
    font-size: 12px; padding: 8px 18px;
  }
  .btn-secondary:hover { border-color: var(--accent2); color: var(--accent2); }
  .loading { display: none; align-items: center; gap: 12px; padding: 16px 0 0; }
  .loading.show { display: flex; }
  .spinner {
    width: 18px; height: 18px; border: 2px solid var(--border);
    border-top-color: var(--accent2); border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-text { font-size: 13px; font-family: var(--mono); color: var(--muted); }
  #results { display: none; }
  #results.show { display: block; }
  .summary-table { width: 100%; border-collapse: collapse; }
  .summary-table th {
    font-size: 10px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 1px;
    color: var(--muted); padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border);
  }
  .summary-table td { padding: 10px 12px; font-size: 13px; border-bottom: 1px solid var(--border); font-family: var(--mono); }
  .summary-table tr:last-child td { border-bottom: none; }
  .summary-table tr.clickable { cursor: pointer; transition: background 0.1s; }
  .summary-table tr.clickable:hover td { background: var(--surface2); }
  .summary-table tr.active-filter td { background: rgba(74,158,255,0.08); }
  .bar-cell { width: 140px; }
  .bar-bg { background: var(--border); border-radius: 2px; height: 5px; overflow: hidden; }
  .bar-fill { background: var(--accent2); border-radius: 2px; height: 5px; transition: width 0.4s; }
  .count-badge {
    display: inline-block; background: var(--surface2); border: 1px solid var(--border);
    border-radius: 4px; padding: 1px 8px; font-size: 11px; color: var(--muted);
  }
  .table-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
  .filter-badge {
    display: none; align-items: center; gap: 8px;
    background: rgba(74,158,255,0.1); border: 1px solid rgba(74,158,255,0.3);
    border-radius: 6px; padding: 4px 10px; font-size: 12px; font-family: var(--mono); color: var(--accent2);
  }
  .filter-badge.show { display: flex; }
  .filter-clear { cursor: pointer; opacity: 0.7; line-height: 1; }
  .filter-clear:hover { opacity: 1; }
  .domain-table { width: 100%; border-collapse: collapse; }
  .domain-table th {
    font-size: 10px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 1px;
    color: var(--muted); padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border);
  }
  .domain-table td { padding: 9px 12px; font-size: 13px; border-bottom: 1px solid var(--border); font-family: var(--mono); word-break: break-all; }
  .domain-table tr:last-child td { border-bottom: none; }
  .tag {
    display: inline-block; border-radius: 4px; padding: 1px 8px;
    font-size: 11px; margin: 2px 2px 2px 0;
  }
  .tag-manager { background: rgba(74,158,255,0.1); border: 1px solid rgba(74,158,255,0.2); color: var(--accent2); }
  .tag-none { background: rgba(90,95,112,0.2); border: 1px solid var(--border); color: var(--muted); }
  .tag-error { background: rgba(230,57,70,0.1); border: 1px solid rgba(230,57,70,0.3); color: var(--accent); }
  .tag-blocked { background: rgba(244,166,35,0.1); border: 1px solid rgba(244,166,35,0.3); color: var(--warn); }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>
<div class="layout">
  <header>
    <div class="logo-mark">K</div>
    <div class="header-text">
      <h1>MANAGERDOMAIN Analyzer</h1>
      <p>Paste up to 250 domains — finds the ads.txt MANAGERDOMAIN for each</p>
    </div>
  </header>

  <div class="card">
    <div class="card-title">Domains</div>
    <textarea id="domain-input"
      placeholder="Paste domains here, one per line&#10;example.com&#10;publisher.com&#10;news-site.org"></textarea>
    <div class="counter-row">
      <span class="counter" id="counter">0 / 250 domains</span>
      <button class="btn btn-primary" id="analyze-btn" onclick="runAnalysis()">Analyze</button>
    </div>
    <div class="loading" id="loading">
      <div class="spinner"></div>
      <span class="loading-text" id="loading-text">Fetching ads.txt files...</span>
    </div>
  </div>

  <div id="results">
    <div class="card">
      <div class="card-title">Results by Manager Domain</div>
      <table class="summary-table">
        <thead>
          <tr>
            <th>Manager Domain</th>
            <th>Publishers</th>
            <th class="bar-cell"></th>
          </tr>
        </thead>
        <tbody id="summary-body"></tbody>
      </table>
    </div>

    <div class="card">
      <div class="table-header">
        <div class="card-title" style="margin-bottom:0">All Domains</div>
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
          <div class="filter-badge" id="filter-badge">
            <span id="filter-label"></span>
            <span class="filter-clear" onclick="clearFilter()">&#x2715;</span>
          </div>
          <button class="btn btn-secondary" onclick="exportCSV()">Export CSV</button>
        </div>
      </div>
      <table class="domain-table">
        <thead>
          <tr>
            <th>Domain</th>
            <th>MANAGERDOMAIN(s)</th>
          </tr>
        </thead>
        <tbody id="domain-body"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
let allResults = [];
let activeFilter = null;

document.getElementById('domain-input').addEventListener('input', updateCounter);

function updateCounter() {
  const lines = getDomains();
  const el = document.getElementById('counter');
  el.textContent = lines.length + ' / 250 domains';
  el.className = 'counter' + (lines.length > 250 ? ' warn' : '');
}

function getDomains() {
  return document.getElementById('domain-input').value
    .split('\\n').map(d => d.trim()).filter(Boolean);
}

async function runAnalysis() {
  const domains = getDomains().slice(0, 250);
  if (!domains.length) return;
  const btn = document.getElementById('analyze-btn');
  btn.disabled = true;
  document.getElementById('loading').classList.add('show');
  document.getElementById('loading-text').textContent =
    'Fetching ads.txt for ' + domains.length + ' domain' + (domains.length > 1 ? 's' : '') + '...';
  document.getElementById('results').classList.remove('show');
  try {
    const resp = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domains }),
    });
    allResults = await resp.json();
    activeFilter = null;
    renderResults();
  } finally {
    btn.disabled = false;
    document.getElementById('loading').classList.remove('show');
  }
}

function renderResults() {
  renderSummary();
  renderTable();
  document.getElementById('results').classList.add('show');
}

function renderSummary() {
  const counts = {};
  for (const r of allResults) {
    if (r.status === 'blocked') {
      counts['Blocked'] = (counts['Blocked'] || 0) + 1;
    } else {
      const managers = r.manager_domains.length ? r.manager_domains : ['None'];
      for (const m of managers) counts[m] = (counts[m] || 0) + 1;
    }
  }
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = sorted[0] ? sorted[0][1] : 1;
  document.getElementById('summary-body').innerHTML = sorted.map(function(entry) {
    const manager = entry[0], count = entry[1];
    const isActive = activeFilter === manager;
    const label = manager === 'None'
      ? '<span style="color:var(--muted)">None</span>'
      : manager === 'Blocked'
          ? '<span style="color:var(--warn)">Blocked</span>'
          : escHtml(manager);
    return '<tr class="clickable' + (isActive ? ' active-filter' : '') + '" data-manager="' + escHtml(manager) + '" onclick="toggleFilter(this.dataset.manager)">'
      + '<td>' + label + '</td>'
      + '<td><span class="count-badge">' + count + '</span></td>'
      + '<td class="bar-cell"><div class="bar-bg"><div class="bar-fill" style="width:' + Math.round(count/max*100) + '%"></div></div></td>'
      + '</tr>';
  }).join('');
}

function renderTable() {
  const filtered = activeFilter
    ? allResults.filter(function(r) {
        if (activeFilter === 'Blocked') return r.status === 'blocked';
        if (r.status === 'blocked') return false;
        const managers = r.manager_domains.length ? r.manager_domains : ['None'];
        return managers.indexOf(activeFilter) !== -1;
      })
    : allResults;
  const badge = document.getElementById('filter-badge');
  if (activeFilter) {
    document.getElementById('filter-label').textContent = 'Filtered: ' + activeFilter;
    badge.classList.add('show');
  } else {
    badge.classList.remove('show');
  }
  document.getElementById('domain-body').innerHTML = filtered.map(function(r) {
    var tags;
    if (r.status === 'error') {
      tags = '<span class="tag tag-error">Error</span>';
    } else if (r.status === 'blocked') {
      tags = '<span class="tag tag-blocked">Blocked</span>';
    } else if (!r.manager_domains.length) {
      tags = '<span class="tag tag-none">None</span>';
    } else {
      tags = r.manager_domains.map(function(m) {
        return '<span class="tag tag-manager">' + escHtml(m) + '</span>';
      }).join('');
    }
    return '<tr><td>' + escHtml(r.domain) + '</td><td>' + tags + '</td></tr>';
  }).join('');
}

function toggleFilter(manager) {
  activeFilter = activeFilter === manager ? null : manager;
  renderSummary();
  renderTable();
}

function clearFilter() {
  activeFilter = null;
  renderSummary();
  renderTable();
}

function exportCSV() {
  const rows = [['Domain', 'MANAGERDOMAIN(s)', 'Status']];
  for (const r of allResults) {
    rows.push([r.domain, r.manager_domains.join('; ') || 'None', r.status]);
  }
  const csv = rows.map(function(row) {
    return row.map(function(c) {
      return '"' + String(c).replace(/"/g, '""') + '"';
    }).join(',');
  }).join('\\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'managerdomain-' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
  URL.revokeObjectURL(url);
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
</script>
</body>
</html>"""


if __name__ == '__main__':
    print("\n  MANAGERDOMAIN Analyzer")
    print("  Open in your browser: http://localhost:5050\n")
    app.run(host='127.0.0.1', port=5050, debug=False)
