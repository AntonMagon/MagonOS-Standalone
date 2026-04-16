import tempfile
import unittest
from pathlib import Path

from magon_standalone.russian_comment_contract import added_ru_comment_lines, find_missing_ru_comment_files, is_code_file


class TestRussianCommentContract(unittest.TestCase):
    def test_is_code_file_covers_repo_code_paths(self):
        # RU: Держим карту проверяемых путей явной, чтобы guard не начал молча пропускать новый кодовый слой.
        self.assertTrue(is_code_file("src/magon_standalone/supplier_intelligence/api.py"))
        self.assertTrue(is_code_file("apps/web/components/navigation/site-header.tsx"))
        self.assertTrue(is_code_file("scripts/verify_workflow.sh"))
        self.assertTrue(is_code_file(".githooks/pre-commit"))
        self.assertFalse(is_code_file("docs/ru/code-map.md"))
        self.assertFalse(is_code_file("apps/web/messages/ru.json"))

    def test_added_ru_comment_lines_detects_cyrillic_ru_markers(self):
        # RU: Валидный маркер обязан содержать и `RU:`, и кириллицу, иначе это не русский поясняющий комментарий.
        diff = "\n".join(
            [
                "+++ b/example.py",
                "+# RU: объясняем, почему тут нужен локальный fallback",
                "+value = 1",
                "+# not enough",
            ]
        )
        matches = added_ru_comment_lines(diff)
        self.assertEqual(matches, ["# RU: объясняем, почему тут нужен локальный fallback"])

    def test_find_missing_ru_comment_files_reports_changed_code_without_marker(self):
        # RU: Документация сама по себе не закрывает comment-contract для изменённого кодового файла.
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            code_file = repo_root / "scripts" / "example.py"
            docs_file = repo_root / "docs" / "ru" / "note.md"
            code_file.parent.mkdir(parents=True, exist_ok=True)
            docs_file.parent.mkdir(parents=True, exist_ok=True)
            code_file.write_text("print('x')\n", encoding="utf-8")
            docs_file.write_text("# note\n", encoding="utf-8")

            def fake_diff_provider(_repo_root: Path, path: str) -> str:
                # RU: Тестируем бизнес-логику контракта без привязки к реальному git index временной директории.
                if path == "scripts/example.py":
                    return "+++ b/scripts/example.py\n+print('x')\n"
                return "+++ b/docs/ru/note.md\n+# note\n"

            missing = find_missing_ru_comment_files(
                repo_root,
                staged_files=["scripts/example.py", "docs/ru/note.md"],
                diff_provider=fake_diff_provider,
            )

            self.assertEqual(missing, ["scripts/example.py"])
