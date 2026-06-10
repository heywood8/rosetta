# plugin-generator — Compliance Review (updated 2026-06-08)

Scope: FR-ARCH-0004, DATA-CFG-0002, FR-CLI-0001/0020/0021/0030, FR-VAR-0070, FR-ARCH-0049.

## Current state (2026-06-09)

`tsc` clean · **304 tests pass** · **r2 exit 1 (1 NFR-0004 violation)** · **r3 exit 1 (5 NFR-0004 violations)**.
Diff counts: r2=12, r3=22, all in accepted buckets — no new-gen bugs outstanding.

NFR-0004 violations:
- r2: `core-cursor-standalone:plugin-files-mode` (10705 chars) — owner will trim the file later
- r3: `core-claude`, `core-cursor`, `core-copilot`, `core-codex`, `core-cursor-standalone` (all plugin-files-mode, ~11.5k chars)
## Architecture issue

Code contains a lot of switch on cursor/claude/copilot/etc. This should never be happening. All required differences must be in pluginspecs itself.

**2026-06-09 — RESOLVED in requirements (code fix = task #8):** authored **FR-ARCH-0005** (Approved) — no branching on IDE/target identity *or* on an identity-discriminant flag (`hookEntryShape`, `ModelVocabulary.kind` are identity relabeled); per-case variation by composition: P0 small units · P1 case-specific processor placed only in that spec's pipeline (selected by composition) · P2 shared low-level helpers · P3 path-scoping via `SpecEntry` globs. All clean-architecture-track requirements set `<implementation>ToBeModified</implementation>` (23 units across FR-ARCH/FR-HOOK/FR-VAR/FR-CLI/FR-COPY/MODEL/NFR). See CHANGES.md RECON-10.

## Remaining parity diffs (all accepted)

### Bucket A — AGENT-REF (~6 r2, ~6 r3) — accept new-gen
Files: `core-copilot/commands/self-help-flow.md`, `pa-knowledge-base.md`, `pa-rosetta.md`, copilot-standalone mirrors.
New gen correctly rewrites `agents/X.md → agents/X.agent.md` (per FR-ARCH-0049). Old gen leaves `.md` = old-gen BUG.

### Bucket D — OLD-GEN double-rewrite (~6 r2, ~5 r3) — accept new-gen
Files: `core-copilot-standalone/.github/configure/*.md`, `pa-rosetta-intro-for-AI.md`, `bootstrap-execution-policy.instructions.md`.
Old gen over-aggressively applied `commands/ → prompts/` rename or double-rewrote folder names = old-gen BUG.

### Decision 3 — plugin-files-mode content change cascade (~11 r3-only) — accept as known
`plugin-files-mode.md` source content changed after baseline was created (new `<phase-steps-json-string>` param). Cascades to 5× hooks.json (bootstrap embeds its body). Do NOT regenerate baseline.
Files: 6× plugin-files-mode.md/mdc/.instructions.md + 5× hooks.json.

## Discrepancies still open

| Location | Req | Issue | Status |
|---|---|---|---|
| `types.ts:124` + `spec/targets.ts:152,184,226,273,368,464` + `plugin-sync-bundles.ts:86` | DATA-CFG-0002 / FR-ARCH-0004 | `createHookFolderInR2` bespoke per-release flag | **DECIDED 2026-06-09: DELETE — empty r2 `.cursor/hooks/` is a valueless old-gen artifact; code = task #17, deferred** |
| ~~`bootstrap/payload.ts:57-59`~~ | FR-VAR-0070 | ~~cursor skips assembly+size-check~~ | **INCORRECTLY FIXED task #6 => WE ALWAYS GENERATE ALL HOOKS FOR ALL IDEs. TMPL engineer makes decision to use it or not in the tmpl file. Current fix only removed condition.** |
| `bootstrap/payload.ts:189-225` + `file-normalize-models.ts:41-106` | FR-ARCH-0004/0005 | `switch (spec.hookEntryShape)` on `'claude'/'codex'/'copilot'` and `switch (vocabulary.kind)` on `'claude'/'cursor'/'copilot'/'codex'` — processors branch on hardcoded IDE names | **REQ AUTHORED — FR-ARCH-0005 (Approved); code fix = task #8** |
| `types.ts:92` | FR-HOOK-0004 / FR-VAR-0070 | unused `includeBootstrapRules` per-target flag | **DECIDED 2026-06-09: DEAD field (never read) — delete; FR-HOOK-0004 amended (bootstrap-rule flag superseded by FR-VAR-0070, RECON-8). `includeIndexEntries` stays. Code deferred.** |
| `plugin-sync-bundles.ts:46` | DATA-CFG-0001 / FR-HOOK-0020 | branch on `release.deterministicHooks` | **RESOLVED 2026-06-09: COMPLIANT, keep — genuine behavior flag from release config; no release name in control flow (NFR-0006 ✓, FR-ARCH-0005 permits). Optional SRP reshape not required.** |

## Fixed (this session)

| Fix | Location | What changed |
|---|---|---|
| Ghost frame ALL processors | `plugin-process-spec-entries.ts:56-79` | Removed `processor.name === 'fileRenameProcessor'` check; run ALL processors on null-content ghost frame (content processors no-op on empty source) |
| Ghost frame same-folder guard | `plugin-rewrite-references.ts:103-115` | Ghost frames (`source.length===0 && target_contents===null`) only emit pairs for same-folder renames; cross-folder pairs rejected |
| Debug cruft removed | `plugin-rewrite-references.ts` | Removed debug stderr.write block and `debugFile?` param |
| Scratch file deleted | `src/debug-pairs-temp.ts` | Untracked scratch file |

## Verified OK

FR-CLI-0001 — CLI entry with optional release/domain/source/output args and exit code (cli.ts).
FR-CLI-0020 — global --source default cwd, derived inputs, per-source overrides, no repo-root arg.
FR-CLI-0021 — --output defaults to `<source>/plugins`.
FR-CLI-0030 — --domain default `core`, resolves `<instructionsSource>/<release>/<domain>/`.

## Open work items

### A. ~~Make cursor bootstrap uniform (task #6)~~ — DONE
Short-circuit removed. r2 exit 1 (1 violation: cursor-standalone), r3 exit 1 (5 violations). Per FR-HOOK-0007: hooks generated for all IDEs always; delivery is a template decision.

### A2. Eliminate IDE-name switch dispatch — REQ AUTHORED (FR-ARCH-0005, Approved); code = task #8
Three sites branch on identity / an identity-discriminant flag (violates FR-ARCH-0004/0005):
- `bootstrap/payload.ts`: `switch (spec.hookEntryShape)` cases `'claude'/'codex'/'copilot'` (default null = cursor)
- `file-normalize-models.ts`: `switch (vocabulary.kind)` cases `'claude'/'cursor'/'copilot'/'codex'`
- `plugin-assemble-bootstrap.ts`: string interpolation `` `bootstrap_hooks_${shape}` `` (softer but same root)

Fix direction (per FR-ARCH-0005 — NOT a callback on a shared processor): write a **separate case-specific processor per case** and compose it only into that target's `PluginSpec` pipeline (the case is selected by *which* processor is in the pipeline, no runtime branch); factor shared logic into **low-level reusable helpers** the case-specific processors call (P1+P2). Remove the `hookEntryShape` and `ModelVocabulary.kind` enums. Model normalizers are per-vocabulary (genuinely different algorithms), not one map.

### B. `createHookFolderInR2` — DECIDED 2026-06-09: delete (code = task #17, deferred)
Bespoke per-release+per-target flag — forbidden by DATA-CFG-0002 / FR-ARCH-0004. **Baseline finding:** the only thing it uniquely creates is the **empty** r2 `core-cursor-standalone/.cursor/hooks/`; the other 4 `true` targets' hook folders are populated by rendered `hooks.json` anyway (flag redundant), codex is `false` (correct). That empty folder has **no functional value** — nothing references the directory; Cursor finds zero hook scripts whether it exists or not (empty = absent); it is a vestigial old-gen artifact (the old Python gen `mkdir`'d the hooks dir unconditionally). **Decision: delete the flag from `types.ts:124` + all 6 specs + the `plugin-sync-bundles.ts:86` branch; accept the now-absent empty `.cursor/hooks/` in r2 as an accepted old-gen artifact (Bucket-style). Code change deferred to a coding-flow session.**

