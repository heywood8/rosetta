#!/usr/bin/env python3
"""Plugin generator: syncs instruction sources into IDE plugin folders."""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ALLOWED_CLAUDE_MODELS = {"opus", "sonnet", "haiku", "inherit"}

EXCLUDED_RULE_FILES = {"rules/bootstrap.md", "rules/local-files-mode.md"}

BOOTSTRAP_PREFIX = (
    "ALWAYS MUST FULLY READ THIS ENTIRE CONTEXT BEFORE PROCEEDING FROM FILE PATH PROVIDED"
    " ESPECIALLY IF TRUNCATED/PREVIEWED. DO IT NOW! THEN PROCEED.\n"
    "Rosetta get_context_instructions:\n"
)

CURSOR_MODEL_MAP: dict[str, str] = {
    "opus":                   "claude-opus-4-6",
    "sonnet":                 "claude-sonnet-4-6",
    "haiku":                  "claude-haiku-4-5",
    "gpt-5.5":                "gpt-5.5",
    "gpt-5.4":                "gpt-5.4",
    "gpt-5.3-codex":          "gpt-5.3-codex",
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "gemini-3.1-pro":         "gemini-3.1-pro",
    "gemini-3-flash":         "gemini-3-flash",
}

COPILOT_MODEL_MAP: dict[str, str] = {
    "opus":                   "Claude Opus 4.6",
    "sonnet":                 "Claude Sonnet 4.6",
    "haiku":                  "Claude Haiku 4.5",
    "gpt-5.5":                "GPT-5.5",
    "gpt-5.4":                "GPT-5.4",
    "gpt-5.3-codex":          "GPT-5.3-Codex",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro (Preview)",
    "gemini-3.1-pro":         "Gemini 3.1 Pro",
    "gemini-3-flash":         "Gemini 3 Flash",
}


@dataclass(frozen=True)
class StandaloneSpec:
    name: str
    source_plugin: str
    destination: Path
    subfolder: str
    excluded_source_folder: str
    pre_cleanup: tuple[str, ...] = ()
    post_cleanup: tuple[str, ...] = ()
    copilot_instructions: bool = False
    cursor_instructions: bool = False
    inject_index_folder: str | None = None
    inject_index_target: str | None = None


@dataclass(frozen=True)
class PluginSyncSpec:
    name: str
    destination: Path
    preserved_folder: str
    preserved_files: tuple[str, ...] = ()
    normalize_models: bool = False
    copilot_models: bool = False
    cursor_models: bool = False
    codex_models: bool = False
    rename_agents: bool = False
    rename_folders: tuple[tuple[str, str], ...] = ()
    rename_files: tuple[tuple[str, str], ...] = ()
    generated_indexes: tuple[str, ...] = ()
    templates: tuple[str, ...] = ()


