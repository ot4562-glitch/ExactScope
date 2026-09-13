#!/usr/bin/env python3
"""Single churn point between ExactScope v1.1-dev and the Bridge delivery contract."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = ROOT / "tools"
for path in (TOOLS, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from delivery import Delivery, from_v11_plan  # noqa: E402
from grounding_engine import (  # noqa: E402
    DEFAULT_CORPUS_EVIDENCE_BYTES,
    DEFAULT_CORPUS_EVIDENCE_POLICY,
    GroundingSession,
    finalize_generation as finalize_v11_generation,
)


def qid_for(question: str) -> str:
    return "bridge-" + hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


def finalize_generation(text: str, answer_spec: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Delegate strict generation validation to the unified v1.1 core."""
    return finalize_v11_generation(text, answer_spec)


def prepare_delivery(
    *,
    profile_dir: Path,
    question: str,
    contract: str = "answer-object-v3",
    qid: str | None = None,
    scope: str | None = None,
    retrieval_query: str | None = None,
    corpus_index: Path | None = None,
    corpus_top_k: int = 12,
    corpus_evidence_bytes: int = DEFAULT_CORPUS_EVIDENCE_BYTES,
    corpus_evidence_policy: str = DEFAULT_CORPUS_EVIDENCE_POLICY,
    answer_spec: dict[str, Any] | None = None,
) -> Delivery:
    """Run current v1.1 planning and immediately collapse it to stable-ish Bridge data."""
    session = GroundingSession.open(profile_dir)
    prepared = session.prepare(
        contract=contract,
        corpus_index=corpus_index,
        corpus_top_k=corpus_top_k,
        corpus_evidence_bytes=corpus_evidence_bytes,
        corpus_evidence_policy=corpus_evidence_policy,
        answer_spec=answer_spec,
    )
    plan = prepared.plan(
        question=question,
        qid=qid or qid_for(question),
        scope=scope,
        retrieval_query=retrieval_query,
    )
    return from_v11_plan(plan)