**Origin trace (2026-06-09): NO requirement created this flag.** No FR mandates an empty r2 hook folder — FR-HOOK-0020 governs only bundle placement (r3) / stale-bundle removal (r2); FR-HOOK-0022 only preserves existing files; STRUCTURES.md documents only generated `hooks.json`/`*.js`, never an empty folder. The *only* requirement-level mentions of `createHookFolderInR2` **forbid** it (FR-ARCH-0004, DATA-CFG-0002; CHANGES.md RECON-7 already flagged it for removal on 2026-06-05). Introduced in impl commit `0b83256` to reproduce a vestigial baseline artifact ⇒ an **unbacked, baseline-overfit invention (wrong-prompt artifact)** — not requirements-driven. Removing it is a deviation correction, not a requirement change.

### C. Full requirements-deviation audit (task #18, deferred — ASK user before spawning)
Reviewer subagent: audit all `src/plugin-generator` vs every requirement. Known seeds: `createHookFolderInR2`, `includeBootstrapRules`, `deterministicHooks` branch.

### D. Tests + docs
Coverage re-verify after task #6. Update `IMPLEMENTATION.md`. `processor-audit.md` (FR-ARCH-0004 reusability audit) still MISSING.

### E. Requirements (Draft → review)
All 2026-06-05/06-08 requirement edits are `Draft` pending owner review (FR-ARCH-0004, FR-VAR-0070, FR-CLI source model, FR-COPY-0011 shell-schemas, FR-HOOK enrichments). Owner to approve.

### F. Distribution (NFR-0008, not started)
`npx` zero-build: ship compiled `dist` or document tsx. `bin` currently `src/cli.ts` (tsx).

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
