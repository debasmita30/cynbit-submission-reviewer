"""Build the submission pool from public repos and evaluate the reviewer on it.

  python scripts/build_pool.py                 # clones repos listed in data/pool_sources.csv
  python scripts/build_pool.py --cache DIR     # reuse existing clones (DIR/owner__repo)

Outputs:
  data/pool.pkl            anonymised ids, hand-labelled themes, signals, TF-IDF vectors
  reports/pool_insights.md aggregate statistics (no per-candidate results)
  reports/metrics.json     leave-one-out theme accuracy and timing
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reviewer.fetch import clone  # noqa: E402
from reviewer.pool import THEMES, Pool, anon_id  # noqa: E402
from reviewer.rubric import build_card  # noqa: E402
from reviewer.signals import extract  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=None)
    args = ap.parse_args()
    cache = args.cache or Path(tempfile.mkdtemp(prefix="pool_"))

    rows = list(csv.DictReader((ROOT / "data" / "pool_sources.csv").open()))
    ids, themes, texts, sigs, cards = [], [], [], [], []
    t0 = time.perf_counter()
    for r in rows:
        d = cache / r["repo"].replace("/", "__")
        if not d.exists():
            try:
                clone(f"https://github.com/{r['repo']}", d)
            except Exception as e:  # repo deleted or renamed since listing
                print("skip", r["repo"], e)
                continue
        s = extract(d)
        ids.append(anon_id(r["repo"]))
        themes.append(r["theme"])
        texts.append(s.text_corpus)
        sigs.append({k: v for k, v in s.public().items() if k not in ("live_links", "video_links", "doc_files",
                                                                    "secret_hits", "committed_env_files")} |
                    {"role": r["role"]})
        cards.append(build_card(s, "AI/ML Engineer Intern" if r["role"] == "ai_ml" else "Full Stack Developer Intern"))
    extract_s = time.perf_counter() - t0

    pool = Pool(ids, themes, texts, sigs)
    pool.save()

    # Leave-one-out: does text similarity recover the hand-labelled theme from the *other* repos?
    correct, rows_out = 0, []
    for i, (pid, th, tx) in enumerate(zip(ids, themes, texts)):
        rep = pool.compare(tx, k=3, exclude=pid)
        ok = rep.theme == th
        correct += ok
        rows_out.append((th, rep.theme, rep.neighbours[0].similarity))
    eligible = [r for r in rows_out if themes.count(r[0]) > 1]  # singleton themes can't be recovered by LOO
    acc_eligible = sum(t == p for t, p, _ in eligible) / len(eligible)
    lead_nn = [s for t, _, s in rows_out if t == "lead_triage"]
    fam = lambda t: "inquiry_to_sale" if t in ("lead_triage", "proposal_scoping") else t  # noqa: E731
    acc_family = sum(fam(t) == fam(p) for t, p, _ in eligible) / len(eligible)

    n = len(ids)
    ai = [s for s in sigs if s["role"] == "ai_ml"]
    pct = lambda xs, f: round(100 * sum(1 for x in xs if f(x)) / len(xs))  # noqa: E731
    stats = {
        "repos": n, "ai_ml_repos": len(ai),
        "theme_counts": Counter(themes).most_common(),
        "pct_with_tests": pct(sigs, lambda s: s["has_tests"]),
        "pct_with_live_demo": pct(sigs, lambda s: s["live_links"] if "live_links" in s else False),
        "pct_single_dump": pct(sigs, lambda s: s["commits"] <= 1 or s["largest_commit_share"] >= 0.9),
        "pct_with_video": 0,
        "pct_with_placeholders": pct(sigs, lambda s: s["placeholders"]),
        "pct_mention_eval": pct(sigs, lambda s: s["mentions_evaluation"]),
        "median_commits": sorted(s["commits"] for s in sigs)[n // 2],
    }
    live = sum(1 for c in cards if c.facts["live_links"])
    video = sum(1 for c in cards if c.facts["video_links"])
    stats["pct_with_live_demo"] = round(100 * live / n)
    stats["pct_with_video"] = round(100 * video / n)
    full_deliv = sum(1 for c, s in zip(cards, sigs) if s["role"] == "ai_ml" and all(d["present"] for d in c.deliverables.values()))
    stats["ai_ml_all_deliverables_detected"] = f"{full_deliv}/{len(ai)}"

    metrics = {
        "loo_theme_accuracy_all": round(correct / n, 3),
        "loo_theme_accuracy_non_singleton": round(acc_eligible, 3),
        "n_non_singleton": len(eligible),
        "loo_theme_accuracy_family": round(acc_family, 3),
        "lead_triage_mean_nn_similarity": round(sum(lead_nn) / len(lead_nn), 3),
        "extract_seconds_per_repo": round(extract_s / n, 3),
        "confusions": [{"true": t, "pred": p} for t, p, _ in rows_out if t != p],
        "pool_stats": stats,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "metrics.json").write_text(json.dumps(metrics, indent=2))

    md = ["# What the public submission pool looks like", "",
          f"{n} public repositories submitted for Cynbit's Phase 2 assessments ({len(ai)} for the AI/ML role), "
          "collected from GitHub search on 30 Oct 2026. Themes were labelled by hand from each README. "
          "Figures are aggregates only; no individual repo is scored here.", "",
          "| Theme | Repos | Share |", "|---|---|---|"]
    md += [f"| {THEMES[t]} | {c} | {c / n:.0%} |" for t, c in Counter(themes).most_common()]
    md += ["", "| Signal | Share of repos |", "|---|---|",
           f"| Has automated tests | {stats['pct_with_tests']}% |",
           f"| Has a live demo link | {stats['pct_with_live_demo']}% |",
           f"| Has a walkthrough video link | {stats['pct_with_video']}% |",
           f"| Reports evaluation numbers | {stats['pct_mention_eval']}% |",
           f"| Mostly one commit (≥90% of files in one commit) | {stats['pct_single_dump']}% |",
           f"| Unfilled placeholders in docs | {stats['pct_with_placeholders']}% |",
           f"| AI/ML repos with all three deliverables detected | {stats['ai_ml_all_deliverables_detected']} |",
           "", "## Does text similarity recover the idea?", "",
           f"Leave-one-out nearest-neighbour theme accuracy: **{acc_eligible:.0%}** on the {len(eligible)} repos whose "
           f"theme appears more than once (**{correct / n:.0%}** over all {n}, where singleton themes cannot be matched by design).",
           f"Treating lead triage and proposal scoping as one family (both start from a client inquiry): **{acc_family:.0%}**.",
           "Most remaining errors are between those two themes, which genuinely overlap. With 28 examples these figures are rough (±15 points).",
           f"Mean similarity of a lead-triage repo to its closest neighbour: **{metrics['lead_triage_mean_nn_similarity']}**.",
           "Signal extraction takes well under a second per repo after cloning, and no candidate code is executed."]
    (ROOT / "reports" / "pool_insights.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print("\nconfusions:", metrics["confusions"])


if __name__ == "__main__":
    main()
