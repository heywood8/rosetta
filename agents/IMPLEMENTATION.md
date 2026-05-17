# Rosetta Implementation Summary

This file is a durable summary of the current implementation state.
It is intentionally concise and should not be used as a chronological work log.

For detailed change history, use git history and PRs instead of expanding this file.

## Current State

- Rosetta is an OSS instruction platform with:
  - a Python MCP server in `ims-mcp-server/`
  - a Python CLI in `rosetta-cli/`
  - public documentation in `docs/` and `docs/web/`
  - deployment examples under `deployment/`
- The MCP server supports both `stdio` and HTTP transports.
- HTTP mode supports OAuth-based authentication, session storage, and policy-based authorization.
- The CLI supports publish, verify, list, parse, cleanup, and related packaging flows.
- The repository contains both user-facing OSS docs and contributor-oriented implementation notes.

## Major Implemented Workstreams

### MCP Server

- Refactored into a modular package structure with dedicated `config`, `context`, `services`, `tools`, `auth`, and `analytics` modules.
- Core MCP tools are implemented, including:
  - `get_context_instructions`
  - `query_instructions`
  - `list_instructions`
  - `submit_feedback`
  - `query_project_context`
  - `store_project_context`
  - `discover_projects`
  - `plan_manager`
- Added HTTP transport support on top of the existing `stdio` mode.
- Added Redis-backed session and plan storage with in-memory fallbacks for local development.
- Added OAuth/OIDC integration for HTTP deployments, including introspection-based validation and offline-refresh handling.
- Added a FastMCP loopback redirect compatibility patch so CIMD-based OAuth clients using ephemeral localhost callback ports can complete HTTP authentication.
- Added origin validation and cross-tool hardening around invalid inputs, malformed requests, and wrapper failures.
- Added response-shape and schema cleanup so tool contracts are more predictable for coding agents.
- MCP dataset lookup caches dataset objects as well as name/id mappings, avoiding repeated dataset-open calls during instruction/resource/project tool execution.
- Analytics repository detection caches MCP roots per HTTP session and uses a fixed singleton cache key for STDIO/local transports.

### Authorization and Security

- Dataset access is policy-driven, with separate read/write behavior for project datasets.
- OAuth configuration supports both generic OAuth token introspection and OIDC discovery-based validation.
- Token/session handling includes encryption hooks, TTL controls, and negative-cache behavior for introspection.
- Public documentation and examples were scrubbed to remove internal infrastructure details while retaining public OSS references.

### CLI and Publishing

- The CLI was migrated to the RAGFlow-backed model and later refactored into a command-pattern architecture.
- Publishing supports change detection, dry-run flows, and dataset-scoped cleanup behavior.
- Publishing reuses in-process dataset lookups during a CLI run and clears that cache after dataset create/delete operations.
- Auth checks were tightened so API-backed commands fail earlier and more predictably.
- A dedicated `version` command was added so package version inspection does not require config loading or auth.
- Package metadata and publish flows were repaired to keep CI/CD and PyPI publishing functional.

### rosettify (npm package)

- Local CLI/MCP tool runner for Rosetta. Published on npm as `rosettify` (`rosettify/`).
- Dual-frontend: same run delegates behind both `npx rosettify <cmd>` CLI and `rosettify --mcp` stdio server.
- Current commands: `plan` (create, next, update_status, show_status, query, upsert, create-with-template, upsert-with-template, list-templates), `help`.
- **Atomic write cycle (FR-PLAN-0024)**: every plan mutation uses a rename-as-guard write cycle — rename plan to `<file>.bakNNN` (backup chain, up to 5 retained), then write new content. `previous_version` field on the plan JSON tracks the prior backup path. Bounded to 50 retries; `backup_create_failed` on exhaustion.
- **Template registry (FR-PLAN-0033)**: two compiled-in template kinds (`create`, `upsert`) with strict bidirectional placeholder matching. Seed templates: `for-orchestrator` (create) and `for-subagent` (upsert). New subcommands `create-with-template`, `upsert-with-template`, `list-templates`.
- **Compressed-tree output (FR-PLAN-0040)**: all write subcommands return `{ plan, previous_version, phases[{steps}] }` instead of ad-hoc result shapes. CLI output is dense JSON (no indent, FR-SHRD-0008).
- Envelope is internal: frontends extract payload via `extractOutput` and log failures via `logFailure` before output — consumers never see the raw envelope wrapper.
- Validated with `npm run typecheck` and `npm run test` (vitest, 90%+ line + branch coverage).

### Instructions and Skills

- Added `plan-manager` skill under `instructions/r2/core/skills/plan-manager/` — primary plan manager for coding agents via local JSON files.
- Skill assets: `plan_manager.js` (CLI, no npm deps), `pm-schema.md` (data structure reference), `plan_manager.test.js` (60 unit tests).
- Key behaviors: resume-safe `next` command returns `in_progress` steps with `resume: true` before `open` steps; plans stored at `plans/<name>/plan.json`; self-describing `help` command.
- Converted `adhoc-flow-with-plan-manager` workflow to `USE SKILL plan-manager`; data structure externalized to `pm-schema.md`.
- All plugins (`core-claude`, `core-cursor`, `core-copilot`, `core-codex`, `core-cursor-standalone`, `core-copilot-standalone`) are auto-synced from core by `scripts/pre_commit.py`.

### Plugin Generator

