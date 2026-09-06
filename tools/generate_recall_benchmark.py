#!/usr/bin/env python3
"""Generate a deterministic candidate-bound everyday factual recall benchmark and fact pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

PEOPLE = ["Mina", "Joon", "Ara", "Noel", "Yuna", "Evan", "Sora", "Theo"]
DEVICES = ["Hall Purifier", "Bedroom Purifier", "Kitchen Hub", "Desk Hub", "Rover Mini", "Rover Plus"]
LOCATIONS = ["B2-17", "B3-04", "C1-22", "A4-09", "D2-11", "C3-07"]
NETWORKS = ["Maple-Guest", "Nori-Home", "Cedar-Guest", "Miso-Net", "Luna-Home", "Bori-Guest"]
FILTERS = ["AF-210", "AF-330", "HX-18", "PX-42", "CF-905", "QF-72"]
COLORS = ["amber", "cobalt", "ivory", "teal", "violet", "silver", "crimson", "indigo"]
KOREAN_NAMES = ["아람", "누리", "미르", "가온", "다온", "라온"]


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def make_code(rng: random.Random, prefix: str) -> str:
    return f"{prefix}-{rng.randint(1000, 9999)}"


def fact(
    fact_id: str,
    evidence: str,
    source: str,
    aliases: list[str],
    *,
    revision: int = 1,
) -> dict[str, Any]:
    return {
        "id": fact_id,
        "evidence": evidence,
        "source": source,
        "revision": revision,
        "aliases": aliases,
        "source_sha256": None,
        "valid_from": None,
        "valid_until": None,
    }


def case(
    case_id: str,
    class_name: str,
    question: str,
    expected_answer: str | None,
    expected_fact_id: str | None,
    *,
    expect_evidence: bool,
    expect_abstain: bool,
    obsolete_answer: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": case_id,
        "class": class_name,
        "question": question,
        "expected_answer": expected_answer,
        "expected_fact_id": expected_fact_id,
        "expect_evidence": expect_evidence,
        "expect_abstain": expect_abstain,
    }
    if obsolete_answer is not None:
        result["obsolete_answer"] = obsolete_answer
    return result


def generate(seed: int) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    facts: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    source = f"recall-everyday@{seed}"

    # Private/device memory: realistic facts a base model cannot know from weights.
    for index, (person, network) in enumerate(zip(PEOPLE[:4], NETWORKS[:4], strict=True), start=1):
        fact_id = f"home.{person.lower()}.guest-network"
        facts.append(
            fact(
                fact_id,
                f"{person}'s saved guest Wi-Fi network name is {network}.",
                source,
                [f"{person} guest wifi network name", f"{person} saved guest network"],
            )
        )
        cases.append(
            case(
                f"private-wifi-{index:02d}",
                "everyday_private",
                f"What is {person}'s saved guest Wi-Fi network name?",
                network,
                fact_id,
                expect_evidence=True,
                expect_abstain=False,
            )
        )

    for index, device in enumerate(DEVICES[:4], start=1):
        filter_code = FILTERS[index - 1]
        fact_id = f"device.{device.lower().replace(' ', '-')}.filter"
        facts.append(
            fact(
                fact_id,
                f"The replacement filter code for {device} is {filter_code}.",
                source,
                [f"{device} replacement filter", f"replacement filter {device}"],
            )
        )
        cases.append(
            case(
                f"device-filter-{index:02d}",
                "everyday_private",
                f"Which replacement filter does the {device} use?",
                filter_code,
                fact_id,
                expect_evidence=True,
                expect_abstain=False,
            )
        )

    for index, (person, location) in enumerate(zip(PEOPLE[4:8], LOCATIONS[:4], strict=True), start=1):
        fact_id = f"memory.{person.lower()}.parking"
        facts.append(
            fact(
                fact_id,
                f"{person}'s saved parking location is {location}.",
                source,
                [f"{person} car parking location", f"saved parking location {person}"],
            )
        )
        cases.append(
            case(
                f"private-parking-{index:02d}",
                "everyday_private",
                f"Where did {person} save the car's parking location?",
                location,
                fact_id,
                expect_evidence=True,
                expect_abstain=False,
            )
        )

    # Distractors: similar device names must not leak the sibling device's value.
    device_pairs = (("Hall Purifier", "Bedroom Purifier"), ("Kitchen Hub", "Desk Hub"))
    for index, (left, right) in enumerate(device_pairs, start=1):
        left_code = make_code(rng, "SN")
        right_code = make_code(rng, "SN")
        for device, serial in ((left, left_code), (right, right_code)):
            fact_id = f"distractor.{device.lower().replace(' ', '-')}.serial"
            facts.append(
                fact(
                    fact_id,
                    f"The device serial for {device} is {serial}.",
                    source,
                    [f"{device} device serial", f"serial number {device}"],
                )
            )
        cases.extend(
            [
                case(
                    f"distractor-{index:02d}-a",
                    "distractor",
                    f"What is the device serial for the {left}?",
                    left_code,
                    f"distractor.{left.lower().replace(' ', '-')}.serial",
                    expect_evidence=True,
                    expect_abstain=False,
                ),
                case(
                    f"distractor-{index:02d}-b",
                    "distractor",
                    f"What is the device serial for the {right}?",
                    right_code,
                    f"distractor.{right.lower().replace(' ', '-')}.serial",
                    expect_evidence=True,
                    expect_abstain=False,
                ),
            ]
        )

    # Stale-memory override: current local setting must beat an explicitly supplied old value.
    for index, person in enumerate(PEOPLE[:4], start=1):
        old_location = LOCATIONS[index - 1]
        new_location = LOCATIONS[index + 1]
        fact_id = f"revision.{person.lower()}.pickup-location"
        facts.append(
            fact(
                fact_id,
                f"{person}'s current pickup location is {new_location}; this is revision 2.",
                source,
                [f"{person} current pickup location", f"pickup location {person}"],
                revision=2,
            )
        )
        cases.append(
            case(
                f"stale-{index:02d}",
                "stale_override",
                f"An old note says {person}'s pickup location is {old_location}. What is the current pickup location?",
                new_location,
                fact_id,
                expect_evidence=True,
                expect_abstain=False,
                obsolete_answer=old_location,
            )
        )

    # No-answer: relevant entities exist, but the requested property was never stored.
    no_answer_questions = [
        ("Mina", "What time did Mina last charge her phone?"),
        ("Joon", "What did Joon eat for breakfast today?"),
        ("Hall Purifier", "When was the Hall Purifier last cleaned?"),
        ("Bedroom Purifier", "Who last moved the Bedroom Purifier?"),
        ("Ara", "Which umbrella did Ara take this morning?"),
        ("Noel", "What was Noel's last bus seat number?"),
    ]
    for index, (_, question) in enumerate(no_answer_questions, start=1):
        cases.append(
            case(
                f"no-answer-{index:02d}",
                "no_answer",
                question,
                None,
                None,
                expect_evidence=False,
                expect_abstain=True,
            )
        )

    # Multilingual private memory using ordinary household/product questions.
    for index, name in enumerate(KOREAN_NAMES[:4], start=1):
        color = COLORS[index - 1]
        fact_id = f"private.ko.{index}.storage-label"
        facts.append(
            fact(
                fact_id,
                f"{name} 보관함의 현재 라벨 색상은 {color}이다.",
                source,
                [f"{name} 보관함의 현재 라벨 색상은", f"{name} 보관함 라벨 색상"],
            )
        )
        cases.append(
            case(
                f"ko-{index:02d}",
                "multilingual_private",
                f"{name} 보관함의 현재 라벨 색상은 무엇인가?",
                color,
                fact_id,
                expect_evidence=True,
                expect_abstain=False,
            )
        )

    # Short product/manual facts resemble consumer support questions.
    for index, device in enumerate(("Rover Mini", "Rover Plus"), start=1):
        dock_clearance = str(rng.choice((45, 50, 55, 60)))
        fact_id = f"manual.{device.lower().replace(' ', '-')}.dock-clearance"
        facts.append(
            fact(
                fact_id,
                f"{device} requires {dock_clearance} cm of clear space in front of its dock.",
                source,
                [f"{device} dock clear space", f"{device} dock clearance"],
            )
        )
        cases.append(
            case(
                f"manual-{index:02d}",
                "everyday_manual",
                f"How much clear space should I leave in front of the {device} dock? Answer with the number only.",
                dock_clearance,
                fact_id,
                expect_evidence=True,
                expect_abstain=False,
            )
        )

    facts.sort(key=lambda item: item["id"])
    cases.sort(key=lambda item: item["id"])
    pack = {
        "format": "exactscope.fact-pack.source",
        "format_version": "0.1",
        "pack_id": f"org.exactscope.recall-benchmark.everyday.seed-{seed}",
        "pack_revision": 1,
        "authority": "authoritative",
        "languages": ["en", "ko"],
        "source_set_sha256": None,
        "facts": facts,
    }
    corpus_bytes = b"".join(canonical(item) for item in cases)
    manifest = {
        "format": "exactscope.recall-benchmark.generated",
        "format_version": "0.2",
        "seed": seed,
        "fact_count": len(facts),
        "case_count": len(cases),
        "class_counts": {
            class_name: sum(item["class"] == class_name for item in cases)
            for class_name in sorted({item["class"] for item in cases})
        },
        "fact_pack_source_sha256": digest(canonical(pack)),
        "corpus_sha256": digest(corpus_bytes),
        "generation_policy": "deterministic-before-inference; everyday consumer-shaped questions; no post-result alias repair",
    }
    return pack, cases, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise SystemExit("output directory already exists; benchmark generation is immutable")
    output.mkdir(parents=True)
    pack, cases, manifest = generate(args.seed)
    write_json(output / "fact-pack-source.json", pack)
    with (output / "corpus.jsonl").open("wb") as handle:
        for item in cases:
            handle.write(canonical(item))
    write_json(output / "generation-manifest.json", manifest)
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
