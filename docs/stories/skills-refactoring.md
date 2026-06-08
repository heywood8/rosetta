# Story: Skills Taxonomy Reconciliation + Frontmatter Refactoring

Status: DRAFT — analysis complete; recommendations only (implementation decides verdicts). Confirmed scope with owner. r3 only; source = `instructions/r3/core/**` (never hand-edit `plugins/`).

## Problem

The skill set has drifted from its own canonical taxonomy and carries cost that does not pay for itself:

- Some `SKILL.md` files are not standalone capabilities — they are thin wrappers over a single workflow phase (`init-workspace-*`) or extensions of a parent skill (`coding-iac`).
- Infra/plumbing and reactive-guardrail skills appear in the user `/` menu where users must never invoke them.
- Workflow phase files are emitted as user commands (generator renames `workflows/`→`commands/`), so internal phases leak into the user `/` menu even though they are only invocable through their parent workflow.
- Frontmatter `description` fields run long. Instructions are agent-facing; every token is paid on every turn.
- The implemented set diverges from `docs/definitions/skills.md` (authoritative but outdated).

## Findings (evidence)

- **F1 — Canonical drift.** `docs/definitions/skills.md` lists ~15 skills never built and omits 12 that exist. It is authoritative intent but outdated: fix it where reality has legitimately moved on.
- **F2 — `init-workspace-*` are thin wrappers.** Each `init-workspace-flow-*.md` phase just does `ACQUIRE init-workspace-X/SKILL.md FROM KB and EXECUTE` (e.g. `init-workspace-flow-context.md:34`). Inlining = merge skill body into its one phase file, delete skill. The canonical list still calls these skills (`skills.md:32-38`) — outdated; W0 removes them.
- **F3 — Description is the NATIVE trigger; our rule is the custom add-on.** `bootstrap-guardrails.md:50-74` issues `MUST USE SKILL hitl / sensitive-data / self-learning / risk-assessment / dangerous-actions / deviation / questioning / self-organization`. Skill descriptions are always present and drive IDE-native auto-activation; the bootstrap rule duplicates that. Correct direction: lean on native descriptions, slim the custom rule (see W5).
- **F4 — Independent skills = subagent-invoked ones.** `agents/*.md` invoke `coding, testing, debugging, planning, tech-specs, reasoning, research, requirements-authoring/use, reverse-engineering, coding-agents-prompt-authoring/adaptation`. These are the keep-visible core.
- **F5 — Precedent.** Commit `cefeea4 "Merge review skills"` — consolidation is established; no competing in-flight branch.

## Confirmed decisions (owner-approved)

1. **Canonical list:** authoritative but outdated — reconcile toward it, update the list where reality moved on.
2. **Names:** `operation-manager` is the correct new name (fix list entry `plan-manager` → `operation-manager`); `load-context` / `load-workflow` / `load-context-instructions` are correct (add to list); `discovery` is a separate, distinct skill (leave as its own unbuilt entry); `context-engineering` is **TBD** (definition unknown — leave as open placeholder). No impl renames.
3. **Guardrails / auto-activated skills:** keep descriptions as the native trigger and *augment* any missing trigger signal; **do not** trim them below activation strength. Simplify the custom bootstrap rule instead (W5).
4. **Off-list skills:** this doc gives **recommendations with confidence**, not verdicts. Implementation decides.
5. **Scope:** one story = taxonomy reconciliation **+** the 4 objectives.
6. **Cross-IDE visibility:** captured as a research task with acceptance criteria (W2), not built here.
7. **Workflow phases:** stay emitted as commands (parent invokes them) but get `user-invocable: false` (+ per-IDE equivalents) to drop them from the user `/` menu; top-level flows stay `user-invocable: true`. Visibility is a frontmatter flag only. ALL workflow descriptions are compressed (W4 diet) — nothing added; the sole top-level/phase difference is the flag.

## Recommendation table (implementation decides)

