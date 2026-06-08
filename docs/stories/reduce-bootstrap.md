# Story: Shrink the Running Bootstrap & Make Plugins Primary

Status: DRAFT — rewritten around user's corrected vision (prior dedup framing discarded). Defaults are proposals, not approvals. Do not implement until approved.
Scope: **r3 only**. Validation design: deferred.

> This is **not** a de-duplication or file-merge effort. The concern is the **running context** the agent carries while executing a user request — make the always-injected bootstrap **smaller, ideally → 0**, by moving content behind a user-invoked entry and on-demand skills. Splitting things further is acceptable; merging into one high-cognitive-load core is not.

## The linchpin: Rosetta becomes a user-invoked `/rosetta` skill

Today the bootstrap is **ambient context**, so it must browbeat the model ("EXTREMELY_IMPORTANT", "you cannot rationalize your way out") to be followed — that's what bloats it and fights the host system prompt. When the user **invokes `/rosetta`**, the same content carries the authority of **"the user told you to do X."** The model obeys that natively. Consequences:

- The adherence / anti-rationalization / red-flags prose becomes **obsolete → delete it** (not compress it).
- **No per-request classification.** Only `/rosetta` requests get the full Rosetta treatment; a plain request runs as a normal agent. **The user decides.**
- `/rosetta` = simplified bootstrap procedure: load context → select workflow → hand off. (No persistence machinery; the workflow + plan carry execution.)

## Target always-on footprint

Minimal shared bootstrap (tiny) **+ exactly one mode file** (tiny). Everything heavy lives behind `/rosetta`, skills, and workflows, loaded on demand (progressive disclosure). Reduce each injected payload toward **0**.

## Mode binding: one alias, different behavior

Command aliases are written **once, mode-agnostically** in every skill/workflow. Exactly one mode file is injected per environment and **binds** each alias to a concrete mechanism — the only place mode logic lives. Three mutually exclusive modes:

- **Plugin mode → `plugin-files-mode.md`**: binds aliases to **literal local reads** from the plugin install location.
- **MCP mode → `bootstrap.md`**: binds the same aliases to MCP behavior + any MCP-only deltas/explanations/mappings ("X means Y by doing Z", e.g. `query_instructions` / `rosetta://{path}`).
- **Local / in-repo dev mode → `local-files-mode.md`**: binds aliases to **literal local reads from the `instructions/r*` folder** (used when developing Rosetta itself in this repo — not plugin, not MCP).

So call sites **never branch on mode**. MCP needs the mapping anyway; plugin and local-dev context shrink. (`rosetta-cli` rewriting content before MCP publish is a fallback, but the in-`bootstrap.md` mapping is preferred.)

**Implication:** the alias vocabulary is a **closed contract** — every alias used anywhere must be bound by *both* mode files. Any ad-hoc load phrasing not in the vocabulary silently breaks in MCP. Defining and policing that finite set is part of this work.

## Verb / alias vocabulary (W4)

Pattern (proposed generalization of the user's example): **`VERB ARTIFACT <name> [FILE <subpath>]`**, human-clear in plugin mode, deterministically mappable to `ACQUIRE/LIST … KB` in MCP.

- **`READ`** = load into context. **`APPLY`** = read **and** act on / execute it.
- Anchor example (user): `ACQUIRE the-skill/assets/some-file.md FROM KB` → **`READ SKILL the-skill FILE assets/some-file.md`** (plugin: read `skills/the-skill/assets/some-file.md`; MCP: maps to `ACQUIRE … FROM KB`).

### Mapping the actual r3 usage (audit basis for the vocabulary)

| # | Pattern today | ~Count | Becomes |
|---|---------------|--------|---------|
| 1 | `ACQUIRE aqa-flow-data-collection.md FROM KB` (phase chaining) | ~35 | `APPLY FLOW aqa-flow-data-collection` (read+execute a phase) |
| 2 | `ACQUIRE reverse-engineering/SKILL.md FROM KB` (skill load) | ~12 | `USE SKILL reverse-engineering` (already canonical; normalize) |
| 3 | `ACQUIRE planning/assets/pl-wbs.md FROM KB` (skill asset/ref) | ~20 | `READ SKILL planning FILE assets/pl-wbs.md` (or `APPLY …` if it must be run) |
| 4 | `ACQUIRE rules/bootstrap.md FROM KB` (rule/template) | ~8 | `READ RULE bootstrap` / `READ TEMPLATE skill-shell` |
| 5 | `ACQUIRE agents/<x>.md … EXECUTE` (subagent) | ~1 | `INVOKE SUBAGENT <x>` (already canonical) |
| 6 | `ACQUIRE <selected TAG> FROM KB` (tag/dynamic) | ~6 | agent selects, then uses the typed verb above |

- **`LIST`** (~10 uses, only enumerates folders) → `LIST SKILLS` / `LIST WORKFLOWS` / `LIST AGENTS` / `LIST configure`, mode-bound like the others.
- **`SEARCH`** (~0 real callers) → drop from the canonical set.
- **Dangling ref:** `ACQUIRE questions.md FROM KB` in `requirements-authoring/SKILL.md` points to a non-existent file → fix or remove.
- **`USE FLOW` vs `RUN WORKFLOW`:** keep canonical `USE`/`APPLY FLOW`; avoid `RUN WORKFLOW` churn unless preferred.

## Subagents (W3): `load-subagent-context` skill

- **Same minimal bootstrap injected to everyone** (orchestrator + subagents). Then the **orchestrator demands each subagent load its subagent SKILL** (`load-subagent-context`). Clear separation of concerns and context: `/rosetta` + role skills inject what the *orchestrator* needs; `load-subagent-context` injects what a *subagent* needs.
- `load-subagent-context` replaces the `load-context-instructions` + `load-context` chain for subagents and lets us **delete the "if subagent / if not" branches** from the always-on bootstrap.
- Subagent prep: minimal seed → read `CONTEXT.md` + `ARCHITECTURE.md` (full) → grep `MEMORY.md` headers → assigned steps via OPERATION_MANAGER `next --target`. **No** workflow selection, **no** full project-context load (orchestrator prepared those).
- Add `load-subagent-context` to `docs/definitions/skills.md`.

## Enforcement in MCP = same as plugins (via shells)

MCP gets the **same minimal bootstrap** and behaves **identically** (loads skills by context; orchestrator tells subagents). On init, Rosetta installs **skill/subagent/workflow shells** (proxy files) that enforce loading the same way plugins do. This is a **mild** architectural shift — change *what triggers classification* (only `/rosetta`), not the execution model.

## Blast radius / scope

- IN: `instructions/r3/core/**` (the ~50 files using `ACQUIRE/SEARCH/LIST`, the bootstrap + mode files, the shell templates), `scripts/plugin_generator.py` rewrite rules, plugin regeneration, `docs/definitions/skills.md`, `docs/ARCHITECTURE.md`, per-platform delivery payloads (hook / rules / MCP bundle) shrunk toward 0.
- OUT: `instructions/r2/**`, MCP server behavior, project-scoped `ABOUT/QUERY/STORE` aliases.

## Open / to confirm

1. **Verb vocabulary** — confirm the `VERB ARTIFACT <name> [FILE <subpath>]` generalization, the `READ` vs `APPLY` split, and the per-category mapping above (the only part I generalized beyond your example).
2. **Minimal bootstrap contents** — what irreducibly stays always-on once the adherence prose is gone (guardrails? a `/rosetta` pointer? nothing)?
3. **Closed alias set** — finalize the complete vocabulary so both mode files can bind every alias.
