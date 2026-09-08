import unittest

from llama_cpp_interface import (
    InterfaceSelectionError,
    normalize_runtime_props,
    select_model_interface,
)


class LlamaCppInterfaceTests(unittest.TestCase):
    def tool_aware_record(self):
        return normalize_runtime_props({
            "supports_tools": True,
            "supports_tool_calls": True,
            "supports_object_arguments": True,
            "supports_parallel_tool_calls": True,
            "chat_template": "tool aware template",
            "chat_template_tool_use": "tool use template",
        })

    def test_auto_selects_native_only_when_all_required_capabilities_are_proven(self):
        selection = select_model_interface("auto", self.tool_aware_record())
        self.assertEqual(selection["resolved"], "native_tools")
        self.assertEqual(selection["selection_phase"], "pre-inference")
        self.assertEqual(selection["fallback"], "none")
        self.assertEqual(selection["missing_or_unproven_native_capabilities"], [])

    def test_auto_selects_constrained_when_native_capability_is_false(self):
        record = normalize_runtime_props({
            "supports_tools": True,
            "supports_tool_calls": False,
            "supports_object_arguments": True,
        })
        selection = select_model_interface("auto", record)
        self.assertEqual(selection["resolved"], "constrained_json")
        self.assertEqual(selection["missing_or_unproven_native_capabilities"], ["supports_tool_calls"])

    def test_auto_selects_constrained_when_native_capability_is_unknown(self):
        record = normalize_runtime_props({"chat_template": "no capability booleans"})
        selection = select_model_interface("auto", record)
        self.assertEqual(selection["resolved"], "constrained_json")
        self.assertEqual(
            selection["missing_or_unproven_native_capabilities"],
            ["supports_tools", "supports_tool_calls", "supports_object_arguments"],
        )

    def test_explicit_native_fails_closed_when_support_is_not_proven(self):
        record = normalize_runtime_props({
            "supports_tools": True,
            "supports_tool_calls": True,
            "supports_object_arguments": False,
        })
        with self.assertRaisesRegex(InterfaceSelectionError, "supports_object_arguments"):
            select_model_interface("native_tools", record)

    def test_explicit_constrained_does_not_require_native_support(self):
        record = normalize_runtime_props({
            "supports_tools": False,
            "supports_tool_calls": False,
            "supports_object_arguments": False,
        })
        selection = select_model_interface("constrained_json", record)
        self.assertEqual(selection["resolved"], "constrained_json")
        self.assertEqual(selection["fallback"], "none")

    def test_explicit_constrained_can_skip_runtime_probe_entirely(self):
        selection = select_model_interface("constrained_json", None)
        self.assertEqual(selection["resolved"], "constrained_json")
        self.assertIsNone(selection["runtime_capabilities"])
        self.assertIn("probe not required", selection["selection_reason"])

    def test_nested_capability_fields_and_template_digests_are_normalized(self):
        record = normalize_runtime_props({
            "runtime": {
                "supports_tools": True,
                "supports_tool_calls": True,
                "supports_object_arguments": True,
                "chat_template": "nested template",
            }
        })
        self.assertEqual(record["capabilities"]["supports_tools"], True)
        self.assertEqual(record["source_paths"]["supports_tools"], "$.runtime.supports_tools")
        self.assertRegex(record["props_sha256"], r"^[a-f0-9]{64}$")
        self.assertRegex(record["chat_template_sha256"], r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
