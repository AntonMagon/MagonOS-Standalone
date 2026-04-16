# Workflow репозитория

## Зачем это есть

В проекте уже были правила, но они были только текстом.
Этот workflow нужен, чтобы контекст проекта:
- не терялся между сессиями
- не оставался только в голове
- не зависел от ручного пересказа
- не считался "сделанным", пока изменения не проверены и не запушены

## Обязательные точки входа

Перед существенной задачей:

```bash
./scripts/restore_context.sh
```

После существенной задачи:

```bash
./.venv/bin/python scripts/finalize_task.py --summary "..." --changed "..." --verify "./scripts/verify_workflow.sh"
```

Этот шаг теперь не только пишет `.codex/project-memory.md`, но и автоматически пересобирает корневые `AGENTS.md` и `README.md`.

## Что обязательно синхронизировать

- `AGENTS.md`
- `README.md`
- `docs/current-project-state.md`
- `docs/ru/README.md`
- `docs/ru/current-project-state.md`
- `.codex/config.toml`
- `.codex/project-memory.md`
- `docs/repo-workflow.md`

Корневые `AGENTS.md` и `README.md` считаются живыми operating docs и должны совпадать с текущим состоянием репозитория.

## Что требуют git hooks

### pre-commit

Если staged product-owned файлы изменились, то в том же коммите обязательно должны быть:
- обновление `.codex/project-memory.md`
- обновление хотя бы одного файла в `docs/ru/`
- хотя бы одна добавленная строка с `RU:` и русским текстом в каждом изменённом кодовом файле

### pre-push

Перед push обязательно проходит:
- `./scripts/verify_workflow.sh`
- `cd apps/web && npm run typecheck`, если в исходящем диапазоне есть `apps/web/`

Внутри `verify_workflow` теперь дополнительно проверяется, что `AGENTS.md` и `README.md` не отстали от project memory, skills и automation state.

## Что теперь автоматизируется по изменению файлов

В репозитории добавлен отдельный локальный autosync-контур:
- Watchman следит за source-of-truth путями
- trigger запускает `scripts/run_repo_autosync.py`
- autosync пересобирает root docs и visual map
- autosync потом прогоняет `verify_workflow` или `verify_workflow --with-web`

Точки входа:

```bash
./scripts/install_repo_automation.sh
./scripts/repo_automation_status.sh
task autosync:watch
```

Ограничение остаётся честным:
- этот слой не заменяет commit/push
- этот слой не даёт настоящего event-driven запуска skills внутри Codex
- он автоматизирует именно repo-native действия поверх сохранения файлов

## Что считается обязательным русским слоем

- русская документация в `docs/ru/`
- русские комментарии/docstrings в неочевидной изменённой логике
- явный `RU:` marker в staged diff изменённого кодового файла

Если меняется код, а русский слой не меняется, commit должен считаться неполным.

## Минимальный рабочий путь

1. `./scripts/restore_context.sh`
2. внести кодовые изменения
3. обновить нужный файл в `docs/ru/`
4. добавить русские комментарии в неочевидную изменённую логику
5. `./scripts/verify_workflow.sh`
6. `./.venv/bin/python scripts/finalize_task.py ...`
7. `git add ...`
8. `git commit -m "..."`
9. `git push`

Если шаг 9 не случился, работа всё ещё только локальная.
