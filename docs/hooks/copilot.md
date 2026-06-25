# Copilot Hooks Contract

Target agent: **GitHub Copilot** (VS Code IDE + GitHub Copilot CLI)

Status: **DRAFT — awaiting user approval**

---

## References

| ID | System | URL / Path |
|---|---|---|
| R1 | GitHub Copilot CLI hooks reference | https://docs.github.com/en/copilot/reference/hooks-reference |
| R2 | VS Code agent customization hooks | https://code.visualstudio.com/docs/agent-customization/hooks |
| R3 | VS Code hooks reference | https://code.visualstudio.com/docs/agents/reference/hooks-reference |
| R4 | VS Code Copilot extension (internal) | `/Applications/Visual Studio Code.app/Contents/Resources/app/extensions/copilot/assets/prompts/skills/agent-customization/references/hooks.md` |

---

## Hook Locations (R4)

| Path | Scope |
|---|---|
| `.github/hooks/*.json` | Workspace (team-shared) |
| `.claude/settings.local.json` | Workspace local (not committed) |
| `.claude/settings.json` | Workspace |
| `~/.claude/settings.json` | User profile |

---

## Hook Events

| Event name (exact) | Source | Trigger |
|---|---|---|
| `SessionStart` | R4 | First prompt of a new agent session |
| `sessionStart` | R1 | New or resumed session begins |
| `UserPromptSubmit` | R4 | User submits a prompt |
| `PreToolUse` | R4 | Before tool invocation |
| `preToolUse` | R1 | Before tool executes |
| `PostToolUse` | R4 | After successful tool invocation |
| `postToolUse` | R1 | Tool completes successfully |
| `Stop` | R4 | Agent session ends |
| `agentStop` | R1 | Main agent finishes turn |
| `SubagentStop` | R4 | Subagent ends |
| `subagentStop` | R1 | Subagent completes |
| `sessionEnd` | R1 | Session terminates |
| `PreCompact` | R4 | Before context compaction |
| `SubagentStart` | R4 | Subagent starts |

Events used by Rosetta hooks: `SessionStart`/`sessionStart`, `PreToolUse`/`preToolUse`, `PostToolUse`/`postToolUse`, `Stop`/`agentStop`, `SubagentStop`/`subagentStop`, `sessionEnd`.

---

## Common Output Fields (ALL hook events)

| Field | Type | Ref | (!) Notes |
|---|---|---|---|
| `continue` | boolean | R4 | `false` = halt processing |
| `stopReason` | string | R4 | shown to user when `continue: false` |
| `systemMessage` | string | R4 | **(!) UX: displayed to user regardless of all other output — always visible** |

---

## SessionStart / sessionStart

### Input

| Field | Type | Required | Ref | Notes |
|---|---|---|---|---|
| `sessionId` | string | yes | R1 | camelCase shape |
| `session_id` | string | yes | R3 | snake_case / VS Code shape |
| `timestamp` | number (unix ms) | yes | R1 | camelCase shape |
| `timestamp` | string (ISO 8601) | yes | R3 | snake_case shape; same key, different type |
| `cwd` | string | yes | R1, R3 | |
| `source` | `"startup"\|"resume"\|"new"` | yes | R1 | R4: always `"new"` |
| `initialPrompt` | string | no | R1 | camelCase |
| `initial_prompt` | string | no | R1 | snake_case |
| `hook_event_name` | `"SessionStart"` | yes | R3 | absent in R1 camelCase shape |

### Output

| Field | Type | Ref | Notes |
|---|---|---|---|
| `additionalContext` | string | R1 | top-level; injected into session |
| `hookSpecificOutput.hookEventName` | `"SessionStart"` | R3 | nested |
| `hookSpecificOutput.additionalContext` | string | R3 | nested; same content as top-level field |

**Merged emit:** `additionalContext` at top-level (R1) AND inside `hookSpecificOutput` (R3).

---

## sessionEnd

### Input

| Field | Type | Required | Ref | Notes |
|---|---|---|---|---|
| `sessionId` | string | yes | R1 | |
| `timestamp` | number (unix ms) | yes | R1 | |
| `cwd` | string | yes | R1 | |
| `reason` | `"complete"\|"error"\|"abort"\|"timeout"\|"user_exit"` | yes | R1 | |

