"""Deterministic evidence extracted from a cloned submission.

Nothing here executes the candidate's code. Everything is read from the file
tree, text files and git history, so it is safe to run on untrusted repos.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx", ".json", ".toml", ".yaml", ".yml",
            ".cfg", ".ini", ".env", ".html", ".css", ".sh", ".rst"}
CODE_EXT = {".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs"}
DOC_EXT = {".md", ".pdf", ".docx", ".rst", ".txt"}
DEP_FILES = {"requirements.txt", "pyproject.toml", "package.json", "environment.yml", "pipfile", "setup.py"}
JUNK_DIRS = ("node_modules/", ".venv/", "venv/", "__pycache__/", ".ipynb_checkpoints/", "dist/", "build/")

LIVE_LINK_RE = re.compile(r"https?://[\w.-]+\.(?:streamlit\.app|vercel\.app|netlify\.app|onrender\.com|"
                          r"railway\.app|herokuapp\.com|hf\.space|pages\.dev|fly\.dev)\S*|"
                          r"https?://huggingface\.co/spaces/\S+|https?://colab\.research\.google\.com/\S+", re.I)
VIDEO_RE = re.compile(r"https?://(?:www\.)?(?:loom\.com|youtu\.be|youtube\.com|drive\.google\.com/file)\S*", re.I)
SECRET_PATTERNS = {
    "OpenAI key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "Anthropic key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Groq key": re.compile(r"\bgsk_[A-Za-z0-9]{40,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}
# Values that look like keys but are clearly fake (found as a false positive in a real repo's test file).
DUMMY_RE = re.compile(r"test|dummy|example|fake|sample|placeholder|xxxx|your", re.I)
PLACEHOLDER_RE =re.compile(r"\[your name\]|<your[- _]name>|your-username|lorem ipsum|\bTODO\b|\bTBD\b|"
                            r"insert (?:link|url) here|<repo-url>|<this-repo-url>", re.I)
RUN_CMD_RE = re.compile(r"(pip install|npm (?:install|i|run)|streamlit run|uvicorn |python3? [\w/.-]+\.py|"
                        r"docker (?:compose|run)|yarn |pnpm |jupyter )", re.I)
EVAL_RE = re.compile(r"\b(accuracy|f1|precision|recall|auc|rmse|mae|bleu|rouge|latency|benchmark|"
                     r"confusion matrix|evaluation)\b", re.I)
LIMITS_RE = re.compile(r"\b(limitation|trade-?off|known issue|future work|next steps|assumption)s?\b", re.I)


@dataclass
class Signals:
    files: int = 0
    code_files: int = 0
    code_lines: int = 0
    languages: dict = field(default_factory=dict)
    readme_words: int = 0
    readme_headings: int = 0
    has_run_instructions: bool = False
    has_dependency_file: bool = False
    has_tests: bool = False
    test_files: int = 0
    has_ci: bool = False
    has_docker: bool = False
    has_env_example: bool = False
    live_links: list = field(default_factory=list)
    video_links: list = field(default_factory=list)
    mentions_evaluation: bool = False
    mentions_limitations: bool = False
    doc_files: list = field(default_factory=list)
    notebooks: int = 0
    # history
    commits: int = 0
    active_days: int = 0
    span_days: float = 0.0
    largest_commit_share: float = 0.0  # share of all tracked files introduced by the single biggest commit
    # red flags
    committed_env_files: list = field(default_factory=list)
    secret_hits: list = field(default_factory=list)  # (kind, path) — values never stored
    junk_committed: list = field(default_factory=list)
    placeholders: list = field(default_factory=list)
    text_corpus: str = ""  # README + docs text, used for idea similarity (not displayed)

    def public(self) -> dict:
        d = asdict(self)
        d.pop("text_corpus")
        return d


def _git(repo: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
    return res.stdout if res.returncode == 0 else ""


def _read(path: Path, limit: int = 400_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _history(repo: Path, s: Signals, n_files: int) -> None:
    dates = [datetime.fromisoformat(x) for x in _git(repo, "log", "--format=%aI").split()]
    log = _git(repo, "log", "--no-renames", "--format=@@%H", "--name-only", "--diff-filter=A")
    adds, current = Counter(), None
    for line in log.splitlines():
        if line.startswith("@@"):
            current = line[2:]
        elif line.strip() and current:
            adds[current] += 1
    s.commits = len(dates)
    if dates:
        s.active_days = len({d.date() for d in dates})
        s.span_days = round((max(dates) - min(dates)).total_seconds() / 86400, 1)
    if adds and n_files:
        s.largest_commit_share = round(min(1.0, max(adds.values()) / n_files), 2)


def extract(repo: str | Path) -> Signals:
    repo = Path(repo)
    s = Signals()
    tracked = [p for p in _git(repo, "ls-files").splitlines() if p]
    s.files = len(tracked)
    lang = Counter()
    readme_text, docs_text = "", []

    for rel in tracked:
        low = rel.lower()
        p = repo / rel
        ext = Path(low).suffix
        name = Path(low).name
        if any(low.startswith(j) or f"/{j}" in low for j in JUNK_DIRS):
            s.junk_committed.append(rel.split("/")[0] + "/")
            continue
        if ext in CODE_EXT:
            s.code_files += 1
            lang[ext] += 1
            if ext != ".ipynb":
                s.code_lines += _read(p).count("\n")
        if ext == ".ipynb":
            s.notebooks += 1
        if name in DEP_FILES:
            s.has_dependency_file = True
        if re.search(r"(^|/)(tests?|__tests__)/|(^|/)test_[\w-]+\.py$|_test\.py$|\.(test|spec)\.[jt]sx?$", low):
            s.has_tests = True
            s.test_files += 1
        if low.startswith(".github/workflows/"):
            s.has_ci = True
        if name in ("dockerfile", "docker-compose.yml", "compose.yaml", "docker-compose.yaml"):
            s.has_docker = True
        if name.startswith(".env"):
            if any(t in name for t in ("example", "sample", "template")):
                s.has_env_example = True
            else:
                s.committed_env_files.append(rel)
        if ext in DOC_EXT and "/" not in rel and name.startswith("readme"):
            readme_text = _read(p)
        elif ext in DOC_EXT and name not in ("license", "license.md", "requirements.txt"):
            s.doc_files.append(rel)
            if ext in (".md", ".rst", ".txt"):
                docs_text.append(_read(p, 200_000))
        if ext in TEXT_EXT or name.startswith(".env"):
            body = _read(p, 300_000)
            for kind, pat in SECRET_PATTERNS.items():
                for m in pat.finditer(body):
                    if not DUMMY_RE.search(m.group(0)):
                        s.secret_hits.append((kind, rel))
                        break

    s.languages = dict(lang.most_common())
    s.junk_committed = sorted(set(s.junk_committed))
    s.readme_words = len(readme_text.split())
    s.readme_headings = len(re.findall(r"^#{1,4} ", readme_text, re.M))
    all_text = readme_text + "\n" + "\n".join(docs_text)
    s.has_run_instructions = bool(RUN_CMD_RE.search(readme_text))
    s.live_links = sorted(set(m.rstrip(").,>`*]") for m in LIVE_LINK_RE.findall(all_text)))[:5]
    s.video_links = sorted(set(m.rstrip(").,>`*]") for m in VIDEO_RE.findall(all_text)))[:3]
    s.mentions_evaluation = len(EVAL_RE.findall(all_text)) >= 3
    s.mentions_limitations = bool(LIMITS_RE.search(all_text))
    s.placeholders = sorted({m.group(0) for m in PLACEHOLDER_RE.finditer(readme_text + "\n".join(docs_text))})[:6]
    s.text_corpus = all_text[:60_000]
    _history(repo, s, s.files)
    return s
