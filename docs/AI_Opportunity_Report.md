# AI Opportunity Report: Cynbit Technologies

AI/ML Engineer Intern assessment, October 2026.

## Summary

Most candidates for this role will build Cynbit a lead-scoring or inquiry-triage tool. I know because I checked: of 29 public repos submitted for Cynbit's Phase 2 assessments that I could find on GitHub, 12 (41%) do exactly that. Revio review analysis is next at six.

I chose something no one in that pool built, and that Cynbit is dealing with right now: **reviewing project submissions.**

Cynbit runs technical assessments for several roles at once, and each one produces a stack of GitHub repos, Figma files and Drive links. Its own products have the same need. Cynbit Studio advertises AI code evaluation and "verified proof" of skill. BitElevate says more than 1,000 learners have been certified through project work. Today a person has to open every repo, work out whether it matches the brief, whether it runs, and whether it is copied or generic.

My proof of concept is a **Submission Review Assistant**. Give it a repo link and a role, and in about a second after cloning it returns:

- which deliverables from the brief are present;
- whether a reviewer could run it;
- red flags such as committed API keys, `.env` files, leftover placeholders, or a whole project dropped in one commit;
- the earlier submissions it most resembles, and how crowded that idea already is;
- interview questions aimed at what is missing.

It never runs the candidate's code and never makes the decision.

## What Cynbit does, and where it is stretched

Cynbit is a roughly 20-person AI and software studio in Jaipur, founded in 2024. It has four service lines (AI automation, web/mobile, cloud, digital marketing), three SaaS products (Cynbit Studio, Revio, TenantEase) and a training programme (BitElevate).

The details that matter for this report:

- **It hires a lot, mostly interns.** Its jobs pages and Internshala listings show many open roles at once. This assessment alone accepts GitHub, Figma, Vercel and Drive links, plus "campaign plans", so several roles run in parallel. Each round means senior engineers reading dozens of repos, and that time comes out of client delivery.
- **Its education side runs on project evaluation.** Cynbit Studio's pitch is AI-evaluated coding missions, "AI Code Evaluation — quality feedback instead of output matching", and verified skill profiles. BitElevate promises industry projects and certification. Grading a single function is a solved problem; grading a whole project (does it meet the brief, is it the student's own, could someone run it) is not, and that is the harder half of what Studio sells.
- **Its brand is AI-first.** A studio that sells "autonomous agents" to others gains a lot from running visibly on its own AI internally.

## What the submission pool shows

I cloned the 29 public repos I could find via search and labelled each one's theme by hand from its README. Then I ran the tool over all of them. These are aggregates; no individual repo is scored in this report.

| Theme | Repos | Share |
|---|---|---|
| Lead / inquiry triage and scoring | 12 | 41% |
| Revio review sentiment and replies | 6 | 21% |
| Proposal and scoping assistants | 4 | 14% |
| TenantEase rent / dues prediction | 2 | 7% |
| BitElevate learner roadmaps | 2 | 7% |
| Delivery operations | 1 | 3% |
| Other (audit, portfolio) | 2 | 7% |

Some things a reviewer would want to know before opening each repo:

- 55% arrived mostly in one commit (90% or more of the files in a single commit).
- 28% include a live demo link, and none include a walkthrough video.
- 14% still contain unfilled placeholder text, such as a template username left in the clone instructions.
- 72% have some automated tests.
- 83% report evaluation numbers, almost always on synthetic data.

None of this says whether a candidate is good. It says where a reviewer's attention should go, and that is the point of the tool.

## Opportunities I considered

| Opportunity | Value to Cynbit | Can it be built from public data? | Already in the pool? |
|---|---|---|---|
| **Submission and project review assistant** | Saves senior review time every hiring round; becomes a Studio/BitElevate feature | Yes: public repos are real data | No |
| Lead triage and scoring | Faster first response to inquiries | Only with synthetic data | 12 repos |
| Proposal / effort estimation | Faster, more consistent quotes | Needs past proposals and actual hours | 4 repos |
| Revio aspect sentiment and crisis alerts | Product feature for Revio | Public review datasets | 6 repos |
| TenantEase late-payment risk | Product feature for TenantEase | Synthetic only | 2 repos |
| Internal agent starter kit (RAG, evals, guardrails) | Cuts delivery cost on every AI project | Internal | 0 |

Lead triage is a reasonable idea, but Cynbit will have seen it a dozen times this week, and it can only be demonstrated on invented inquiries. The review assistant can be tested on real submissions today, and it pays off twice: once in hiring, and once as a product.

## The opportunity in detail

**Internal use (hiring).** A reviewer opens the assistant's card instead of the raw repo. The deliverables, run instructions, red flags and similar submissions are already laid out, so the reviewer can spend their minutes on the thinking: is the opportunity well chosen, are the trade-offs understood? Cards also make reviews more consistent across reviewers, and the interview questions give the next round a head start.

My rough estimate is that the first-pass sort of a submission drops from about 10 minutes to about 2. That is a guess for illustration, not a measurement. Across 50 submissions in a round, it frees most of a working day for a senior person.

**Product use (Cynbit Studio and BitElevate).** The same engine becomes a "project proof" feature. A learner links a project and gets back a card showing what is complete, what is missing and what to fix before applying. With history-based checks, the card can also show that the project was built over time. Colleges' placement cells, which Studio already targets, could run it across a whole batch.

**What it must not become.** It should not be an auto-reject filter. A checklist rewards polish, and candidates would learn to game it. It is there to point attention, and a person decides.

## Risks

| Risk | How I would handle it |
|---|---|
| Candidates optimise for the checklist | Keep the weights private and treat completeness as triage, not a grade; judge the idea and reasoning by hand |
| Similarity unfairly marks a common idea as weak | Show "crowded", never "bad". A crowded idea done well still wins |
| Running untrusted code | Phase 1 never executes code. Phase 2 uses a locked-down container with no network and a time limit |
| Privacy of candidates | Only public repos; per-person results are visible only to reviewers; published statistics are aggregated and anonymised; retention rules in line with India's DPDP Rules (notified November 2025) |
| False red flags | Secret detection already skips dummy values (I found and fixed one false positive on the real pool). Every flag shows its evidence so a reviewer can dismiss it |

## Roadmap

1. **Now (this PoC):** static review, pool comparison, interview questions.
2. **Weeks 1–2:** run it beside reviewers in the next hiring round and compare its cards with their notes on 30–50 submissions; fix what disagrees.
3. **Weeks 3–6:** sandboxed execution (install, run the tests, screenshot the app); an LLM grader for the written reports, calibrated against reviewer scores; embedding-based similarity; near-duplicate detection on code.
4. **After that:** wire it into Studio as the project proof feature and pilot with one college.
