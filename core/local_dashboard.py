"""Local-only dashboard for the SNA AI Agent Engine demo.

Start with: python examples/local_dashboard.py
The server binds to 127.0.0.1 only. It uses an in-memory mock CRM and local
rules-based scoring; it is not a production web application and has no auth.
Do not expose this server to a LAN or the public internet.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from typing import Any

from .lead_qualification import LeadProfile, qualify_lead
from .mock_crm import MockCRM


HOST = "127.0.0.1"
PORT = 8765
MAX_BODY_BYTES = 16_384
CRM = MockCRM()


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SNA AI · Lead Qualification Demo</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;color:#182033;background:#f5f7fb}
body{margin:0}.shell{max-width:1000px;margin:0 auto;padding:32px 20px}
header{margin-bottom:24px}h1{margin:0 0 8px;font-size:28px}p{color:#667085;line-height:1.5}
.notice{padding:12px 14px;background:#fff7e6;border:1px solid #f4d59a;border-radius:12px;color:#7a4d00}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
.card{background:white;border:1px solid #e3e8f2;border-radius:16px;padding:20px;box-shadow:0 6px 24px #1820330a}
h2{font-size:18px;margin-top:0}label{display:block;font-size:13px;font-weight:650;margin:12px 0 6px}
input,textarea{box-sizing:border-box;width:100%;padding:11px;border:1px solid #d0d5dd;border-radius:9px;font:inherit}
textarea{min-height:70px;resize:vertical}.check{display:flex;align-items:center;gap:8px;font-weight:500}.check input{width:auto}
button{margin-top:16px;padding:11px 15px;background:#4338ca;color:white;border:0;border-radius:9px;font-weight:700;cursor:pointer}
button:hover{background:#3730a3}.result{margin-top:14px;padding:12px;background:#f8fafc;border-radius:10px;white-space:pre-wrap;overflow-wrap:anywhere}
small{color:#667085}.footer{margin-top:20px;font-size:12px;color:#667085}
</style>
</head>
<body><main class="shell">
<header><h1>SNA AI · Lead Qualification</h1><p>A local prototype for testing lead readiness and read-only CRM lookup.</p>
<div class="notice"><strong>Demo only.</strong> Rules-based score + temporary mock data. No real AI model, customer database, or outbound messages are connected.</div></header>
<div class="grid">
<section class="card"><h2>Qualify an enquiry</h2>
<form id="qualify">
<label for="need">Need or goal</label><textarea id="need" name="need" placeholder="What does the prospect need?"></textarea>
<label for="budget">Budget range</label><input id="budget" name="budget" placeholder="e.g. ₹80 lakh–₹1 crore">
<label for="timeline">Timeline</label><input id="timeline" name="timeline" placeholder="e.g. within 3 months">
<label for="contact">Preferred contact method</label><input id="contact" name="contact_method" placeholder="e.g. email or phone">
<label class="check"><input id="consent" type="checkbox" name="consent_to_contact"> Prospect explicitly agreed to follow-up</label>
<button type="submit">Calculate qualification</button></form><div class="result" id="qualification-result" aria-live="polite">Your result will appear here.</div>
</section>
<section class="card"><h2>Search demo CRM</h2><p>Search the temporary sample contacts. This action is read-only.</p>
<form id="search"><label for="query">Name or email</label><input id="query" name="query" required maxlength="100" placeholder="Try Asha or Ravi">
<button type="submit">Search contacts</button></form><div class="result" id="crm-result" aria-live="polite">Search results will appear here.</div>
</section></div>
<div class="footer">Local-only prototype · Data resets when the server restarts · Never enter real customer secrets.</div>
</main>
<script>
async function post(path,data){const response=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const body=await response.json();if(!response.ok)throw new Error(body.error||"Request failed");return body}
document.getElementById("qualify").addEventListener("submit",async event=>{event.preventDefault();const form=event.currentTarget;const data=Object.fromEntries(new FormData(form));data.consent_to_contact=document.getElementById("consent").checked;try{const result=await post("/api/qualify",data);document.getElementById("qualification-result").textContent=JSON.stringify(result,null,2)}catch(error){document.getElementById("qualification-result").textContent=error.message}});
document.getElementById("search").addEventListener("submit",async event=>{event.preventDefault();const query=document.getElementById("query").value;try{const result=await post("/api/crm/search",{query});document.getElementById("crm-result").textContent=JSON.stringify(result,null,2)}catch(error){document.getElementById("crm-result").textContent=error.message}});
</script></body></html>"""


def qualification_from_payload(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    string_fields = ("need", "budget", "timeline", "contact_method")
    if any(not isinstance(payload.get(key, ""), str) for key in string_fields):
        raise ValueError("Need, budget, timeline, and contact method must be strings.")
    consent = payload.get("consent_to_contact", False)
    if not isinstance(consent, bool):
        raise ValueError("consent_to_contact must be a boolean.")
    result = qualify_lead(LeadProfile(
        need=payload.get("need", ""),
        budget=payload.get("budget", ""),
        timeline=payload.get("timeline", ""),
        contact_method=payload.get("contact_method", ""),
        consent_to_contact=consent,
    ))
    return {
        "score": result.score,
        "tier": result.tier,
        "reasons": list(result.reasons),
        "missing_fields": list(result.missing_fields),
        "can_contact": consent is True and bool(payload.get("contact_method", "").strip()),
        "note": "Readiness heuristic only; not a conversion probability.",
    }


def search_mock_crm(crm: MockCRM, payload: Any) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("query"), str):
        raise ValueError("Request body must contain a string query.")
    query = payload["query"].strip()
    if not query or len(query) > 100:
        raise ValueError("Query must contain 1–100 characters.")
    return crm.search_contacts(query)


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "SNA-AI-Demo"
    sys_version = ""

    def log_message(self, format, *args):
        # Avoid logging query/body content in this local demo.
        return

    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict):
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path == "/":
            self._send(200, DASHBOARD_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/health":
            self._json(200, {"ok": True, "mode": "local-demo"})
        else:
            self._json(404, {"error": "Not found."})

    def do_POST(self):
        if self.path not in {"/api/qualify", "/api/crm/search"}:
            self._json(404, {"error": "Not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "Invalid content length."})
            return
        if length < 1 or length > MAX_BODY_BYTES:
            self._json(413 if length > MAX_BODY_BYTES else 400, {"error": "Request body size is invalid."})
            return
        if "application/json" not in self.headers.get("Content-Type", ""):
            self._json(415, {"error": "Content-Type must be application/json."})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = qualification_from_payload(payload) if self.path == "/api/qualify" else search_mock_crm(CRM, payload)
            self._json(200, result)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "Invalid request. Check the fields and JSON format."})


def main():
    server = HTTPServer((HOST, PORT), DashboardHandler)
    print(f"SNA AI local demo running at http://{HOST}:{PORT}")
    print("Local-only. Do not expose this server to a LAN or the public internet.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local demo.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
