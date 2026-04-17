import tempfile
import unittest
from pathlib import Path

from magon_standalone.automation_contract import scan_automation_contract


VALID_AUTOMATION = """version = 1
id = "repo-guard-2h"
kind = "cron"
name = "Repo Guard 2h"
prompt = "Use [$automation-context-guard](/Users/anton/Desktop/MagonOS-Standalone/skills/automation-context-guard/SKILL.md) first."
status = "ACTIVE"
rrule = "FREQ=HOURLY;INTERVAL=2"
model = "gpt-5.4-mini"
reasoning_effort = "medium"
execution_environment = "local"
cwds = ["/Users/anton/Desktop/MagonOS-Standalone"]
"""


class TestAutomationContract(unittest.TestCase):
    def test_scan_automation_contract_accepts_valid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            automation_dir = root / "repo-guard-2h"
            automation_dir.mkdir(parents=True, exist_ok=True)
            (automation_dir / "automation.toml").write_text(VALID_AUTOMATION, encoding="utf-8")

            self.assertEqual(scan_automation_contract(root), [])

    def test_scan_automation_contract_rejects_missing_context_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            automation_dir = root / "repo-guard-2h"
            automation_dir.mkdir(parents=True, exist_ok=True)
            # RU: Этот тест страхует главный meta-contract automation layer: если prompt больше не тянет automation-context-guard, расписание уже живёт вне общего контекста проекта.
            (automation_dir / "automation.toml").write_text(
                VALID_AUTOMATION.replace("Use [$automation-context-guard](/Users/anton/Desktop/MagonOS-Standalone/skills/automation-context-guard/SKILL.md) first.", "No context here."),
                encoding="utf-8",
            )

            issues = scan_automation_contract(root)
            self.assertIn(
                "repo-guard-2h/automation.toml: prompt must reference automation-context-guard",
                issues,
            )

    def test_scan_automation_contract_rejects_wrong_cwd_and_rrule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            automation_dir = root / "repo-guard-2h"
            automation_dir.mkdir(parents=True, exist_ok=True)
            broken = VALID_AUTOMATION.replace(
                'cwds = ["/Users/anton/Desktop/MagonOS-Standalone"]',
                'cwds = ["/tmp/other"]',
            ).replace(
                'rrule = "FREQ=HOURLY;INTERVAL=2"',
                'rrule = "FREQ=DAILY;INTERVAL=1"',
            )
            (automation_dir / "automation.toml").write_text(broken, encoding="utf-8")

            issues = scan_automation_contract(root)

            self.assertIn(
                "repo-guard-2h/automation.toml: cwds must contain exactly the standalone repo root",
                issues,
            )
            self.assertIn(
                "repo-guard-2h/automation.toml: rrule must stay within supported hourly or weekly cron shapes",
                issues,
            )


if __name__ == "__main__":
    unittest.main()
