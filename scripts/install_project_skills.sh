#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST_DIR="$CODEX_HOME/skills"

# RU: Этот installer не копирует skills, а линкует их из репозитория, чтобы проект оставался single source of truth.
mkdir -p "$DEST_DIR"

installed=0

while IFS= read -r skill_file; do
  skill_dir="$(dirname "$skill_file")"
  skill_name="$(basename "$skill_dir")"
  target="$DEST_DIR/$skill_name"

  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "install_project_skills: $target exists and is not a symlink; refusing to overwrite" >&2
    exit 1
  fi

  ln -sfn "$skill_dir" "$target"
  printf 'linked %s -> %s\n' "$target" "$skill_dir"
  installed=$((installed + 1))
done < <(find "$REPO_ROOT/skills" -mindepth 2 -maxdepth 2 -name 'SKILL.md' | sort)

printf 'Installed %d project skills into %s\n' "$installed" "$DEST_DIR"
printf 'Restart Codex to pick up newly linked skills.\n'
