"""Get a submission onto disk: a shallow-history git clone of a public GitHub repo."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

GITHUB_RE = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/.*)?$")


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")
    short = re.fullmatch(r"([\w.-]+)/([\w.-]+?)(?:\.git)?", url)  # accept "owner/repo"
    if short:
        return short.group(1), short.group(2)
    m = GITHUB_RE.search(url)
    if not m:
        raise ValueError("Paste a GitHub repo link like https://github.com/owner/repo or just owner/repo")
    return m.group(1), m.group(2)


def clone(url: str, dest: str | Path | None = None, timeout: int = 90) -> Path:
    """Clone with full commit history but skip large blobs (>500 KB) to stay fast."""
    owner, repo = parse_github_url(url)
    dest = Path(dest) if dest else Path(tempfile.mkdtemp(prefix="review_")) / f"{owner}__{repo}"
    if dest.exists():
        shutil.rmtree(dest)
    cmd = ["git", "clone", "--quiet", "--filter=blob:limit=500k", f"https://github.com/{owner}/{repo}.git", str(dest)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                         env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if res.returncode != 0:
        err = res.stderr.lower()
        if "username" in err or "not found" in err or "403" in err:
            raise RuntimeError(f"Couldn't open {owner}/{repo}. Check the link, and make sure the repo is public.")
        raise RuntimeError(f"Could not clone {owner}/{repo}: {res.stderr.strip()[:200]}")
    return dest
