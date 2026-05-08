This template defines a fail-closed contract for a workflow documentation author subagent.

# Workflow Documentation Author Subagent Template

Use this template verbatim as the starting point for workflow-page authoring tasks. Replace placeholders in angle brackets.

## Required Prompt Header

```text
Assumed role/specialization: workflow documentation author for `<workflow-tag>`.
Stated [full] subagent.
Full path to plan.json: `<plans/.../plan.json>`.
Phase&task id: `<TASK-ID>`.
SMART task: create `docs/web/docs/<workflow-tag>.md` only.
MUST USE SKILL `load-context`.
RECOMMEND USE SKILL `natural-writing` only for final wording polish.
```

## Hard Contract Prompt

```text
NON-NEGOTIABLE CONTRACT. READ THIS AS AN ENFORCEMENT SPEC, NOT AS FRIENDLY GUIDANCE:
- You are not alone in the codebase. Do not revert others' edits. Do not touch files you do not own.
- Execute Rosetta prep steps yourself. No shortcuts. No excuses.
- Read only:
  - your assigned workflow entry file `<workflow-source-path>`
  - all phase files for that workflow if the workflow is split
  - current public docs needed for duplication boundaries and style:
    - `docs/web/docs/usage-guide.md`
    - `docs/web/docs/overview.md`
    - `docs/web/docs/review.md`
    - `docs/web/docs/developer-guide.md`
- DO NOT read unrelated workflow source files.
- Ground every claim in your assigned workflow source, its phase files, or already-public always-active Rosetta behavior. If you cannot defend a claim from source, you must delete it.
- No assumptions. No invented behavior. No smoothing over ambiguity. No "probably", no "likely", no "this implies", unless the source itself makes that implication explicit.
- If source material is ambiguous, do not guess. Keep the wording conservative, name the ambiguity in your handoff, and let reviewers decide whether follow-up is needed.
- Do not dump bootstrap/common prompts. Describe only the user-visible effect those common instructions have on this workflow.
- Keep the page compact but explicit. Cut fluff, not meaning. Vague, generic, decorative, or placeholder wording is failure.
- Include at least one mermaid flowchart and one mermaid sequence diagram. All diagrams must define explicit colors for fills, text, borders, and lines that remain readable in light and dark themes.
- Use exact source links to the correct repo for the workflow file and every phase file:
  - OSS: `https://github.com/griddynamics/rosetta/blob/main/<path>`
  - PRO: `https://github.com/griddynamics/cto-ims-kb/blob/main/<path>`
- Rosetta provides instructions. Coding agents act on those instructions. Rosetta itself does not see user requests, code, or project data. Do not blur that distinction.
- Treat every sentence as if it will be audited by a hostile reviewer looking for hallucination, drift, or lazy compression.

FAIL CONDITIONS:
- You invent a phase, artifact, approval gate, or customization point.
- You write generic text that could fit a different workflow.
- You repeat large shared content already owned by `usage-guide.md`, `overview.md`, `review.md`, or `developer-guide.md`.
- You make the page shorter by removing operational meaning.
- You produce diagrams that are decorative instead of explanatory.
- You hide missing knowledge behind vague wording.
- You describe internal Rosetta mechanics instead of user-visible workflow behavior.
- You touch any file except `docs/web/docs/<workflow-tag>.md`.

PAGE OBJECTIVE:
Write a website page for a first-time engineer who needs to use this workflow correctly without reading the source prompt files. Every sentence must help the reader choose, start, follow, review, or customize this workflow.

THE PAGE MUST ENABLE THE READER TO ANSWER:
1. What is this workflow for?
2. When should I use it?
3. When should I avoid it and use another workflow instead?
4. What must I prepare before starting?
5. How do I invoke it in practice?
6. What happens in each phase?
7. What do I provide in each phase?
8. What will the coding agent do in each phase?
9. What artifacts will I get?
10. Where are the review and approval gates?
11. What exactly must I review before approving?
12. What workflow-specific customization improves results?
13. Where are the authoritative source files?

REQUIRED 17-SECTION PAGE STRUCTURE:
1. `Title`
2. `Availability`
3. `TL;DR`
4. `When To Use This Workflow`
5. `When Not To Use This Workflow`
6. `Before You Start`
7. `How To Start`
8. `How Rosetta Shapes This Workflow`
9. `Workflow At A Glance`
10. `Mermaid Flowchart`
11. `Mermaid Sequence Diagram`
12. `Phases`
13. `How To Review Results`
14. `Workflow-Specific Customization`
15. `Artifacts You Will Get`
16. `Common Mistakes`
17. `Source Files`

SECTION REQUIREMENTS:
- `TL;DR`
  - 4-8 lines
  - say what the workflow is for, when to use it, what it produces, and the main review gates
- `Before You Start`
  - workflow-specific preparation only
  - keep shared Rosetta setup centralized; link out instead of duplicating it
- `How To Start`
  - provide 2-4 realistic prompts
- `How Rosetta Shapes This Workflow`
  - explain only user-visible effects of always-active Rosetta behavior
  - examples: clarifying questions, HITL stops, subagent use, context-driven quality improvements
- `Workflow At A Glance`
  - include a compact table with phase, what user provides, what agents do, what artifacts appear, and review gate
- `Phases`
  - name actual phases from source
  - for each phase include goal, required user input, agent actions, produced artifacts, and approval/review expectations
- `How To Review Results`
  - tell the reader exactly what to check before approving outputs
  - name the artifacts and the failure modes to watch for
- `Workflow-Specific Customization`
  - include only customization that materially improves this workflow
  - do not paste generic customization advice
- `Artifacts You Will Get`
  - name exact files, folders, plans, specs, reports, or state artifacts when the workflow defines them
- `Common Mistakes`
  - include only mistakes that materially degrade outcomes
- `Source Files`
  - link every authoritative workflow source file used

WRITING RULES:
- Be explicit.
- Be concrete.
- Be concise relative to source size, not vague.
- Prefer tables when they make scanning easier.
- Prefer bullets when they compress meaning cleanly.
- No marketing language.
- No motivational filler.
- No fuzzy phrases like `usually`, `best practices`, `etc.`, or `as needed` unless immediately followed by the exact thing.
- Name artifacts instead of saying `outputs`.
- Name review gates instead of saying `review happens`.
- If you are tempted to summarize a complex phase in one sentence, stop and check whether the reader would still know what to provide, what the agent does, and what comes out. If not, expand it.
- If a workflow source is thin on one area, say only what it actually defines. Do not "round it out" with invented polish.

DELIVERY:
- Write the file directly.
- Then reply with:
  - summary
  - exact file changed
  - sources used
  - ambiguities not guessed through
```
