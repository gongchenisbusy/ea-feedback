from __future__ import annotations

import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDER = _load("render_feedback_report", ROOT / "scripts" / "render_feedback_report.py")
SUBMIT = _load("submit_feedback", ROOT / "scripts" / "submit_feedback.py")


class RenderAndSubmitTest(unittest.TestCase):
    def test_current_pass_does_not_turn_old_failure_into_p1(self) -> None:
        context = {
            "user_notes": "",
            "installed_ea_skills": [],
            "ea_cli_discovery": {"status": "available", "source": "project_virtualenv"},
            "ea_projects": [
                {
                    "root": "project",
                    "counts": {},
                    "reviews": {"statuses": {}},
                    "potential_findings": [{"path": "evaluation/old.yml", "line": "status: failed"}],
                    "current_validation": {"status": "pass", "ref": "evaluation/current.yml"},
                    "execution_events": {
                        "events": [
                            {
                                "stage": "health",
                                "status": "failed",
                                "history_state": "resolved_historical",
                            },
                            {"stage": "health", "status": "recovered", "history_state": "current"},
                        ]
                    },
                    "config_excerpt": "",
                }
            ],
        }

        titles = [item["title"] for item in RENDER.detect_issues(context)]

        self.assertNotIn("Existing EA artifacts contain error or warning signals", titles)
        self.assertNotIn("Current or unreconciled EA execution events need attention", titles)

    def test_public_body_and_email_draft_are_utf8_verified(self) -> None:
        body = "# EA Feedback Report: EA-FB-20260715-120000-demo\n\n中文 — → `code`\n"
        validation = SUBMIT.validate_public_body(body)
        self.assertEqual(validation["status"], "pass")

        with tempfile.TemporaryDirectory() as directory:
            draft = SUBMIT.write_email_draft(
                feedback_id="EA-FB-20260715-120000-demo",
                title="反馈 — verified",
                body=body,
                draft_dir=Path(directory),
            )
            self.assertEqual(draft["preparation_status"], "draft_prepared")
            self.assertEqual(draft["verification_status"], "draft_verified")
            self.assertEqual(Path(draft["path"]).read_text(encoding="utf-8").count("中文"), 1)

    def test_no_gh_fallback_reports_verified_email_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            report.write_text(
                "# EA Feedback Report: EA-FB-20260715-120000-demo\n\nPublic-safe body.\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(
                report=str(report),
                body_file=None,
                no_redact=False,
                feedback_id=None,
                title=None,
                repo=SUBMIT.DEFAULT_REPO,
                dry_run=False,
                github_mode="disabled",
                timeout=1,
                email_mode="draft",
                email_draft_dir=directory,
                email_to=SUBMIT.DEFAULT_EMAIL,
            )

            result = SUBMIT.submit(args)

            self.assertEqual(result["status"], "email_draft_verified")
            self.assertEqual(result["email"]["verification_status"], "draft_verified")
            self.assertEqual(result["github_failure"]["stage"], "disabled")


if __name__ == "__main__":
    unittest.main()
