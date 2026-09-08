#!/usr/bin/env python3
"""Fetch official public benchmark inputs into an untracked local data directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

DATASETS = {
    "hotpotqa-dev-distractor": {
        "url": "http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json",
        "filename": "hotpot_dev_distractor_v1.json",
        "license": "CC BY-SA 4.0",
        "source": "HotpotQA official repository/homepage",
    },
    "hotpotqa-dev-distractor-hf-parquet": {
        "url": "https://huggingface.co/datasets/hotpotqa/hotpot_qa/resolve/a8af52d40ca73810f304ad1aa28b0cbb518f37de/distractor/validation-00000-of-00001.parquet?download=true",
        "filename": "hotpotqa-distractor-validation-a8af52d.parquet",
        "license": "CC BY-SA 4.0",
        "source": "HotpotQA Hugging Face dataset organization, pinned auto-converted Parquet revision",
        "expected_sha256": "c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6",
    },
    "nq-open-dev": {
        "url": "https://raw.githubusercontent.com/google-research-datasets/natural-questions/master/nq_open/NQ-open.dev.jsonl",
        "filename": "NQ-open.dev.jsonl",
        "license": "CC BY-SA 3.0",
        "source": "Google Natural Questions official dataset repository",
    },
    "nq-official-tiny-dev": {
        "url": "https://storage.googleapis.com/bert-nq/tiny-dev/nq-dev-sample.jsonl.gz",
        "filename": "nq-dev-sample.jsonl.gz",
        "license": "CC BY-SA 3.0",
        "source": "Google Natural Questions official competition tiny-dev sample",
    },
    "nq-official-dev-00": {
        "url": "https://storage.googleapis.com/natural_questions/v1.0/dev/nq-dev-00.jsonl.gz",
        "filename": "nq-dev-00.jsonl.gz",
        "license": "CC BY-SA 3.0",
        "source": "Google Natural Questions official v1.0 development shard 00",
        "expected_sha256": "78a7f7899aa7d0bc9a29878cdb90daabbeda21a93e3730d8861f20ec736790b2",
    },
    "nq-clean-validation-hf-mirror": {
        "url": "https://huggingface.co/datasets/lighteval/natural_questions_clean/resolve/refs%2Fconvert%2Fparquet/default/validation/0000.parquet",
        "filename": "nq-clean-validation-hf-mirror.parquet",
        "license": "CC BY-SA 3.0",
        "source": "lighteval/natural_questions_clean Hugging Face development mirror derived from Natural Questions; not an official Google download",
    },
    "fever-paper-dev": {
        "url": "https://fever.ai/download/fever/paper_dev.jsonl",
        "filename": "fever-paper-dev.jsonl",
        "license": "FEVER dataset license; see https://fever.ai/dataset/fever.html",
        "source": "FEVER official dataset site",
    },
    "fever-wiki-pages-2017": {
        "url": "https://fever.ai/download/fever/wiki-pages.zip",
        "filename": "fever-wiki-pages-2017.zip",
        "license": "FEVER dataset license; see https://fever.ai/dataset/fever.html",
        "source": "FEVER official pre-processed June 2017 Wikipedia pages",
        "expected_sha256": "4b06d95da6adf7fe02d2796176c670dacccb21348da89cba4c50676ab99665f2",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(dataset_id: str, root: Path) -> dict[str, object]:
    spec = DATASETS[dataset_id]
    root.mkdir(parents=True, exist_ok=True)
    output = root / str(spec["filename"])
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing dataset: {output}")
    request = urllib.request.Request(str(spec["url"]), headers={"User-Agent": "ExactScope-public-benchmark-fetch/1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, output.open("wb") as handle:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                handle.write(block)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    digest = sha256(output)
    expected = spec.get("expected_sha256")
    if expected is not None and digest != expected:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"download SHA-256 mismatch for {dataset_id}")
    return {
        "dataset_id": dataset_id,
        "url": spec["url"],
        "filename": spec["filename"],
        "license": spec["license"],
        "source": spec["source"],
        "bytes": output.stat().st_size,
        "sha256": digest,
        "expected_sha256": expected,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=sorted(DATASETS))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        record = fetch(args.dataset, args.output_dir)
    except (OSError, RuntimeError) as exc:
        print(f"ExactScope public benchmark fetch: FAIL: {exc}")
        return 1
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
