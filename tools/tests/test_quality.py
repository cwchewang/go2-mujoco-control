"""Repository hygiene fixtures; no experiment code is imported or executed."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.check_quality import check_syntax, source_paths
from tools.check_repo_hygiene import check_markdown_links


class QualityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def put(self, name, text, tracked=True):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if tracked:
            subprocess.run(["git", "add", "--", name], cwd=self.root, check=True)

    def test_ignores_raw_dependencies_and_retained_experiment_sources(self):
        self.put("tools/safe.py", "raise RuntimeError('never execute')\n")
        self.put("_runs/raw/broken.py", "invalid (", tracked=False)
        self.put(".substrate/dependency/broken.py", "invalid (", tracked=False)
        self.put("example/cpp/experiments/old/fixture.py", "invalid (")
        names = source_paths(self.root)
        self.assertEqual(names, ["tools/safe.py"])
        self.assertEqual(check_syntax(self.root, names), [])
        self.assertFalse(list(self.root.rglob("*.pyc")))

    def test_syntax_errors_are_reported_without_running_scripts(self):
        self.put("tools/bad.py", "def incomplete(")
        self.put("scripts/bad.sh", "if then\n")
        errors = check_syntax(self.root, source_paths(self.root))
        self.assertEqual(len(errors), 2)

    def test_local_links_must_resolve_to_tracked_paths(self):
        self.put("docs/guide.md", "guide")
        self.put("_runs/private.md", "not portable", tracked=False)
        problems = []
        check_markdown_links(
            self.root,
            "README.md",
            "[valid](docs/guide.md) [bad](_runs/private.md)",
            problems,
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("untracked", problems[0])

    def test_local_links_cannot_escape_checkout(self):
        problems = []
        check_markdown_links(
            self.root, "README.md", "[outside](../elsewhere.md)", problems
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("outside", problems[0])


if __name__ == "__main__":
    unittest.main()
