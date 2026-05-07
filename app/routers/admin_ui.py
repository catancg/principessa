from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

router = APIRouter(prefix="/admin", tags=["admin-ui"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


@router.get("/login", response_class=HTMLResponse)
def admin_login():
    return HTMLResponse(content=jinja_env.get_template("admin_login.html").render())


def _nav(active: str) -> str:
    pages = [
        ("Dashboard",     "/admin/ui"),
        ("Clientes",      "/admin/ui/customers"),
        ("Email Builder", "/admin/email-builder"),
        ("Cumpleaños",    "/admin/birthday-builder"),
    ]
    links = ""
    for label, href in pages:
        if label == active:
            links += (
                f'<a href="{href}" style="text-decoration:none;font-size:14px;font-weight:700;'
                f'color:#6B3217;border-bottom:2px solid #6B3217;padding-bottom:2px;">{label}</a>'
            )
        else:
            links += f'<a href="{href}" style="text-decoration:none;font-size:14px;color:#555;">{label}</a>'
    return (
        '<nav style="background:#fff;border-bottom:1px solid #e0e0e0;padding:12px 20px;'
        'display:flex;align-items:center;gap:24px;">'
        '<span style="font-weight:900;font-size:16px;color:#111;margin-right:8px;">'
        'Principessa Pastelería</span>'
        + links + '</nav>'
    )


# ── /admin/ui — Dashboard ─────────────────────────────────────────────────────

@router.get("/ui", response_class=HTMLResponse)
def admin_ui():
    nav = _nav("Dashboard")
    return HTMLResponse(f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Dashboard — Principessa</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:system-ui,Arial,sans-serif;background:#f8f9fa;color:#111;}}
    main{{padding:20px;}}
    .cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;}}
    .card{{background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:16px 20px;min-width:130px;}}
    .card-num{{font-size:30px;font-weight:900;color:#111;line-height:1;}}
    .card-label{{font-size:10px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:.5px;margin-top:6px;}}
    .tools{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;}}
    .tool{{background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:16px;flex:1;min-width:300px;}}
    .tool h3{{font-size:15px;font-weight:700;margin-bottom:12px;}}
    table{{width:100%;border-collapse:collapse;font-size:13px;}}
    th{{font-size:10px;font-weight:700;text-transform:uppercase;color:#6b7280;padding:6px 10px;text-align:left;border-bottom:2px solid #e0e0e0;white-space:nowrap;}}
    td{{padding:8px 10px;border-bottom:1px solid #f0f0f0;vertical-align:middle;}}
    .badge{{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:700;}}
    .bq{{background:#fef3c7;color:#92400e;}}
    .bs{{background:#d1fae5;color:#065f46;}}
    .bf{{background:#fee2e2;color:#991b1b;}}
    .row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;}}
    select,input[type=text]{{font-family:inherit;font-size:13px;padding:7px 10px;border:1px solid #d1d5db;border-radius:8px;background:#fff;}}
    button{{font-family:inherit;font-size:13px;padding:7px 14px;background:#6B3217;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700;}}
    button:hover{{opacity:.85;}}
    .err{{color:#991b1b;font-size:13px;margin-top:6px;min-height:18px;}}
    .mono{{font-family:monospace;font-size:11px;}}
    .kv table{{width:auto;margin-top:4px;}}
    .kv th{{min-width:110px;font-size:12px;color:#374151;text-transform:none;font-weight:700;border-bottom:1px solid #f0f0f0;padding:5px 8px;}}
    .kv td{{font-size:12px;border-bottom:1px solid #f0f0f0;padding:5px 8px;}}
    h4{{font-size:13px;font-weight:700;color:#374151;margin:14px 0 6px;}}
    .empty{{color:#6b7280;font-size:13px;margin-top:8px;}}
  </style>
</head>
<body>
{nav}
<main>
  <div class="cards">
    <div class="card"><div class="card-num" id="nCust">—</div><div class="card-label">Total Customers</div></div>
    <div class="card"><div class="card-num" id="nOutbox">—</div><div class="card-label">Outbox Total</div></div>
    <div class="card"><div class="card-num" id="nQueued">—</div><div class="card-label">En Cola</div></div>
    <div class="card"><div class="card-num" id="nSent">—</div><div class="card-label">Enviados</div></div>
    <div class="card"><div class="card-num" id="nFailed">—</div><div class="card-label">Fallidos</div></div>
    <div class="card"><div class="card-num" id="nConsent">—</div><div class="card-label">Con Consentimiento</div></div>
  </div>

  <div class="tools">
    <div class="tool">
      <h3>Outbox</h3>
      <div class="row">
        <select id="statusSel">
          <option value="queued">En cola</option>
          <option value="sent">Enviados</option>
          <option value="failed">Fallidos</option>
        </select>
        <button onclick="loadOutbox()">Ver</button>
      </div>
      <div class="err" id="outboxErr"></div>
      <div id="outboxRes"></div>
    </div>

    <div class="tool">
      <h3>Debug por identidad</h3>
      <div class="row">
        <select id="chanSel">
          <option value="email">email</option>
          <option value="whatsapp">whatsapp</option>
          <option value="instagram">instagram</option>
        </select>
        <input type="text" id="valInput" placeholder="email, teléfono o @usuario" style="flex:1;min-width:160px;">
        <button onclick="debugIdentity()">Buscar</button>
      </div>
      <div class="err" id="debugErr"></div>
      <div id="debugRes"></div>
    </div>
  </div>
</main>

<script>
  const KEY = sessionStorage.getItem('builderKey') || '';
  if (!KEY) window.location.replace('/builder-login?next=/admin/ui');

  async function api(path) {{
    const res = await fetch(path, {{headers:{{'x-admin-key':KEY}}}});
    if (res.status === 401) {{ window.location.replace('/builder-login?next=/admin/ui'); return null; }}
    if (!res.ok) throw new Error('HTTP ' + res.status + ': ' + await res.text());
    return res.json();
  }}

  function badge(s) {{
    const cls = {{queued:'bq',sent:'bs',failed:'bf'}}[s] || '';
    return `<span class="badge ${{cls}}">${{s}}</span>`;
  }}

  function ts(v) {{
    if (!v) return '—';
    let s = String(v).replace(' ', 'T');
    if (s.length >= 19 && !s.slice(19).match(/[Z+\-]/)) s += 'Z';
    const d = new Date(s);
    if (isNaN(d)) return String(v).replace('T',' ').slice(0,16);
    const art = new Date(d.getTime() - 3 * 60 * 60 * 1000);
    return art.toISOString().replace('T',' ').slice(0,16) + ' (ART)';
  }}

  function kv(obj) {{
    return '<div class="kv"><table>' +
      Object.entries(obj).map(([k,v]) => `<tr><th>${{k}}</th><td>${{v ?? '—'}}</td></tr>`).join('') +
      '</table></div>';
  }}

  async function loadSummary() {{
    try {{
      const d = await api('/admin/summary');
      if (!d) return;
      document.getElementById('nCust').textContent   = d.counts?.customers ?? '—';
      document.getElementById('nOutbox').textContent = d.counts?.outbox    ?? '—';
      const m = Object.fromEntries((d.outbox_by_status || []).map(x => [x.status, x.count]));
      document.getElementById('nQueued').textContent = m.queued  ?? 0;
      document.getElementById('nSent').textContent   = m.sent    ?? 0;
      document.getElementById('nFailed').textContent = m.failed  ?? 0;
      const granted = (d.current_promotions_consent_by_status || []).find(x => x.status === 'granted');
      document.getElementById('nConsent').textContent = granted?.count ?? 0;
    }} catch(e) {{ console.error('summary:', e); }}
  }}

  async function loadOutbox() {{
    document.getElementById('outboxErr').textContent = '';
    document.getElementById('outboxRes').innerHTML = '';
    const status = document.getElementById('statusSel').value;
    try {{
      const d = await api(`/admin/outbox?status=${{encodeURIComponent(status)}}&limit=50`);
      if (!d) return;
      const items = d.items || [];
      if (!items.length) {{
        document.getElementById('outboxRes').innerHTML = '<p class="empty">Sin resultados.</p>';
        return;
      }}
      const rows = items.map(it => `<tr>
        <td class="mono">${{String(it.outbox_id).slice(0,8)}}…</td>
        <td>${{it.first_name || '—'}}</td>
        <td>${{it.recipient  || '—'}}</td>
        <td>${{badge(it.status)}}</td>
        <td>${{it.template_key || '—'}}</td>
        <td>${{ts(it.scheduled_for)}}</td>
        <td>${{ts(it.sent_at)}}</td>
      </tr>`).join('');
      document.getElementById('outboxRes').innerHTML = `<table style="margin-top:12px;">
        <thead><tr><th>ID</th><th>Nombre</th><th>Email</th><th>Estado</th><th>Template</th><th>Programado</th><th>Enviado</th></tr></thead>
        <tbody>${{rows}}</tbody></table>`;
    }} catch(e) {{ document.getElementById('outboxErr').textContent = String(e); }}
  }}

  async function debugIdentity() {{
    document.getElementById('debugErr').textContent = '';
    document.getElementById('debugRes').innerHTML = '';
    const channel = document.getElementById('chanSel').value;
    const value   = document.getElementById('valInput').value.trim();
    if (!value) {{ document.getElementById('debugErr').textContent = 'Ingresá un valor.'; return; }}
    try {{
      const d = await api(`/admin/debug/identity?channel=${{encodeURIComponent(channel)}}&value=${{encodeURIComponent(value)}}`);
      if (!d) return;
      const outboxRows = (d.recent_outbox || []).map(it => `<tr>
        <td class="mono">${{String(it.outbox_id).slice(0,8)}}…</td>
        <td>${{badge(it.status)}}</td>
        <td>${{it.template_key || '—'}}</td>
        <td>${{ts(it.scheduled_for)}}</td>
        <td>${{ts(it.sent_at)}}</td>
      </tr>`).join('');
      document.getElementById('debugRes').innerHTML = `
        <h4>Cliente</h4>${{kv(d.customer || {{}})}}
        <h4>Consentimiento actual (promociones)</h4>
        ${{d.current_promotions_consent
          ? kv(d.current_promotions_consent)
          : '<p class="empty">Sin consentimiento.</p>'}}
        <h4>Outbox reciente</h4>
        ${{outboxRows
          ? `<table><thead><tr><th>ID</th><th>Estado</th><th>Template</th><th>Programado</th><th>Enviado</th></tr></thead><tbody>${{outboxRows}}</tbody></table>`
          : '<p class="empty">Sin registros.</p>'}}`;
    }} catch(e) {{ document.getElementById('debugErr').textContent = String(e); }}
  }}

  document.getElementById('valInput').addEventListener('keydown', e => {{
    if (e.key === 'Enter') debugIdentity();
  }});

  loadSummary();
</script>
</body>
</html>""")


# ── /admin/ui/customers — Customers ──────────────────────────────────────────

@router.get("/ui/customers", response_class=HTMLResponse)
def admin_ui_customers():
    nav = _nav("Clientes")
    return HTMLResponse(f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Clientes — Principessa</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:system-ui,Arial,sans-serif;background:#f8f9fa;color:#111;}}
    main{{padding:20px;}}
    .cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;}}
    .card{{background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:16px 20px;min-width:130px;}}
    .card-num{{font-size:30px;font-weight:900;color:#111;line-height:1;}}
    .card-label{{font-size:10px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:.5px;margin-top:6px;}}
    .controls{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px;}}
    input[type=text]{{font-family:inherit;font-size:13px;padding:7px 10px;border:1px solid #d1d5db;border-radius:8px;background:#fff;}}
    .live-count{{font-size:13px;color:#6b7280;margin-left:auto;}}
    .table-wrap{{background:#fff;border:1px solid #e0e0e0;border-radius:10px;overflow:auto;}}
    table{{width:100%;border-collapse:collapse;font-size:13px;}}
    th{{font-size:11px;font-weight:700;text-transform:uppercase;color:#6b7280;padding:10px 14px;
        text-align:left;border-bottom:2px solid #e0e0e0;white-space:nowrap;
        cursor:pointer;user-select:none;}}
    th:hover{{color:#111;}}
    td{{padding:9px 14px;border-bottom:1px solid #f0f0f0;vertical-align:middle;}}
    tr:last-child td{{border-bottom:none;}}
    .empty-row{{padding:32px;text-align:center;color:#6b7280;font-size:14px;}}
  </style>
</head>
<body>
{nav}
<main>
  <div class="cards">
    <div class="card">
      <div class="card-num" id="nTotal">—</div>
      <div class="card-label">Total Customers</div>
    </div>
  </div>

  <div class="controls">
    <input type="text" id="search" placeholder="Buscar por nombre o email…" style="width:240px;" oninput="applyFilters()">
    <span class="live-count" id="liveCount"></span>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th onclick="sortBy('first_name')">Nombre <span id="si_first_name"></span></th>
          <th onclick="sortBy('email')">Email <span id="si_email"></span></th>
          <th onclick="sortBy('birthday_sort')">Cumpleaños <span id="si_birthday_sort"></span></th>
          <th onclick="sortBy('created_at')">Registro <span id="si_created_at">▼</span></th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</main>

<script>
  const KEY = sessionStorage.getItem('builderKey') || '';
  if (!KEY) window.location.replace('/builder-login?next=/admin/ui/customers');

  let allCustomers = [];
  let sortKey = 'created_at';
  let sortDir = -1;

  async function load() {{
    try {{
      const res = await fetch('/admin/customers/interests?limit=500', {{headers:{{'x-admin-key':KEY}}}});
      if (res.status === 401) {{ window.location.replace('/builder-login?next=/admin/ui/customers'); return; }}
      const d = await res.json();
      allCustomers = (d.customers || []).map(c => ({{
        ...c,
        birthday_sort: (c.birth_month && c.birth_day)
          ? c.birth_month * 100 + c.birth_day
          : 9999,
      }}));
      document.getElementById('nTotal').textContent = allCustomers.length;
      applyFilters();
    }} catch(e) {{ console.error(e); }}
  }}

  const MONTHS = ['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];

  function fmtBirthday(c) {{
    if (!c.birth_day || !c.birth_month) return '—';
    return `${{c.birth_day}} ${{MONTHS[c.birth_month]}}`;
  }}

  function applyFilters() {{
    const search = document.getElementById('search').value.toLowerCase();
    let filtered = allCustomers.filter(c =>
      !search
      || (c.first_name || '').toLowerCase().includes(search)
      || (c.email      || '').toLowerCase().includes(search)
    );
    filtered.sort((a, b) => {{
      let av = a[sortKey] ?? '', bv = b[sortKey] ?? '';
      if (typeof av === 'string') av = av.toLowerCase();
      if (typeof bv === 'string') bv = bv.toLowerCase();
      return av < bv ? -sortDir : av > bv ? sortDir : 0;
    }});
    renderTable(filtered);
    document.getElementById('liveCount').textContent =
      filtered.length === allCustomers.length
        ? `${{allCustomers.length}} clientes`
        : `${{filtered.length}} de ${{allCustomers.length}} clientes`;
  }}

  function sortBy(key) {{
    sortDir = (sortKey === key) ? -sortDir : 1;
    sortKey = key;
    ['first_name','email','birthday_sort','created_at'].forEach(k => {{
      const el = document.getElementById('si_' + k);
      if (el) el.textContent = k === sortKey ? (sortDir === 1 ? '▲' : '▼') : '';
    }});
    applyFilters();
  }}

  function renderTable(rows) {{
    const tbody = document.getElementById('tbody');
    if (!rows.length) {{
      tbody.innerHTML = '<tr><td colspan="4" class="empty-row">Sin resultados.</td></tr>';
      return;
    }}
    tbody.innerHTML = rows.map(c => `<tr>
      <td>${{c.first_name || '—'}}</td>
      <td>${{c.email      || '—'}}</td>
      <td>${{fmtBirthday(c)}}</td>
      <td>${{(c.created_at || '').slice(0,10)}}</td>
    </tr>`).join('');
  }}

  load();
</script>
</body>
</html>""")
