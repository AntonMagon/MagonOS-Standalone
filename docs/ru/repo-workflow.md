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

## Что обязательно синхронизировать

- `AGENTS.md`
- `docs/current-project-state.md`
- `docs/ru/README.md`
- `docs/ru/current-project-state.md`
- `.codex/config.toml`
- `.codex/project-memory.md`
- `docs/repo-workflow.md`

## Что требуют git hooks

### pre-commit

Если staged product-owned файлы изменились, то в том же коммите обязательно должны быть:
- обновление `.codex/project-memory.md`
- обновление хотя бы одного файла в `docs/ru/`

### pre-push

Перед push обязательно проходит:
- `./scripts/verify_workflow.sh`
- `cd apps/web && npm run typecheck`, если в исходящем диапазоне есть `apps/web/`

## Что считается обязательным русским слоем

- русская документация в `docs/ru/`
- русские комментарии/docstrings в неочевидной изменённой логике

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
