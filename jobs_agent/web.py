from __future__ import annotations

from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .sources import fetch_all
from .store import JobStore


STYLE = """
:root{color-scheme:dark;--bg:#090d14;--card:#121925;--muted:#94a3b8;--line:#263244;--accent:#5eead4;--blue:#60a5fa}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#090d14,#0d1726);color:#e5edf8;font:15px system-ui,-apple-system,sans-serif}
main{max-width:1180px;margin:auto;padding:38px 22px}.top{display:flex;align-items:end;justify-content:space-between;gap:18px;flex-wrap:wrap}
h1{font-size:clamp(28px,5vw,54px);line-height:1;margin:0}.sub{color:var(--muted);max-width:650px}.stats{display:flex;gap:10px;flex-wrap:wrap;margin:25px 0}
.stat,.pill{border:1px solid var(--line);background:#101824;padding:8px 12px;border-radius:999px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:15px}
.card{background:rgba(18,25,37,.92);border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 12px 32px #0004}.card:hover{border-color:#3d526d;transform:translateY(-2px)}
a{color:inherit}.title{font-size:20px;font-weight:750;text-decoration:none}.company{color:var(--accent);font-weight:650}.meta,.reasons{color:var(--muted);font-size:13px}.score{font-size:28px;font-weight:800;color:var(--accent)}
.row{display:flex;justify-content:space-between;gap:15px}.actions{display:flex;gap:7px;margin-top:16px;flex-wrap:wrap}button,.button{border:1px solid var(--line);border-radius:10px;background:#172235;color:#e5edf8;padding:9px 12px;cursor:pointer;text-decoration:none}button:hover,.button:hover{border-color:var(--blue)}
button.primary{background:#0f766e;border-color:#14b8a6}.empty{padding:50px;border:1px dashed var(--line);border-radius:18px;text-align:center;color:var(--muted)}
"""


def render_dashboard(jobs: list[dict]) -> str:
    cards = []
    for job in jobs:
        reasons = " · ".join(escape(reason) for reason in job["reasons"])
        actions = "".join(
            f'<form method="post" action="/status/{escape(job["id"])}/{status}"><button>{label}</button></form>'
            for status, label in (("saved", "Save"), ("applied", "Applied"), ("dismissed", "Dismiss"))
        )
        cards.append(f"""
        <article class="card"><div class="row"><div>
          <a class="title" href="{escape(job['url'], quote=True)}" target="_blank" rel="noreferrer">{escape(job['title'])}</a>
          <div class="company">{escape(job['company'])}</div></div><div class="score">{job['score']}</div></div>
          <p class="meta">{escape(job['location'])} · {escape(job['role_type'])} · {escape(job['source'])} · {escape(job['status'])}</p>
          <p class="reasons">{reasons}</p><div class="actions">{actions}<a class="button" href="{escape(job['url'], quote=True)}" target="_blank">Apply ↗</a></div>
        </article>""")
    content = "".join(cards) or '<div class="empty">No suitable jobs yet. Click “Search now” to collect roles.</div>'
    counts = {state: sum(job["status"] == state for job in jobs) for state in ("new", "saved", "applied")}
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Germany CS Jobs Agent</title><style>{STYLE}</style></head>
    <body><main><div class="top"><div><h1>Germany CS Jobs</h1><p class="sub">Werkstudent and entry-level tech roles ranked for a computer-science student.</p></div>
    <form method="post" action="/refresh"><button class="primary">Search now</button></form></div>
    <div class="stats"><span class="stat">{len(jobs)} matches</span><span class="stat">{counts['new']} new</span><span class="stat">{counts['saved']} saved</span><span class="stat">{counts['applied']} applied</span></div>
    <section class="grid">{content}</section></main></body></html>"""


def render_digest(jobs: list[dict], new_count: int, limit: int = 10) -> str:
    noun = "role" if new_count == 1 else "roles"
    lines = [f"## Germany CS Jobs Digest — {new_count} new suitable {noun}", ""]
    if not jobs:
        return "\n".join(lines + ["No suitable Werkstudent or entry-level tech roles are currently stored."])
    for index, job in enumerate(jobs[:limit], 1):
        lines.append(f"{index}. **[{job['title']}]({job['url']})** — {job['company']}")
        lines.append(f"   {job['location']} · {job['role_type']} · **{job['score']}/100** · {', '.join(job['reasons'])}")
    lines.extend(["", "Open the local dashboard with: `python3 -m jobs_agent serve`"]) 
    return "\n".join(lines)


def serve(store_path: str | Path, host: str = "127.0.0.1", port: int = 8787) -> None:
    store = JobStore(store_path)

    class Handler(BaseHTTPRequestHandler):
        def _redirect(self) -> None:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/")
            self.end_headers()

        def do_GET(self) -> None:
            if urlparse(self.path).path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = render_dashboard(store.list_jobs()).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/refresh":
                store.upsert(fetch_all())
                self._redirect()
                return
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "status":
                try:
                    store.set_status(parts[1], parts[2])
                except ValueError:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return
                self._redirect()
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

    print(f"Dashboard: http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
