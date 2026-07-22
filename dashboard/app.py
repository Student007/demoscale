"""Serve the local learning dashboard and expose observations as JSON."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen
from urllib.parse import urlparse

import redis


REDIS_HOST = os.environ.get("REDIS_HOST", "queue")
QUEUE_KEY = os.environ.get("QUEUE_KEY", "jobs")
PRODUCER_URL = os.environ.get("PRODUCER_URL", "http://producer:8000")
redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)


HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Docker-Skalierungsdemo</title>
<style>
:root{color-scheme:light;--blue:#174ea6;--blue-dark:#123b7a;--blue-light:#eaf2ff;--green:#18794e;--amber:#a15c00;--ink:#17233b;--muted:#5d6b82;--line:#d8e1ef}
*{box-sizing:border-box}body{margin:0;background:#f6f8fc;color:var(--ink);font:16px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1050px;margin:0 auto;padding:2.5rem 1.25rem 3rem}h1,h2,h3{line-height:1.2;margin:0}h1{font-size:clamp(2rem,4vw,3.25rem);color:var(--blue-dark);letter-spacing:-.03em}h2{font-size:1.35rem;color:var(--blue-dark)}p{margin:.5rem 0}.eyebrow{color:var(--blue);font-size:.78rem;font-weight:750;letter-spacing:.12em;text-transform:uppercase}.lead{max-width:720px;color:var(--muted);font-size:1.08rem;margin-top:.75rem}
.quickstart,.panel,.explanation{background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:0 8px 24px #21447812}.quickstart{display:grid;grid-template-columns:1.5fr 1fr;gap:1.25rem;margin:2rem 0;padding:1.25rem 1.5rem}.quickstart strong{color:var(--blue-dark)}ol{margin:.55rem 0 0;padding-left:1.35rem}.command{align-self:center;background:var(--blue-light);border-left:4px solid var(--blue);border-radius:10px;color:var(--blue-dark);font:700 .92rem/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;padding:1rem;overflow-wrap:anywhere}
.actions{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;margin:1.25rem 0 1.5rem}.actions h2{margin-right:.5rem}.button{background:var(--blue);border:0;border-radius:10px;color:#fff;cursor:pointer;font:700 .95rem system-ui;padding:.7rem 1rem;transition:background .15s,transform .15s}.button:hover{background:var(--blue-dark);transform:translateY(-1px)}.button:disabled{cursor:wait;opacity:.6;transform:none}.message{color:var(--muted);font-size:.9rem}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1.5rem}.stat{background:var(--blue-light);border-radius:14px;padding:1rem 1.1rem}.stat-label{color:var(--muted);font-size:.88rem}.stat-value{color:var(--blue-dark);font-size:2rem;font-weight:800;line-height:1.1;margin-top:.2rem}
.panel{padding:1.35rem 1.5rem}.section-head{align-items:baseline;display:flex;justify-content:space-between;gap:1rem;margin-bottom:1rem}.updated{color:var(--muted);font-size:.84rem}.workers{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}.worker{border:1px solid var(--line);border-radius:13px;padding:1rem}.worker-top{align-items:center;display:flex;gap:.6rem;justify-content:space-between}.worker-name{font:700 .88rem ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere}.badge{border-radius:999px;font-size:.78rem;font-weight:750;padding:.2rem .55rem;white-space:nowrap}.waiting{background:#eaf6ef;color:var(--green)}.processing{background:#fff3df;color:var(--amber)}.stopped{background:#fbeaea;color:#a33}.worker-meta{color:var(--muted);font-size:.9rem;margin-top:.8rem}.empty{border:1px dashed var(--line);border-radius:12px;color:var(--muted);padding:1.1rem;text-align:center}
.explanation{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-top:1.5rem;padding:1.25rem 1.5rem}.explanation h3{color:var(--blue);font-size:1rem}.explanation p{color:var(--muted);font-size:.92rem}.footer{color:var(--muted);font-size:.85rem;margin-top:1.4rem}.footer a{color:var(--blue)}
@media(max-width:720px){main{padding-top:1.5rem}.quickstart,.explanation{grid-template-columns:1fr}.stats{grid-template-columns:1fr}.section-head{align-items:flex-start;flex-direction:column}}
</style>
</head>
<body>
<main>
<span class="eyebrow">Docker-Praxisprojekt</span>
<h1>Docker-Skalierungsdemo</h1>
<p class="lead">Erzeuge Aufträge und beobachte, wie mehrere gleichartige Worker sie aus derselben Queue verarbeiten. Die Seite aktualisiert sich automatisch.</p>

<section class="quickstart" aria-labelledby="quickstart-title">
  <div><strong id="quickstart-title">So untersuchen Sie die Skalierung</strong>
    <ol><li>Erzeugen Sie unten einige Jobs.</li><li>Starten Sie danach weitere Worker mit dem angegebenen Befehl.</li><li>Beobachten Sie, wie neue Container als eigene Worker erscheinen.</li></ol>
  </div>
  <div class="command">docker compose up -d --scale worker=4</div>
</section>

<section class="actions" aria-label="Jobs erzeugen">
  <h2>Aufträge erzeugen</h2>
  <button class="button" data-jobs="5">5 Jobs</button>
  <button class="button" data-jobs="20">20 Jobs</button>
  <button class="button" data-jobs="40">40 Jobs</button>
  <span id="message" class="message" role="status"></span>
</section>

<section class="stats" aria-label="Aktuelle Kennzahlen">
  <div class="stat"><div class="stat-label">Jobs in der Queue</div><div id="queue" class="stat-value">–</div></div>
  <div class="stat"><div class="stat-label">Insgesamt verarbeitet</div><div id="processed" class="stat-value">–</div></div>
  <div class="stat"><div class="stat-label">Aktive Worker</div><div id="worker-count" class="stat-value">–</div></div>
</section>

<section class="panel" aria-labelledby="workers-title">
  <div class="section-head"><h2 id="workers-title">Aktive Worker-Container</h2><span id="updated" class="updated">Lade Status …</span></div>
  <div id="workers" class="workers"><div class="empty">Die Worker werden geladen …</div></div>
</section>

<section class="explanation" aria-label="Was ist zu beobachten">
  <div><h3>Queue</h3><p>Neue Jobs warten zunächst in Redis. Eine größere Zahl zeigt, dass mehr Arbeit ansteht.</p></div>
  <div><h3>Worker</h3><p>Jede Karte entspricht einem eigenen Container. Alle Worker verwenden dasselbe Image.</p></div>
  <div><h3>Skalierung</h3><p>Mit <b>--scale worker=4</b> erhöhen Sie die Zahl der Container zur Laufzeit.</p></div>
</section>
<p class="footer"><a href="/status">Technischer JSON-Status (/status)</a> · Diese Ansicht ist die grafische Alternative für die Untersuchung im Browser.</p>
</main>
<script>
const labels={waiting:'wartet auf Job',processing:'verarbeitet gerade',stopped:'gestoppt'};
const escapeHtml=value=>String(value??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
function render(state){
  document.querySelector('#queue').textContent=state.queue_length;
  document.querySelector('#processed').textContent=state.processed;
  document.querySelector('#worker-count').textContent=state.workers.length;
  document.querySelector('#updated').textContent='Zuletzt aktualisiert: '+new Date().toLocaleTimeString('de-DE');
  const container=document.querySelector('#workers');
  if(!state.workers.length){container.innerHTML='<div class="empty">Noch kein Worker sichtbar. Starten Sie den Compose-Stack.</div>';return;}
  container.innerHTML=state.workers.map(worker=>{
    const status=worker.status||'waiting';
    return `<article class="worker"><div class="worker-top"><span class="worker-name">${escapeHtml(worker.name)}</span><span class="badge ${escapeHtml(status)}">${escapeHtml(labels[status]||status)}</span></div><div class="worker-meta">Verarbeitet: <b>${escapeHtml(worker.processed||0)}</b><br>Aktueller Job: <b>${escapeHtml(worker.current_job||'–')}</b></div></article>`;
  }).join('');
}
async function refresh(){
  try{const response=await fetch('/status');if(!response.ok)throw new Error('Status '+response.status);render(await response.json());}
  catch(error){document.querySelector('#updated').textContent='Status momentan nicht erreichbar';console.error(error);}
}
async function enqueue(amount,button){
  button.disabled=true;document.querySelector('#message').textContent=amount+' Jobs werden erzeugt …';
  try{const response=await fetch('/enqueue?n='+amount);if(!response.ok)throw new Error('Producer '+response.status);document.querySelector('#message').textContent=amount+' Jobs wurden in die Queue gelegt.';await refresh();}
  catch(error){document.querySelector('#message').textContent='Jobs konnten nicht erzeugt werden.';console.error(error);}
  finally{button.disabled=false;}
}
document.querySelectorAll('[data-jobs]').forEach(button=>button.addEventListener('click',()=>enqueue(button.dataset.jobs,button)));
refresh();setInterval(refresh,2000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, body, content_type="application/json; charset=utf-8", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def status_payload(self):
        # Die GUI fragt diesen JSON-Endpunkt regelmäßig ab. Damit bleibt die
        # Beobachtungslogik von der Darstellung im Browser getrennt.
        workers = []
        for key in sorted(redis_client.scan_iter("scale:worker:*")):
            worker = redis_client.hgetall(key)
            if worker:
                workers.append(worker)
        return {
            "queue_length": redis_client.llen(QUEUE_KEY),
            "processed": int(redis_client.get("scale:processed") or 0),
            "workers": workers,
        }

    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            redis_client.ping()
            self.send_bytes(json.dumps({"status": "ok"}).encode("utf-8"))
            return
        if parsed.path == "/status":
            self.send_bytes(json.dumps(self.status_payload()).encode("utf-8"))
            return
        if parsed.path == "/enqueue":
            # The dashboard calls producer by its Compose DNS name. No
            # producer port is published to the host.
            query = parsed.query or "n=12"
            with urlopen(f"{PRODUCER_URL}/enqueue?{query}", timeout=5) as response:
                self.send_bytes(response.read())
            return
        self.send_bytes(HTML.encode("utf-8"), "text/html; charset=utf-8")

    def log_message(self, format, *args):
        print(f"dashboard: {format % args}", flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print("dashboard listening on :8080", flush=True)
    server.serve_forever()
