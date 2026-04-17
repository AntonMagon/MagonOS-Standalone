"""Validation helpers for repo-local skill naming."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ALLOWED_PREFIXES = {
    "audit",
    "automation",
    "ci",
    "docs",
    "donor",
    "git",
    "operate",
    "project",
    "release",
    "skill",
    "verify",
    "web",
}
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){1,3}$")
FRONTMATTER_NAME_PATTERN = re.compile(r"^name:\s*(.+)$", re.M)


@dataclass(frozen=True)
class SkillNamingIssue:
    path: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.message}"


def extract_frontmatter_name(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    frontmatter = text[4:end]
    match = FRONTMATTER_NAME_PATTERN.search(frontmatter)
    return match.group(1).strip() if match else None


def validate_skill_dir(skill_dir: Path, repo_root: Path) -> list[SkillNamingIssue]:
    issues: list[SkillNamingIssue] = []
    relative_dir = skill_dir.relative_to(repo_root).as_posix()
    skill_name = skill_dir.name
    parts = skill_name.split("-")
    skill_file = skill_dir / "SKILL.md"

    if not SKILL_NAME_PATTERN.match(skill_name):
        issues.append(
            SkillNamingIssue(
                relative_dir,
                "skill directory must be lowercase kebab-case with 2-4 tokens",
            )
        )
    if parts[0] not in ALLOWED_PREFIXES:
        # RU: Первый токен закрепляем как тип действия, чтобы repo-local skills не расползались в хаотичные названия без общего словаря.
        issues.append(
            SkillNamingIssue(
                relative_dir,
                f"skill prefix `{parts[0]}` is not in the allowed naming contract",
            )
        )
    if len(parts) < 2 or len(parts) > 4:
        issues.append(
            SkillNamingIssue(
                relative_dir,
                "skill name must contain between 2 and 4 kebab-case tokens",
            )
        )
    if not skill_file.is_file():
        issues.append(SkillNamingIssue(relative_dir, "missing SKILL.md"))
        return issues

    frontmatter_name = extract_frontmatter_name(skill_file.read_text(encoding="utf-8"))
    if not frontmatter_name:
        issues.append(SkillNamingIssue(skill_file.relative_to(repo_root).as_posix(), "missing frontmatter `name`"))
    elif frontmatter_name != skill_name:
        issues.append(
            SkillNamingIssue(
                skill_file.relative_to(repo_root).as_posix(),
                f"frontmatter name `{frontmatter_name}` must match directory name `{skill_name}`",
            )
        )

    return issues


def scan_skill_names(repo_root: Path) -> list[str]:
    issues: list[str] = []
    for skill_file in sorted((repo_root / "skills").glob("*/SKILL.md")):
        for issue in validate_skill_dir(skill_file.parent, repo_root):
            issues.append(issue.render())
    return issues
