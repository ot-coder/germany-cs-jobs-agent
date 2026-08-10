from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from .core import Job


STATIC_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Germany Student Jobs Agent</title><style>
:root{color-scheme:dark;--bg:#080c13;--card:#111925;--muted:#94a3b8;--line:#263349;--accent:#5eead4;--blue:#60a5fa}*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at 15% 0,#10243b,#080c13 46%);color:#e8eef7;font:15px system-ui,-apple-system,sans-serif;min-height:100vh}
main{max-width:1200px;margin:auto;padding:42px 22px 70px}.top{display:flex;justify-content:space-between;align-items:end;gap:20px;flex-wrap:wrap}
h1{font-size:clamp(34px,6vw,62px);line-height:.95;margin:0;letter-spacing:-.04em}.sub{color:var(--muted);max-width:650px}.updated{color:var(--muted);font-size:12px}
.controls{display:grid;grid-template-columns:minmax(220px,1fr) auto auto;gap:10px;margin:14px 0}input,select{background:#111925;border:1px solid var(--line);border-radius:12px;color:#e8eef7;padding:12px 14px;font:inherit}
.tabs{display:flex;gap:8px;margin-top:28px;flex-wrap:wrap}.tab{font-weight:750;padding:11px 16px}.tab.active{background:#0f766e;border-color:#2dd4bf;color:#fff}
.stats{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:18px}.pill{border:1px solid var(--line);background:#0f1723;padding:7px 11px;border-radius:999px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:15px}.card{background:#111925ed;border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 14px 38px #0005;transition:.18s}.card:hover{transform:translateY(-2px);border-color:#405575}
.row{display:flex;justify-content:space-between;gap:15px}.title{font-size:20px;font-weight:780;text-decoration:none;color:#f3f7fc}.company{color:var(--accent);font-weight:700;margin-top:5px}.score{font-size:29px;font-weight:850;color:var(--accent)}
.meta,.reasons{color:var(--muted);font-size:13px;line-height:1.5}.actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:16px}button,.button{background:#172337;color:#e8eef7;border:1px solid var(--line);border-radius:10px;padding:9px 11px;cursor:pointer;text-decoration:none}button:hover,.button:hover{border-color:var(--blue)}button.active{background:#0f766e;border-color:#2dd4bf}.empty{padding:60px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:18px}@media(max-width:650px){.controls{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
</style></head><body><main>
<div class="top"><div><h1>Germany Student Jobs</h1><p class="sub">Switch between computer-science opportunities and flexible part-time or minijob work across Germany.</p></div><div class="updated" id="updated"></div></div>
<div class="tabs" aria-label="Job category"><button class="tab active" data-category="cs" onclick="setCategory('cs')">CS & Tech</button><button class="tab" data-category="part-time" onclick="setCategory('part-time')">Part-time & Minijob</button></div>
<div class="controls"><input id="search" type="search" placeholder="Search title, company, city…"><select id="type"><option value="">All role types</option><option value="werkstudent">Werkstudent</option><option value="entry-level">Entry level</option><option value="part-time">Part-time</option><option value="minijob">Minijob</option></select><select id="status"><option value="">All statuses</option><option value="new">New</option><option value="saved">Saved</option><option value="applied">Applied</option><option value="dismissed">Dismissed</option></select></div>
<div class="stats" id="stats"></div><section class="grid" id="jobs"><div class="empty">Loading live roles…</div></section>
</main><script>
const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const getState=id=>localStorage.getItem('job:'+id)||'new';
function setState(id,state){localStorage.setItem('job:'+id,state);render()}
let all=[],activeCategory='cs';
function setCategory(category){activeCategory=category;document.querySelector('#type').value='';document.querySelectorAll('.tab').forEach(button=>button.classList.toggle('active',button.dataset.category===category));render()}
function render(){const q=document.querySelector('#search').value.toLowerCase(),type=document.querySelector('#type').value,status=document.querySelector('#status').value;
 const categoryJobs=all.filter(j=>(j.category||'cs')===activeCategory);
 const rows=categoryJobs.filter(j=>(!q||`${j.title} ${j.company} ${j.location}`.toLowerCase().includes(q))&&(!type||j.role_type===type)&&(!status||getState(j.id)===status));
 document.querySelector('#stats').innerHTML=`<span class="pill">${rows.length} shown</span><span class="pill">${categoryJobs.length} in this category</span><span class="pill">${categoryJobs.filter(j=>getState(j.id)==='saved').length} saved</span><span class="pill">${categoryJobs.filter(j=>getState(j.id)==='applied').length} applied</span>`;
 document.querySelector('#jobs').innerHTML=rows.length?rows.map(j=>{const st=getState(j.id),label=(j.category||'cs')==='cs'?'CS & Tech':'Part-time & Minijob';return `<article class="card"><div class="row"><div><a class="title" href="${esc(j.url)}" target="_blank" rel="noreferrer">${esc(j.title)}</a><div class="company">${esc(j.company)}</div></div><div class="score">${j.score}</div></div><p class="meta">${esc(j.location)} · ${esc(label)} · ${esc(j.role_type)} · ${esc(j.source)} · ${esc(st)}</p><p class="reasons">${j.reasons.map(esc).join(' · ')}</p><div class="actions">${['saved','applied','dismissed'].map(s=>`<button class="${st===s?'active':''}" onclick="setState('${esc(j.id)}','${s}')">${s[0].toUpperCase()+s.slice(1)}</button>`).join('')}<a class="button" href="${esc(j.url)}" target="_blank" rel="noreferrer">Apply ↗</a></div></article>`}).join(''):'<div class="empty">No jobs match these filters.</div>'}
for(const id of ['search','type','status'])document.querySelector('#'+id).addEventListener(id==='search'?'input':'change',render);
fetch('./jobs.json?'+Date.now()).then(r=>r.json()).then(data=>{all=data.sort((a,b)=>b.score-a.score);document.querySelector('#updated').textContent=`Updated ${new Date(document.lastModified).toLocaleString()}`;render()}).catch(()=>document.querySelector('#jobs').innerHTML='<div class="empty">Could not load jobs. Please refresh.</div>');
</script></body></html>'''


def _load_previous(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(item.get("id")): item for item in value if isinstance(item, dict) and item.get("id")}


def publish_jobs(jobs: list[Job], docs_dir: str | Path) -> list[Job]:
    docs = Path(docs_dir)
    docs.mkdir(parents=True, exist_ok=True)
    jobs_path = docs / "jobs.json"
    previous = _load_previous(jobs_path)
    exported = []
    new_jobs = []
    for job in jobs:
        item = asdict(job)
        if job.id in previous:
            item["first_seen_at"] = previous[job.id].get("first_seen_at", item["first_seen_at"])
        else:
            new_jobs.append(job)
        exported.append(item)
    exported.sort(key=lambda item: (-int(item["score"]), item["title"].casefold()))
    jobs_path.write_text(json.dumps(exported, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (docs / "index.html").write_text(STATIC_HTML, encoding="utf-8")
    (docs / ".nojekyll").write_text("", encoding="utf-8")
    return new_jobs


def telegram_message(
    new_jobs: list[Job], site_url: str, limit: int = 8, total_jobs: int | None = None
) -> str:
    if not new_jobs:
        lines = ["✅ Germany Student Jobs: Daily scan complete", "", "No new suitable roles today."]
        if total_jobs is not None:
            noun = "match" if total_jobs == 1 else "matches"
            lines.append(f"The dashboard currently has {total_jobs} live {noun}.")
        lines.extend(["", f"Open dashboard: {site_url}"])
        return "\n".join(lines)
    noun = "role" if len(new_jobs) == 1 else "roles"
    lines = [f"Germany Student Jobs: {len(new_jobs)} new suitable {noun}", ""]
    for job in new_jobs[:limit]:
        category = "CS & Tech" if job.category == "cs" else "Part-time & Minijob"
        lines.extend([
            f"• {job.title}",
            f"  {category} · {job.company} · {job.location} · {job.score}/100",
            f"  {job.url}",
            "",
        ])
    if len(new_jobs) > limit:
        lines.append(f"+ {len(new_jobs) - limit} more")
    lines.append(f"Open dashboard: {site_url}")
    return "\n".join(lines)
