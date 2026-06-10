# plugin-generator — Session Context Handoff (updated 2026-06-08)

Compact state to **fully restart** this session and continue the TS-rewrite parity/compliance effort without re-discovery. Read this + `report.md` first.

## Goal
`src/plugin-generator/` (TypeScript, ESM, run via npx) re-architects the old Python `scripts/plugin_generator.py`. Targets: (1) byte-for-byte parity (NFR-0001) with the Python output, AND (2) the clean FR-ARCH two-tier processor architecture (universal/reusable processors, data-driven specs). Both must hold. Rewrite is mid-refactor; partial compliance expected.

## HARD PROHIBITIONS
- NEVER read `scripts/plugin_generator.py` or `specs/plugin-generator.allium` (old architecture). Use as DATA only: the requirements, the baselines, and the preserved templates.
- NEVER modify `agents/TEMP/` (the parity baseline) except via the regen recipe below.

## Owner standing rules (LOCKED — this session)
- **Requirements are the source of truth and FROZEN.** Do NOT change ANY requirement without explicit owner instruction. The old generator is a *reference with bugs*; where it violates a requirement, the NEW gen is correct and SHOULD differ — do not reproduce old-gen bugs.
- **No autonomous design decisions.** ASK the owner first. "Auto/autonomous mode" now means tool/permission approvals ONLY — nothing else.
- `target_contents === null` ⇒ file NOT written (FR-ARCH-0036), but the frame still exists and still carries its rename (so other files' references resolve).
- r3 oversize bootstrap is CORRECT (r3 `plugin-files-mode` ~11k > 10000 → NFR-0004 soft error, exit 1, output still emitted).

## Verified current state (2026-06-08)
- `npx tsc --noEmit`: **clean**. `npx vitest run`: **304 pass / 31 files**.
- Parity: **r2 exit 1 (1 NFR-0004 violation) · r3 exit 1 (5 NFR-0004 violations)** — diff counts: r2=12, r3=22, all in accepted buckets, ZERO structural/Only-in diffs.
- Ghost frame fix complete: removed `processor.name === 'fileRenameProcessor'` check; run ALL processors on ghost frame. Added same-folder guard in `buildRenamePairs` for ghost frames (source.length===0 && target_contents===null).

## Accepted diff buckets (owner decisions locked)

### Bucket A — AGENT-REF (~6 r2 diffs, ~6 r3 diffs)
Files like `core-copilot/commands/self-help-flow.md`, `pa-knowledge-base.md`, `pa-rosetta.md`.
New gen rewrites `agents/X.md → agents/X.agent.md` (correct per FR-ARCH-0049). Old gen leaves `.md`. **Decision: accept new-gen (old-gen BUG).**

### Bucket D — OLD-GEN double-rewrite (~6 r2 diffs, ~5 r3 diffs)
Files like `core-copilot-standalone/.github/configure/*.md`, `pa-rosetta-intro-for-AI.md`.
Old gen over-aggressively applied `commands/ → prompts/` rename or double-rewrote folder names. **Decision: accept new-gen (old-gen BUG).**

### Decision 3 — plugin-files-mode content change cascade (~11 r3-only diffs)
`plugin-files-mode.md` source content changed after baseline was created (new `<phase-steps-json-string>` param in plan-manager command signatures). Cascades to hooks.json (bootstrap embeds its body).
Files: 6× plugin-files-mode.md/mdc/.instructions.md + 5× hooks.json (core-claude, core-codex×2, core-copilot×2). **Decision: accept as known differences (do not regenerate baseline).**

## Ghost frame design (FR-ARCH-0049)

**Ghost frames**: null-content `FileProcessingFrame` entries (`source: [], target_contents: null`) created for excluded files to populate the reference-rewrite lookup.

**`plugin-process-spec-entries.ts`** (fixed): for excluded files, run ALL processors on ghost frame. `fileRead` is a no-op on empty source (returns immediately). Only `fileRename` changes the target; content processors guard `target_contents === null`. Previously broken: `processor.name === 'fileRenameProcessor'` never matched anonymous arrow fns.

**`buildRenamePairs`** (fixed): ghost frames (detected by `source.length === 0 && target_contents === null`) only emit pairs for same-folder renames (e.g. `.md → .mdc`). Cross-folder ghost pairs (excluded from entry A → instructions/, processed by entry B → rules/) are filtered out to prevent wrong rewrites.

## Remaining compliance discrepancies (pending owner decisions)

> **2026-06-09:** Authored **FR-ARCH-0005** (Approved) — no identity branching / no identity-discriminant flags; per-case variation by composition (P0–P3). CHANGES.md RECON-10. All clean-architecture-track requirements set `<implementation>ToBeModified</implementation>` (23 units). `createHookFolderInR2` (task #17) under owner review now.

- **`createHookFolderInR2`** — bespoke per-release+per-target flag (forbidden, DATA-CFG-0002/FR-ARCH-0004). **DECIDED 2026-06-09: DELETE.** Baseline: it only uniquely creates the **empty** r2 `core-cursor-standalone/.cursor/hooks/`; the other 4 `true` targets' folders are populated by rendered `hooks.json` (redundant), codex `false`. That empty folder has **no functional value** — nothing references the dir; empty = no hooks = same as absent; vestigial old-gen artifact. Remove flag from `types.ts:124` + 6 specs + `plugin-sync-bundles.ts:86` branch; accept the absent folder as an old-gen artifact. **Code = task #17, deferred (coding-flow).** **Origin: NO requirement created it** — no FR mandates an empty r2 hook folder (FR-HOOK-0020 = bundle placement/stale-removal only; STRUCTURES = generated files only); it is mentioned in requirements only to be *forbidden* (FR-ARCH-0004/DATA-CFG-0002, RECON-7). Introduced in impl commit `0b83256` ⇒ baseline-overfit / wrong-prompt artifact, not requirements-driven.
- ~~Cursor bootstrap not uniform~~ — **FIXED** (task #6). Short-circuit removed. Assembly+size-check now runs for all targets. r2 has 1 violation (cursor-standalone plugin-files-mode = 10705 chars → r2 exit 1). r3 has 5 violations (claude, cursor, copilot, codex, cursor-standalone). Whether the assembled payload reaches the agent is decided by the preserved templates (cursor templates carry no `{{{bootstrap_hooks_cursor}}}` placeholder → nothing injected).
- **`includeBootstrapRules` (`types.ts:92`) — DECIDED 2026-06-09: DEAD field, delete.** Never read (`grep .includeBootstrapRules` = 0 reads); set in 6 specs but unconsumed. Concept was FR-HOOK-0004 but its bootstrap-rule half is superseded by FR-VAR-0070/RECON-8 (delivery = template decision, not a field). **FR-HOOK-0004 amended** (drop bootstrap-rule-flag clause, keep `includeIndexEntries`). Code deletion deferred (coding-flow).
- **`deterministicHooks` branch (`plugin-sync-bundles.ts:46`) — RESOLVED 2026-06-09: COMPLIANT, keep.** Requirement-backed (DATA-CFG-0001 + FR-HOOK-0020); a genuine behavior flag carried as release config; the branch holds no release name (NFR-0006 ✓; FR-ARCH-0005 permits branching on genuine behavior flags). Optional per-release processor composition is polish, not required.

## Open task list
- **#5** Fix ghost-frame rename → **COMPLETED** (2026-06-08)
- **#6** Make cursor bootstrap assembly+size-check uniform (FR-VAR-0070) → **COMPLETED** (2026-06-09)
- **#8** Eliminate IDE-name switch dispatch: `hookEntryShape`/`vocabulary.kind` → **requirement DONE (FR-ARCH-0005, Approved, 2026-06-09); CODE pending**. Fix per FR-ARCH-0005 = case-specific processor per case composed into that target's `PluginSpec` pipeline + shared low-level helpers (P1+P2) — NOT a callback on a shared processor; remove `hookEntryShape`/`ModelVocabulary.kind` enums; per-vocabulary model normalizers.
  - `bootstrap/payload.ts:189-225` — `switch (spec.hookEntryShape)` on `'claude'/'codex'/'copilot'`
  - `file-normalize-models.ts:41-106` — `switch (vocabulary.kind)` on `'claude'/'cursor'/'copilot'/'codex'`
  - `plugin-assemble-bootstrap.ts:19` — `` `bootstrap_hooks_${shape}` `` string interpolation on shape
- **#7** Re-verify: parity, tests, exit codes, coverage → re-run after #8
- **#17** Remove `createHookFolderInR2` → **DECIDED 2026-06-09: delete (empty r2 `.cursor/hooks/` is a valueless old-gen artifact); code pending (coding-flow)**
- **#18** Full requirements-deviation audit → **ask owner before spawning**

## Baseline regen recipe
```
cd /Users/isolomatov/Sources/GAIN/rosetta
rm -rf agents/TEMP/old-gen-r2 agents/TEMP/old-gen-r3
mkdir -p agents/TEMP/old-gen-r2 agents/TEMP/old-gen-r3
cp -R src/plugin-generator/plugins/. agents/TEMP/old-gen-r2/
cp -R src/plugin-generator/plugins/. agents/TEMP/old-gen-r3/
venv/bin/python scripts/plugin_generator.py --release r2 --output-dir agents/TEMP/old-gen-r2 >/dev/null 2>&1
venv/bin/python scripts/plugin_generator.py --release r3 --output-dir agents/TEMP/old-gen-r3 >/dev/null 2>&1
find agents/TEMP/old-gen-r2 agents/TEMP/old-gen-r3 -type d -name shell-schemas -prune -exec rm -rf {} +
find agents/TEMP/old-gen-r2 agents/TEMP/old-gen-r3 -type d -name templates -empty -delete
```
Counts after: r2=880, r3=946. Preserved version currently **2.0.42**.

## Parity check recipe (run gen + diff as SEPARATE statements — r3 exits 1 by design)
```
cd /Users/isolomatov/Sources/GAIN/rosetta/src/plugin-generator
S=/Users/isolomatov/Sources/GAIN/rosetta
rm -rf /tmp/g2 /tmp/g3
npx tsx src/cli.ts --release r2 --domain core --source "$S" --output /tmp/g2; diff -rq /tmp/g2 "$S/agents/TEMP/old-gen-r2"
npx tsx src/cli.ts --release r3 --domain core --source "$S" --output /tmp/g3; diff -rq /tmp/g3 "$S/agents/TEMP/old-gen-r3"
```

## Key files / docs
- Requirements: `docs/requirements/plugin-generator/*` (FR-ARCH-0004, FR-VAR-0070, FR-CLI source model, FR-COPY-0011, DATA-CFG-0002; CHANGES.md logs RECONCILIATION-1..9; many units `Draft` pending owner approval).
- Ground truth (byte facts, decoded from baseline): `plans/plugin-generator/GROUND-TRUTH.md`.
- Specs/plan: `plans/plugin-generator/plugin-generator-SPECS.md`, `plugin-generator-PLAN.md`.
- Code: `src/plugin-generator/src/` (cli, generate, types, vfs/*, file-processors/*, plugin-processors/*, serialize/*, escaping/*, bootstrap/*, spec/*). Tests: `src/plugin-generator/tests/{unit,e2e,fixtures}`.
