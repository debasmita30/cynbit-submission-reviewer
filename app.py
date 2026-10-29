"""Submission Review Assistant for Cynbit: paste a repo link, get a reviewer card.

Run:  streamlit run app.py
"""

import html
import json
import shutil
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from reviewer.fetch import clone, parse_github_url
from reviewer.pool import THEMES
from reviewer.report_card import render_html
from reviewer.review import get_pool, review_path
from reviewer.rubric import BRIEFS

ROOT = Path(__file__).parent
st.set_page_config(page_title="Submission Review Assistant", page_icon="◎", layout="wide")


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
.hero { position: relative; overflow: hidden; border-radius: 18px; padding: 28px 30px; margin-bottom: 18px;
  background: linear-gradient(120deg, #4f46e5, #7c3aed, #db2777, #4f46e5); background-size: 300% 300%;
  animation: drift 12s ease infinite; color: #fff; }
.hero h1 { margin: 0; font-size: 2.1rem; font-weight: 800; letter-spacing: -0.02em; color: #fff; }
.hero p { margin: 6px 0 0; opacity: .9; max-width: 760px; }
.hero .orb { position: absolute; border-radius: 50%; background: rgba(255,255,255,.12); animation: float 9s ease-in-out infinite; }
@keyframes drift { 0% {background-position: 0% 50%} 50% {background-position: 100% 50%} 100% {background-position: 0% 50%} }
@keyframes float { 0%,100% {transform: translateY(0)} 50% {transform: translateY(-14px)} }
@keyframes rise { from {opacity: 0; transform: translateY(14px)} to {opacity: 1; transform: none} }
@keyframes fill { from {stroke-dashoffset: 327} }
@keyframes grow { from {width: 0} }
.card { border: 1px solid rgba(128,128,128,.22); border-radius: 14px; padding: 16px 18px; margin-bottom: 14px;
  background: rgba(128,128,128,.05); animation: rise .55s ease both; }
.card h4 { margin: 0 0 10px; font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; opacity: .65; }
.d1 { animation-delay: .05s } .d2 { animation-delay: .15s } .d3 { animation-delay: .25s } .d4 { animation-delay: .35s }
.ring-wrap { display: flex; align-items: center; gap: 22px; }
.ring text { font-weight: 800; }
.ring .val { animation: fill 1.3s cubic-bezier(.2,.8,.2,1) both; transform: rotate(-90deg); transform-origin: 60px 60px; }
.kpi { font-size: 1.6rem; font-weight: 800; line-height: 1.1; }
.kpi-l { font-size: .78rem; opacity: .65; }
.row { display: grid; grid-template-columns: 1fr 34% 52px; align-items: center; gap: 12px; padding: 6px 0;
  border-bottom: 1px dashed rgba(128,128,128,.2); font-size: .92rem; }
.row:last-child { border-bottom: none; }
.row.two { grid-template-columns: 1fr auto; }
.row.nb { grid-template-columns: 90px 1fr 30%; }
.row > .kpi-l:last-child { text-align: right; }
.repo { font-size: 1.05rem; font-weight: 700; word-break: break-word; }
.bar { width: 100%; height: 8px; border-radius: 6px; background: rgba(128,128,128,.2); overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, #6366f1, #a855f7);
  animation: grow 1s ease both; }
.pill { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .8rem; margin: 3px 4px 3px 0;
  border: 1px solid rgba(128,128,128,.3); }
.ok { color: #16a34a; } .no { color: #dc2626; }
.flag { border-left: 3px solid #f59e0b; padding: 6px 10px; margin: 6px 0; border-radius: 4px; background: rgba(245,158,11,.08); }
.q { padding: 6px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="orb" style="width:180px;height:180px;right:-40px;top:-60px"></div>
  <div class="orb" style="width:90px;height:90px;right:160px;bottom:-30px;animation-delay:-3s"></div>
  <h1>Submission Review Assistant</h1>
  <p>Paste any public GitHub repo. In seconds you get a review card: deliverables against the brief,
  whether it runs, red flags, how it compares with earlier submissions, and questions for the interview.
  It never runs the candidate's code and never makes the decision.</p>
</div>
""", unsafe_allow_html=True)


def ring(score: int) -> str:
    color = "#16a34a" if score >= 75 else "#f59e0b" if score >= 45 else "#dc2626"
    off = 327 * (1 - score / 100)
    return (f"<svg class='ring' width='120' height='120' viewBox='0 0 120 120'>"
            f"<circle cx='60' cy='60' r='52' fill='none' stroke='rgba(128,128,128,.2)' stroke-width='11'/>"
            f"<circle class='val' cx='60' cy='60' r='52' fill='none' stroke='{color}' stroke-width='11' "
            f"stroke-linecap='round' stroke-dasharray='327' stroke-dashoffset='{off:.1f}'/>"
            f"<text x='60' y='58' text-anchor='middle' font-size='28' fill='{color}'>{score}</text>"
            f"<text x='60' y='78' text-anchor='middle' font-size='11' fill='gray'>/ 100</text></svg>")


def e(x) -> str:
    return html.escape(str(x))


tab_review, tab_pool, tab_how = st.tabs(["Review a repo", "Submission pool", "How it works"])

DEMOS = {
    "This project": "debasmita30/cynbit-submission-reviewer",
    "karpathy/micrograd": "karpathy/micrograd",
    "streamlit/llm-examples": "streamlit/llm-examples",
    "pallets/click": "pallets/click",
}

with tab_review:
    st.markdown("<div class='kpi-l' style='margin-bottom:6px'>Try a demo repo</div>", unsafe_allow_html=True)
    demo_cols = st.columns(len(DEMOS))
    for col, (label, slug) in zip(demo_cols, DEMOS.items()):
        if col.button(label, key=f"demo_{slug}", width="stretch"):
            st.session_state["url_in"] = slug
            st.session_state["auto_run"] = True

    with st.form("f"):
        c1, c2 = st.columns([3, 1])
        url = c1.text_input("Public GitHub repo URL", key="url_in",
                            placeholder="https://github.com/owner/repo  or  owner/repo")
        role = c2.selectbox("Role brief", list(BRIEFS))
        go = st.form_submit_button("Review repo", type="primary", width="stretch")
    go = go or st.session_state.pop("auto_run", False)

    if go and url.strip():
        try:
            owner, repo = parse_github_url(url)
        except ValueError as err:
            st.error(str(err))
            st.stop()
        r, path = None, None
        with st.status(f"Reviewing {owner}/{repo}", expanded=True) as status:
            try:
                t = time.perf_counter()
                st.write("Cloning repository and history…")
                path = clone(f"https://github.com/{owner}/{repo}")
                st.write(f"Cloned in {time.perf_counter() - t:.1f}s. Reading files, docs and commits…")
                r = review_path(path, role, f"{owner}/{repo}")
                r["repo"] = f"{owner}/{repo}"
                st.write("Checking the brief, scanning for red flags, comparing with the submission pool…")
                status.update(label=f"Review ready · {owner}/{repo}", state="complete", expanded=False)
            except Exception as err:
                status.update(label="Review failed", state="error")
                st.error(str(err))
            finally:
                if path is not None:
                    shutil.rmtree(path.parent, ignore_errors=True)
        if r is None:
            st.stop()
        st.session_state["last"] = r

    r = st.session_state.get("last")
    if r:
        f = r["facts"]
        idea = r.get("idea")
        top = st.columns([1.3, 1, 1, 1])
        top[0].markdown(f"<div class='card d1'><h4>Completeness</h4><div class='ring-wrap'>{ring(r['completeness'])}"
                        f"<div><div class='repo'>{e(r.get('repo', ''))}</div><div class='kpi-l'>{e(r['role'])}</div>"
                        f"</div></div></div>", unsafe_allow_html=True)
        top[1].markdown(f"<div class='card d2'><h4>Red flags</h4><div class='kpi {'no' if r['red_flags'] else 'ok'}'>"
                        f"{len(r['red_flags'])}</div><div class='kpi-l'>things to check by hand</div></div>",
                        unsafe_allow_html=True)
        top[2].markdown(f"<div class='card d3'><h4>History</h4><div class='kpi'>{f['commits']} commit{'s' if f['commits'] != 1 else ''}</div>"
                        f"<div class='kpi-l'>over {f['active_days']} day(s) · {f['code_lines']:,} lines of code</div></div>",
                        unsafe_allow_html=True)
        if idea:
            top[3].markdown(f"<div class='card d4'><h4>Idea</h4><div class='kpi' style='font-size:1.1rem'>"
                            f"{e(idea['theme_name'])}</div><div class='kpi-l'>{idea['theme_share']:.0%} of earlier "
                            f"submissions share this theme</div></div>", unsafe_allow_html=True)

        left, right = st.columns(2)
        with left:
            deliv = "".join(
                f"<div class='row two'><span class='{'ok' if d['present'] else 'no'}'>{'✓' if d['present'] else '✗'} "
                f"{e(d['label'])}</span><span class='kpi-l'>{e(', '.join(d['evidence'])[:60])}</span></div>"
                for d in r["deliverables"].values())
            st.markdown(f"<div class='card d1'><h4>Deliverables in the brief</h4>{deliv}</div>", unsafe_allow_html=True)
            rows = "".join(
                f"<div class='row'><span>{'✓' if c['passed'] else '·'} {e(c['check'])}</span>"
                f"<span class='bar'><i style='width:{100 * c['points'] / c['of']:.0f}%;animation-delay:{0.08 * k:.2f}s'></i></span>"
                f"<span class='kpi-l'>{c['points']}/{c['of']}</span></div>" for k, c in enumerate(r["checks"]))
            st.markdown(f"<div class='card d2'><h4>Checks</h4>{rows}</div>", unsafe_allow_html=True)
            links = f["live_links"] + f["video_links"]
            if links:
                st.markdown("<div class='card d3'><h4>Links found</h4>" + "".join(
                    f"<a class='pill' href='{e(l)}' target='_blank'>{e(l[:60])}</a>" for l in links) + "</div>",
                    unsafe_allow_html=True)
        with right:
            flags = "".join(f"<div class='flag'>{e(x)}</div>" for x in r["red_flags"]) or \
                "<div class='ok'>None found.</div>"
            st.markdown(f"<div class='card d1'><h4>Red flags</h4>{flags}</div>", unsafe_allow_html=True)
            pills = "".join(f"<span class='pill'>{e(s)}</span>" for s in r["strengths"]) or "—"
            st.markdown(f"<div class='card d2'><h4>Strengths</h4>{pills}</div>", unsafe_allow_html=True)
            qs = "".join(f"<div class='q'>{i}. {e(q)}</div>" for i, q in enumerate(r["questions"], 1))
            st.markdown(f"<div class='card d3'><h4>Questions for the interview</h4>{qs}</div>", unsafe_allow_html=True)
            if idea:
                nb = "".join(f"<div class='row nb'><span>{e(n['id'])}</span><span class='kpi-l'>"
                             f"{e(THEMES.get(n['theme'], n['theme']))}</span><span class='bar'><i style='width:"
                             f"{max(0, n['similarity']) * 100:.0f}%'></i></span></div>" for n in idea["neighbours"])
                st.markdown(f"<div class='card d4'><h4>Closest earlier submissions (similarity)</h4>{nb}</div>",
                            unsafe_allow_html=True)

        d1, d2 = st.columns(2)
        name = r.get("repo", "repo").replace("/", "_")
        d1.download_button("Download review card (HTML)", render_html(r), f"review_{name}.html", "text/html",
                           width="stretch")
        d2.download_button("Download raw JSON", json.dumps(r, indent=2, default=str), f"review_{name}.json",
                           "application/json", width="stretch")
    elif not go:
        st.info("Paste a public GitHub link above. Try your own project, or any repo you know.")

with tab_pool:
    pool = get_pool()
    if pool:
        counts = pool.theme_counts()
        st.subheader("What earlier submissions chose")
        st.bar_chart(pd.Series({THEMES[k]: v for k, v in counts.items()}).sort_values(), horizontal=True,
                     color="#7c3aed")
    md = ROOT / "reports" / "pool_insights.md"
    if md.exists():
        st.markdown(md.read_text(encoding="utf-8"))

with tab_how:
    st.markdown((ROOT / "docs" / "how_it_works.md").read_text(encoding="utf-8"))
