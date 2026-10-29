"""Idea similarity against the pool of earlier submissions.

Every submission's README + docs is embedded with TF-IDF (word 1-2 grams,
min_df=2 so one-off words such as candidate names never enter the vocabulary).
For a new repo we report its nearest neighbours, the theme those neighbours
share, and how crowded that theme already is. A reviewer reading their 15th
lead-scoring tool deserves to know that before the first line.

The pool artifact stores only anonymised ids, hand-assigned themes, derived
signals and TF-IDF vectors. It does not store anyone's text or repo URL.
"""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

POOL_PATH = Path(__file__).resolve().parent.parent / "data" / "pool.pkl"

THEMES = {
    "lead_triage": "Lead / inquiry triage & scoring",
    "proposal_scoping": "Proposal, scoping & solution planning",
    "revio_reviews": "Revio: review sentiment & replies",
    "tenantease": "TenantEase: rent / dues prediction",
    "learning": "BitElevate / Studio: learner roadmaps",
    "delivery_ops": "Delivery operations",
    "submission_review": "Submission / project review",
    "other": "Other (audits, portfolio, etc.)",
}


def anon_id(name: str) -> str:
    return "S-" + hashlib.sha256(name.lower().encode()).hexdigest()[:6]


@dataclass
class Neighbour:
    id: str
    theme: str
    similarity: float


@dataclass
class IdeaReport:
    theme: str
    theme_name: str
    theme_share: float  # fraction of the pool already in this theme
    novelty: float  # 1 - max similarity
    neighbours: list[Neighbour]


class Pool:
    def __init__(self, ids: list[str], themes: list[str], texts: list[str] | None = None,
                 signals: list[dict] | None = None):
        self.ids, self.themes, self.signals = ids, themes, signals or []
        self.vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, sublinear_tf=True,
                                   stop_words="english", token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
        if texts is not None:
            self.matrix = self.vec.fit_transform(texts)

    def compare(self, text: str, k: int = 3, exclude: str | None = None) -> IdeaReport:
        sims = cosine_similarity(self.vec.transform([text]), self.matrix)[0]
        if exclude is not None and exclude in self.ids:
            sims[self.ids.index(exclude)] = -1
        order = np.argsort(sims)[::-1][:k]
        neigh = [Neighbour(self.ids[i], self.themes[i], round(float(sims[i]), 3)) for i in order]
        # similarity-weighted vote among neighbours
        votes: dict[str, float] = {}
        for n in neigh:
            votes[n.theme] = votes.get(n.theme, 0) + max(n.similarity, 0)
        theme = max(votes, key=votes.get) if votes else "other"
        max_sim = max(n.similarity for n in neigh) if neigh else 0.0
        if max_sim < 0.12:  # nothing in the pool is close: a new idea
            theme = "novel"
        share = self.themes.count(theme) / len(self.themes) if theme in self.themes else 0.0
        return IdeaReport(theme, THEMES.get(theme, "New idea (no close match in pool)"), round(share, 2),
                          round(1 - max_sim, 3), neigh)

    def theme_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.themes:
            out[t] = out.get(t, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def save(self, path: Path = POOL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump({"ids": self.ids, "themes": self.themes, "signals": self.signals,
                         "vec": self.vec, "matrix": self.matrix}, f)

    @classmethod
    def load(cls, path: Path = POOL_PATH) -> "Pool":
        with path.open("rb") as f:
            d = pickle.load(f)
        p = cls(d["ids"], d["themes"], None, d["signals"])
        p.vec, p.matrix = d["vec"], d["matrix"]
        return p
