from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from personal_mcp.core.event import ALLOWED_DOMAINS
from personal_mcp.tools.candidates import list_candidates
from personal_mcp.tools.daily_summary import (
    count_events_by_date,
    get_latest_summary,
    list_summaries,
)
from personal_mcp.tools.log_form import (
    ALLOWED_KINDS,
    event_add_sqlite,
    ui_event_add_sqlite,
)

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
h2 { margin-bottom: 0.25rem; }
p { margin-top: 0; color: #555; font-size: 0.9rem; }
label { display: block; margin-top: 1rem; font-size: 0.9rem; color: #444; }
select, textarea { width: 100%; padding: 0.5rem; font-size: 1rem; box-sizing: border-box; }
textarea { height: 5rem; resize: vertical; }
details { margin-top: 1rem; border-top: 1px solid #ddd; padding-top: 0.75rem; }
summary { cursor: pointer; color: #333; font-size: 0.9rem; }
button { margin-top: 1rem; width: 100%; padding: 0.75rem; font-size: 1rem; cursor: pointer; }
.mode-switcher { display: flex; gap: 0.5rem; margin-top: 1rem; }
.mode-btn {
  flex: 1;
  margin-top: 0;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  background: #f8f8f8;
  color: #333;
}
.mode-btn.active { border-color: #ff7700; background: #fff3e6; color: #b14b00; font-weight: 600; }
.mode-panel { display: none; margin-top: 0.75rem; }
.mode-panel.active { display: block; }
.chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.chip {
  margin-top: 0;
  width: auto;
  padding: 0.45rem 0.7rem;
  border-radius: 999px;
  border: 1px solid #ddd;
  background: #fff;
  font-size: 0.9rem;
}
.chip.active { border-color: #ff7700; background: #fff3e6; color: #b14b00; }
#tag-preview { margin-top: 0.5rem; color: #555; font-size: 0.85rem; min-height: 1.1rem; }
#suggestion { margin-top: 0.5rem; color: #444; font-size: 0.9rem; }
#msg { margin-top: 1rem; min-height: 1.5rem; }
</style>
</head>
<body>
<h2>クイックログ</h2>
<p>まずは気づきを記録。分類は後からでも大丈夫です。</p>
<form id="f">
  <div class="mode-switcher" aria-label="入力モード切替">
    <button type="button" class="mode-btn" data-mode="quick">quick</button>
    <button type="button" class="mode-btn" data-mode="tag">tag</button>
    <button type="button" class="mode-btn" data-mode="text">text</button>
  </div>

  <div id="panel-quick" class="mode-panel">
    <div class="chip-row">
      <button type="button" class="chip quick-chip" data-text="開始した">開始</button>
      <button type="button" class="chip quick-chip" data-text="完了した">完了</button>
      <button type="button" class="chip quick-chip" data-text="休憩する">休憩</button>
    </div>
  </div>

  <div id="panel-tag" class="mode-panel">
    <div class="chip-row">
      <button type="button" class="chip tag-chip" data-tag="作業">作業</button>
      <button type="button" class="chip tag-chip" data-tag="移動">移動</button>
      <button type="button" class="chip tag-chip" data-tag="食事">食事</button>
      <button type="button" class="chip tag-chip" data-tag="運動">運動</button>
      <button type="button" class="chip tag-chip" data-tag="読書">読書</button>
      <button type="button" class="chip tag-chip" data-tag="休憩">休憩</button>
    </div>
    <div id="tag-preview"></div>
  </div>

  <div id="panel-text" class="mode-panel"></div>
  <label>気づき<textarea id="text" placeholder="いま起きたことを短く記録"></textarea></label>
  <div id="suggestion"></div>
  <details>
    <summary>分類・補足を追加（任意）</summary>
    <label>ドメイン
      <select id="domain">
        <option value="">(未指定) 候補を使う</option>
        DOMAIN_OPTIONS
      </select>
    </label>
    <label>カインド
      <select id="kind">
        <option value="">(未指定) 候補を使う</option>
        KIND_OPTIONS
      </select>
    </label>
    <label>アノテーション<textarea id="annotation"></textarea></label>
  </details>
  <button type="submit">保存</button>
</form>
<div id="msg"></div>
<script>
var UI_MODE_KEY = "daily_log_ui_mode";
var VALID_UI_MODES = ["quick", "tag", "text"];
var currentMode = "quick";
var selectedTags = [];
var inputStarted = false;

function inferLabels(text) {
  var t = (text || "").toLowerCase();
  function hasAny(keywords) {
    return keywords.some(function(k) {
      return t.indexOf(k) >= 0;
    });
  }

  var domain = "general";
  if (hasAny(["poe", "map", "atlas", "ボス", "loot"])) {
    domain = "poe2";
  } else if (hasAny(["mood", "疲", "眠", "気分", "しんど"])) {
    domain = "mood";
  } else if (hasAny(["todo", "meeting", "進捗", "作業", "タスク"])) {
    domain = "worklog";
  } else if (hasAny(["issue", "pr", "実装", "設計", "docs", "コード"])) {
    domain = "eng";
  }

  var kind = "note";
  if (hasAny(["完了", "達成", "release", "マイルストーン"])) {
    kind = "milestone";
  } else if (hasAny(["作成", "更新", "artifact", "成果物"])) {
    kind = "artifact";
  } else if (hasAny(["調査", "検証", "対応", "実施", "session"])) {
    kind = "session";
  }
  return { domain: domain, kind: kind };
}

function renderSuggestion() {
  var text = document.getElementById("text").value;
  var s = inferLabels(text);
  document.getElementById("suggestion").textContent = "候補: " + s.domain + " / " + s.kind;
}

function isValidMode(mode) {
  return VALID_UI_MODES.indexOf(mode) >= 0;
}

function persistMode(mode) {
  try { localStorage.setItem(UI_MODE_KEY, mode); } catch (e) {}
}

function readPersistedMode() {
  try {
    var mode = localStorage.getItem(UI_MODE_KEY);
    return isValidMode(mode) ? mode : null;
  } catch (e) {
    return null;
  }
}

async function postUiEvent(eventName, extraData) {
  var payload = {
    event_name: eventName,
    ui_mode: currentMode
  };
  if (extraData && typeof extraData === "object") {
    payload.extra_data = extraData;
  }
  try {
    await fetch("/events/ui", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
  } catch (e) {}
}

function setMode(mode, emitChange) {
  if (!isValidMode(mode)) return;
  var prev = currentMode;
  currentMode = mode;
  persistMode(mode);

  document.querySelectorAll(".mode-btn").forEach(function(btn) {
    var active = btn.dataset.mode === mode;
    btn.classList.toggle("active", active);
  });
  document.querySelectorAll(".mode-panel").forEach(function(panel) {
    panel.classList.toggle("active", panel.id === "panel-" + mode);
  });

  if (emitChange && prev !== mode) {
    postUiEvent("ui_mode_changed", { from_mode: prev, to_mode: mode });
  }
}

function markInputStarted() {
  if (inputStarted) return;
  inputStarted = true;
  postUiEvent("input_started", {
    text_length: document.getElementById("text").value.length,
    selected_tag_count: selectedTags.length
  });
}

function updateTagPreview() {
  var preview = document.getElementById("tag-preview");
  if (selectedTags.length === 0) {
    preview.textContent = "タグ未選択";
    return;
  }
  preview.textContent = "選択中: " + selectedTags.join(" / ");
  document.getElementById("text").value = selectedTags.join(" ");
  renderSuggestion();
}

function resetTagSelection() {
  selectedTags = [];
  document.querySelectorAll(".tag-chip").forEach(function(btn) {
    btn.classList.remove("active");
  });
  updateTagPreview();
}

async function submitLog(trigger) {
  var msg = document.getElementById("msg");
  var body = { text: document.getElementById("text").value };
  var domain = document.getElementById("domain").value;
  var kind = document.getElementById("kind").value;
  var annotation = document.getElementById("annotation").value;
  if (domain) body.domain = domain;
  if (kind) body.kind = kind;
  if (annotation) body.annotation = annotation;
  try {
    var r = await fetch("/events", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    });
    if (r.ok) {
      var saved = await r.json();
      msg.textContent = "保存しました: " + saved.domain + " / " + saved.kind;
      await postUiEvent("input_submitted", {
        trigger: trigger,
        text_length: body.text.length,
        resolved_domain: saved.domain,
        resolved_kind: saved.kind,
        selected_tag_count: selectedTags.length
      });
      document.getElementById("f").reset();
      resetTagSelection();
      inputStarted = false;
      renderSuggestion();
    } else {
      var err = await r.json();
      msg.textContent = "エラー: " + (err.error || r.status);
    }
  } catch(ex) {
    msg.textContent = "接続エラー: " + ex.message;
  }
}

document.querySelectorAll(".mode-btn").forEach(function(btn) {
  btn.addEventListener("click", function() {
    setMode(btn.dataset.mode, true);
  });
});

document.querySelectorAll(".quick-chip").forEach(function(btn) {
  btn.addEventListener("click", async function() {
    markInputStarted();
    document.getElementById("text").value = btn.dataset.text || "";
    renderSuggestion();
    await submitLog("quick_chip");
  });
});

document.querySelectorAll(".tag-chip").forEach(function(btn) {
  btn.addEventListener("click", function() {
    markInputStarted();
    var tag = btn.dataset.tag || "";
    var idx = selectedTags.indexOf(tag);
    if (idx >= 0) {
      selectedTags.splice(idx, 1);
      btn.classList.remove("active");
    } else {
      selectedTags.push(tag);
      btn.classList.add("active");
    }
    updateTagPreview();
  });
});

document.getElementById("text").addEventListener("focus", markInputStarted);
document.getElementById("text").addEventListener("input", function() {
  markInputStarted();
  renderSuggestion();
});

document.getElementById("f").addEventListener("submit", async function(e) {
  e.preventDefault();
  markInputStarted();
  await submitLog("form_submit");
});

setMode(readPersistedMode() || "quick", false);
updateTagPreview();
renderSuggestion();
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
#candidates { margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.candidate-tag {
  margin-top: 0;
  width: auto;
  padding: 0.55rem 0.9rem;
  border-radius: 999px;
  border: 1px solid #ddd;
  background: #fff;
  font-size: 1rem;
  cursor: pointer;
  min-height: 2.75rem;
  display: inline-flex;
  align-items: center;
}
#log-form { margin-bottom: 1.5rem; }
#log-text {
  width: 100%;
  padding: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
  height: 4rem;
  resize: vertical;
}
#log-submit {
  margin-top: 0.5rem;
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  cursor: pointer;
  min-height: 2.75rem;
}
#log-msg { margin-top: 0.5rem; min-height: 1.2rem; font-size: 0.85rem; color: #555; }
.summary-card { border-top: 1px solid #ddd; padding: 0.75rem 0; }
.summary-date { font-size: 0.85rem; color: #666; margin-bottom: 0.25rem; }
.summary-text { font-size: 0.95rem; }
.summary-annotation, .summary-interpretation { font-size: 0.85rem; color: #555; margin-top: 0.25rem; }
</style>
</head>
<body>
<h2>直近28日</h2>
<div class="heatmap" id="heatmap"></div>
<div id="candidates"></div>
<div id="log-form">
  <textarea id="log-text" placeholder="いま起きたことを短く記録"></textarea>
  <button type="button" id="log-submit">保存</button>
  <div id="log-msg"></div>
</div>
<div id="summaries"></div>
<script>
var DASHBOARD_FALLBACK_CANDIDATES = ["作業開始", "休憩", "移動", "食事", "作業完了"];

function heatColor(n) {
  if (n === 0) return '#eeeeee';
  if (n <= 2) return '#ffd9b3';
  if (n <= 5) return '#ffaa55';
  if (n <= 10) return '#ff7700';
  return '#cc4400';
}

function candidateText(item) {
  if (item && typeof item === "object") {
    return (item.text || "").trim();
  }
  if (typeof item === "string") {
    return item.trim();
  }
  return "";
}

function candidateSource(item) {
  if (item && typeof item === "object") {
    return (item.source || "").trim();
  }
  return "";
}

function renderCandidates(items) {
  var el = document.getElementById("candidates");
  el.innerHTML = "";
  if (!Array.isArray(items) || items.length === 0) {
    el.style.display = "none";
    return;
  }
  el.style.display = "";
  items.forEach(function(item) {
    var text = candidateText(item);
    if (!text) return;
    var tag = document.createElement("button");
    tag.type = "button";
    tag.className = "candidate-tag";
    tag.textContent = text;
    var source = candidateSource(item);
    if (source) tag.dataset.source = source;
    tag.addEventListener("click", function() {
      var input = document.getElementById("log-text");
      input.value = text;
      input.focus();
    });
    el.appendChild(tag);
  });
  if (el.childElementCount === 0) {
    el.style.display = "none";
  }
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

async function loadCandidates() {
  try {
    var r = await fetch("/api/candidates");
    if (!r.ok) throw new Error("http " + r.status);
    var data = await r.json();
    renderCandidates(data);
  } catch (e) {
    renderCandidates(DASHBOARD_FALLBACK_CANDIDATES);
  }
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

async function submitDashboardLog() {
  var msg = document.getElementById("log-msg");
  var text = document.getElementById("log-text").value.trim();
  if (!text) return;
  try {
    var r = await fetch("/events", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text})
    });
    if (r.ok) {
      msg.textContent = "保存しました";
      document.getElementById("log-text").value = "";
      setTimeout(function() { msg.textContent = ""; }, 2000);
    } else {
      var err = await r.json();
      msg.textContent = "エラー: " + (err.error || r.status);
    }
  } catch (ex) {
    msg.textContent = "接続エラー: " + ex.message;
  }
}

document.getElementById("log-submit").addEventListener("click", submitDashboardLog);
loadHeatmap();
loadCandidates();
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

        def _read_json_body(self) -> Any:
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            try:
                return json.loads(self.rfile.read(length))
            except Exception as exc:
                raise ValueError("invalid JSON") from exc

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html", "/dashboard"):
                html = _DASHBOARD_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            elif parsed.path == "/input":
                html = _make_html().encode("utf-8")
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
            elif parsed.path == "/api/candidates":
                self._json(200, list_candidates(data_dir or None))
            elif parsed.path == "/api/summaries/list":
                self._json(200, list_summaries(28, data_dir or None))
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path not in ("/events", "/events/ui"):
                self._json(404, {"error": "not found"})
                return
            try:
                body = self._read_json_body()
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            if not isinstance(body, dict):
                self._json(400, {"error": "invalid JSON"})
                return

            if self.path == "/events/ui":
                event_name = (body.get("event_name") or "").strip()
                ui_mode = (body.get("ui_mode") or "").strip()
                extra_data = body.get("extra_data")
                if extra_data is not None and not isinstance(extra_data, dict):
                    self._json(400, {"error": "extra_data must be an object"})
                    return
                try:
                    record = ui_event_add_sqlite(
                        event_name=event_name,
                        ui_mode=ui_mode,
                        data_dir=data_dir or None,
                        extra_data=extra_data,
                    )
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                self._json(201, record)
                return

            domain = (body.get("domain") or "").strip()
            kind = (body.get("kind") or "").strip()
            text = (body.get("text") or "").strip()
            annotation = (body.get("annotation") or "").strip() or None

            try:
                record = event_add_sqlite(
                    domain=domain or None,
                    kind=kind or None,
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
