#!/usr/bin/env python3
"""Freeze gold-blind LlamaIndex BM25 retrieval for a Kubernetes proxy candidate."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any

from llama_index.core.schema import TextNode
from llama_index.retrievers.bm25 import BM25Retriever

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/dev32/candidate"
DEFAULT_OUT = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/dev32/host-retrieval"
TOP_K = 12


class RetrievalError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RetrievalError(f"invalid JSONL row: {path}")
            rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def freeze(candidate: Path, out: Path) -> dict[str, Any]:
    if out.exists():
        raise RetrievalError(f"output already exists: {out}")
    manifest = load_json(candidate / "manifest.json")
    if manifest.get("development_only") is not True or manifest.get("qualification_eligible") is not False:
        raise RetrievalError("candidate qualification boundary drift")
    if manifest.get("gold_visible_to_runner") is not False:
        raise RetrievalError("candidate does not preserve gold isolation")
    questions = load_jsonl(candidate / "serving/questions.jsonl")
    corpus = load_json(candidate / "serving/corpus-index.json")
    docs = corpus.get("documents")
    if not isinstance(docs, list) or len(docs) < TOP_K:
        raise RetrievalError("candidate corpus is too small")
    if len(questions) != manifest.get("item_count"):
        raise RetrievalError("candidate question count drift")

    nodes: list[TextNode] = []
    by_id: dict[str, dict[str, Any]] = {}
    for doc in docs:
        if not isinstance(doc, dict):
            raise RetrievalError("invalid corpus document")
        doc_id = doc.get("id")
        path = doc.get("path")
        title = doc.get("title")
        text = doc.get("text")
        digest = doc.get("sha256")
        if not all(isinstance(v, str) and v for v in (doc_id, path, title, text, digest)):
            raise RetrievalError("invalid corpus document fields")
        if len(digest) != 64 or hashlib.sha256(text.encode("utf-8")).hexdigest() != digest:
            raise RetrievalError(f"corpus text digest mismatch: {doc_id}")
        if doc_id in by_id:
            raise RetrievalError(f"duplicate corpus id: {doc_id}")
        by_id[doc_id] = doc
        nodes.append(TextNode(id_=doc_id, text=text, metadata={"title": title, "path": path}))

    retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=TOP_K)
    output_rows: list[dict[str, Any]] = []
    for question_row in questions:
        item_id = question_row.get("item_id")
        question = question_row.get("question")
        if not isinstance(item_id, str) or not isinstance(question, str) or not question:
            raise RetrievalError("invalid runner-visible question")
        ranked = retriever.retrieve(question)
        if len(ranked) != TOP_K:
            raise RetrievalError(f"{item_id}: expected top-{TOP_K}, got {len(ranked)}")
        seen: set[str] = set()
        hits: list[dict[str, Any]] = []
        for rank, node_with_score in enumerate(ranked, 1):
            node = node_with_score.node
            doc_id = node.node_id
            if doc_id in seen or doc_id not in by_id:
                raise RetrievalError(f"{item_id}: duplicate/unknown retrieved id: {doc_id}")
            seen.add(doc_id)
            doc = by_id[doc_id]
            hits.append(
                {
                    "rank": rank,
                    "id": doc_id,
                    "path": doc["path"],
                    "title": doc["title"],
                    "text": doc["text"],
                    "text_sha256": doc["sha256"],
                    "score": float(node_with_score.score or 0.0),
                }
            )
        output_rows.append({"item_id": item_id, "question": question, "hits": hits})

    out.mkdir(parents=True)
    retrieval_path = out / "retrieval.jsonl"
    write_jsonl(retrieval_path, output_rows)
    retrieval_manifest = {
        "format": "exactscope.public-proxy-host-retrieval",
        "format_version": "0.1",
        "proxy_id": manifest["proxy_id"],
        "split": manifest["split"],
        "development_only": True,
        "qualification_eligible": False,
        "host_framework": "LlamaIndex",
        "host_retriever": "llama-index-retrievers-bm25/BM25Retriever",
        "host_owns_retrieval": True,
        "exactscope_used_during_retrieval": False,
        "gold_visible_during_retrieval": False,
        "candidate_manifest_sha256": sha256_file(candidate / "manifest.json"),
        "questions_sha256": sha256_file(candidate / "serving/questions.jsonl"),
        "corpus_index_sha256": sha256_file(candidate / "serving/corpus-index.json"),
        "item_count": len(output_rows),
        "document_count": len(nodes),
        "top_k": TOP_K,
        "retrieval_sha256": sha256_file(retrieval_path),
        "packages": {
            "llama-index-core": importlib.metadata.version("llama-index-core"),
            "llama-index-retrievers-bm25": importlib.metadata.version("llama-index-retrievers-bm25"),
            "bm25s": importlib.metadata.version("bm25s"),
        },
    }
    write_json(out / "retrieval-manifest.json", retrieval_manifest)
    return {
        "status": "RETRIEVAL_FROZEN",
        "item_count": len(output_rows),
        "document_count": len(nodes),
        "top_k": TOP_K,
        "retrieval_sha256": retrieval_manifest["retrieval_sha256"],
        "manifest_sha256": sha256_file(out / "retrieval-manifest.json"),
        "output": str(out),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    candidate = args.candidate if args.candidate.is_absolute() else ROOT / args.candidate
    out = args.output if args.output.is_absolute() else ROOT / args.output
    print(json.dumps(freeze(candidate.resolve(), out.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