### Output

**Notification only — no output processed. (R1)**

---

## Stop (R4) / agentStop (R1)

Two distinct event names from two systems. May represent the same lifecycle moment.

### Input

| Field | Type | Required | Ref | Notes |
|---|---|---|---|---|
| `sessionId` | string | yes | R1 | camelCase |
| `session_id` | string | yes | R3 | snake_case |
| `timestamp` | number / string | yes | R1, R3 | |
| `cwd` | string | yes | R1 | |
| `transcriptPath` | string | yes | R1 | camelCase |
| `transcript_path` | string | yes | R3 | snake_case |
| `stopReason` | `"end_turn"` | yes | R1 | camelCase |
| `stop_reason` | `"end_turn"` | yes | R3 | snake_case |
| `hook_event_name` | `"Stop"` | yes | R3 | R4 event name |
| `stop_hook_active` | boolean | yes | R3 | whether agent continues from previous stop hook invocation |

### Output

| Field | Type | Ref | Notes |
|---|---|---|---|
| `decision` | `"block"\|"allow"` | R1 | top-level; omit = allow |
| `reason` | string | R1 | top-level; **(!) REQUIRED when `decision` is `"block"`**; used as next prompt |
| `hookSpecificOutput.hookEventName` | `"Stop"` | R3 | nested |
| `hookSpecificOutput.decision` | `"block"` | R3 | nested |
| `hookSpecificOutput.reason` | string | R3 | nested; **(!) REQUIRED when `decision` is `"block"`** |

**Merged emit:** top-level `decision`/`reason` (R1) AND `hookSpecificOutput.decision`/`reason` (R3).

---

## SubagentStop / subagentStop

### Input

| Field | Type | Required | Ref | Notes |
|---|---|---|---|---|
| `sessionId` | string | yes | R1 | camelCase |
| `session_id` | string | yes | R3 | snake_case |
| `timestamp` | number / string | yes | R1, R3 | |
| `cwd` | string | yes | R1 | |
| `agentName` | string | yes | R1 | camelCase |
| `agent_name` | string | yes | R3 | snake_case |
| `agentDisplayName` | string | no | R1 | camelCase |
| `agent_display_name` | string | no | R3 | snake_case |
| `stopReason` | `"end_turn"` | yes | R1 | camelCase |
| `stop_reason` | `"end_turn"` | yes | R3 | snake_case |
| `hook_event_name` | `"SubagentStop"` | yes | R3 | |
| `agent_id` | string | yes | R3 | VS Code only |
| `agent_type` | string | yes | R3 | VS Code only |
| `stop_hook_active` | boolean | yes | R3 | |
| `transcriptPath` / `transcript_path` | string | yes | R1 | |

### Output

| Field | Type | Ref | Notes |
|---|---|---|---|
| `decision` | `"block"\|"allow"` | R1, R3 | top-level; omit = allow |
| `reason` | string | R1, R3 | top-level; **(!) REQUIRED when `decision` is `"block"`** |

**Note:** R3 SubagentStop output is top-level only — no `hookSpecificOutput` wrapper.

---

## PreToolUse / preToolUse

### Input

| Field | Type | Required | Ref | Notes |
|---|---|---|---|---|
| `sessionId` | string | yes | R1 | camelCase |
| `session_id` | string | yes | R3 | snake_case |
| `timestamp` | number / string | yes | R1, R3 | |
| `cwd` | string | yes | R1 | |
| `toolName` | string | yes | R1 | camelCase; matched against optional matcher |
| `tool_name` | string | yes | R3 | snake_case |
| `toolArgs` | string (JSON) | yes | R1 | **(!) JSON string — must be parsed, NOT an object** |
| `tool_input` | object | yes | R3 | already parsed object |
| `tool_use_id` | string | yes | R3 | absent in R1 |
| `hook_event_name` | `"PreToolUse"` | yes | R3 | absent in R1 camelCase shape |

### Output

