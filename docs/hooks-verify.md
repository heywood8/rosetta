# Hooks Output Format Verification

Terse, factual findings. Grounded in public docs and codebase inspection.
Session: 2026-06-24. Status: findings complete, implementation NOT started.

---

## User Intent

Verify all hook output formats used in Rosetta hooks. Check public docs per IDE/agent one at a time.
Check usage in `docs/requirements`, `rosettify-plugins`, and `instructions` (r2 + r3).

---

## Working Protocol (per agent, explicit — MUST follow)

For each IDE/agent, in this exact order:

1. **Spec doc**: Create/update `docs/hooks/<ide>.md` — EXACT contract: input model, output model, field-by-field meaning, constraints, direct links to official docs. No prose. Specs only.
2. **HITL — spec review**: Present spec to user. Resolve all uncertainties. Wait for **explicit approval** before proceeding.
3. Check `src/hooks` (grep/search — no full reads)
4. Check `docs/REQUIREMENTS` (grep; reset requirement status to `Draft` AFTER implementation, not before)
5. Check `src/rosettify-plugins` (grep for all affected usages)
6. Check `instructions/r*/configure/*.md` (grep; both r2 + r3)
7. **HITL gate**: present all findings — wait for **explicit approval** before touching code or docs
8. Update `hooks-verify.md` with confirmed decisions
9. Make changes across all areas
10. Update `hooks-verify.md` with post-change summary

**Constraint:** ONE agent at a time. No jumping ahead.
**Spec files:** `docs/hooks/copilot.md`, `docs/hooks/claude.md`, `docs/hooks/cursor.md`, `docs/hooks/codex.md`, `docs/hooks/windsurf.md` — one per IDE, created before any code work on that IDE.
**Target hook events (all IDEs):** `SessionStart`, `SessionStop`, `AgentStop`/`SubagentStop`, `PreToolUse`, `PostToolUse` — only these five. Each spec covers: exact input JSON model, exact output JSON model, field-by-field types/meanings/constraints, direct doc links. No prose.
**Matchers:** Document per-IDE matchers and wiring inside the respective `docs/hooks/<ide>.md`.

---

## User Decisions (HITL answers)

| Issue | Decision |
|---|---|
| Bug 1 — exit code never matches hook result | **Fix for all IDEs. Process exit code MUST match what hook returned. NOT Windsurf-only.** |
| Bug 2 — Copilot `additionalContext` placement | **Emit BOTH: top-level `additionalContext` AND inside `hookSpecificOutput.additionalContext`. Both contracts satisfied, nothing breaks. Do NOT switch between formats — merge them.** |
| Bug 2 — Copilot `additionalContext` on PreToolUse / PostToolUse | **RESOLVED (OI-1, 2026-06-25): earlier wording mis-recorded. Rule = use the dedicated field per purpose — PreToolUse deny → `permissionDecisionReason`; PostToolUse advisory + SessionStart context → `additionalContext` (its dedicated injection field). "Do NOT use `additionalContext`" applies ONLY to deny-reasons, NOT as a blanket ban.** |
| Gap 3 — `cursor.md` and `codex.md` missing Output Contract sections | **Yes, add. Re-verify whether all hooks follow same format OR some differ (in addition to IDE diffs). Include proof links. Output findings here.** |
| Gap 4/5 — `suppressOutput` dead, `ask` unsupported in Codex | **Not a gap — fields defined for future support. No change.** |

---

## Internal Pipeline

```
HookResult (hook logic)
  → toCanonical() in run-hook.ts
  → CanonicalOutput (intermediate)
  → adapter.formatOutput(canonical, ide) in adapter.ts
  → IDE-specific wire JSON → stdout
```

`run-hook.ts` always exits 0 on success (BUG — see below). Exit 1 on error.

### HookResult kinds

```typescript
| { kind: 'advise';      message: string }  // → hookSpecificOutput with additionalContext
| { kind: 'allow' }                          // → hookSpecificOutput with permissionDecision:'allow'
| { kind: 'deny';        reason: string }   // → hookSpecificOutput with permissionDecision:'deny', continue:false
| { kind: 'side-effect' }                   // → no stdout
| null                                       // → no stdout
```

