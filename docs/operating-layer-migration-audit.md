# Operating Layer Migration Audit

## Purpose
This audit records how the project operating layer was migrated from the legacy donor repo into the standalone repo.

## Canonical result
- Active product repo: `/Users/anton/Desktop/MagonOS-Standalone`
- Legacy donor / bridge repo: `/Users/anton/Desktop/MagonOS/MagonOS`
- The standalone repo now contains the active repo-local operating layer.

## 1. Source operating-layer artifacts found on disk

| Artifact | Found in source repo | Notes |
| --- | --- | --- |
| `AGENTS.md` | yes | Real repo-level instructions existed. |
| `.codex/config.toml` | yes | Real Codex project context existed. |
| `skills/audit-docs-vs-runtime/SKILL.md` | yes | Useful and portable with adaptation. |
| `skills/operate-platform/SKILL.md` | yes | Useful, but old wrapper/source assumptions had to be removed. |
| `skills/operate-standalone-intelligence/SKILL.md` | yes | Useful, but Odoo-side sync assumptions had to be cut back. |
| `skills/git-safe-commit/SKILL.md` | yes | Useful as optional git discipline only. |
| `skills/debug-odoo/SKILL.md` | yes | Odoo-specific legacy skill. |
| `skills/setup-odoo/SKILL.md` | yes | Odoo-specific legacy skill. |
| `skills/update-module/SKILL.md` | yes | Odoo-specific legacy skill. |
| `docs/development-workflow.md` | yes | Real repo discipline artifact. |
| `docs/development-workflow-audit.md` | yes | Useful evidence about workflow intent. |
| `docs/ROUTING_WORKFLOW_MVP.md` | yes | Workflow evidence, but business-domain specific, not generic operating layer. |

## 2. Standalone operating-layer artifacts that already existed

| Artifact | Existed in standalone before this run | Notes |
| --- | --- | --- |
| `AGENTS.md` | yes | Present, but incomplete as a full migrated operating layer. |
| repo-local `.codex/config.toml` | no | Missing. |
| `skills/` directory | no | Missing. |
| `docs/audit-context.md` | yes | Useful context, but not an operating-layer migration audit. |
| `docs/business-logic-parity-audit.md` | yes | Useful parity truth, but not an instruction layer. |

## 3. Classification

| Source artifact | Classification | Reason |
| --- | --- | --- |
| source `AGENTS.md` | ADAPT TO STANDALONE | The intent is still valid; source-repo authority assumptions are not. |
| source `.codex/config.toml` | ADAPT TO STANDALONE | Useful structure existed, but all paths and truth order had to be rewritten. |
| `skills/audit-docs-vs-runtime` | ADAPT TO STANDALONE | Still useful, but standalone code/tests/scripts must be primary truth. |
| `skills/operate-platform` | ADAPT TO STANDALONE | Keep the idea, remove source-wrapper/Odoo assumptions. |
| `skills/operate-standalone-intelligence` | ADAPT TO STANDALONE | Keep the contour, remove donor-side runtime assumptions. |
| `skills/git-safe-commit` | KEEP WITH LIGHT ADAPTATION | Still useful, but must remain opt-in and non-automatic. |
| `skills/debug-odoo` | DROP AS LEGACY | Source-only, Odoo-runtime specific. |
| `skills/setup-odoo` | DROP AS LEGACY | Source-only, Odoo-runtime specific. |
| `skills/update-module` | DROP AS LEGACY | Source-only, Odoo module workflow. |
| `docs/development-workflow.md` | RECONSTRUCT FROM EVIDENCE | Intent was useful, but the standalone repo needed its own repo-local operating expression instead of copied branch policy prose. |

## 4. What was migrated into standalone

### Transferred as real repo-local artifacts
- `AGENTS.md`
- `.codex/config.toml`
- `skills/audit-docs-vs-runtime/SKILL.md`
- `skills/operate-platform/SKILL.md`
- `skills/operate-standalone-intelligence/SKILL.md`
- `skills/git-safe-commit/SKILL.md`
- this audit file

### Carried over as intent, not as literal copy
- truth-order discipline
- script-first verification discipline
- narrow verification commands
- explicit done criteria
- explicit failure-pattern warnings

## 5. What was adapted for standalone reality

### Rewritten assumptions
Old assumption:
- source repo is the main work area

New standalone rule:
- standalone repo is the default work target
- source repo is donor/inspection only

Old assumption:
- Odoo runtime and wrappers are central

New standalone rule:
- standalone runtime is central
- Odoo is donor/bridge only

Old assumption:
- source startup scripts and Odoo shell define current workflow

New standalone rule:
- `scripts/run_unified_platform.sh` and `scripts/run_platform.sh` define the active local platform

Old assumption:
- operating layer can be split between both repos

New standalone rule:
- active project operating layer must live inside the standalone repo

## 6. What was dropped as legacy

The following were intentionally not migrated into the standalone operating layer:
- Odoo debugging instructions
- Odoo setup instructions
- Odoo module update instructions
- any rule that treats the source repo as the normal development target
- any rule that treats Odoo as the future runtime
- any operating assumption that source `apps/web` is canonical

## 7. What had to be reconstructed

These items were reconstructed because they did not exist in standalone as repo-local artifacts:
- repo-local `.codex/config.toml`
- repo-local `skills/` directory
- standalone-specific audit/runtime/verification skills
- the explicit rule that current dangerous overlap is commercial semantics around customer/account, opportunity/lead, RFQ, and quote boundaries
- the explicit statement of the current validated contour:
  - company
  - commercial/customer context
  - opportunity
  - quote intent / RFQ boundary
  - production handoff
  - production board

This reconstruction was based on:
- current standalone code
- current standalone tests
- current parity audit
- existing source operating-layer intent

## 8. Why the new standalone operating layer matches reality better

It is better because it now:
- points future work to the active repo by default
- treats the source repo as donor/bridge only
- references real standalone commands and paths
- encodes the current validated contour instead of old Odoo-centered assumptions
- warns directly against common drift:
  - docs-first work
  - source-repo normalization work
  - generic Odoo sync expansion
  - hallucinated business parity

## 9. Remaining weak spots

The operating layer is stronger now, but some things are still weak or informal:
- no repo-local automation around branch policy or pre-commit in standalone
- no standalone-specific contribution policy file yet
- auth/roles/admin replacement is still not formalized as an operating discipline because the product itself has not implemented it yet
- business-parity truth still depends on periodic donor-vs-standalone audits as the migration continues
