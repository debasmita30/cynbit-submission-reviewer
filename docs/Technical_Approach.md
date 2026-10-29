# Technical Approach: Submission Review Assistant

Companion to the [AI Opportunity Report](AI_Opportunity_Report.md). Author: [Debasmita Chatterjee]

## Goal and constraints

**Input.** A public GitHub repo URL and a role brief.

**Output.** A reviewer card: deliverables found, readiness checks, red flags, closest earlier submissions, and interview questions.

**Constraints I set myself:**

- **Never execute candidate code.** A repo is untrusted input.
- **Every finding must show its evidence.** A reviewer has to be able to see why the tool says something.
- **It must work without an API key or GPU,** so it costs nothing per review and can run on a free Streamlit instance.
- **Be honest about what static analysis cannot judge.** The quality of the thinking is the reviewer's job.

## Architecture

```
repo URL ─► git clone (full history, blobs > 500 KB skipped)
              │
              ├─► signals.py   file tree · README/docs text · deps · tests · CI · Docker
              │                live/video links · .env files · key-shaped strings (dummy filter)
              │                placeholders · git history (commits, active days, biggest-commit share)
              │
              ├─► pool.py      TF-IDF over README + docs ─► 3 nearest earlier submissions
              │                ─► theme vote, theme crowding, novelty = 1 − max similarity
              │
              └─► rubric.py    role brief ─► deliverables · weighted checks (0–100)
                               red flags · strengths · interview questions
                                     │
                         review.py ─► card (JSON) ─► app.py (Streamlit) / any other UI
```

`scripts/build_pool.py` builds the comparison pool from `data/pool_sources.csv` (29 public repos with hand-labelled themes) and writes `reports/pool_insights.md` and `reports/metrics.json`.

## Data

**Source.** I found 29 public repos submitted for Cynbit's Phase 2 assessments through search on 30 October 2026: 25 for the AI/ML role, 3 full-stack and 1 backend. I labelled each repo's theme by hand from its README, using 7 themes.

**What is stored.** `data/pool.pkl` keeps anonymised ids (a hash of the repo name), themes, derived signals and TF-IDF vectors. It keeps no README text. The vectoriser uses `min_df=2`, so a word that appears in only one repo, such as a candidate's name, never enters the vocabulary. The source list is in the repo so the pool can be rebuilt; it contains only public URLs and neutral theme labels.

**Why this matters.** Nearly every submission I looked at evaluates on synthetic data, because Cynbit's internal data is private. This problem has real data in public, so the numbers below are measured on real submissions.

## Methods and choices

### 1. Signals (deterministic)

Regexes and file-tree rules, chosen because they are instant, free and explainable.

**Tests** count if there is a `tests/` folder, a `test_*.py` or `*_test.py` file, or a `*.test|spec.(js|ts)` file.

**Live links** match the common free hosts (streamlit.app, vercel.app, netlify.app, onrender.com, hf.space, and similar) plus Colab.

**Secrets** are matched by the formats of OpenAI, Anthropic, Google, Groq, GitHub and AWS keys. Only the kind of key and the file path are stored, never the value.
- My first version flagged `sk-test-…` in someone's test file. That was a deliberate dummy, so I added a dummy-value filter and a regression test. It is a small example of why checking against real data matters.

**History** records the number of commits, the number of distinct days with commits, and the share of all files that the single largest commit added.
- ≥ 90% from one commit is flagged, because it is the cheapest signal that a project was pasted in rather than built up.
- It is phrased as a question for the interview, not an accusation. Plenty of people squash commits or work locally first.

### 2. Brief matching

Each role has its deliverables and a filename/heading pattern for each. For AI/ML, the opportunity report, the technical approach report and the PoC (any code files) count as present if a doc file name or a README/doc heading matches.

On the 25 AI/ML repos, all three were detected in 23. I checked the 2 misses by hand: both repos genuinely lack that document. I have not hand-checked every positive, so precision is unmeasured. That goes into the phase-2 evaluation.

