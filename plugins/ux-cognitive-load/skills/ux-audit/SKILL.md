---
name: ux-audit
description: >
  Cognitive load audit of UI code. Use this skill when the user wants to audit,
  review, or analyze UI components for cognitive load, usability, or UX quality.
  Triggers on: "ux audit", "cognitive load audit", "audit my form", "review this
  UI for usability", "check cognitive load", "is this form too complex",
  "analyze UX of these components", or any request to evaluate UI code against
  cognitive load principles, usability heuristics, or form design best practices.
  Also triggers when the user provides UI file paths and asks about complexity,
  overwhelm, or user confusion.
---

# UX Cognitive Load Audit

Analyzes UI code for cognitive load issues using three parallel specialist agents, then synthesizes findings into a unified report.

ARGUMENTS: file paths, glob patterns, or directory paths to audit

## Phase 0 — Identify Target Files

Check if the user provided file paths or glob patterns as arguments.

- If args contain file paths or globs: use Glob to resolve them into a concrete file list. Verify each file exists and is a UI-related file (HTML, CSS, JSX, TSX, Vue, Svelte, template files, stylesheets, etc.). Silently skip non-UI files.
- If no args provided: use the `AskUserQuestion` tool to ask the user which files or directories to audit. Suggest they provide paths like `src/components/**` or specific files.

Store the resolved file list for the agents. If zero UI files resolve, tell the user no auditable files were found and stop.

## Phase 1 — Reconnaissance

Before spawning agents, do a quick scan yourself:

1. Use Read to open 2-3 of the target files to understand what framework/approach is used (plain HTML, React, Vue, Svelte, Web Components, etc.) and the general structure.
2. Use Glob to check for related files the user might have missed (stylesheets imported by the components, layout wrappers, shared form components in the same directory).
3. Build a brief context summary covering:
   - What files are being audited
   - What they appear to do (e.g., "checkout form with 3 steps", "settings page with tabbed sections")
   - Any framework observations (e.g., "React components using JSX", "plain HTML with Tailwind classes")
   - Any shared patterns observed (e.g., "all forms use a shared FormField component")

This context summary gets passed to each agent so they don't waste tokens re-discovering basic facts.

## Phase 2 — Parallel Agent Analysis

Spawn all three agents in a **single message** using three Agent tool calls so they run concurrently.

### Agent 1: UX Auditor

Use the Agent tool with `subagent_type: "UX Auditor"`. Pass this prompt:

> **Context:** {context summary from Phase 1}
>
> **Files to audit:** {file list with full paths}
>
> Perform a cognitive load audit of these UI files. Read each file and evaluate against your cognitive load framework. Return your findings in this exact format:
>
> ## Cognitive Load Analysis
> ### Issues
> | # | Severity | Issue | Location | Recommendation |
> |---|----------|-------|----------|----------------|
> | 1 | critical/warning/info | description | file:line | how to fix |
>
> ### Completeness: X/10
> (How thoroughly you were able to evaluate the code — 10 means you covered every principle, lower means some were not applicable or not assessable from code alone)

### Agent 2: Design Advisor

Use the Agent tool with `subagent_type: "Design Advisor"`. Pass this prompt:

> **Context:** {context summary from Phase 1}
>
> **Files to audit:** {file list with full paths}
>
> Evaluate these UI files for design pattern quality. Read each file and assess against your design principles framework. Return your findings in this exact format:
>
> ## Design Patterns Analysis
> ### Issues
> | # | Severity | Issue | Location | Recommendation |
> |---|----------|-------|----------|----------------|
> | 1 | critical/warning/info | description | file:line | how to fix |
>
> ### Completeness: X/10

### Agent 3: Code Reviewer

Use the Agent tool with `subagent_type: "Code Reviewer"`. Pass this prompt:

> **Context:** {context summary from Phase 1}
>
> **Files to audit:** {file list with full paths}
>
> Analyze these UI files for code-level anti-patterns affecting cognitive usability. Read each file and check against your code review checklist. Return your findings in this exact format:
>
> ## Code Review
> ### Issues
> | # | Severity | Issue | Location | Recommendation |
> |---|----------|-------|----------|----------------|
> | 1 | critical/warning/info | description | file:line | how to fix |
>
> ### Completeness: X/10

## Phase 3 — Synthesis

Once all three agents return, synthesize their reports into the final audit:

1. **Count issues** by severity across all three reports. Tally critical, warning, and info counts.
2. **Calculate overall score**: Start at 10, subtract 2 per critical issue, subtract 0.5 per warning. Floor at 0. Round to 1 decimal place.
3. **Deduplicate**: If two agents flagged the same issue (same file, same location, same core problem), merge them into one entry and keep the more detailed recommendation. Note which agents both caught it.
4. **Rank priority actions**: Pick the top 5 issues by impact. Critical severity first, then warnings that affect the most users or appear across multiple files. For each, write a 1-2 sentence action item explaining what to fix and why it matters.

### Output Format

```markdown
# UX Cognitive Load Audit Report

## Summary
- **Overall Score:** X/10
- **Critical Issues:** N
- **Warnings:** N
- **Info:** N
- **Files Audited:** file1, file2, ...

## Cognitive Load Analysis
{UX Auditor agent output — full issues table}
### Completeness: X/10

## Design Patterns Analysis
{Design Advisor agent output — full issues table}
### Completeness: X/10

## Code Review
{Code Reviewer agent output — full issues table}
### Completeness: X/10

## Priority Action Items
1. **[file:location]** — What to fix and why it matters most
2. ...
3. ...
4. ...
5. ...
```

Present the full report inline. Do not save to a file unless the user explicitly asks.
