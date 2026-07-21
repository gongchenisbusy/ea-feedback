from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "collect_ea_context.py"
SPEC = importlib.util.spec_from_file_location("collect_ea_context", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LiteratureStatusCollectorTest(unittest.TestCase):
    def test_installed_skill_discovery_defaults_to_active_install_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            active = home / ".codex" / "skills" / "ea" / "SKILL.md"
            backup = home / ".codex" / "skills" / "backups" / "ea-old" / "SKILL.md"
            feedback = home / ".codex" / "skills" / "ea-feedback" / "SKILL.md"
            active.parent.mkdir(parents=True)
            backup.parent.mkdir(parents=True)
            feedback.parent.mkdir(parents=True)
            active.write_text("---\nname: ea\n---\nExperimental Assistant active\n", encoding="utf-8")
            backup.write_text("---\nname: ea\n---\nExperimental Assistant backup\n", encoding="utf-8")
            feedback.write_text("---\nname: ea-feedback\n---\nExperimental Assistant feedback\n", encoding="utf-8")

            with mock.patch.object(Path, "home", return_value=home):
                default = MODULE.find_installed_ea_skills()
                with_backups = MODULE.find_installed_ea_skills(include_backups=True)

            self.assertEqual([item["path"] for item in default], [str(active)])
            self.assertEqual(len(with_backups), 2)
            self.assertTrue(default[0]["active_install"])

    def test_local_context_collection_does_not_probe_github_auth(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            calls: list[list[str]] = []

            def fake_run(args, cwd, timeout=10):
                calls.append(args)
                return {"command": args, "returncode": 0}

            with (
                mock.patch.object(MODULE, "run_command", side_effect=fake_run),
                mock.patch.object(MODULE, "discover_ea_cli", return_value={"status": "unknown", "probe": None}),
                mock.patch.object(MODULE, "find_ea_projects", return_value=[]),
                mock.patch.object(MODULE, "find_installed_ea_skills", return_value=[]),
            ):
                context = MODULE.build_context(workspace)

            self.assertEqual(calls, [["git", "status", "--short"]])
            self.assertNotIn("gh_auth_status", context["commands"])

    def test_structured_warning_codes_are_not_runtime_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            reports = project / "reports"
            reports.mkdir()
            (reports / "warning-only.yml").write_text(
                "status: pass\nwarning_count: 1\nwarning_codes:\n- optional_literature_missing\nfindings:\n- severity: warning\n",
                encoding="utf-8",
            )

            self.assertEqual(MODULE.scan_findings(project), [])

    def test_collects_only_status_sidecars_and_counts_mixed_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            literature = project / "literature"
            literature.mkdir()
            (literature / "acquisition_status_batch.json").write_text(
                json.dumps(
                    {
                        "targets": [
                            {"status": "acquired"},
                            {"status": "cache_verified"},
                            {"status": "needs_login"},
                            {"status": "needs_subscription"},
                            {"status": "blocked"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (literature / "private-paper.pdf").write_bytes(b"%PDF-secret-fulltext")
            (literature / "cookies.json").write_text('{"cookie": "secret"}', encoding="utf-8")
            (literature / "acquisition_status_batch.md").write_text(
                "| DOI | title | status |\n|---|---|---|\n| 10.test/duplicate | duplicate | blocked |\n",
                encoding="utf-8",
            )

            summary = MODULE.summarize_literature_acquisition(project)

            self.assertEqual(summary["acquired"], 2)
            self.assertEqual(summary["blocked"], 3)
            self.assertEqual(summary["status_refs"], ["literature/acquisition_status_batch.json"])
            self.assertNotIn("secret", json.dumps(summary))

    def test_utf8_subprocess_output_survives_non_utf8_parent_locale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "utf8_output.py"
            script.write_text(
                'import sys\nsys.stdout.buffer.write("中文 — → `code`".encode("utf-8"))\n',
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"PYTHONIOENCODING": "gbk"}):
                result = MODULE.run_command([sys.executable, str(script)], Path(directory))

            self.assertEqual(result["returncode"], 0)
            self.assertEqual(result["stdout"], "中文 — → `code`")

    def test_cli_discovery_prefers_explicit_ea_bin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "ea_probe.py"
            script.write_text('print("EA v0.9.8 中文")\n', encoding="utf-8")
            explicit = f'"{sys.executable}" "{script}"'
            with mock.patch.dict(os.environ, {"EA_BIN": explicit}):
                result = MODULE.discover_ea_cli(Path(directory))

            self.assertEqual(result["status"], "available")
            self.assertEqual(result["source"], "explicit_EA_BIN")
            self.assertIn("v0.9.8", result["probe"]["stdout"])

    def test_execution_events_reconcile_old_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            events_dir = project / ".ea"
            events_dir.mkdir()
            (events_dir / "execution_events.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "event_id": "attempt-1",
                                "scope_id": "health-run",
                                "stage": "health",
                                "status": "failed",
                                "attempt": 1,
                                "error_code": "old_fail",
                                "occurred_at": "2026-07-01T00:00:00Z",
                            },
                            {
                                "event_id": "attempt-2",
                                "scope_id": "health-run",
                                "stage": "health",
                                "status": "recovered",
                                "attempt": 2,
                                "supersedes": ["attempt-1"],
                                "artifact_count": 3,
                                "occurred_at": "2026-07-01T00:05:00Z",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            collected = MODULE.collect_execution_events(project)

            states = {event["event_id"]: event["history_state"] for event in collected["events"]}
            self.assertEqual(states, {"attempt-1": "resolved_historical", "attempt-2": "current"})
            self.assertEqual(collected["summary"]["resolved_historical"], 1)


if __name__ == "__main__":
    unittest.main()
