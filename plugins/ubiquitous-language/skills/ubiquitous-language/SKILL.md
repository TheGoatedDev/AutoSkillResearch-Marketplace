---
name: ubiquitous-language
description: >
  Use when user wants to define domain terms, build a glossary, harden terminology,
  create a ubiquitous language, audit codebase terminology, or mentions "domain model"
  or "DDD". Also triggers on "audit" with terminology context.
---

# Ubiquitous Language

Extract and formalize domain terminology from the current conversation and codebase into a
consistent, DDD-style glossary. Saves to `ubiquitous_language.md` at the project root.

## Modes

This skill has two modes:

- **Default** (no args): Build or update the glossary from conversation + targeted codebase grep
- **Audit** (`/ubiquitous-language audit`): Read existing glossary, walk the full codebase for violations

## Default Mode

1. **Scan the conversation** for domain-relevant nouns, verbs, and concepts. Skip generic
   programming terms (array, function, endpoint) unless they have domain-specific meaning.
2. **Identify problems:**
   - Same word used for different concepts (ambiguity)
   - Different words used for the same concept (synonyms)
   - Vague or overloaded terms
   - Same term meaning different things in different bounded contexts
3. **Grep the codebase** for each identified term and its aliases. Check variable names, class
   names, function names, comments, and documentation. Note where domain language is already in
   use, misused, or inconsistent.
4. **Propose a canonical glossary** with opinionated term choices, bounded context assignments,
   rationale for each choice, and aliases to avoid.
5. **Check for existing `ubiquitous_language.md`** at the project root. If it exists, merge new
   terms and update definitions. Never silently drop existing terms. If a term previously marked
   "Global" now has context-specific meanings, split it into separate rows.
6. **Write or update `ubiquitous_language.md`** at the project root using the output format below.
7. **Output a summary inline** — new terms added, ambiguities flagged, deprecated terms found in code.

## Audit Mode

1. **Read existing `ubiquitous_language.md`.** If it does not exist, tell the user to run the
   default mode first and stop.
2. **Build a search list** from the glossary — all canonical terms, all aliases-to-avoid, and all
   deprecated terms.
3. **Walk the codebase** — grep for every alias-to-avoid and deprecated term across source files,
   comments, documentation, and config files.
4. **Report inline** with:
   - Deprecated terms still found in code (term, recommended replacement, file count)
   - Aliases-to-avoid found in code (which canonical term to use instead, file count)
   - Glossary terms not found anywhere in the codebase (potentially unused or misnamed)
5. **Do not modify `ubiquitous_language.md`.** Audit is read-only and report-only. The user
   decides what to act on.

## Output Format

Write `ubiquitous_language.md` with this structure:

```md
# Ubiquitous Language

## {Group Name}

| Term | Context | Definition | Rationale | Aliases to avoid |
| --- | --- | --- | --- | --- |
| **{Term}** | {Context} | {One sentence definition} | {Why this term was chosen} | {Comma-separated list} |

## Relationships

- A **{Term}** ({Context}) {relationship verb} one or more **{Term}**
- A **{Term}** ({Context}) belongs to exactly one **{Term}**

## Example Dialogue

> **Dev:** "{Question using precise domain terms}"
> **Domain expert:** "{Answer clarifying boundaries between terms}"

## Flagged Ambiguities

- "{word}" was used to mean both **{Term A}** and **{Term B}** — {explanation of distinction and recommendation}

## Deprecated Terms

- `{old_term}` → use **{Canonical Term}** — {reason for deprecation}
```

### Column Definitions

- **Term**: Bold canonical name for the domain concept.
- **Context**: The bounded context where this definition applies. Use "Global" when the term means the same thing everywhere.
- **Definition**: One sentence max. Define what it IS, not what it does.
- **Rationale**: Why this canonical term was chosen over alternatives. Especially important for contentious or non-obvious choices.
- **Aliases to avoid**: Synonyms or conflicting terms that should not be used for this concept in this context.

### Section Rules

- **Glossary tables**: Group by natural clusters — subdomain, lifecycle, actor type. Each group gets its own H2 heading and table. If all terms belong to one cohesive domain, one table is fine. Do not force artificial groupings.
- **Relationships**: Use bold term names with cardinality. Include bounded context in parentheses when a term has context-specific definitions.
- **Example dialogue**: 3-5 exchanges between a dev and domain expert. Show terms interacting naturally, clarify boundaries between related concepts, demonstrate precise usage.
- **Flagged ambiguities**: Terms used inconsistently in conversation, with clear recommendation.
- **Deprecated terms**: Terms actively in use that should be migrated. Format: `` `old_term` → use **Canonical Term** — reason ``.

## Rules

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others as aliases to avoid.
- **Flag conflicts explicitly.** If a term is used ambiguously, call it out in "Flagged ambiguities" with a clear recommendation.
- **Only domain terms.** Skip module or class names unless they have meaning in the domain language.
- **Tight definitions.** One sentence max. What it IS, not what it does.
- **Assign bounded context.** Use "Global" when a term means the same thing everywhere. When the same word means different things in different parts of the system, create separate rows with different Context values.
- **Document rationale.** Especially for contentious or non-obvious term choices. This prevents future debates.
- **Populate deprecated terms** when codebase grep reveals aliases-to-avoid or old terminology actively in use.
- **Group naturally.** Multiple tables when clusters emerge, one table when they don't.
- **Write example dialogue.** 3-5 exchanges showing terms used precisely in context.

## Re-running

When invoked again in default mode:

1. Read the existing `ubiquitous_language.md`
2. Incorporate new terms from the conversation
3. Update definitions if understanding has evolved — never silently drop existing terms
4. Merge bounded contexts — split "Global" terms into context-specific rows when needed
5. Re-flag ambiguities — update or resolve previous flags
6. Rewrite example dialogue to incorporate new terms
7. Update deprecated terms if new aliases-to-avoid are found in the codebase
