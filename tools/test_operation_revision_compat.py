"""Static tests for operation-revision upgrade policy. No runtime execution."""
from __future__ import annotations

import copy
import unittest

from check_operation_revision_compat import (
    RevisionCompatibilityError,
    compare_capability_metadata,
)


def profile(revision: int, *, profile_id: str = "unit-capability") -> dict:
    return {"profile_id": profile_id, "profile_revision": revision, "domain": "statistics"}


def operation(key: str = "stats.mean", revision: int = 1, method: str = "arithmetic") -> dict:
    return {
        "op": key,
        "revision": revision,
        "method": method,
        "sig": f"{key}(values)",
        "args": [{"name": "values", "semantic": "number", "shape": "vector"}],
        "pack_id": "org.exactscope.statistics-core",
        "pack_version": "0.1.0",
        "pack_binding_sha256": "1" * 64,
    }


def catalog(*operations: dict) -> dict:
    return {"operations": list(operations)}


class OperationRevisionCompatibilityTests(unittest.TestCase):
    def test_metadata_equivalent_profile_revision_advance_is_compatible(self):
        operations = [
            operation("stats.sum"),
            operation("stats.mean"),
            operation("stats.mean.weighted"),
            operation("stats.var.pop"),
            operation("stats.var.sample"),
            operation("stats.sd.pop"),
            operation("stats.sd.sample"),
            operation("stats.corr.pearson"),
        ]
        result = compare_capability_metadata(
            profile(27), catalog(*operations), profile(28), catalog(*copy.deepcopy(operations))
        )
        self.assertEqual(result["status"], "COMPATIBLE")
        self.assertEqual(len(result["unchanged_operations"]), 8)
        self.assertEqual(result["revision_upgrades"], [])
        self.assertFalse(result["evidence_inheritance"])

    def test_same_revision_observable_metadata_drift_is_rejected(self):
        baseline = operation()
        candidate = copy.deepcopy(baseline)
        candidate["method"] = "different-method"
        with self.assertRaisesRegex(RevisionCompatibilityError, "same operation revision changed"):
            compare_capability_metadata(
                profile(1), catalog(baseline), profile(2), catalog(candidate)
            )

    def test_revision_upgrade_requires_explicit_review_and_never_inherits_evidence(self):
        baseline = operation(revision=1)
        candidate = operation(revision=2)
        with self.assertRaisesRegex(RevisionCompatibilityError, "requires explicit review"):
            compare_capability_metadata(
                profile(1), catalog(baseline), profile(2), catalog(candidate)
            )
        result = compare_capability_metadata(
            profile(1), catalog(baseline), profile(2), catalog(candidate),
            allow_revision_upgrade=True,
        )
        self.assertEqual(
            result["revision_upgrades"],
            [{"op": "stats.mean", "from_revision": 1, "to_revision": 2}],
        )
        self.assertFalse(result["evidence_inheritance"])

    def test_removal_and_revision_rollback_are_never_transparent_upgrades(self):
        baseline = catalog(operation("stats.mean", 2), operation("stats.sum", 1, "exact_ordered"))
        with self.assertRaisesRegex(RevisionCompatibilityError, "removes baseline operations"):
            compare_capability_metadata(profile(1), baseline, profile(2), catalog(operation("stats.mean", 2)))
        with self.assertRaisesRegex(RevisionCompatibilityError, "rollback is forbidden"):
            compare_capability_metadata(
                profile(1), catalog(operation(revision=2)), profile(2), catalog(operation(revision=1)),
                allow_revision_upgrade=True,
            )

    def test_changed_bytes_require_new_profile_revision_and_same_profile_identity(self):
        base = catalog(operation())
        with self.assertRaisesRegex(RevisionCompatibilityError, "strictly newer profile revision"):
            compare_capability_metadata(profile(2), base, profile(2), base)
        with self.assertRaisesRegex(RevisionCompatibilityError, "same capability profile id and domain"):
            compare_capability_metadata(profile(1), base, profile(2, profile_id="other"), base)


if __name__ == "__main__":
    unittest.main()