| Skill(s) | Canon? | Recommendation | Visibility | Conf. |
|---|---|---|---|---|
| coding, testing, debugging, planning, tech-specs, reasoning, research, requirements-authoring, requirements-use, reverse-engineering, coding-agents-prompt-authoring, coding-agents-prompt-adaptation, large-workspace-handling | ✓ | Keep — independent capability (F4) | visible | High |
| hitl, sensitive-data, dangerous-actions, deviation, risk-assessment, self-learning, self-organization, questioning | ✓ | Keep — reactive guardrail; description carries trigger (F3, W5) | hidden | High |
| load-context, load-workflow, load-context-instructions, operation-manager, orchestrator-contract, subagent-contract | partial | Keep — infra/plumbing | hidden | High |
| init-workspace-context, -discovery, -documentation, -patterns, -rules, -shells, -verification | (outdated) | Inline into matching `init-workspace-flow-*.md`; delete skill (F2) | n/a (phase) | High |
| coding-iac | ✗ | Fold into `coding` (`coding/assets/` + call-to-action) | n/a | High |
| gitnexus-cli, gitnexus-setup, gitnexus-tools | ✗ | Consolidate → 1 `gitnexus` skill (alt: keep tools+cli, fold setup) | hidden/conditional | Med |
| specflow-use | ✗ | Keep — integration connector, conditional on SpecFlow MCP | hidden/conditional | Med |
| hooks-authoring | ✗ | Keep — meta/dev skill (authoring Rosetta itself) | hidden | Med |
| natural-writing | ✗ | Keep — capability (used by `self-help-flow`) | visible | Med |
| coding-agents-farm | ✗ | Keep — standalone orchestration capability | visible | Med |

## Workstreams

- **W0 — Reconcile taxonomy.** Update `docs/definitions/skills.md` per Confirmed Decision 2: rename entry `plan-manager`→`operation-manager`; add `load-context/load-workflow/load-context-instructions`; remove `init-workspace-*` (now phases); keep `discovery` distinct, `context-engineering` as TBD placeholder; record the off-list recommendations. Update every `USE SKILL` / `ACQUIRE …/SKILL.md` reference; zero dangling refs.
- **W1 — Inline / fold.** Merge `init-workspace-*` bodies into phases (delete skills); fold `coding-iac` into `coding`; consolidate `gitnexus-*` per recommendation.
- **W2 — Visibility + cross-IDE research.** Tag each kept skill **and each workflow/command** visible/hidden via frontmatter flags (`user-invocable`, etc.). **Research task (AC):** produce IDE→attribute matrix (Claude Code, Cursor, Copilot, Codex, OpenCode) for hide-from-menu vs disable-auto, for **both skills and commands**; apply per-IDE frontmatter; extend `plugin_generator.py` where an IDE ignores the flag. Acceptance: every hidden skill/phase verified non-listed in the user menu yet still invocable (auto for guardrails, parent-invoked for phases) on each supported IDE, or the limitation documented.
- **W3 — Workflow phase hiding + description compression.** Phases stay emitted as commands (parent invokes them); add `user-invocable: false` (+ per-IDE equivalents) to remove them from the user `/` menu. Top-level flows stay `user-invocable: true`. Compress **all** workflow descriptions per the W4 diet — nothing added. The only top-level/phase difference is the visibility flag.
- **W4 — Description diet (non-critical skills).** Non-guardrail, non-auto skill + workflow descriptions → ≤25 tokens, verb-first ("To …"), no "Use when", drop "Rosetta … skill" boilerplate. Example — `coding`: → *"To implement features, fix bugs, and refactor with KISS/SOLID/DRY and systematic validation."*
- **W5 — Native-trigger reframe (F3).** Audit guardrail/auto-activated skill descriptions; ensure each carries its activation trigger (add where missing). Then simplify `bootstrap-guardrails.md` from full directives toward a lean "invoke X when Y" pointer, removing duplication with native description-based invocation. Acceptance: each guardrail still fires from its description alone (rule absent) in a test.

## Scope, success, risks

- IN: `instructions/r3/core/skills/**` + `workflows/**`, `instructions/r3/core/rules/bootstrap-guardrails.md`, `docs/definitions/skills.md`, `docs/schemas/skill.md`, `scripts/plugin_generator.py` (only if W2 needs it), plugin regen.
- OUT: r2, MCP server behavior, impl renames.
- Success: list reconciled; recommendations applied by implementation; zero dangling refs; phases hidden from the user menu via flag yet still parent-invocable; all workflow descriptions compressed; non-critical descriptions ≤25 tokens; guardrails fire from description alone; clean plugin regen.
- Risks: reference breakage from inlines/folds (W1); IDE that ignores the `user-invocable` flag leaves a hidden skill/phase visible or a hidden skill un-activatable (W2/W3); weakened guardrail activation if a description loses its trigger during W5.

## Open items for implementation

1. **F2 confirmation** at execution: `init-workspace-*` become phases (removed as skills).
2. **gitnexus** consolidation shape: 3→1, or keep tools+cli and fold setup.
3. **W5 rule shape:** how lean the simplified `bootstrap-guardrails` pointer should be once native triggers carry the load.
4. **Validation mechanism:** regression prompt suite vs manual checklist vs eval — to prove hidden-but-auto and native-trigger behavior.
