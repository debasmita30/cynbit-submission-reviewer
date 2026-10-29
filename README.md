# Submission Review Assistant for Cynbit

AI/ML Engineer Intern assessment: *Identify an AI opportunity for Cynbit*. Author: [Your Name]

Live demo: [add your Streamlit link]

## The idea

41% of the public submissions for this assessment that I could find build the same thing: a lead-scoring or inquiry-triage tool. Meanwhile, Cynbit's reviewers have dozens of repos to read every hiring round. Cynbit Studio and BitElevate also promise AI evaluation and verified proof of project skills.

So I built the tool that sits in front of a reviewer. Paste a GitHub link and choose the role, and it shows:

- which deliverables from the brief are present;
- whether you could run the project;
- red flags: committed keys or `.env` files, leftover placeholders, a project that arrived in one commit;
- the earlier submissions it most resembles, and how crowded that idea already is;
- interview questions aimed at what is missing.

It reads the repo; it never runs the candidate's code, and it never decides who gets through.

Everything here is measured on **real data**: 29 public repos submitted for Cynbit's Phase 2 assessments, with themes labelled by hand.

## Documents

- [AI Opportunity Report](docs/AI_Opportunity_Report.md): Cynbit's situation, what the submission pool shows, the options I considered and why this one
- [Technical Approach](docs/Technical_Approach.md): architecture, data, model choices, evaluation, what I'd build next
- [Pool insights](reports/pool_insights.md): aggregate statistics across the 29 submissions (no individual scores)

## Results

| | |
|---|---|
| Submissions in the pool | 29 public repos (25 AI/ML) |
| Most common theme | lead / inquiry triage, 12 of 29 |
| Deliverable detection on AI/ML repos | 23 of 25 complete; the 2 misses checked by hand and genuinely missing |
| Idea recovery by nearest neighbour (leave-one-out) | 57%; 71% when lead triage and proposal tools count as one family |
| Secret scan | one false positive on real data (a dummy test key), fixed and regression-tested |
| Speed | under a second per repo after cloning |

The theme numbers come from 28 examples, so they are rough. The report explains why I did not tune them further.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

To rebuild the pool and metrics from the source list (this clones 29 public repos):

```bash
python scripts/build_pool.py
```

Tests: `pytest -q`

## Layout

```
reviewer/fetch.py     clone a public repo (history kept, large files skipped)
reviewer/signals.py   evidence from files, docs and git history; no code execution
reviewer/pool.py      TF-IDF similarity against the anonymised submission pool
reviewer/rubric.py    role briefs, completeness checks, red flags, interview questions
reviewer/review.py    URL in, reviewer card out
app.py                Streamlit interface
scripts/build_pool.py builds data/pool.pkl and reports/
data/pool_sources.csv the public repos and their hand-labelled themes
```

## Privacy

The tool only reads public repositories. The stored pool contains anonymised ids, themes, derived signals and TF-IDF vectors, but no README text, and words that appear in a single repo (such as names) are excluded from the vocabulary. The reports publish only aggregates.
