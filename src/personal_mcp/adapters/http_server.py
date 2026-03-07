from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from personal_mcp.core.event import ALLOWED_DOMAINS
from personal_mcp.tools.daily_summary import (
    count_events_by_date,
    get_latest_summary,
    list_summaries,
)
from personal_mcp.tools.log_form import ALLOWED_KINDS, event_add_sqlite

# DOMAIN_OPTIONS / KIND_OPTIONS are replaced at render time via str.replace()
_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ログ入力</title>
<style>
body { font-family: system-ui; max-width: 480px; margin: 0 auto; padding: 1rem; }
label { display: block; margin-top: 1rem; font-size: 0.9rem; color: #444; }
select, textarea { width: 100%; padding: 0.5rem; font-size: 1rem; box-sizing: border-box; }
textarea { height: 5rem; resize: vertical; }
button { margin-top: 1.5rem; width: 100%; padding: 0.75rem; font-size: 1rem; cursor: pointer; }
#msg { margin-top: 1rem; min-height: 1.5rem; }
</style>
</head>
<body>
<h2>ログ入力</h2>
<form id="f">
  <label>テキスト<textarea id="text"></textarea></label>
  <label>ドメイン *
    <select id="domain" required>
      <option value="">-- 選択 --</option>
      DOMAIN_OPTIONS
    </select>
  </label>
  <label>カインド *
    <select id="kind" required>
      <option value="">-- 選択 --</option>
      KIND_OPTIONS
    </select>
  </label>
  <label>アノテーション<textarea id="annotation"></textarea></label>
  <button type="submit">保存</button>
</form>
<div id="msg"></div>
<script>
document.getElementById("f").addEventListener("submit", async function(e) {
  e.preventDefault();
  var msg = document.getElementById("msg");
  var body = {
    text: document.getElementById("text").value,
    domain: document.getElementById("domain").value,
    kind: document.getElementById("kind").value,
    annotation: document.getElementById("annotation").value
  };
  try {
    var r = await fetch("/events", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    });
    if (r.ok) {
      msg.textContent = "保存しました";
      document.getElementById("f").reset();
    } else {
      var err = await r.json();
      msg.textContent = "エラー: " + (err.error || r.status);
    }
  } catch(ex) {
    msg.textContent = "接続エラー: " + ex.message;
  }
});
</script>
</body>
</html>"""

_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>活動</title>
<style>
body { font-family: system-ui; max-width: 480px; margin: 0 auto; padding: 1rem; }
h2 { font-size: 1.1rem; margin-bottom: 0.75rem; }
.heatmap { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; margin-bottom: 1.5rem; }
.heatmap-cell { aspect-ratio: 1; border-radius: 2px; }
.summary-card { border-top: 1px solid #ddd; padding: 0.75rem 0; }
.summary-date { font-size: 0.85rem; color: #666; margin-bottom: 0.25rem; }
.summary-text { font-size: 0.95rem; }
.summary-annotation, .summary-interpretation { font-size: 0.85rem; color: #555; margin-top: 0.25rem; }
</style>
</head>
<body>
<h2>直近28日</h2>
<div class="heatmap" id="heatmap"></div>
<div id="summaries"></div>
<script>
function heatColor(n) {
  if (n === 0) return '#eeeeee';
  if (n <= 2) return '#ffd9b3';
  if (n <= 5) return '#ffaa55';
  if (n <= 10) return '#ff7700';
  return '#cc4400';
}
async function loadHeatmap() {
  var r = await fetch('/api/heatmap');
  var data = await r.json();
  var el = document.getElementById('heatmap');
  data.forEach(function(item) {
    var cell = document.createElement('div');
    cell.className = 'heatmap-cell';
    cell.style.background = heatColor(item.count);
    cell.title = item.date + ': ' + item.count + '件';
    el.appendChild(cell);
  });
}
async function loadSummaries() {
  var r = await fetch('/api/summaries/list');
  var data = await r.json();
  var el = document.getElementById('summaries');
  data.forEach(function(item) {
    var card = document.createElement('div'); card.className = 'summary-card';
    var d = document.createElement('div'); d.className = 'summary-date'; d.textContent = item.date; card.appendChild(d);
    var t = document.createElement('div'); t.className = 'summary-text'; t.textContent = item.text; card.appendChild(t);
    if (item.annotation) { var a = document.createElement('div'); a.className = 'summary-annotation'; a.textContent = item.annotation; card.appendChild(a); }
    if (item.interpretation) { var i = document.createElement('div'); i.className = 'summary-interpretation'; i.textContent = item.interpretation; card.appendChild(i); }
    el.appendChild(card);
  });
}
loadHeatmap();
loadSummaries();
</script>
</body>
</html>"""  # noqa: E501


def _make_html() -> str:
    domain_opts = "\n      ".join(
        f'<option value="{d}">{d}</option>' for d in sorted(ALLOWED_DOMAINS)
    )
    kind_opts = "\n      ".join(f'<option value="{k}">{k}</option>' for k in sorted(ALLOWED_KINDS))
    return _HTML.replace("DOMAIN_OPTIONS", domain_opts).replace("KIND_OPTIONS", kind_opts)


def _make_handler(data_dir: str):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def _json(self, status: int, body: Any) -> None:
            payload = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                html = _make_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            elif parsed.path == "/dashboard":
                html = _DASHBOARD_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            elif parsed.path == "/health":
                self._json(200, {"status": "ok"})
            elif parsed.path == "/summaries":
                params = parse_qs(parsed.query)
                date_vals = params.get("date", [])
                if not date_vals:
                    self._json(400, {"error": "date query param required"})
                    return
                rec = get_latest_summary(date_vals[0], data_dir or None)
                if rec is None:
                    self._json(404, {"error": "no summary for date"})
                else:
                    self._json(200, rec)
            elif parsed.path == "/api/heatmap":
                self._json(200, count_events_by_date(28, data_dir or None))
            elif parsed.path == "/api/summaries/list":
                self._json(200, list_summaries(28, data_dir or None))
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/events":
                self._json(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                self._json(400, {"error": "invalid Content-Length"})
                return
            try:
                body = json.loads(self.rfile.read(length))
            except Exception:
                self._json(400, {"error": "invalid JSON"})
                return

            domain = (body.get("domain") or "").strip()
            kind = (body.get("kind") or "").strip()
            text = (body.get("text") or "").strip()
            annotation = (body.get("annotation") or "").strip() or None

            if not domain:
                self._json(400, {"error": "domain is required"})
                return
            if not kind:
                self._json(400, {"error": "kind is required"})
                return
            try:
                record = event_add_sqlite(
                    domain=domain,
                    kind=kind,
                    text=text,
                    annotation=annotation,
                    data_dir=data_dir or None,
                )
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(201, record)

    return _Handler


def serve(host: str = "0.0.0.0", port: int = 8080, data_dir: str = "") -> None:
    handler_cls = _make_handler(data_dir)
    server = HTTPServer((host, port), handler_cls)
    print(f"serving on http://{host}:{port}  data_dir={data_dir or '(default)'}", flush=True)
    server.serve_forever()
