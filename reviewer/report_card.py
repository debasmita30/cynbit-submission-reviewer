"""Render a reviewer card as a standalone, shareable HTML file."""

from __future__ import annotations

import html
from datetime import date

from reviewer.pool import THEMES


def _e(x) -> str:
    return html.escape(str(x))


def render_html(r: dict) -> str:
    score = r["completeness"]
    color = "#16a34a" if score >= 75 else "#d97706" if score >= 45 else "#dc2626"
    deliv = "".join(
        f"<li class='{'ok' if d['present'] else 'no'}'>{'✓' if d['present'] else '✗'} {_e(d['label'])}"
        f"{' <span>' + _e(', '.join(d['evidence'])) + '</span>' if d['evidence'] else ''}</li>"
        for d in r["deliverables"].values())
    checks = "".join(
        f"<tr><td>{_e(c['check'])}</td><td><div class='bar'><i style='width:{100 * c['points'] / c['of']:.0f}%'></i>"
        f"</div></td><td>{c['points']}/{c['of']}</td></tr>" for c in r["checks"])
    flags = "".join(f"<li>{_e(f)}</li>" for f in r["red_flags"]) or "<li class='none'>None found</li>"
    qs = "".join(f"<li>{_e(q)}</li>" for q in r["questions"])
    idea = ""
    if r.get("idea"):
        i = r["idea"]
        idea = (f"<h2>Idea</h2><p><b>{_e(i['theme_name'])}</b> — {i['theme_share']:.0%} of earlier submissions "
                f"share this theme. Novelty {i['novelty']:.2f}.</p><p class='muted'>Closest: "
                + ", ".join(f"{_e(n['id'])} ({_e(THEMES.get(n['theme'], n['theme']))}, {n['similarity']:.2f})"
                            for n in i["neighbours"]) + "</p>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review card · {_e(r.get('repo', 'repo'))}</title><style>
body{{font-family:Inter,system-ui,sans-serif;max-width:820px;margin:32px auto;padding:0 16px;color:#111827;background:#fafafa}}
header{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #e5e7eb;padding-bottom:12px}}
.score{{font-size:44px;font-weight:800;color:{color}}} .muted{{color:#6b7280;font-size:14px}}
h2{{font-size:18px;margin-top:28px}} ul{{padding-left:0;list-style:none}} li{{padding:6px 0;border-bottom:1px solid #f0f0f0}}
li.ok{{color:#15803d}} li.no{{color:#b91c1c}} li span{{color:#6b7280;font-size:13px}} li.none{{color:#15803d}}
table{{width:100%;border-collapse:collapse}} td{{padding:5px 4px;font-size:14px}} td:nth-child(2){{width:40%}}
.bar{{background:#e5e7eb;border-radius:6px;height:8px}} .bar i{{display:block;height:8px;border-radius:6px;background:#6366f1}}
ol li{{border:none}} footer{{margin-top:32px;font-size:12px;color:#9ca3af}}
</style></head><body>
<header><div><h1 style="margin:0">{_e(r.get('repo', 'Submission'))}</h1>
<div class="muted">{_e(r['role'])} · {r['facts']['commits']} commits over {r['facts']['active_days']} day(s) · {date.today():%d %b %Y}</div></div>
<div class="score">{score}<span class="muted">/100</span></div></header>
<h2>Deliverables</h2><ul>{deliv}</ul>
<h2>Checks</h2><table>{checks}</table>
<h2>Red flags</h2><ul>{flags}</ul>
<h2>Strengths</h2><p>{_e(', '.join(r['strengths']) or '—')}</p>
{idea}
<h2>Questions for the interview</h2><ol>{qs}</ol>
<footer>Completeness measures how much of the brief is present and runnable. It is not a quality grade and not a hiring decision.</footer>
</body></html>"""