- **Model normalization** — `plugin_generator.py` selects the first model from the frontmatter `model:` comma-separated list using `_normalize_by_map`. `CURSOR_MODEL_MAP` maps to Cursor format (`claude-sonnet-4-6`, `gpt-5.4`); `COPILOT_MODEL_MAP` maps to Copilot format (`Claude Sonnet 4.6`, `GPT-5.4`). Fixes previous behavior where Copilot searched the entire comma-separated string and always returned Claude even when the intended first model was GPT.
- **Folder/file rename (precise path replacement)** — `copy_core_tree` builds two dicts from a source scan: `file_renames` (old filename → new filename, for actual file renaming) and `path_renames` (full old path → full new path, for content replacement). `path_renames` entries are exact strings like `"workflows/coding-flow.md"` → `"commands/coding-flow.md"`, preventing accidental partial-word matches. Folder-level entries (`"workflows/"` → `"commands/"`) are added explicitly so bare folder references in instruction text are also updated. Both dicts are derived from `spec.rename_folders` and `spec.rename_files`. Cursor renames `workflows/` → `commands/`; Copilot renames `workflows/` → `prompts/` and files `*.md` → `*.prompt.md`. Bootstrap hook content is patched with the same `path_renames` before template processing. Index title is normalized to `# Rosetta Workflows Index` regardless of physical folder name via `_FOLDER_TITLE_ALIASES`.
- **Copilot prompts rename** — `workflows/` → `prompts/`, files `*.md` → `*.prompt.md` for core-copilot and core-copilot-standalone. `PluginSyncSpec` gains `rename_files: tuple[tuple[str, str], ...]` (suffix pairs). `copilot-instructions.md` and bootstrap hook content reference `prompts/*.prompt.md`. `_FOLDER_TITLE_ALIASES` maps `"prompts"` → `"Workflows"`.
- **Workflow index filtering** — `generate_folder_index` accepts `required_tag` parameter. Only files with `tags: ["workflow"]` appear in workflow/commands indexes; the 31 phase files (aqa-flow-*, init-workspace-flow-*, etc.) are excluded.
- **Standalone plugins** — `StandaloneSpec` dataclass drives a second-pass generation loop producing `core-cursor-standalone` and `core-copilot-standalone`. Each standalone is fully wiped and recreated from its main plugin. Supports `pre_cleanup`, `post_cleanup`, `copilot_instructions`, `inject_index_folder`/`inject_index_target` for per-platform customizations. Copilot standalone generates `copilot-instructions.md` from `plugin-files-mode.md` with an inserted context instruction and appended workflow index; removes hooks, mcp.json, templates, and plugin-files-mode.md. Cursor standalone injects the commands index into `rules/plugin-files-mode.md`. Standalone `plugin.json` (version inherited from main plugin) is excluded from CI zip archives via `*-standalone` branch in `publish-instructions.yml`.

### Workflows and Automation

- GitHub Actions were updated to remove most deprecated Node 20-era dependencies and align with newer action runtimes where upstream allowed it.
- Init-workspace instructions now treat `rosetta@rosetta` as the MCP connector path rather than plugin mode, while any other plugin type is handled as plugin mode.
- Workflow maintenance included:
  - Bun runtime override for Claude workflows
  - build/publish pipeline repairs
  - rosetta-mcp publish gating that waits for the matching `ims-mcp` version to appear on PyPI before upload
  - native Git pre-commit hook shim with a shared Python entrypoint under `scripts/`
  - generated plugin trees sourced from `instructions/r2/core` for all six plugin variants
  - plugin-specific packaging transforms for model metadata, generated indexes, and local marketplace/manifests
  - bootstrap hooks inlined at build time via `hooks.json.tmpl` templates and generic `process_templates` engine; runtime shell scripts eliminated; 4 platform-specific placeholder formats (Claude, Codex, Cursor, Copilot) generated once per build
  - Jira loader recovery after upstream API changes
  - shared type-validation entrypoint
- Some GitHub Pages actions remain upstream-limited and may still depend on older Node runtimes until upstream changes.

### Documentation and Public Surface

- Installation, deployment, quickstart, troubleshooting, and README content were aligned with the current transport/auth model.
- Usage guides describe workflow phases, expected subagents/artifacts, HITL gates, and user responsibilities for the unified Rosetta workflow set.
- Docs pages rendered via the Jekyll site now convert fenced Mermaid blocks client-side in the docs layout, preserve authoring as plain ````mermaid` fences, rerender on theme changes, and scale rendered SVGs for better readability on GitHub Pages direct loads.
- Internal/private environment details were replaced with public-safe placeholders where appropriate.
- Public Docker Hub references remain intentionally visible because they are part of the OSS distribution surface.

## Known Constraints

- Local test execution depends on the correct Python version and optional package dependencies being installed.
- Some flows depend on external systems such as RAGFlow, Redis, OAuth providers, GitHub Actions, or Jira; local code changes cannot fully validate those integrations without environment access.
- HTTP deployments require careful environment configuration for callback URLs, token storage, TLS, and origin policy.
- Legacy compatibility paths exist for older clients, but the preferred path is the current Rosetta HTTP/modern MCP setup.
- Temporary research utilities under `agents/TEMP/` are not part of the stable product surface unless promoted elsewhere.

## Validation Status

- The repository has focused unit and regression coverage across MCP tools, config parsing, auth flows, analytics wrappers, and CLI behaviors.
- Validation scripts and targeted pytest runs are used regularly, but passing them depends on local environment readiness.
- Integration verification exists for MCP behavior, including live or semi-live harnesses, but external services remain the main source of non-code failures.

## Maintenance Rules For This File

- Keep this file under roughly 150 lines.
- Prefer stable summaries over date-stamped status bullets.
- Do not add per-day implementation logs here.
- Do not duplicate information already captured in architecture docs, READMEs, or git history.
- If a new capability materially changes Rosetta, update the relevant section above instead of appending a diary entry.
