---
name: skill-pattern-scan
description: Scan recent repo work for recurring workflows and propose or update project-specific skills that capture real reusable patterns.
---

# skill-pattern-scan

## Purpose
Detect repeated repository workflows and turn them into maintainable local skills.

## When to use
- The user asks what new skills should be added.
- A pattern has repeated across multiple tasks or commits.
- Existing skills look incomplete or stale compared with current repo behavior.

## Read first
- `./scripts/restore_context.sh`
- `git log --oneline -10 --name-only`
- `find skills -maxdepth 2 -name 'SKILL.md' | sort`
- `.codex/project-memory.md`

## Skill-worthiness test
A pattern is worth a skill only if it is:
- reusable
- non-obvious
- repeated
- cheaper to institutionalize than to rediscover every session

## Execution
1. Inventory current local skills.
2. Scan recent commits and touched files for repeated workflows.
3. Classify each detected pattern:
   - create new skill
   - update existing skill
   - skip
4. Prefer updating an existing skill over creating duplicates.

## Output contract
For each proposed skill, state:
- short name
- exact responsibility
- owning files or workflows it covers
- why the current skill set does not already cover it

## Failure note
- Do not create skills for one-off tasks.
- Do not create overlapping skills when one narrow update would do.
