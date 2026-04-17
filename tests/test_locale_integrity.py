import tempfile
import unittest
from pathlib import Path

from magon_standalone.locale_integrity import (
    detect_discouraged_copy,
    detect_forbidden_leaks,
    extract_visible_text,
    scan_runtime_routes,
    scan_source_files,
)


class TestLocaleIntegrity(unittest.TestCase):
    def test_detect_forbidden_leaks_is_case_insensitive(self):
        # RU: Явные доменные ярлыки должны ловиться независимо от регистра, иначе утечка легко пройдёт через "Company" или "AUTOMATIONS".
        matches = detect_forbidden_leaks("Company + AUTOMATIONS + review queue")
        self.assertEqual(matches, ["automations", "company", "review queue"])

    def test_extract_visible_text_drops_script_noise(self):
        html = """
        <html>
          <head><script>const leaked = "company";</script></head>
          <body><h1>Компания</h1><p>Очередь проверки</p></body>
        </html>
        """
        visible = extract_visible_text(html)
        self.assertIn("Компания", visible)
        self.assertNotIn("company", visible)

    def test_detect_discouraged_copy_flags_technical_russian_mixed_phrases(self):
        # RU: Даже без прямой английской бизнес-утечки guard должен резать phrases вроде worklog/scope guard, потому что это плохой русский для пользовательского слоя.
        matches = detect_discouraged_copy("В этом worklog ещё остался scope guard и technical log")
        self.assertEqual(matches, ["scope guard", "technical log", "worklog"])

    def test_scan_source_files_reports_forbidden_english_in_ru_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            target = repo_root / "apps" / "web" / "messages" / "ru.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('{"title":"Automations и company"}', encoding="utf-8")

            issues = scan_source_files(repo_root, ("apps/web/messages/ru.json",))

            self.assertEqual(
                issues,
                [
                    "apps/web/messages/ru.json: forbidden English locale leak `automations`",
                    "apps/web/messages/ru.json: forbidden English locale leak `company`",
                ],
            )

    def test_scan_source_files_reports_discouraged_copy_phrases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            target = repo_root / "docs" / "ru" / "current-project-state.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Здесь внезапно остался worklog и project-memory dump", encoding="utf-8")

            issues = scan_source_files(repo_root, ("docs/ru/current-project-state.md",))

            self.assertEqual(
                issues,
                [
                    "docs/ru/current-project-state.md: discouraged Russian copy phrase `project-memory dump`",
                    "docs/ru/current-project-state.md: discouraged Russian copy phrase `worklog`",
                ],
            )

    def test_scan_runtime_routes_reports_visible_leaks(self):
        html_map = {
            "http://127.0.0.1:3000/": "<html><body><h1>Компания</h1></body></html>",
            "http://127.0.0.1:3000/project-map": "<html><body><h1>review queue</h1></body></html>",
        }

        def fake_fetcher(url: str) -> str:
            return extract_visible_text(html_map[url])

        issues = scan_runtime_routes(
            "http://127.0.0.1:3000",
            routes=("/", "/project-map"),
            fetcher=fake_fetcher,
        )

        self.assertEqual(
            issues,
            ["http://127.0.0.1:3000/project-map: forbidden English locale leak `review queue`"],
        )

    def test_scan_runtime_routes_reports_discouraged_copy(self):
        html_map = {
            "http://127.0.0.1:3000/": "<html><body><h1>Нормально</h1></body></html>",
            "http://127.0.0.1:3000/project-map": "<html><body><h1>worklog</h1></body></html>",
        }

        def fake_fetcher(url: str) -> str:
            return extract_visible_text(html_map[url])

        issues = scan_runtime_routes(
            "http://127.0.0.1:3000",
            routes=("/", "/project-map"),
            fetcher=fake_fetcher,
        )

        self.assertEqual(
            issues,
            ["http://127.0.0.1:3000/project-map: discouraged Russian copy phrase `worklog`"],
        )


if __name__ == "__main__":
    unittest.main()
