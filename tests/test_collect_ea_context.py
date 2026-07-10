from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "collect_ea_context.py"
SPEC = importlib.util.spec_from_file_location("collect_ea_context", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LiteratureStatusCollectorTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
