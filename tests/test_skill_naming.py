import tempfile
import unittest
from pathlib import Path

from magon_standalone.skill_naming import extract_frontmatter_name, scan_skill_names


class TestSkillNaming(unittest.TestCase):
    def test_extract_frontmatter_name_reads_name(self):
        # RU: Frontmatter name должен читаться отдельно от markdown heading, иначе repo guard не сможет сравнить skill metadata с именем папки.
        content = """---
name: audit-docs-vs-runtime
description: test
---

# heading
"""
        self.assertEqual(extract_frontmatter_name(content), "audit-docs-vs-runtime")

    def test_scan_skill_names_accepts_valid_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            skill_dir = repo_root / "skills" / "verify-platform"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                """---
name: verify-platform
description: test
---

# verify-platform
""",
                encoding="utf-8",
            )

            self.assertEqual(scan_skill_names(repo_root), [])

    def test_scan_skill_names_rejects_bad_prefix_and_name_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            skill_dir = repo_root / "skills" / "random-helper"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                """---
name: audit-helper
description: test
---

# random-helper
""",
                encoding="utf-8",
            )

            issues = scan_skill_names(repo_root)

            self.assertIn(
                "skills/random-helper: skill prefix `random` is not in the allowed naming contract",
                issues,
            )
            self.assertIn(
                "skills/random-helper/SKILL.md: frontmatter name `audit-helper` must match directory name `random-helper`",
                issues,
            )


if __name__ == "__main__":
    unittest.main()
