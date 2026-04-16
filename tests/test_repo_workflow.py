import unittest

from magon_standalone.repo_workflow import FinalizeRecord, update_project_memory


class TestRepoWorkflow(unittest.TestCase):
    def test_update_project_memory_replaces_active_block_and_prepends_worklog(self):
        original = """# Project Memory

## Active Context
<!-- ACTIVE:START -->
- Updated at: `old`
- Branch: `old`
- Current focus: old
- Last verified workflow status: old
- Biggest operational risk: old
<!-- ACTIVE:END -->

## Recent Worklog
<!-- WORKLOG:START -->
### older
- Summary: older
<!-- WORKLOG:END -->
"""
        record = FinalizeRecord(
            timestamp_label="2026-04-17 11:20 ICT",
            branch="develop",
            summary="tighten repo workflow",
            changed=[".codex/project-memory.md", ".githooks/pre-commit"],
            verified=["PASS `./scripts/verify_workflow.sh`"],
            risk="push is still an explicit manual step",
            focus="enforce repo memory and hooks",
        )

        updated = update_project_memory(original, record)

        self.assertIn("- Branch: `develop`", updated)
        self.assertIn("- Current focus: enforce repo memory and hooks", updated)
        self.assertIn("### 2026-04-17 11:20 ICT | develop", updated)
        self.assertIn("  - .codex/project-memory.md", updated)
        self.assertIn("  - PASS `./scripts/verify_workflow.sh`", updated)
        self.assertLess(updated.index("### 2026-04-17 11:20 ICT | develop"), updated.index("### older"))

    def test_update_project_memory_requires_markers(self):
        record = FinalizeRecord(
            timestamp_label="2026-04-17 11:20 ICT",
            branch="develop",
            summary="tighten repo workflow",
            changed=["x"],
            verified=["PASS `cmd`"],
            risk="none",
            focus="focus",
        )

        with self.assertRaises(ValueError):
            update_project_memory("# no markers here", record)
