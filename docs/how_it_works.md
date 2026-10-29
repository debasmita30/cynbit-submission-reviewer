**Pipeline**

1. **Fetch.** `git clone` with full history but without blobs over 500 KB. Nothing is executed.
2. **Signals.** File tree, README and docs text, dependency files, tests, CI, Docker, live/video links, committed `.env` files, key-shaped strings (with a dummy-value filter), leftover placeholders, and git history (commits, active days, share of files added by the biggest commit).
3. **Brief check.** Each role has its own deliverables. For AI/ML: opportunity report, technical approach report, working PoC. They are matched by file names and section headings.
4. **Idea similarity.** TF-IDF over README + docs, compared with the hand-labelled pool of earlier submissions. Shows the nearest three and how crowded that theme is.
5. **Card.** A completeness score (0–100, weighted checklist), red flags, strengths and interview questions picked from what's missing.

**What it deliberately doesn't do**

- Decide who gets an interview. Completeness isn't quality; a thin repo with a sharp idea can beat a polished one.
- Run untrusted code. That needs a sandbox (container, no network, time limit), which is phase 2.
- Judge writing quality. That needs an LLM grader calibrated against reviewer scores, which is phase 2.
