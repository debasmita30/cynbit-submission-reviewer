import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from reviewer.fetch import parse_github_url  # noqa: E402
from reviewer.pool import Pool  # noqa: E402
from reviewer.review import review_path  # noqa: E402
from reviewer.signals import extract  # noqa: E402

FAKE_KEY = "sk-" + "A1b2C3d4" * 6  # built at runtime so this file itself holds no key-shaped string


def make_repo(tmp: Path, files: dict[str, str], commits: int = 1) -> Path:
    def git(*a):
        subprocess.run(["git", "-C", str(tmp), *a], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@t.t")
    git("config", "user.name", "t")
    items = list(files.items())
    chunk = max(1, len(items) // commits)
    for i in range(0, len(items), chunk):
        for rel, body in items[i:i + chunk]:
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
        git("add", "-A")
        git("commit", "-q", "-m", f"step {i}")
    return tmp


GOOD = {
    "README.md": "# Demo\n\n## Setup\n\n```\npip install -r requirements.txt\nstreamlit run app.py\n```\n\n"
                 "Live: https://demo-app.streamlit.app\n\n## Evaluation\naccuracy 0.8, f1 0.7, precision 0.9\n\n"
                 "## Limitations\nsmall data.\n" + "word " * 320,
    "requirements.txt": "streamlit\n",
    "app.py": "print('hi')\n",
    "docs/AI_Opportunity_Report.md": "# Opportunities\n",
    "docs/Technical_Approach.md": "# Architecture\n",
    "tests/test_app.py": "def test_x():\n    assert True\n",
}


def test_parse_url():
    assert parse_github_url("https://github.com/a-b/c.d.git") == ("a-b", "c.d")
    with pytest.raises(ValueError):
        parse_github_url("https://gitlab.com/x/y")


def test_complete_repo_scores_high(tmp_path):
    r = review_path(make_repo(tmp_path, GOOD, commits=3))
    assert all(d["present"] for d in r["deliverables"].values())
    assert r["completeness"] >= 90
    assert not any("secret" in f.lower() for f in r["red_flags"])


def test_secret_env_and_placeholder_flagged(tmp_path):
    files = dict(GOOD)
    files[".env"] = f"OPENAI_API_KEY={FAKE_KEY}\n"
    files["README.md"] = GOOD["README.md"] + "\nAuthor: [Your Name]\n"
    r = review_path(make_repo(tmp_path, files))
    flags = " ".join(r["red_flags"])
    assert "secret" in flags and ".env" in flags and "[Your Name]" in flags
    assert "one commit" in flags


def test_dummy_key_is_not_a_secret(tmp_path):
    files = {"README.md": "x", "t.ts": 'const dummyKey = "sk-test-' + "a" * 40 + '";'}
    assert extract(make_repo(tmp_path, files)).secret_hits == []


def test_missing_deliverables(tmp_path):
    r = review_path(make_repo(tmp_path, {"README.md": "# hi", "main.py": "x=1"}))
    assert not r["deliverables"]["opportunity_report"]["present"]
    assert r["completeness"] < 30
    assert any("check that it works" in q for q in r["questions"])


def test_pool_similarity_prefers_same_theme():
    texts = ["lead scoring inquiry triage crm sales lead", "lead triage inquiry scoring sales pipeline crm",
             "review sentiment revio reply reputation", "revio review reply sentiment crisis reputation"]
    p = Pool(["a", "b", "c", "d"], ["lead_triage", "lead_triage", "revio_reviews", "revio_reviews"], texts)
    rep = p.compare("an inquiry triage tool with lead scoring for crm sales", k=1)
    assert rep.theme == "lead_triage" and rep.theme_share == 0.5