### 3. Idea similarity

TF-IDF on word 1–2-grams, with English stop words removed, sublinear term frequency, `min_df=2` and `max_df=0.9`. The tool takes the 3 nearest neighbours by cosine similarity and runs a similarity-weighted vote for the theme. "Theme crowding" is that theme's share of the pool, and "novelty" is 1 minus the maximum similarity.

I considered three alternatives:

| Option | Why not (yet) |
|---|---|
| Sentence embeddings (e.g. a small multilingual model) | Would likely do better on paraphrase, but it adds a 100 MB+ model download to a free deployment. Next step. |
| LLM theme labelling | The most accurate, but it needs a key and costs per review. A good option for the paid internal version. |
| Clustering (k-means) | Clusters need names anyway, and hand-labelled themes are easier to read for a reviewer. |

### 4. Rubric

A weighted checklist: deliverables 30, run instructions 15, dependency file 10, tests 10, live demo 10, reports evaluation 10, limitations 5, history 5, substantial README 5.

The weights reflect what saves a reviewer time, not what makes a good engineer. That is why the score is called **completeness**.

Interview questions are chosen from the gaps:
- no tests → "how did you check it works?";
- reported metrics → "on what data?";
- one-commit history → "show me how it evolved";
- crowded theme → "why this opportunity?".

## Evaluation

| What | Result |
|---|---|
| Theme recovery, leave-one-out nearest neighbour (28 repos whose theme appears at least twice) | 57% |
| Same, treating lead triage and proposal scoping as one family | 71% |
| Deliverable detection on 25 AI/ML repos | 23 detected; the 2 misses confirmed as genuine gaps by hand |
| Secret scan | 1 false positive found on the real pool, fixed, regression-tested |
| Speed | well under a second per repo after cloning; cloning takes a few seconds |
| Tests | 6 passing (built repos for good/bad cases, dummy-key filter, URL parsing, similarity) |

**How to read the 57%.** It is modest, and with 28 examples it is only accurate to about ±15 points. Most errors fall between lead triage and proposal scoping, and those two genuinely overlap: both take a client inquiry and produce something for sales. That is why the card shows the three nearest submissions and their similarity, not just a label.

I tried other settings: README-only text, different `max_df`, and k = 1/3/5. They ranged from 50% to 71% with no consistent winner. Choosing the best of those would have been tuning to 28 examples, so I kept the defaults.

## What I would build next

1. **Sandboxed execution.** Docker with no network after dependency install, CPU/time limits and a read-only source folder. Install, run the tests, start the app, take a screenshot. That answers "does it actually run", which static analysis cannot.
2. **LLM grader for the written reports.** A rubric covering problem understanding, evidence, trade-offs and clarity. Calibrate it on 30–50 submissions that Cynbit reviewers have scored (target: Spearman ≥ 0.6 with the human scores) before showing grades to anyone. Never use it to auto-reject.
3. **Embeddings + near-duplicate detection.** Embeddings for idea similarity, and MinHash over code files to catch reused code across candidates.
4. **Integration.** A webhook from the assessment form so a card is ready when a reviewer opens a submission, plus an export to whatever tracker the team uses.
5. **Studio version.** The same engine with learner-facing wording ("what to fix before you apply"), and a history check that powers the "verified proof" claim.

## Privacy and fairness

- **Public data only.** The tool only reads public repos. Per-candidate cards are for reviewers, and published statistics are aggregated and anonymised.
- **Retention.** For production, a retention period and deletion on request, in line with India's DPDP Rules.
- **Fair weighting.** A live-demo link favours candidates who know free hosting, and the history check penalises people who squash commits. Both carry low weight and appear as questions, not verdicts.
- **No ranking.** No score ranks people against each other.

## Limitations

- Static analysis can't tell whether code runs or whether the thinking is good.
- The theme labels are mine, made by one person.
- The pool is only what search surfaced; private and Drive submissions aren't in it.
- Only GitHub is supported, not Figma, Vercel or Drive links yet.
