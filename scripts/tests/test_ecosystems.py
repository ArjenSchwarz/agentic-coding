"""Schema checks for scripts/ecosystems.json.

The file is read by ``blast_radius.py`` (extensions, test files, imports,
units, tools) and by the review skills (runners, notes). Both sets of keys
are validated here so a row that renders diagrams but breaks recipe
selection, or the reverse, fails ``make test``.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ECOSYSTEMS = Path(__file__).resolve().parents[1] / "ecosystems.json"

UNIT_KINDS = {"directory", "target_root", "module_file"}
RESOLVERS = {"relative", "roots", "unit"}
TOOL_FORMATS = {"go-list-json", "pairs"}
COVERAGE_FORMATS = {"lcov", "cobertura", "coverprofile"}
PLACEHOLDERS = {"junit", "coverage", "inputs"}
DETECT_KEYS = {"files", "package_json_keys"}
ROWS_WITH_RUNNERS = {"go", "python", "typescript", "swift", "rust"}

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value)


class EcosystemsSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(ECOSYSTEMS.read_text(encoding="utf-8"))

    def rows(self):
        for name, row in self.data.items():
            with self.subTest(row=name):
                yield name, row

    # --- keys the script reads ---------------------------------------------

    def test_file_is_an_object_of_rows(self) -> None:
        self.assertIsInstance(self.data, dict)
        self.assertTrue(self.data)
        for name, row in self.rows():
            self.assertIsInstance(row, dict, name)

    def test_required_script_keys(self) -> None:
        for name, row in self.rows():
            self.assertTrue(_is_str_list(row.get("extensions")) and row["extensions"], name)
            for ext in row["extensions"]:
                self.assertTrue(ext.startswith("."), f"{name}: extension {ext!r} lacks a dot")
            self.assertTrue(_is_str_list(row.get("test_files")) and row["test_files"], name)
            self.assertIn("unit", row, name)
            self.assertTrue("imports" in row or "notes" in row,
                            f"{name}: needs imports or notes explaining their absence")

    def test_extensions_are_unique_across_rows(self) -> None:
        seen = {}
        for name, row in self.data.items():
            for ext in row["extensions"]:
                self.assertNotIn(ext, seen, f"{ext} claimed by both {seen.get(ext)} and {name}")
                seen[ext] = name

    def test_unit_rules(self) -> None:
        for name, row in self.rows():
            unit = row["unit"]
            self.assertIsInstance(unit, dict, name)
            self.assertIn(unit.get("kind"), UNIT_KINDS, name)
            if unit["kind"] == "module_file":
                self.assertIsInstance(unit.get("module_file"), str, name)
                re.compile(unit["module_regex"])
            if unit["kind"] == "target_root":
                self.assertIsInstance(unit.get("target_root"), str, name)

    def test_every_regex_compiles(self) -> None:
        for name, row in self.rows():
            for pattern in row["test_files"]:
                re.compile(pattern)
            if row.get("test_decl"):
                re.compile(row["test_decl"], re.MULTILINE)
            for spec in row.get("imports", []):
                re.compile(spec["regex"], re.MULTILINE)

    def test_test_decl_has_at_most_one_group(self) -> None:
        for name, row in self.rows():
            if row.get("test_decl"):
                self.assertLessEqual(re.compile(row["test_decl"]).groups, 1, name)

    def test_import_specs(self) -> None:
        for name, row in self.rows():
            imports = row.get("imports", [])
            self.assertIsInstance(imports, list, name)
            for spec in imports:
                self.assertIsInstance(spec, dict, name)
                self.assertIsInstance(spec.get("regex"), str, name)
                self.assertIn(spec.get("resolve", "relative"), RESOLVERS, name)
                if "separator" in spec:
                    self.assertIsInstance(spec["separator"], str, name)
                if spec.get("resolve") == "roots":
                    self.assertTrue(_is_str_list(row.get("source_roots")), f"{name}: roots needs source_roots")

    def test_optional_resolver_inputs(self) -> None:
        for name, row in self.rows():
            for key in ("source_roots", "index_files"):
                if key in row:
                    self.assertTrue(_is_str_list(row[key]), f"{name}.{key}")
            if "extension_map" in row:
                self.assertIsInstance(row["extension_map"], dict, name)
                for ext, alternatives in row["extension_map"].items():
                    self.assertTrue(ext.startswith("."), f"{name}: {ext}")
                    self.assertTrue(_is_str_list(alternatives), f"{name}: {ext}")

    def test_tool_rows(self) -> None:
        for name, row in self.rows():
            tool = row.get("tool")
            if tool is None:
                continue
            self.assertIsInstance(tool, dict, name)
            self.assertIsInstance(tool.get("name"), str, name)
            self.assertIsInstance(tool.get("deps"), str, name)
            self.assertIn(tool.get("format"), TOOL_FORMATS, name)
            self.assertIn(tool.get("granularity"), {"file", "package"}, name)

    def test_notes_are_strings(self) -> None:
        for name, row in self.rows():
            if "notes" in row:
                self.assertTrue(_is_str_list(row["notes"]), name)

    # --- keys the agent reads ----------------------------------------------

    def test_known_rows_declare_runners(self) -> None:
        for name in sorted(ROWS_WITH_RUNNERS):
            with self.subTest(row=name):
                self.assertIn(name, self.data)
                self.assertTrue(self.data[name].get("runners"), f"{name}: no runners")

    def test_runner_shape(self) -> None:
        for name, row in self.rows():
            runners = row.get("runners", [])
            self.assertIsInstance(runners, list, name)
            names = [r.get("name") for r in runners]
            self.assertEqual(len(names), len(set(names)), f"{name}: duplicate runner names")
            for runner in runners:
                label = f"{name}/{runner.get('name')}"
                self.assertIsInstance(runner, dict, label)
                self.assertTrue(isinstance(runner.get("name"), str) and runner["name"], label)
                self.assertIsInstance(runner.get("recipe"), str, label)
                self.assertTrue(runner["recipe"].strip(), label)
                self.assertTrue(_is_str_list(runner.get("requires")) and runner["requires"], label)
                self.assertIn(runner.get("coverage_format"), COVERAGE_FORMATS, label)
                self.assertIsInstance(runner.get("install"), str, label)
                self.assertTrue(_is_str_list(runner.get("junit_flags")) and runner["junit_flags"], label)
                # Alternate spellings are allowed, but the recipe must use one of them.
                self.assertTrue(any(flag in runner["recipe"] for flag in runner["junit_flags"]),
                                f"{label}: none of junit_flags appear in its own recipe")

    def test_runner_detection_rules(self) -> None:
        for name, row in self.rows():
            for runner in row.get("runners", []):
                label = f"{name}/{runner.get('name')}"
                detect = runner.get("detect")
                self.assertIsInstance(detect, dict, label)
                self.assertTrue(set(detect) & DETECT_KEYS, f"{label}: detect needs files or package_json_keys")
                self.assertFalse(set(detect) - DETECT_KEYS, f"{label}: unknown detect keys")
                for key, value in detect.items():
                    self.assertTrue(_is_str_list(value) and value, f"{label}: detect.{key}")

    def test_recipes_use_only_known_placeholders(self) -> None:
        for name, row in self.rows():
            for runner in row.get("runners", []):
                label = f"{name}/{runner.get('name')}"
                texts = [runner["recipe"], runner.get("install", "")]
                texts += list((runner.get("env") or {}).values())
                texts += list((runner.get("config_files") or {}).values())
                for text in texts:
                    used = set(_PLACEHOLDER.findall(text))
                    self.assertFalse(used - PLACEHOLDERS, f"{label}: unknown placeholders {used - PLACEHOLDERS}")
                # {junit} must land somewhere: the recipe, an env value, or a config template.
                self.assertIn("{junit}", " ".join(texts), f"{label}: recipe never names {{junit}}")

    def test_env_and_config_files_are_objects_of_strings(self) -> None:
        for name, row in self.rows():
            for runner in row.get("runners", []):
                label = f"{name}/{runner.get('name')}"
                for key in ("env", "config_files"):
                    if key in runner:
                        self.assertIsInstance(runner[key], dict, f"{label}.{key}")
                        for k, v in runner[key].items():
                            self.assertIsInstance(k, str, f"{label}.{key}")
                            self.assertIsInstance(v, str, f"{label}.{key}.{k}")
                for template in (runner.get("config_files") or {}):
                    self.assertIn(template, runner["recipe"],
                                  f"{label}: config file {template!r} is written but never passed")


if __name__ == "__main__":
    unittest.main()
