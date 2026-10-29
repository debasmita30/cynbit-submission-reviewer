"""Turn signals into a reviewer card: deliverables, readiness checks, red flags, interview questions.

The score is a *completeness* score, not a hiring score. It tells a reviewer
how much of the brief is present and runnable, so their time goes on judging
the thinking, which no checklist can do.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from reviewer.pool import IdeaReport
from reviewer.signals import Signals

BRIEFS = {
    "AI/ML Engineer Intern": {
        "deliverables": {
            "opportunity_report": ("AI Opportunity Report", r"opportunit|industry analysis|use[- ]?cases?|ai[-_ ]?roadmap"),
            "technical_report": ("Technical Approach Report", r"technical|approach|architecture|system design|design doc"),
            "poc": ("Working PoC (app, API, notebook or script)", None),
        },
    },
    "Full Stack Developer Intern": {
        "deliverables": {
            "readme_plan": ("Write-up of the problem and solution", r"problem|solution|overview|feature"),
            "poc": ("Working application", None),
        },
    },
}

CHECKS = [  # (key, label, weight)
    ("deliverables", "All brief deliverables present", 30),
    ("run", "README explains how to run it", 15),
    ("deps", "Dependency file present", 10),
    ("tests", "Automated tests", 10),
    ("live", "Live demo link", 10),
    ("eval", "Reports results / evaluation", 10),
    ("limits", "Discusses limitations or trade-offs", 5),
    ("history", "Built over more than one commit", 5),
    ("readme", "README is substantial (300+ words)", 5),
]


@dataclass
class Card:
    role: str
    completeness: int
    deliverables: dict[str, dict]
    checks: list[dict]
    red_flags: list[str]
    strengths: list[str]
    questions: list[str]
    idea: dict | None = None
    facts: dict = field(default_factory=dict)


def _has_deliverable(pattern: str, s: Signals) -> list[str]:
    hits = [p for p in s.doc_files if re.search(pattern, p, re.I)]
    if not hits:  # also accept a clearly marked README/doc section
        heads = re.findall(r"^#{1,3} .*$", s.text_corpus, re.M)
        hits = [h.strip("# ").strip()[:60] for h in heads if re.search(pattern, h, re.I)][:1]
    return hits


def build_card(s: Signals, role: str = "AI/ML Engineer Intern", idea: IdeaReport | None = None) -> Card:
    brief = BRIEFS.get(role, BRIEFS["AI/ML Engineer Intern"])
    deliv = {}
    for key, (label, pat) in brief["deliverables"].items():
        if pat is None:
            ok = s.code_files > 0
            evidence = [f"{s.code_files} code files, {s.code_lines:,} lines"] if ok else []
        else:
            evidence = _has_deliverable(pat, s)
            ok = bool(evidence)
        deliv[key] = {"label": label, "present": ok, "evidence": evidence[:3]}
    n_ok = sum(d["present"] for d in deliv.values())

    passed = {
        "deliverables": n_ok == len(deliv),
        "run": s.has_run_instructions,
        "deps": s.has_dependency_file,
        "tests": s.has_tests,
        "live": bool(s.live_links),
        "eval": s.mentions_evaluation,
        "limits": s.mentions_limitations,
        "history": s.commits > 1 and s.largest_commit_share < 0.9,
        "readme": s.readme_words >= 300,
    }
    score = 0
    checks = []
    for key, label, w in CHECKS:
        pts = w if passed[key] else (round(w * n_ok / len(deliv)) if key == "deliverables" else 0)
        score += pts
        checks.append({"check": label, "passed": passed[key], "points": pts, "of": w})

    flags = []
    if s.secret_hits:
        flags.append(f"Possible committed secret ({', '.join(sorted({k for k, _ in s.secret_hits}))}) in "
                     f"{len(s.secret_hits)} file(s) — rotate the key and purge history")
    if s.committed_env_files:
        flags.append(f".env file committed: {', '.join(s.committed_env_files[:3])}")
    if s.junk_committed:
        flags.append(f"Build/vendor folders committed: {', '.join(s.junk_committed[:4])}")
    if s.placeholders:
        flags.append(f"Unfilled placeholders: {', '.join(s.placeholders)}")
    if s.commits <= 1 or s.largest_commit_share >= 0.9:
        flags.append(f"Most of the repo arrived in one commit ({s.largest_commit_share:.0%} of files) — "
                     "ask how it was built")
    if s.code_files == 0:
        flags.append("No code found")

    strengths = []
    if s.has_tests:
        strengths.append(f"{s.test_files} test file(s)")
    if s.has_ci:
        strengths.append("CI workflow")
    if s.live_links:
        strengths.append("Live demo")
    if s.video_links:
        strengths.append("Walkthrough video")
    if s.has_docker:
        strengths.append("Dockerised")
    if s.mentions_evaluation:
        strengths.append("Reports evaluation numbers")
    if s.active_days >= 2:
        strengths.append(f"Worked on across {s.active_days} days")

    q = []
    if idea and idea.theme_share >= 0.25:
        q.append(f"About {idea.theme_share:.0%} of submissions chose the same theme. What did you see that "
                 "made this the highest-value opportunity, and what did you rule out?")
    if not s.has_tests:
        q.append("How did you check that it works? Walk me through one case that failed while you were building it.")
    if s.mentions_evaluation:
        q.append("Your evaluation numbers: what data were they computed on, and why should I trust them on real data?")
    else:
        q.append("How would you measure whether this works once it's live? Which metric would you watch first?")
    if s.commits <= 1 or s.largest_commit_share >= 0.9:
        q.append("Show me how this evolved. What was the first version, and what did you change after testing it?")
    if not s.live_links:
        q.append("What would it take to put this in front of a real user next week?")
    q.append("If Cynbit gave you two weeks, what would you build next, and what would you cut?")

    return Card(role, min(100, score), deliv, checks, flags, strengths, q[:5],
                idea.__dict__ | {"neighbours": [n.__dict__ for n in idea.neighbours]} if idea else None,
                {"commits": s.commits, "active_days": s.active_days, "files": s.files, "code_lines": s.code_lines,
                 "languages": s.languages, "live_links": s.live_links, "video_links": s.video_links})