def normalize_claude_model(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in ALLOWED_CLAUDE_MODELS:
        return lowered
    if "opus" in lowered:
        return "opus"
    if "sonnet" in lowered:
        return "sonnet"
    if "haiku" in lowered:
        return "haiku"
    return "inherit"


def _normalize_by_map(value: str, model_map: dict[str, str]) -> str:
    first = value.split(",")[0].strip().lower()
    for key, mapped in model_map.items():
        if key in first:
            return mapped
    return first


def normalize_copilot_model(value: str) -> str:
    return _normalize_by_map(value, COPILOT_MODEL_MAP)


def normalize_cursor_model(value: str) -> str:
    return _normalize_by_map(value, CURSOR_MODEL_MAP)


def normalize_codex_model(value: str) -> tuple[str | None, str | None]:
    for raw_candidate in value.split(","):
        candidate = raw_candidate.strip()
        if not candidate.startswith("gpt-"):
            continue

        base, separator, tail = candidate.rpartition("-")
        if separator and tail in {"low", "medium", "high", "minimal", "xhigh"} and base.startswith("gpt-"):
            effort = tail if tail in {"low", "medium", "high"} else None
            return base, effort

        return candidate, None

    return None, None


def rewrite_frontmatter_models(content: str, normalizer: Callable[[str], str] = normalize_claude_model) -> str:
    if not content.startswith("---\n"):
        return content

    end = content.find("\n---\n", 4)
    if end == -1:
        return content

    frontmatter = content[4:end]

    def replace_model(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        value = match.group("value")
        suffix = match.group("suffix")
        return f"{prefix}{normalizer(value)}{suffix}"

    updated = re.sub(
        r"(?m)^(?P<prefix>model:\s*)(?P<value>.*?)(?P<suffix>\s*)$",
        replace_model,
        frontmatter,
    )
    return f"---\n{updated}{content[end:]}"


def rewrite_codex_frontmatter_models(content: str) -> str:
    if not content.startswith("---\n"):
        return content

    end = content.find("\n---\n", 4)
    if end == -1:
        return content

    frontmatter = content[4:end]
    rewritten_lines: list[str] = []

    for line in frontmatter.splitlines():
        if line.startswith("model:"):
            model, effort = normalize_codex_model(line.split(":", 1)[1].strip())
            if model:
                rewritten_lines.append(f"model: {model}")
                if effort:
                    rewritten_lines.append(f"model_reasoning_effort: {effort}")
            continue

        if line.startswith("model_reasoning_effort:"):
            continue

        rewritten_lines.append(line)

    rewritten_frontmatter = "\n".join(rewritten_lines)
    return f"---\n{rewritten_frontmatter}{content[end:]}"


def reset_generated_tree(
    destination: Path,
    preserved_folder: str,
    preserved_files: tuple[str, ...] = (),
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    preserved = {preserved_folder, *preserved_files}
    deleted_count = 0
    for child in destination.iterdir():
        if child.name in preserved:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        deleted_count += 1

    print(
        f"      deleted {deleted_count} item(s) from {destination} preserving {', '.join(sorted(preserved))}",
        flush=True,
    )


def copy_core_tree(spec: PluginSyncSpec, core_source: Path) -> dict[str, str]:
    destination = spec.destination
    copied_count = 0
    renamed_count = 0

    if spec.codex_models:
        normalizer = None
    elif spec.copilot_models:
        normalizer = normalize_copilot_model
    elif spec.cursor_models:
        normalizer = normalize_cursor_model
    else:
        normalizer = normalize_claude_model

    should_normalize = spec.normalize_models or spec.copilot_models or spec.cursor_models or spec.codex_models
    folder_renames: dict[str, str] = dict(spec.rename_folders)

    # Build path_renames: maps source-relative path → final destination-relative path.
    # Covers both folder renames and regex file renames so content rewriting is precise.
    path_renames: dict[str, str] = {}
    if folder_renames or spec.rename_files:
        for src in sorted(core_source.rglob("*")):
            if src.is_dir():
                continue
            rel = src.relative_to(core_source)
            source_rel = "/".join(rel.parts)
            parts = list(rel.parts)
            if folder_renames:
                parts[0] = folder_renames.get(parts[0], parts[0])
            intermediate_rel = "/".join(parts)
            final_rel = (
                _apply_rename_files(intermediate_rel, spec.rename_files)
                if spec.rename_files else None
            ) or intermediate_rel
            if final_rel != source_rel:
                path_renames[source_rel] = final_rel
    # Add folder-level entries so bare "workflows/" references in instruction text are also updated
    for old_folder, new_folder in folder_renames.items():
        path_renames[f"{old_folder}/"] = f"{new_folder}/"

    for source_file in sorted(core_source.rglob("*")):
        if source_file.name == ".DS_Store":
            continue

        relative_path = source_file.relative_to(core_source)
        if folder_renames:
            parts = list(relative_path.parts)
            parts[0] = folder_renames.get(parts[0], parts[0])
            target = destination / Path(*parts)
        else:
            target = destination / relative_path

        if source_file.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        if str(relative_path) in EXCLUDED_RULE_FILES:
            continue

        # Rename agents/*.md → agents/*.agent.md for Copilot
        if spec.rename_agents and _is_agent_file(relative_path):
            target = target.with_suffix(".agent.md")
            renamed_count += 1

        # Rename files using regex patterns (e.g. rules/*.md → rules/*.mdc for Cursor)
        if spec.rename_files:
            dest_rel = "/".join(target.relative_to(destination).parts)
            new_rel = _apply_rename_files(dest_rel, spec.rename_files)
            if new_rel:
                target = destination / new_rel
                renamed_count += 1

        target.parent.mkdir(parents=True, exist_ok=True)

        if source_file.suffix == ".md" and (should_normalize or path_renames):
            source_content = source_file.read_text(encoding="utf-8")
            if should_normalize:
                if spec.codex_models:
                    rewritten = rewrite_codex_frontmatter_models(source_content)
                else:
                    rewritten = rewrite_frontmatter_models(source_content, normalizer=normalizer)
            else:
                rewritten = source_content
            for old, new in path_renames.items():
                rewritten = rewritten.replace(old, new)
            target.write_text(rewritten, encoding="utf-8")
            shutil.copystat(source_file, target, follow_symlinks=True)
            copied_count += 1
            continue

        shutil.copy2(source_file, target)
        copied_count += 1

    msg = f"      copied {copied_count} item(s) to {destination}"
    if renamed_count:
        msg += f" (renamed {renamed_count} file(s))"
    print(msg, flush=True)
    return path_renames


def _extract_frontmatter_field(content: str, field: str) -> str:
    """Extract a field value from YAML frontmatter."""
    if not content.startswith("---\n"):
        return ""
    end = content.find("\n---\n", 4)
    if end == -1:
        return ""
    frontmatter = content[4:end]
    match = re.search(rf"(?m)^{field}:\s*(.+)$", frontmatter)
    return match.group(1).strip() if match else ""


def _extract_frontmatter_and_body(content: str) -> tuple[str, str]:
    if not content.startswith("---\n"):
        return "", content

    end = content.find("\n---\n", 4)
    if end == -1:
        return "", content

    return content[4:end], content[end + len("\n---\n") :]


def strip_frontmatter(content: str) -> str:
    _, body = _extract_frontmatter_and_body(content)
    return body


def json_escape_for_additional_context(content: str) -> str:
    content = content.replace("\\", "\\\\")
    content = content.replace('"', '\\"')
    content = content.replace("\n", "\\n")
    content = content.replace("\r", "\\r")
    content = content.replace("\t", "\\t")
    return content


def _bash_single_quote_escape(content: str) -> str:
    """Escape single quotes for safe embedding inside a bash single-quoted string."""
    return content.replace("'", "'\\''")


def _ps_single_quote_escape(content: str) -> str:
    """Escape single quotes for safe embedding inside a PowerShell single-quoted string."""
    return content.replace("'", "''")


def _bash_lock(n: int) -> str:
    cleanup = (
        'find /tmp -maxdepth 1 -name "rosetta-bs-*.lock" -mmin +1 -delete 2>/dev/null; '
        if n == 0 else ""
    )
    return (
        f"{cleanup}"
        f"INPUT=$(cat); "
        f"SESSION_ID=$(printf '%s' \"$INPUT\" | sed -n 's/.*\"session_id\":\"\\([^\"]*\\)\".*/\\1/p'); "
        f'LOCK="/tmp/rosetta-bs-${{SESSION_ID:-$$}}-{n}.lock"; '
        f'if [ -f "$LOCK" ]; then exit 0; fi; touch "$LOCK"'
    )


def _ps_lock(n: int) -> str:
    cleanup = (
        'Get-ChildItem "$env:TEMP\\rosetta-bs-*-0.lock" -ErrorAction SilentlyContinue | '
        'Where-Object { $_.LastWriteTime -lt (Get-Date).AddMinutes(-1) } | '
        'Remove-Item -Force -ErrorAction SilentlyContinue; '
        if n == 0 else ""
    )
    return (
        f"{cleanup}"
        f"$Inp = [Console]::In.ReadToEnd(); "
        f'$Sid = if ($Inp -match \'"session_id":"([^"]*)"\') {{ $Matches[1] }} '
        f"else {{ [System.Diagnostics.Process]::GetCurrentProcess().Id }}; "
        f'$Lk = "$env:TEMP\\rosetta-bs-$Sid-{n}.lock"; '
        f"if (Test-Path $Lk) {{ exit 0 }}; "
        f"New-Item -Path $Lk -ItemType File -Force | Out-Null"
    )


_BOOTSTRAP_FILES: tuple[str, ...] = (
    "rules/plugin-files-mode.md",
    "rules/bootstrap-core-policy.md",
    "rules/bootstrap-execution-policy.md",
    "rules/bootstrap-guardrails.md",
    "rules/bootstrap-rosetta-files.md",
    "rules/INDEX.md",
    "workflows/INDEX.md",
)

_PLUGIN_PATH_HOOKS: dict[str, dict] = {
    "core-claude": {"type": "command", "command": 'printf \'%s\' "{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"SessionStart\\\",\\\"additionalContext\\\":\\\"Rosetta Plugin Path: ${CLAUDE_PLUGIN_ROOT}\\\"}}"', "once": True},
    "core-codex": {
        "type": "command",
        "command": (
            'workspace_root="$PWD"; '
            'while [ "$workspace_root" != "/" ] && '
            '[ ! -f "$workspace_root/.agents/rules/bootstrap-rosetta-files.md" ]; do '
            'workspace_root="$(dirname "$workspace_root")"; done; '
            'if [ -f "$workspace_root/.agents/rules/bootstrap-rosetta-files.md" ]; then '
            'printf \'%s\' "{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"SessionStart\\\",\\\"additionalContext\\\":\\\"Rosetta Plugin Path: $workspace_root/.agents\\\"}}"; fi'
        ),
        "statusMessage": "Loading Rosetta bootstrap",
        "timeout": 30,
    },
    "core-copilot": {
        "type": "command",
        "bash": (
            'for base in "$HOME/Library/Application Support/Code/agentPlugins" '
            '"$HOME/.local/share/Code/agentPlugins"; do '
            'root="$base/github.com/griddynamics/rosetta/plugins/core-copilot"; '
            'if [ -f "$root/rules/bootstrap-rosetta-files.md" ]; then '
            'printf \'%s\' "{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"SessionStart\\\",\\\"additionalContext\\\":\\\"Rosetta Plugin Path: $root\\\"}}"; '
            'break; fi; done'
        ),
        "powershell": (
            '$root = "$env:LOCALAPPDATA\\Code\\agentPlugins\\github.com\\griddynamics\\rosetta\\plugins\\core-copilot"; '
            'if (Test-Path "$root\\rules\\bootstrap-rosetta-files.md") '
            '{ Write-Output (\'{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Rosetta Plugin Path: \' + $root + \'"}}\') }'
        ),
    },
    "core-cursor": {"type": "command", "command": 'printf \'{"additional_context":"Rosetta Plugin Path: %s"}\' "${CURSOR_PROJECT_DIR}"'},
}

def build_bootstrap_replacements(dest_dir: Path) -> tuple[dict[str, str], int]:
    """Read bootstrap files once, build all platform-specific placeholder values.

    Returns (replacements dict, violation count).
    """
    violations = 0
    errors: list[str] = []
    claude_entries: list[dict] = []
    codex_entries: list[dict] = []
    cursor_entries: list[dict] = []
    copilot_entries: list[dict] = []

    for n, rel_file in enumerate(_BOOTSTRAP_FILES):
        src = dest_dir / rel_file
        if not src.is_file():
            print(f"WARNING: {src} not found, skipping", file=sys.stderr)
            continue

        content = src.read_text(encoding="utf-8")
        body = strip_frontmatter(content)
        text = (BOOTSTRAP_PREFIX + body) if n == 0 else body
        escaped = json_escape_for_additional_context(text)
        bash_escaped = _bash_single_quote_escape(escaped)
        ps_escaped = _ps_single_quote_escape(escaped)

        if len(escaped) > 10000:
            errors.append(f"ERROR: {rel_file} additionalContext is {len(escaped)} chars (max 10000)")
            violations += 1

        claude_entries.append({
            "type": "command",
            "command": f'printf \'%s\' \'{{"hookSpecificOutput":{{"hookEventName":"SessionStart","additionalContext":"{bash_escaped}"}}}}\'',
            "once": True,
        })
        codex_entries.append({
            "type": "command",
            "command": f'printf \'%s\' \'{{"hookSpecificOutput":{{"hookEventName":"SessionStart","additionalContext":"{bash_escaped}"}}}}\'',
            "statusMessage": "Loading Rosetta bootstrap",
            "timeout": 30,
        })
        cursor_entries.append({
            "type": "command",
            "command": f'printf \'%s\' \'{{"additional_context":"{bash_escaped}"}}\'',
        })
        copilot_entries.append({
            "type": "command",
            "bash": f'{_bash_lock(n)}; printf \'%s\' \'{{"hookSpecificOutput":{{"hookEventName":"SessionStart","additionalContext":"{bash_escaped}"}}}}\'',
            "powershell": f'{_ps_lock(n)}; Write-Output \'{{"hookSpecificOutput":{{"hookEventName":"SessionStart","additionalContext":"{ps_escaped}"}}}}\'',
        })

    for entries, name in (
        (claude_entries, "core-claude"),
        (codex_entries, "core-codex"),
        (copilot_entries, "core-copilot"),
        (cursor_entries, "core-cursor"),
    ):
        path_hook = _PLUGIN_PATH_HOOKS.get(name)
        if path_hook:
            entries.append(path_hook)

    def _inner(entries: list[dict]) -> str:
        return json.dumps(entries, ensure_ascii=False)[1:-1]

    replacements = {
        "{{BOOTSTRAP_HOOKS_CLAUDE}}": _inner(claude_entries),
        "{{BOOTSTRAP_HOOKS_CODEX}}": _inner(codex_entries),
        "{{BOOTSTRAP_HOOKS_CURSOR}}": _inner(cursor_entries),
        "{{BOOTSTRAP_HOOKS_COPILOT}}": _inner(copilot_entries),
    }

    for err in errors:
        print(err, file=sys.stderr)

    print(f"      built {len(replacements)} template replacements from {len(_BOOTSTRAP_FILES)} bootstrap files", flush=True)
    return replacements, violations


def process_templates(
    dest_dir: Path,
    templates: tuple[str, ...],
    replacements: dict[str, str],
) -> None:
    """Replace all known placeholders in .tmpl files, write output (path minus .tmpl suffix)."""
    for tmpl_rel in templates:
        tmpl_path = dest_dir / tmpl_rel
        if not tmpl_path.is_file():
            print(f"WARNING: {tmpl_path} not found, skipping", file=sys.stderr)
            continue

        text = tmpl_path.read_text(encoding="utf-8")
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)

        output_path = tmpl_path.with_suffix("")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        print(f"      processed {tmpl_rel}", flush=True)


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_multiline(value: str) -> str:
    escaped = value.replace('"""', '\\"\\"\\"')
    return f'"""\n{escaped}\n"""'


def generate_folder_index(destination: Path, folder_name: str, required_tag: str | None = None) -> None:
    """Generate <folder>/INDEX.md listing markdown files with descriptions."""
    target_dir = destination / folder_name
    if not target_dir.is_dir():
        return

    entries: list[tuple[str, str]] = []
    for item in sorted(target_dir.iterdir()):
        if item.name == "INDEX.md" or item.suffix not in (".md", ".mdc"):
            continue
        content = item.read_text(encoding="utf-8")
        if required_tag is not None:
            raw_tags = _extract_frontmatter_field(content, "tags")
            if required_tag not in raw_tags:
                continue
        description = _extract_frontmatter_field(content, "description")
        if not description:
            description = item.stem.replace("-", " ").title()
        entries.append((item.name, description))

    if not entries:
        return

    _FOLDER_TITLE_ALIASES: dict[str, str] = {"commands": "Workflows", "prompts": "Workflows"}
    display_name = _FOLDER_TITLE_ALIASES.get(folder_name, folder_name.title())
    lines = [
        f"# Rosetta {display_name} Index",
        "",
        "All paths are relative to Rosetta Plugin Path.",
        "",
    ]
    for filename, description in entries:
        lines.append(f"- `{folder_name}/{filename}`: {description}")
    lines.append("")

    index_path = target_dir / "INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"      generated {folder_name}/INDEX.md with {len(entries)} entries", flush=True)


def _replace_tree(source: Path, target: Path) -> None:
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def generate_codex_subagents(destination: Path, core_source: Path) -> None:
    subagents_dir = destination / ".codex" / "agents"
    subagents_dir.mkdir(parents=True, exist_ok=True)

    generated_count = 0
    for source_file in sorted((core_source / "agents").glob("*.md")):
        content = source_file.read_text(encoding="utf-8")
        frontmatter, body = _extract_frontmatter_and_body(content)
        if not frontmatter:
            continue

        name = _extract_frontmatter_field(content, "name")
        description = _extract_frontmatter_field(content, "description")
        readonly = _extract_frontmatter_field(content, "readonly").lower() == "true"
        raw_model = _extract_frontmatter_field(content, "model")
        model, effort = normalize_codex_model(raw_model)

        toml_lines = [
            f"name = {_toml_quote(name or source_file.stem)}",
            f"description = {_toml_quote(description or source_file.stem.replace('-', ' ').title())}",
            f"developer_instructions = {_toml_multiline(body.strip())}",
        ]

        if model:
            toml_lines.append(f"model = {_toml_quote(model)}")
        if effort:
            toml_lines.append(f"model_reasoning_effort = {_toml_quote(effort)}")

        toml_lines.append(
            'sandbox_mode = "read-only"' if readonly else 'sandbox_mode = "workspace-write"'
        )

        target = subagents_dir / f"{source_file.stem}.toml"
        target.write_text("\n".join(toml_lines) + "\n", encoding="utf-8")
        generated_count += 1

    legacy_agents_dir = destination / "agents"
    if legacy_agents_dir.is_dir():
        shutil.rmtree(legacy_agents_dir)

    print(f"      generated .codex/agents with {generated_count} subagent(s)", flush=True)


def generate_copilot_runtime_layout(destination: Path) -> None:
    plugin_dir = destination / ".github" / "plugin"
    copied = 0
    for filename in ("hooks.json", ".mcp.json"):
        source = plugin_dir / filename
        if source.is_file():
            shutil.copy2(source, destination / filename)
            copied += 1
    print(f"      copied {copied} config(s) from .github/plugin/ to plugin root", flush=True)


def generate_codex_runtime_layout(destination: Path) -> None:
    source_hooks = destination / ".codex-plugin" / "hooks.json"
    codex_hooks = destination / ".codex" / "hooks.json"
    if source_hooks.is_file():
        _replace_tree(source_hooks, codex_hooks)
        print("      copied .codex/hooks.json for core-codex", flush=True)

    reserved_dirs = {".agents", ".codex", ".codex-plugin"}
    for child in sorted(destination.iterdir()):
        if not child.is_dir() or child.name in reserved_dirs:
            continue

        target_dir = destination / ".agents" / child.name
        _replace_tree(child, target_dir)
        shutil.rmtree(child)
        print(f"      moved {child.name} to .agents/{child.name} for core-codex", flush=True)

    agents_path = destination / "agents"
    if agents_path.exists():
        if agents_path.is_dir():
            shutil.rmtree(agents_path)
        else:
            agents_path.unlink()


def _is_agent_file(relative_path: Path) -> bool:
    """Check if a relative path is an agent markdown file (agents/<name>.md)."""
    parts = relative_path.parts
    return (
        len(parts) == 2
        and parts[0] == "agents"
        and relative_path.suffix == ".md"
    )


def _apply_rename_files(dest_rel: str, rename_files: tuple[tuple[str, str], ...]) -> str | None:
    for pattern, replacement in rename_files:
        if re.fullmatch(pattern, dest_rel):
            folder = dest_rel.rsplit("/", 1)[0] if "/" in dest_rel else ""
            new_filename = re.sub(pattern, replacement, dest_rel)
            return f"{folder}/{new_filename}" if folder else new_filename
    return None


def _inject_index_content(subfolder: Path, index_folder: str, target_rel: str) -> None:
    index_content = (subfolder / index_folder / "INDEX.md").read_text(encoding="utf-8")
    target = subfolder / target_rel
    content = target.read_text(encoding="utf-8")
    closing_tag = "</plugin_files_mode>"
    content = content.replace(closing_tag, f"\n{index_content.strip()}\n\n{closing_tag}")
    target.write_text(content, encoding="utf-8")
    print(f"      injected {index_folder}/INDEX.md into {target_rel}", flush=True)


def _generate_cursor_instructions(subfolder: Path) -> None:
    target = subfolder / "rules" / "plugin-files-mode.mdc"
    content = target.read_text(encoding="utf-8")
    insert_text = (
        'Rosetta plugin root: ".cursor". You MUST FOLLOW ALL bootstrap-* instructions and execute every prep step in order. '
        'After prep steps, you MUST select a workflow and execute it. All workflows (commands) are stored in '
        '".cursor/commands/<workflowtag>.md". Example ".cursor/commands/coding-flow.md".'
    )
    closing_tag = "</plugin_files_mode>"
    content = content.replace(closing_tag, f"{insert_text}\n{closing_tag}")
    target.write_text(content, encoding="utf-8")
    print("      injected cursor instructions into rules/plugin-files-mode.mdc", flush=True)


def _generate_copilot_instructions(subfolder: Path) -> None:
    source_file = subfolder / "rules" / "plugin-files-mode.md"
    content = source_file.read_text(encoding="utf-8")
    body = strip_frontmatter(content)
    insert_text = (
        'Rosetta plugin root: ".github", get_context_instructions: must read fully all five '
        '"cat .github/rules/bootstrap-*.md" files all lines. READ THE ENTIRE OUTPUT ALL ~700 LINES. Do not stop until fully read. '
        'Bootstrap contains very important content in the beginning, middle, and in the end. You MUST FOLLOW ALL instructions '
        'and then MUST select workflow and execute it. All workflows (prompts) are stored in '
        '".github/prompts/<workflowtag>.prompt.md". Example ".github/prompts/coding-flow.prompt.md".'
    )
    closing_tag = "</plugin_files_mode>"
    body = body.replace(closing_tag, f"{insert_text}\n{closing_tag}")
    (subfolder / "copilot-instructions.md").write_text(body, encoding="utf-8")
    print("      generated copilot-instructions.md", flush=True)


def _generate_standalone_plugin_json(source: Path, spec: StandaloneSpec) -> None:
    plugin_json_path = next(source.rglob("plugin.json"), None)
    version = "0.0.0"
    if plugin_json_path:
        version = json.loads(plugin_json_path.read_text(encoding="utf-8")).get("version", version)
    data = {"name": spec.name, "version": version}
    (spec.destination / "plugin.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"      generated plugin.json (version: {version})", flush=True)


def generate_standalone_plugin(spec: StandaloneSpec, plugins_root: Path) -> None:
    source = plugins_root / spec.source_plugin
    if spec.destination.exists():
        shutil.rmtree(spec.destination)
    spec.destination.mkdir(parents=True)

    subfolder_path = spec.destination / spec.subfolder
    subfolder_path.mkdir(parents=True)

    copied = 0
    for item in sorted(source.iterdir()):
        if item.name == spec.excluded_source_folder:
            continue
        target = subfolder_path / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
        copied += 1

    for rel in spec.pre_cleanup:
        path = subfolder_path / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()

    if spec.copilot_instructions:
        _generate_copilot_instructions(subfolder_path)

    if spec.cursor_instructions:
        _generate_cursor_instructions(subfolder_path)

    if spec.inject_index_folder and spec.inject_index_target:
        _inject_index_content(subfolder_path, spec.inject_index_folder, spec.inject_index_target)

    for rel in spec.post_cleanup:
        path = subfolder_path / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()

    _generate_standalone_plugin_json(source, spec)
    print(f"      copied {copied} item(s) into {spec.subfolder}/", flush=True)


def sync_generated_plugins(repo_root: Path) -> int:
    core_source = repo_root / "instructions" / "r2" / "core"
    if not core_source.is_dir():
        print(f"ERROR: Core source folder not found: {core_source}", file=sys.stderr)
        return 1

    plugin_specs = [
        PluginSyncSpec(
            name="core-claude",
            destination=repo_root / "plugins" / "core-claude",
            preserved_folder=".claude-plugin",
            preserved_files=("hooks",),
            normalize_models=True,
            generated_indexes=("rules", "workflows"),
            templates=("hooks/hooks.json.tmpl",),
        ),
        PluginSyncSpec(
            name="core-cursor",
            destination=repo_root / "plugins" / "core-cursor",
            preserved_folder=".cursor-plugin",
            preserved_files=("hooks",),
            cursor_models=True,
            rename_folders=(("workflows", "commands"),),
            rename_files=((r"rules/(.+)\.md", r"\1.mdc"),),
            generated_indexes=("rules", "commands"),
            templates=("hooks/hooks.json.tmpl",),
        ),
        PluginSyncSpec(
            name="core-copilot",
            destination=repo_root / "plugins" / "core-copilot",
            preserved_folder=".github",
            copilot_models=True,
            rename_agents=True,
            rename_folders=(("workflows", "prompts"),),
            rename_files=((r"prompts/(.+)\.md", r"\1.prompt.md"),),
            generated_indexes=("rules", "prompts"),
            templates=(".github/plugin/hooks.json.tmpl",),
        ),
        PluginSyncSpec(
            name="core-codex",
            destination=repo_root / "plugins" / "core-codex",
            preserved_folder=".codex-plugin",
            codex_models=True,
            generated_indexes=("rules", "workflows"),
            templates=(".codex-plugin/hooks.json.tmpl",),
        ),
    ]

    replacements: dict[str, str] | None = None
    total_violations = 0
    for spec in plugin_specs:
        print(f"   syncing {spec.name}", flush=True)
        reset_generated_tree(spec.destination, spec.preserved_folder, spec.preserved_files)
        path_renames = copy_core_tree(spec, core_source)
        for folder_name in spec.generated_indexes:
            tag = "workflow" if folder_name in ("workflows", "commands", "prompts") else None
            generate_folder_index(spec.destination, folder_name, required_tag=tag)
        if replacements is None:
            replacements, total_violations = build_bootstrap_replacements(spec.destination)
        if spec.templates:
            plugin_replacements = replacements
            if path_renames:
                plugin_replacements = {}
                for k, v in replacements.items():
                    for old, new in path_renames.items():
                        v = v.replace(old, new)
                    plugin_replacements[k] = v
            process_templates(spec.destination, spec.templates, plugin_replacements)
        if spec.name == "core-copilot":
            generate_copilot_runtime_layout(spec.destination)
        if spec.name == "core-codex":
            generate_codex_subagents(spec.destination, core_source)
            generate_codex_runtime_layout(spec.destination)

    standalone_specs = [
        StandaloneSpec(
            name="core-cursor-standalone",
            source_plugin="core-cursor",
            destination=repo_root / "plugins" / "core-cursor-standalone",
            subfolder=".cursor",
            excluded_source_folder=".cursor-plugin",
            cursor_instructions=True,
            inject_index_folder="commands",
            inject_index_target="rules/plugin-files-mode.mdc",
        ),
        StandaloneSpec(
            name="core-copilot-standalone",
            source_plugin="core-copilot",
            destination=repo_root / "plugins" / "core-copilot-standalone",
            subfolder=".github",
            excluded_source_folder=".github",
            pre_cleanup=(".mcp.json", "hooks.json", "templates"),
            post_cleanup=("rules/plugin-files-mode.md",),
            copilot_instructions=True,
            inject_index_folder="prompts",
            inject_index_target="copilot-instructions.md",
        ),
    ]

    for spec in standalone_specs:
        print(f"   generating {spec.name}", flush=True)
        generate_standalone_plugin(spec, repo_root / "plugins")

    return 1 if total_violations else 0
