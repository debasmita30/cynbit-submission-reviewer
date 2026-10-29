# What the public submission pool looks like

29 public repositories submitted for Cynbit's Phase 2 assessments (25 for the AI/ML role), collected from GitHub search on 30 Oct 2026. Themes were labelled by hand from each README. Figures are aggregates only; no individual repo is scored here.

| Theme | Repos | Share |
|---|---|---|
| Lead / inquiry triage & scoring | 12 | 41% |
| Revio: review sentiment & replies | 6 | 21% |
| Proposal, scoping & solution planning | 4 | 14% |
| TenantEase: rent / dues prediction | 2 | 7% |
| BitElevate / Studio: learner roadmaps | 2 | 7% |
| Other (audits, portfolio, etc.) | 2 | 7% |
| Delivery operations | 1 | 3% |

| Signal | Share of repos |
|---|---|
| Has automated tests | 72% |
| Has a live demo link | 28% |
| Has a walkthrough video link | 0% |
| Reports evaluation numbers | 83% |
| Mostly one commit (≥90% of files in one commit) | 55% |
| Unfilled placeholders in docs | 14% |
| AI/ML repos with all three deliverables detected | 23/25 |

## Does text similarity recover the idea?

Leave-one-out nearest-neighbour theme accuracy: **57%** on the 28 repos whose theme appears more than once (**55%** over all 29, where singleton themes cannot be matched by design).
Treating lead triage and proposal scoping as one family (both start from a client inquiry): **71%**.
Most remaining errors are between those two themes, which genuinely overlap. With 28 examples these figures are rough (±15 points).
Mean similarity of a lead-triage repo to its closest neighbour: **0.36**.
Signal extraction takes well under a second per repo after cloning, and no candidate code is executed.