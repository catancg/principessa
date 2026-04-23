import os
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import Query
router = APIRouter(prefix="/admin", tags=["admin-ui"])

def require_admin_key(x_admin_key: str | None):
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not set")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/ui", response_class=HTMLResponse)
def admin_ui(key: str | None = Query(default=None),
    x_admin_key: str | None = Header(default=None),
):
    admin_key = key or x_admin_key
    require_admin_key(admin_key)

    # JS will call the API endpoints using the same x-admin-key
    html = f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Principessa Pastelería — Admin</title>
  <style>
    body {{ font-family: system-ui, Arial; margin: 20px; }}
    .row {{ display:flex; gap:12px; flex-wrap:wrap; }}
    .card {{ border:1px solid #ddd; border-radius:10px; padding:12px; min-width:260px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border-bottom:1px solid #eee; padding:8px; text-align:left; font-size:14px; }}
    input, select, button {{ padding:8px; font-size:14px; }}
    button {{ cursor:pointer; }}
    .muted {{ color:#666; }}
    code {{ background:#f5f5f5; padding:2px 4px; border-radius:6px; }}
    .error {{ color:#b00020; white-space:pre-wrap; }}
  </style>
</head>
<body>
  <h2>Admin Dashboard — Principessa Pastelería</h2>
  <p class="muted">Este panel usa tu <code>x-admin-key</code> (ya validada en el server).</p>

  <div class="row">
    <div class="card">
      <h3>Resumen</h3>
      <div id="summary">Cargando...</div>
      <div id="summaryErr" class="error"></div>
      <button onclick="loadSummary()">Actualizar</button>
    </div>

    <div class="card">
      <h3>Outbox</h3>
      <div class="row">
        <select id="statusSel">
          <option value="queued">queued</option>
          <option value="sent">sent</option>
          <option value="failed">failed</option>
        </select>
        <button onclick="loadOutbox()">Ver</button>
      </div>
      <div id="outboxErr" class="error"></div>
    </div>

    <div class="card">
      <h3>Debug por identidad</h3>
      <div class="row">
        <select id="chanSel">
          <option value="email">email</option>
          <option value="whatsapp">whatsapp</option>
          <option value="instagram">instagram</option>
        </select>
        <input id="valInput" placeholder="email o teléfono o @usuario" style="flex:1;" />
      </div>
      <button onclick="debugIdentity()" style="margin-top:8px;">Buscar</button>
      <div id="debugErr" class="error"></div>
    </div>
  </div>

  <h3 style="margin-top:20px;">Resultados</h3>
  <div id="results"></div>

<script>
  const ADMIN_KEY = "{admin_key}";

  async function apiGet(path) {{
    const res = await fetch(path, {{
      headers: {{
        "x-admin-key": ADMIN_KEY
      }}
    }});
    const text = await res.text();
    if (!res.ok) throw new Error(`HTTP ${{res.status}}: ${{text}}`);
    return JSON.parse(text);
  }}

  function renderKv(obj) {{
    return "<table>" + Object.entries(obj).map(([k,v]) =>
      `<tr><th>${{k}}</th><td>${{v}}</td></tr>`
    ).join("") + "</table>";
  }}

  async function loadSummary() {{
    document.getElementById("summaryErr").innerText = "";
    document.getElementById("summary").innerText = "Cargando...";
    try {{
      const data = await apiGet("/admin/summary");
      const counts = data.counts || {{}};
      const outbox = (data.outbox_by_status || []).map(x => `${{x.status}}: ${{x.count}}`).join("<br>");
      const cons = (data.current_promotions_consent_by_status || []).map(x => `${{x.status}}: ${{x.count}}`).join("<br>") || "(view no disponible)";
      document.getElementById("summary").innerHTML =
        `<b>Counts</b>${{renderKv(counts)}}<br><b>Outbox</b><br>${{outbox}}<br><br><b>Consent</b><br>${{cons}}`;
    }} catch(e) {{
      document.getElementById("summary").innerText = "";
      document.getElementById("summaryErr").innerText = String(e);
    }}
  }}

  async function loadOutbox() {{
    document.getElementById("outboxErr").innerText = "";
    const status = document.getElementById("statusSel").value;
    try {{
      const data = await apiGet(`/admin/outbox?status=${{encodeURIComponent(status)}}&limit=50`);
      const items = data.items || [];
      const rows = items.map(it => `
        <tr>
          <td>${{it.outbox_id}}</td>
          <td>${{it.recipient}}</td>
          <td>${{it.template_key}}</td>
          <td>${{it.status}}</td>
          <td>${{it.scheduled_for || ""}}</td>
          <td>${{it.sent_at || ""}}</td>
        </tr>`).join("");
      document.getElementById("results").innerHTML = `
        <h4>Outbox: ${{status}} (últimos 50)</h4>
        <table>
          <thead><tr>
            <th>outbox_id</th><th>recipient</th><th>template</th><th>status</th><th>scheduled_for</th><th>sent_at</th>
          </tr></thead>
          <tbody>${{rows || "<tr><td colspan='6'>(sin datos)</td></tr>"}}</tbody>
        </table>`;
    }} catch(e) {{
      document.getElementById("outboxErr").innerText = String(e);
    }}
  }}

  async function debugIdentity() {{
    document.getElementById("debugErr").innerText = "";
    const channel = document.getElementById("chanSel").value;
    const value = document.getElementById("valInput").value.trim();
    if (!value) {{
      document.getElementById("debugErr").innerText = "Ingresá un valor.";
      return;
    }}
    try {{
      const data = await apiGet(`/admin/debug/identity?channel=${{encodeURIComponent(channel)}}&value=${{encodeURIComponent(value)}}`);
      const cust = data.customer || {{}};
      const consent = data.current_promotions_consent || null;
      const outbox = data.recent_outbox || [];
      const outboxRows = outbox.map(it => `
        <tr>
          <td>${{it.outbox_id}}</td>
          <td>${{it.status}}</td>
          <td>${{it.template_key}}</td>
          <td>${{it.scheduled_for || ""}}</td>
          <td>${{it.sent_at || ""}}</td>
          <td>${{it.created_at || ""}}</td>
        </tr>`).join("");

      document.getElementById("results").innerHTML = `
        <h4>Debug</h4>
        <b>Customer</b>${{renderKv(cust)}}<br>
        <b>Current promotions consent</b><br>${{consent ? renderKv(consent) : "(no disponible)"}}
        <br><br>
        <b>Recent outbox</b>
        <table>
          <thead><tr>
            <th>outbox_id</th><th>status</th><th>template</th><th>scheduled_for</th><th>sent_at</th><th>created_at</th>
          </tr></thead>
          <tbody>${{outboxRows || "<tr><td colspan='6'>(sin datos)</td></tr>"}}</tbody>
        </table>`;
    }} catch(e) {{
      document.getElementById("debugErr").innerText = String(e);
    }}
  }}

  loadSummary();
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)
