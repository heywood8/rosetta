---
layout: docs
title: Plugins
permalink: /docs/plugins/
---

# Plugins

> [!CAUTION]
> You must receive a prior approval from your manager and company to use it.

> [!WARNING]
> Use **Sonnet 4.6**, **GPT-5.3-codex-medium**, **gemini-3.1-pro** or better models. Avoid Auto model selection.

> [!NOTE]
> This is pre-release, but it already works.

## Claude Code Full Plugin Installation

```sh
claude plugin marketplace add griddynamics/rosetta
claude plugin install rosetta@rosetta
```

## Cursor Standalone

1. Download `core-cursor-standalone-*.zip` from the [latest release](https://github.com/griddynamics/rosetta/releases/latest)
2. Extract the archive contents directly into the repository.
3. Verify you can see a file `.cursor/agents/architect.md`. Ensure there are no `.cursor/.cursor` folders.

## Cursor Team Marketplace

If you have respective edition of Cursor you can add it as plugin to your corporate marketplace. See https://cursor.com/docs/plugins#team-marketplaces

You can also install plugin to claude code and it will appear in Cursor :)

`https://github.com/griddynamics/rosetta` provides marketplace and plugin for Cursor.

> [!WARNING]
> Cursor sees and uses all claude code plugins, so you should not install plugins to claude code and cursor, just install to claude code. Otherwise everything will be duplicated in Cursor context!

## VS Code GitHub Copilot

Add marketplace to `chat.plugins.marketplaces` in settings using local files path: `https://github.com/griddynamics/rosetta`.

Go to agent customizations screen (settings gear icon in Copilot chat pane), click `Browse Marketplaces`, click `install` for `rosetta`.

<img src="/rosetta/assets/images/vscode-add-marketplaces.png" alt="Add marketplaces to VS Code" width="710"/>

<img src="/rosetta/assets/images/vscode-open-customizations.png" alt="Open agent customizations" width="710"/>

<img src="/rosetta/assets/images/vscode-install-plugins.png" alt="Install plugins" width="710"/>

## GitHub Copilot Standalone (JetBrains and VS Code)

1. Download `core-copilot-standalone-*.zip` from the [latest release](https://github.com/griddynamics/rosetta/releases/latest)
2. Extract the archive contents directly into the repository. If `.github/copilot-instructions.md` already exists, merge contents: first from Rosetta, then the original content.
3. Verify you can see a file `.github/agents/architect.agent.md`. Ensure there are no `.github/.github` folders.

## Codex Plugins (standalone only)

Codex plugins only allow hooks, MCPs, and skills as of now (Apr 2026).

Download `core-codex-*.zip` from the [latest release](https://github.com/griddynamics/rosetta/releases/latest), extract on top of the repository, and enable hooks:

```sh
codex features enable hooks
```