### CanonicalOutput type (`src/hooks/src/types.ts`)

```typescript
interface CanonicalOutput {
  hookSpecificOutput?: {
    hookEventName?: string;
    additionalContext?: string;
    permissionDecision?: string;  // 'allow' | 'deny' | (per user: 'ask' kept for future)
    permissionDecisionReason?: string;
  };
  continue?: boolean;
  suppressOutput?: boolean;  // defined for future use, never set today
}
```

---

## Per-IDE Output Formats

### Claude Code

**Docs:** https://docs.anthropic.com/en/docs/claude-code/hooks  
**Our adapter:** `src/hooks/src/adapters/claude-code.ts` — identity pass-through, CanonicalOutput IS wire format.

Wire format (Claude Code = canonical):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "permissionDecision": "allow|deny|ask|defer",
    "permissionDecisionReason": "optional",
    "additionalContext": "optional string injected into Claude context"
  },
  "continue": false,
  "suppressOutput": false
}
```

Exit code semantics (official docs):
- `0` = success, stdout parsed as JSON
- `2` = blocking error; stderr → Claude; stdout ignored
- other non-zero = non-blocking; execution continues

**SessionStart additional fields** (not in our CanonicalOutput, not needed today):
`sessionTitle`, `initialUserMessage`, `watchPaths`, `reloadSkills`

---

### Codex (OpenAI)

**Docs:** https://platform.openai.com/docs/guides/codex/hooks  
**Our adapter:** `src/hooks/src/adapters/codex.ts` — identity pass-through (same schema as Claude Code).

Wire format: identical to Claude Code `hookSpecificOutput` schema.  
**Important:** `permissionDecision: "ask"` is NOT supported by Codex (parse failure). Claude Code allows it; Codex does not. Current hooks only emit `"deny"` so not triggered in practice.

Exit codes: `0` = success, `2` = failure with stderr reason.

**Documentation gap:** `instructions/*/configure/codex.md` has no Output Contract section. Only event names and `hooks.json` registration are documented.

---

### Cursor

**Docs:** https://cursor.com/docs/reference/hooks  
**Our adapter:** `src/hooks/src/adapters/cursor.ts` — maps canonical → Cursor snake_case.

Wire format mapping:

| CanonicalOutput field | Cursor wire field | Notes |
|---|---|---|
| `hookSpecificOutput.additionalContext` | `additional_context` | snake_case |
| `hookSpecificOutput.permissionDecision` | `permission` | renamed; values: `allow`/`deny` |
| `hookSpecificOutput.permissionDecisionReason` | `user_message` | user-facing |
| `continue: false` (fallback) | `permission: "deny"` | only if no explicit permissionDecision |

Cursor also documents `agent_message` (agent-visible reason) — our CanonicalOutput has no equivalent field.

Exit codes: `0` = success, `2` = block (equivalent to `permission: "deny"`). Both mechanisms work.

**Documentation gap:** `instructions/*/configure/cursor.md` has NO hook output format / Output Contract section. Cursor's `additional_context` format is only in `docs/requirements/plugin-generator/FR-VAR.md` and source code. Violates INT-IDE-0002 which designates configure guides as authoritative.

---

### GitHub Copilot

**Docs:** https://docs.github.com/en/copilot/tutorials/copilot-cli-hooks  
**Docs:** https://docs.github.com/en/copilot/reference/hooks-reference  
**Docs:** https://code.visualstudio.com/docs/agent-customization/hooks  
**Our adapter:** `src/hooks/src/adapters/copilot.ts`

**Two references, two different output contracts — both must be satisfied (merged approach per user decision):**
- GitHub Copilot CLI docs → `additionalContext` at **top level**
- VS Code agent hooks docs → `additionalContext` inside **`hookSpecificOutput`**

#### Official Copilot output schemas (both references)

**GitHub Copilot CLI** (`docs.github.com/copilot/reference/hooks-reference`):

| Hook | Output fields | Level |
|---|---|---|
| `sessionStart` | `additionalContext` | top-level |
| `preToolUse` | `permissionDecision`, `permissionDecisionReason`, `modifiedArgs` | top-level |
| `postToolUse` | `additionalContext`, `modifiedResult` | top-level |
| `sessionEnd` / `errorOccurred` | none | — |

**VS Code agent hooks** (`code.visualstudio.com/docs/agent-customization/hooks`):

| Hook | Output fields | Level |
|---|---|---|
| `sessionStart` | `hookSpecificOutput.hookEventName`, `hookSpecificOutput.additionalContext` | nested |
| `preToolUse` | `hookSpecificOutput.permissionDecision`, `hookSpecificOutput.permissionDecisionReason` | nested |
| `postToolUse` | `hookSpecificOutput.hookEventName`, `hookSpecificOutput.additionalContext` | nested |
| `sessionEnd` / `errorOccurred` | none | — |

#### Wire format — our adapter output today:
```typescript
// copilot.ts formatOutput (lines 90–94)
if (permissionDecision)       out.permissionDecision = permissionDecision;        // ✅ top-level — correct
if (permissionDecisionReason) out.permissionDecisionReason = permissionDecisionReason; // ✅ top-level — correct
if (cont === false && !out.permissionDecision) out.permissionDecision = 'deny';   // ✅ correct
if (additionalContext)        out.hookSpecificOutput = { hookEventName, additionalContext }; // ⚠️ nested only — missing top-level emit
```

**⚠️ BUG 2 — adapter emits `additionalContext` in `hookSpecificOutput` only. Must emit in BOTH locations for SessionStart.**
**⚠️ PreToolUse / PostToolUse must NOT use `additionalContext` — use specific reason field (TBD).**

Affected files:

| Layer | File | Issue |
|---|---|---|
| Runtime hook adapter | `src/hooks/src/adapters/copilot.ts:93` | Missing top-level `out.additionalContext` alongside existing `hookSpecificOutput` |
| Bootstrap generator | `src/rosettify-plugins/src/escaping/json-string.ts:47` | `buildHookPayloadJson` emits nested only — Copilot needs both top-level AND nested |
| Bootstrap manifest | `src/rosettify-plugins/src/spec/bootstrap-manifest.ts:47,54,62` | Copilot commands emit nested only |
| Lock comment | `src/rosettify-plugins/src/bootstrap/copilot-lock.ts:13` | References nested-only format — needs update |

`permissionDecision` values: `allow`, `deny`, `ask`. `ask` treated as deny in cloud agent.  
`preToolUse` is **fail-closed**: crash/non-zero/timeout denies the tool call.

Exit codes: `0` = parse JSON. `2` = warning or deny (context-dependent). Copilot dedup lock is file-based (session-based lock key per entry index) — handles the duplicate-fire bug.

#### Copilot Input Normalization — Adapter Contract (`src/hooks/src/adapters/copilot.ts`)

`normalize()` maps raw Copilot input to internal `NormalizedInput`. Copilot CLI sends camelCase; VS Code sends snake_case. Both shapes must be handled.

| NormalizedInput field | Source field(s) read | Ref | Notes |
|---|---|---|---|
| `session_id` | `raw.sessionId ?? raw.session_id` | R1, R3 | ✅ both shapes handled |
| `tool_name` | `raw.toolName` | R1 | ⚠️ camelCase only; `raw.tool_name` (R3 snake_case) NOT read |
| `tool_input` | `raw.toolArgs` (JSON string, parsed) | R1 | ⚠️ Copilot CLI sends string; VS Code (R3) sends `tool_input` as object — NOT read |
| `tool_use_id` | — (always `undefined`) | R3 | ⚠️ VS Code provides `tool_use_id` — never mapped |
| `cwd` | `raw.cwd` | R1, R3 | ✅ |
| `tool_response` | `raw.toolResult` (object `{resultType, textResultForLlm}`) | R1 | ⚠️ VS Code (R3) sends `tool_response` as plain string — type mismatch, NOT read |
| `file_path` | derived via `getFilePath(raw)` | — | extracted from parsed `toolArgs` |
| `source` | `raw.source` | R1 | |
| `reason` | `raw.reason` | R1 | |
| `transcript_path` | `raw.transcriptPath ?? raw.transcript_path` | R1, R3 | ✅ both shapes handled |
| `hook_event_name` | inferred via `inferHookEventName(raw)` | R3 | ⚠️ Copilot CLI sends no explicit event name; VS Code sends `hook_event_name` — not consumed directly, always inferred |
| `event` | inferred via `inferEvent(raw)` | — | derived from input shape: `toolResult` present → `PostToolUse`, else `PreToolUse` |

**Input normalization changes required (not yet implemented):**
- `tool_name`: must also read `raw.tool_name` (snake_case, R3 VS Code shape)
- `tool_input`: must handle `raw.tool_input` (object, R3); currently reads only `raw.toolArgs` (JSON string, R1)
- `tool_use_id`: must map `raw.tool_use_id` from R3 — always `undefined` today
- `tool_response`: must handle `raw.tool_response` (string, R3); currently reads only `raw.toolResult` (object, R1) — type mismatch
- `hook_event_name`: when `raw.hook_event_name` is present (R3), consume directly instead of always inferring

Resolution priority — see Open Items OI-3 in hooks-verify.md (below).

---

### Windsurf

**Docs:** https://docs.windsurf.com/windsurf/cascade/hooks (currently redirects to docs.devin.ai/desktop/cascade/hooks)  
**Our adapter:** `src/hooks/src/adapters/windsurf.ts`

**⚠️ BUG 1 (CONFIRMED):** Windsurf does NOT parse hook stdout JSON. Only process exit code matters.
- `_exitCode: 2` in our JSON stdout → silently ignored by Windsurf.
- To block a pre-hook in Windsurf, the process MUST exit with code 2.
- Our `dangerous-actions.js` deny is silently broken for Windsurf.
- `additionalContext` in JSON stdout also ignored (Windsurf has no context injection from hooks).

Current windsurf adapter `formatOutput` output:
```typescript
out.additionalContext = additionalContext;  // ignored by Windsurf
out._exitCode = 2;                           // ignored by Windsurf (not an exit code, just a JSON field)
```

Windsurf-only events (no CC equivalent): `PostResponse`, `PostWorktree`, `PrePromptSubmit`.

Exit code semantics: `0` = success, `2` = blocking (pre-hooks only), other non-zero = error continues.

---

## Hooks — Output Shape by Hook Type

| Hook | Result kinds | Notes |
|---|---|---|
| `dangerous-actions.js` | `deny`, `null` | Uses `deny(reason)` on pattern match; null if safe or marker allows |
| `lint-format-advisory.js` | `advise` | Always `advise(message)` on trigger |
| `loose-files.js` | `advise`, `null` | `advise` if loose file; null if within module |
| `md-file-advisory.js` | `advise` | Always `advise(message)` |
| `codemap-refresh.js` | `side-effect` | No stdout; agent must NOT see this hook |
| `read-once.js` | `advise`, `deny`, `null` | `deny` only in `READ_ONCE_MODE=deny` |
| `read-once-reset.js` | `side-effect` | No stdout |

All advisory hooks (`advise`) set `additionalContext` — relevant to Bug 2 for Copilot PostToolUse.
All deny hooks set `continue: false` + `permissionDecision: 'deny'` — relevant to Bug 1 (exit code).

---

## Bug 1 — Exit Code Never Matches Hook Result

**File:** `src/hooks/src/runtime/run-hook.ts` lines 397–403.

Current: all success paths return `exitCode: 0`. `process.exit(report.exitCode)` at line 33.
Expected: `deny` result → process must exit with code appropriate per IDE.
Additional: nullable _exitCode if set to NOT null must allow to override process exit code from the hooks (must be properly documented TO NOT use it unless EXTREMELY necessary).

Decision Tree: try { _ExitCode is not null ? return it : (deny ? return IDE specific : default 0) } catch { return 1000; }

Per-IDE expected exit code for deny:
- Claude Code: `0` (uses `continue: false` in JSON; exit 2 = error, not deny)
- Codex: `0` (same as Claude Code)
- Copilot: `0` (uses `permissionDecision: "deny"` in JSON; exit 2 = warning)
- Cursor: `2` (both JSON `permission: "deny"` and exit 2 work; being standard)
- Windsurf: `2` (ONLY mechanism; stdout not parsed)

**Fix design:** Add optional `exitCode(canonical: CanonicalOutput): number` to `IdeAdapter` interface (default: `() => 0`). Windsurf and Cursor adapters implement returning 2 on deny. `run-hook.ts` reads it. Remove `_exitCode` field from Windsurf `formatOutput`.

**Exit code decision tree (per user, 2026-06-25):**
```
try {
  _exitCode is not null  → return _exitCode   // emergency override; MUST document: DO NOT use unless EXTREMELY necessary
  deny                   → return IDE-specific exit code (see per-IDE table above)
  default                → return 0
} catch {
  return 1000
}
```

`_exitCode` override: nullable field; if set to non-null, it bypasses both deny-logic and default. Must be documented prominently as a last-resort escape hatch — NOT for normal hook use.

---

## Matchers and Hook Trigger Wiring

Matchers are internal TypeScript predicates that determine whether a hook fires for a given tool call.

**Regex convention:** `^(?:PATTERN)$` — anchored, non-capturing group wrapping alternatives. `PATTERN` is the content of the matcher itself. Example from `dangerous-actions/patterns.ts`:
```typescript
{ id: 'ssh-private-key', re: /^(?:id_rsa|id_ed25519|id_ecdsa|id_dsa)$/, ... }
```

**Wiring in `run-hook.ts`:**
- `FilePathPredicate` → checked at `evalFilePath()` — matches `ctx.filePath` against basename/extension/notContainsAny rules
- `ToolInputPredicate.commandMatchWhen` → checked at `evalToolInput()` — matches `ctx.toolInput.command` against `re.test(command)`
  - Only fires when `ctx.toolName` is in the `tools` array AND the command matches the regex

**Per-hook wiring (Copilot):**

| Hook | Matcher type | Pattern | Notes |
|---|---|---|---|
| `dangerous-actions` | `DANGEROUS_BASH[].re` | Various regex on bash commands | Applied to `ctx.toolInput.command` |
| `dangerous-actions` | `DANGEROUS_PATHS[].re` | `^(?:PATTERN)$` on file paths | Applied to `ctx.toolInput.file_path` |
| `dangerous-actions` | `DANGEROUS_CONTENT[].re` | Pattern on file content | Applied at write/edit time |
| `loose-files` | `commandMatchWhen.re` | `/^\*\*\* (?:Add\|Create) File:/m` | Only for `apply_patch` tool |
| `lint-format-advisory` | no commandMatchWhen | — | Fires on all write/edit tool calls |
| `md-file-advisory` | no commandMatchWhen | — | Fires on `.md` extension |

Document per-IDE matchers and wiring when working on each IDE's configure guide.

---

## Requirements / Instructions Alignment

| Source | Finding |
|---|---|
| `docs/requirements/plugin-generator/FR-HOOK.md` | ✅ Per-IDE entry shapes correct: Claude (`once:true`), Codex (`statusMessage+timeout`), Copilot (`bash+powershell`+lock), Cursor (plain command). ⚠️ Copilot bootstrap payload format (`hookSpecificOutput`) NOT explicitly required in FR-HOOK — no requirement currently captures that the Copilot bash command must emit `{"additionalContext":"..."}` (top-level). Requirement must be ADDED; status reset to `Draft` happens only AFTER changes are approved and implemented. |
| `docs/requirements/plugin-generator/FR-VAR.md` | ✅ Cursor `additional_context` (FR-VAR-0020) required explicitly |
| `docs/requirements/plugin-generator/REFERENCES.md` | INT-IDE-0002 designates configure guides as authoritative for hook output format |
| `instructions/*/configure/github-copilot.md` | ❌ Output Contract section present (lines 529-556, r2+r3 identical) BUT documents `hookSpecificOutput` wrapper for ALL events — WRONG for Copilot. Must be rewritten to show correct top-level format per event type. |
| `instructions/*/configure/cursor.md` | ❌ No Output Contract section — gap vs INT-IDE-0002 |
| `instructions/*/configure/codex.md` | ❌ No hook stdout output contract — gap vs INT-IDE-0002 |
| `src/rosettify-plugins/src/escaping/json-string.ts` | ❌ `buildHookPayloadJson` (used for Claude/Codex/Copilot) wraps in `hookSpecificOutput` — correct for Claude/Codex, WRONG for Copilot. Need `buildCopilotHookPayloadJson` → `{"additionalContext":"..."}`. |
| `src/rosettify-plugins/src/spec/bootstrap-manifest.ts` | ❌ Copilot plugin-root entries (lines 47, 54, 62) hardcode `hookSpecificOutput` → must change to `{"additionalContext":"..."}` |
| `src/rosettify-plugins/src/bootstrap/copilot-lock.ts:13` | ❌ Comment references wrong format `{"hookSpecificOutput":...}` — needs update |
| `src/rosettify-plugins/src/plugin-processors/plugin-assemble-copilot-bootstrap.ts:34` | ❌ Calls `buildHookPayloadJson` → must switch to `buildCopilotHookPayloadJson` |

**Note on requirement status reset:** FR-HOOK.md status fields are reset to `Draft` AFTER changes are approved AND implemented — not during discovery or check phase.

---

## Spec Authoring Rules (Mandatory — apply to every spec doc)

These are standing rules. Violations are NOT acceptable and must be caught before HITL approval.

1. **Ref column on every field table.** Every field table MUST have a `Ref` column citing which reference (R1/R2/R3/R4/etc.) defines each field. No field without a source. No exceptions.
2. **UX-destructive behaviors must be actively flagged.** Behaviors like "`systemMessage` is shown to the user regardless of all other output" are NOT plain field notes — they destroy UX if missed. Mark with `(!) UX: ...` and make it impossible to overlook. Manufacturer guidance must NEVER be downgraded.
3. **Hook names must be EXACT as defined by the manufacturer.** No invented names (e.g., `SessionStop`, `SessionEnd` that appear in no reference). No suggestions. No thinking. FACTS ONLY. If a name exists in R1 and a different name exists in R4, document both separately under their exact names.
4. **Merge by identity, never split, never guess.** Two SEPARATELY-NAMED hooks are TWO hooks — each its own section under its exact manufacturer name (`Stop` vs `agentStop` = separate; `agentStop` vs `subagentStop` = separate). When the ONLY difference is letter-case or model shape of the SAME hook name (`SessionStart`/`sessionStart`, `PreToolUse`/`preToolUse`), it is ONE hook with different field shapes — MERGE into a single section and document the per-shape fields (with `Ref` per field). Never split a single hook into multiple; never invent structure.
5. **Input normalization gaps ARE required work.** Where our adapters in `src/hooks` handle input only partially (e.g., camelCase only, not snake_case), those gaps must be documented as required changes — not deferred silently.
6. **`permissionDecisionReason` constraint must never be simplified.** Correct form: `(!) REQUIRED when permissionDecision is "deny" OR when decision is "block"`. Writing "required when deny" or any shorter form is a violation.
7. **Merged output contract must be explicit.** When a field is emitted at both top-level AND inside `hookSpecificOutput`, that must be stated explicitly — not implied by listing the field twice without explanation.
8. **Document EXACTLY as the manufacturer defines — zero improvements.** No speculation, no editorializing, no "may represent the same lifecycle moment," no inferred unification, no narrating reasoning. State only what the manufacturer documents. If two things are documented separately, keep them separate; if a behavior is unknown, say "unknown / not documented" — never invent a bridge between facts.
9. **Use the dedicated field per purpose — `additionalContext` is not a catch-all.** Map each output to the field the manufacturer designates: deny reason → `permissionDecisionReason`; context injection (SessionStart, PostToolUse advisory) → `additionalContext`. Never use `additionalContext` to carry a deny reason, and never default everything to `additionalContext`.
10. **Scope reasonably — no extremes.** Support the real input/output shapes (CLI camelCase + VS Code snake_case) sensibly; platforms are largely case-tolerant. Don't over-engineer for every theoretical variant, and don't under-handle real ones. When a behavior is uncertain, CONFIRM it empirically (build/install a throwaway probe and observe) rather than guess or speculate in the doc.

---

## Spec Authoring Violations — First Draft of `docs/hooks/copilot.md`

Record of violations found and corrected:

1. **Missing Ref column** — field tables had no source citations. Fixed in rewrite.
2. **`systemMessage` downgraded** — treated as plain field. Fixed: marked `(!) UX: shown to user regardless of all other output`.
3. **Fabricated event names** — used `SessionStop`, `SessionEnd` as section headers; neither exists in any reference. Fixed: R4 uses `Stop`; R1 uses `sessionEnd` as separate event.
4. **Illegal event merge** — merged R4 `Stop` and R1 `agentStop` into one section. Fixed: each is its own section under its exact name from its source.
5. **Implementation detail in spec** — "Input Normalization Contract" referencing `src/hooks/src/adapters/copilot.ts` placed in spec doc. Fixed: removed from spec; documented in hooks-verify.md (Copilot section, normalization table).
6. **`permissionDecisionReason` duplicated without explanation** — appeared in two rows with no statement that both are intentional. Fixed: merged output contract explicitly stated.
7. **`permissionDecisionReason` constraint simplified** — written as "required when deny". Fixed: `(!) REQUIRED when permissionDecision is "deny" OR when decision is "block"`.

---

## Open Items — TBD Before Implementation

| # | Question |
|---|---|
| OI-1 | ✅ RESOLVED (2026-06-25): `additionalContext` IS the dedicated PostToolUse advisory field (R1 top-level + R3 nested); no other advisory field exists, `reason` is block-only. Advisory hooks use `additionalContext`; deny uses `permissionDecisionReason`. Dedicated-field-per-purpose principle. |
| OI-2 | ✅ RESOLVED (2026-06-25): `Stop` is a STANDARD (VS Code) hook event; `agentStop` is a COPILOT-CUSTOM event. They are SEPARATE events — document EACH EXACTLY as the manufacturer defines it. NO merging, NO "same lifecycle moment" speculation, NO improvements. No adapter change needed for now. |
| OI-3 | ⏳ Scope set (2026-06-25): support BOTH Copilot CLI (R1 camelCase) AND VS Code (R3 snake_case), reasonably — platforms are case-tolerant, do NOT over-engineer. Correctness-blocking: `tool_name`/`tool_input` snake_case (matchers + file-path extraction fail under VS Code today). NOTE (R2): VS Code IGNORES matcher values — hooks fire on ALL tools, must self-guard internally. Empirical plugin probe deferred to later this session to confirm real case-tolerance before finalizing which gaps are truly blocking. |

---

## Verification — copilot.md vs sources (2026-06-25, opus subagent, read-only)

Field-by-field verification of `docs/hooks/copilot.md` against R1 (GitHub Copilot CLI), R2 (VS Code agent-customization), R3 (VS Code hooks reference), R4 (local VS Code extension `hooks.md`). All four fetched/read.

**Verdict:** substantially faithful on field mechanics — key names, camelCase/snake_case split, timestamp type split (number-ms vs ISO string), enum values, `REQUIRED when block/deny` constraints, top-level-vs-`hookSpecificOutput` merged-emit claims, exit codes all grounded. No fabricated event names. SubagentStop "top-level only, no wrapper" nuance correct.

**Must-fix — 5 corrections (pending HITL edit pass, not yet applied):**
1. SessionStart `source` "always new" → cite **R3**, not R4 (R4 has no SessionStart input schema).
2. Matcher section "(R1, R4)" → **drop R4** (R4 documents no matcher format).
3. PreToolUse "Fail-closed (R1, R4)" → **drop R4** (R4 states no fail-closed behavior).
4. SessionStart Output top-level `additionalContext` cited R1 → inferred, not verbatim in R1 output schema → soften / re-cite.
5. Stop/agentStop section (line 111) → **remove** "May represent the same lifecycle moment" speculation (OI-2). Document `Stop` as standard VS Code event and `agentStop` as Copilot-custom event, each exactly as the manufacturer defines — no merging, no improvements.

**Withdrawn — verifier false positive (keep doc as-is):** `systemMessage` "(!) UX: displayed regardless / always visible" is CORRECT — real Copilot behavior (shows approval dialog). Verifier was over-constrained (cite-verbatim-or-reject), graded a true-but-not-verbatim UX behavior as "ungrounded embellishment." Prompt defect, not doc defect. Lesson recorded in `agents/MEMORY.md`.

**Completeness (acceptable):** doc deliberately scoped to "events used by Rosetta hooks" (line 50); R1 defines more events (`errorOccurred`, `notification`, `permissionRequest`, `postToolUseFailure`, camelCase `subagentStart`) intentionally omitted. Caveat: "Hook Locations" attributed solely to R4 while dropping R1's broader location set (`.github/hooks/*.json`, `~/.copilot/hooks/`, policy paths) — re-scope or re-attribute in the edit pass.

---

## Pending Actions (current session — awaiting explicit user approval before implementation)

### Action 1 — Fix Bug 2: Copilot `additionalContext` placement (CONFIRMED — wider than originally scoped)

Affects 4 files in `src/rosettify-plugins` + 1 file in `src/hooks/src/adapters` + configure docs r2+r3:

- `src/hooks/src/adapters/copilot.ts:93` — replace `out.hookSpecificOutput = { hookEventName, additionalContext }` with `out.additionalContext = additionalContext`
- `src/rosettify-plugins/src/escaping/json-string.ts` — add `buildCopilotHookPayloadJson` → `{"additionalContext":"${escaped}"}`
- `src/rosettify-plugins/src/plugin-processors/plugin-assemble-copilot-bootstrap.ts:34` — switch to `buildCopilotHookPayloadJson`
- `src/rosettify-plugins/src/spec/bootstrap-manifest.ts:47,54,62` — change Copilot payload from `{"hookSpecificOutput":...}` to `{"additionalContext":"..."}`
- `src/rosettify-plugins/src/bootstrap/copilot-lock.ts:13` — update comment
- `instructions/r2+r3/core/configure/github-copilot.md` — rewrite Output Contract: correct per-event top-level schema, add sessionStart two-type table, add matchers/wiring section
- `docs/REQUIREMENTS/plugin-generator/FR-HOOK.md` — add new requirement for Copilot payload format; reset affected requirement status to `Draft` AFTER implementation

### Action 2 — Fix Bug 1: exit code decision tree

- `src/hooks/src/types.ts` — add `exitCode?(canonical: CanonicalOutput): number` to `IdeAdapter` interface
- `src/hooks/src/adapters/windsurf.ts` — implement `exitCode`: return 2 on deny; remove `_exitCode` from `formatOutput`
- `src/hooks/src/adapters/cursor.ts` — implement `exitCode`: return 2 on deny
- `src/hooks/src/runtime/run-hook.ts` — apply decision tree: `_exitCode not null → use it; deny → adapter.exitCode(); default → 0; catch → 1000`
- Document `_exitCode` override as last-resort escape hatch in configure docs

### Action 3 — Add Output Contract to `cursor.md` (r2 + r3)

- Document `additional_context`, `permission`, `user_message` — top-level Cursor fields
- Include matchers/wiring section for Cursor
- Proof link: https://cursor.com/docs/reference/hooks

### Action 4 — Add Output Contract to `codex.md` (r2 + r3)

- Document `hookSpecificOutput` schema (same as Claude Code)
- Note: `permissionDecision: "ask"` NOT supported by Codex
- Proof link: https://platform.openai.com/docs/guides/codex/hooks

### Action 5 — Update tests: exit code assertions per IDE for deny

- `src/hooks/tests/` — Windsurf deny → exit 2, Cursor deny → exit 2, Claude Code deny → exit 0, Copilot deny → exit 0, Codex deny → exit 0

---

## Key Source Files

- `src/hooks/src/runtime/run-hook.ts` — hook executor, exit code decision
- `src/hooks/src/types.ts` — `CanonicalOutput`, `IdeAdapter` interface
- `src/hooks/src/adapter.ts` — `formatOutput` dispatcher
- `src/hooks/src/adapters/*.ts` — per-IDE formatOutput implementations
- `src/rosettify-plugins/src/escaping/json-string.ts` — bootstrap payload builders
- `src/rosettify-plugins/src/bootstrap/payload.ts` — per-IDE entry shape builders
- `docs/requirements/plugin-generator/FR-HOOK.md` — authoritative entry shapes
- `docs/requirements/plugin-generator/FR-VAR.md` — Cursor `additional_context` requirement
- `instructions/r2/core/configure/github-copilot.md` — Output Contract reference (lines 529-556)