| Field | Type | Ref | Notes |
|---|---|---|---|
| `permissionDecision` | `"allow"\|"deny"\|"ask"` | R1 | top-level; omit = normal flow; cloud agent: `"ask"` → treated as `"deny"` |
| `permissionDecisionReason` | string | R1 | top-level; **(!) REQUIRED when `permissionDecision` is `"deny"`** |
| `modifiedArgs` | object | R1 | top-level; substitutes tool arguments |
| `hookSpecificOutput.hookEventName` | `"PreToolUse"` | R3 | nested |
| `hookSpecificOutput.permissionDecision` | `"allow"\|"deny"\|"ask"` | R3, R4 | nested |
| `hookSpecificOutput.permissionDecisionReason` | string | R3 | nested; **(!) REQUIRED when `permissionDecision` is `"deny"`** |
| `hookSpecificOutput.updatedInput` | object | R3 | nested; VS Code equivalent of `modifiedArgs` |
| `hookSpecificOutput.additionalContext` | string | R3 | nested; extra context for model |

**Merged emit:** top-level fields (R1) AND `hookSpecificOutput.*` (R3) — both sets emitted simultaneously.  
**Fail-closed (R1, R4):** crash / non-zero exit / timeout = deny.

### Matcher (R1, R4)

Pattern applied to `toolName` / `tool_name`. Format: `^(?:PATTERN)$` where PATTERN is the matcher content.  
Omit matcher = fires on all tools.  
Claude Code matchers: `*` / `**` / empty = all; `|`-separated literals = alternation; other = case-sensitive regex.

---

## PostToolUse / postToolUse

### Input

| Field | Type | Required | Ref | Notes |
|---|---|---|---|---|
| `sessionId` | string | yes | R1 | camelCase |
| `session_id` | string | yes | R3 | snake_case |
| `timestamp` | number / string | yes | R1, R3 | |
| `cwd` | string | yes | R1 | |
| `toolName` | string | yes | R1 | camelCase |
| `tool_name` | string | yes | R3 | snake_case |
| `toolArgs` | string (JSON) | yes | R1 | **(!) JSON string — must be parsed** |
| `tool_input` | object | yes | R3 | already parsed |
| `toolResult` | object `{resultType: "success", textResultForLlm: string}` | yes | R1 | |
| `tool_response` | string | yes | R3 | plain string, not object |
| `tool_use_id` | string | yes | R3 | absent in R1 |
| `hook_event_name` | `"PostToolUse"` | yes | R3 | absent in R1 camelCase shape |

### Output

| Field | Type | Ref | Notes |
|---|---|---|---|
| `modifiedResult.resultType` | `"success"` | R1 | **(!) REQUIRED when `modifiedResult` present** |
| `modifiedResult.textResultForLlm` | string | R1 | **(!) REQUIRED when `modifiedResult` present**; replaces tool result seen by model |
| `additionalContext` | string | R1 | top-level; appended after tool result; max 10 KB across all hooks joined |
| `decision` | `"block"` | R3, R4 | top-level; halts further processing |
| `reason` | string | R3 | top-level; **(!) REQUIRED when `decision` is `"block"`** |
| `hookSpecificOutput.hookEventName` | `"PostToolUse"` | R3 | nested |
| `hookSpecificOutput.additionalContext` | string | R3 | nested; injected into conversation |

**Merged emit:** top-level `additionalContext` (R1) AND `hookSpecificOutput.additionalContext` (R3).  
**For block:** top-level `decision`/`reason` (R3, R4). No R1 equivalent for blocking on PostToolUse — R1 uses exit code 2.

### Matcher (R1)

Pattern: `^(?:PATTERN)$` on `toolName`. Omit = all tools.

---

## Exit Codes (all hooks)

| Code | Meaning | Ref |
|---|---|---|
| `0` | Success; stdout parsed as JSON | R1, R4 |
| `2` | Blocking error (PreToolUse: deny; PostToolUse: warning or deny — context-dependent) | R1, R4 |
| other non-zero | Non-blocking warning; execution continues | R4 |

---

**Open items:** see `docs/hooks-verify.md` — Open Items OI-1, OI-2, OI-3.
