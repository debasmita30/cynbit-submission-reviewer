"""One call: repo URL in, reviewer card out."""

from __future__ import annotations

import shutil
import time
from dataclasses import asdict
from pathlib import Path

from reviewer.fetch import clone, parse_github_url
from reviewer.pool import POOL_PATH, Pool, anon_id
from reviewer.rubric import build_card
from reviewer.signals import extract

_pool: Pool | None = None


def get_pool() -> Pool | None:
    global _pool
    if _pool is None and POOL_PATH.exists():
        _pool = Pool.load()
    return _pool


def review_path(path: str | Path, role: str = "AI/ML Engineer Intern", repo_name: str | None = None) -> dict:
    t0 = time.perf_counter()
    s = extract(path)
    pool = get_pool()
    idea = None
    if pool is not None and s.text_corpus.strip():
        idea = pool.compare(s.text_corpus, exclude=anon_id(repo_name) if repo_name else None)
    card = build_card(s, role, idea)
    out = asdict(card)
    out["signals"] = s.public()
    out["seconds"] = round(time.perf_counter() - t0, 2)
    return out


def review_url(url: str, role: str = "AI/ML Engineer Intern") -> dict:
    owner, repo = parse_github_url(url)
    path = clone(url)
    try:
        out = review_path(path, role, f"{owner}/{repo}")
        out["repo"] = f"{owner}/{repo}"
        return out
    finally:
        shutil.rmtree(path.parent, ignore_errors=True)
