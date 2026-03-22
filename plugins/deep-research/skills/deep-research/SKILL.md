---
name: deep-research
description: >-
  Multi-phase deep research pipeline that discovers, validates, and synthesizes
  information from many sources into a comprehensive report. Uses parallel
  Researcher subagents for maximum coverage and depth.

  Use this skill whenever the user says "deep research" followed by a topic,
  when they explicitly invoke it, or when you determine that a question requires
  thorough, multi-source investigation rather than a quick lookup. This is
  different from a simple documentation search or a single web query — use this
  when the user needs a comprehensive understanding of a topic drawn from many
  sources, cross-validated and synthesized into a structured report.

  Triggers include: "deep research on X", "research X thoroughly", "I need a
  full report on X", "dive deep into X", "investigate X comprehensively", or
  any context where surface-level answers won't cut it and the user (or you)
  needs authoritative, multi-source coverage of a topic.
---

# Deep Research

A four-phase research pipeline that goes wide first (discover everything), filters for quality (validate and rank sources), goes deep second (parallel agents extract detail from the best sources), and then synthesizes everything into a single structured report.

## Phase 0 — Output Preference

Before doing any research, ask the user where they want the report delivered. Use the `AskUserQuestion` tool:

- **Question**: "Where would you like the research report delivered?"
- **Options**:
  1. **Inline** — "Display the report directly in this conversation"
  2. **Save to file** — "Save as a markdown file in `deep-research/`"

Wait for their answer before proceeding. Store their choice for Phase 4.

## Phase 1 — Wide Source Discovery

The goal here is breadth — cast the widest possible net before filtering. If the user gave a vague topic, spend a moment refining the research question first. A well-framed question produces dramatically better results.

**Spawn a single Researcher subagent** (using the Agent tool with `subagent_type: "Researcher"`) with a prompt like:

> Research the following topic as broadly as possible: **{topic}**
>
> Your job is pure discovery — find as many distinct, relevant sources as you can. Use at least 4-5 different search queries to cover different angles. For example, if the topic is "WebTransport API maturity":
> - Search for the technology name directly: "WebTransport API"
> - Search for comparisons: "WebTransport vs WebSockets"
> - Search for adoption/production use: "WebTransport production readiness 2026"
> - Search for official specs/standards: "W3C WebTransport specification status"
> - Search for community sentiment: "WebTransport developer experience"
>
> For each source you find, return:
>
> 1. **URL** — the full URL
> 2. **Title** — the page or document title
> 3. **Type** — what kind of source it is (official docs, blog post, academic paper, GitHub repo, forum thread, news article, vendor page, etc.)
> 4. **Publisher** — who published this (e.g., "Mozilla/MDN", "Cloudflare blog", "personal blog by [name]", "Company X marketing page")
> 5. **Brief description** — 1-2 sentences on what this source covers
> 6. **Apparent date** — any publication or last-updated date you can find
>
> Return the full list as a structured markdown table. Aim for at least 10-15 distinct sources. Prioritize diversity — different authors, different types of sources, different angles on the topic. Include at least some sources from each category: official/spec docs, independent analysis, community/developer experience, and (if applicable) vendor-published content.

## Phase 2 — Source Validation and Prioritization

Now you have a list of sources. Your job is to analytically assess and rank them. Do this yourself (no subagent needed) — you're the one with the full picture.

**For each source, score it on four dimensions** (1-5 scale each):

| Dimension | What it measures |
|-----------|-----------------|
| **Recency** | How recent is the content? Published this year = 5, last year = 4, 2-3 years = 3, older = 2, unknown = 1 |
| **Authority** | Is this an official source, a respected publication, a known expert? Official docs/specs = 5, reputable tech blog = 4, personal blog with demonstrated expertise = 3, forum thread = 2, unknown = 1 |
| **Relevance** | How directly does this source address the research topic? Dead-on = 5, closely related = 4, tangential = 3, barely related = 2, off-topic = 1 |
| **Independence** | How free is this source from commercial bias? Independent research/analysis = 5, editorial tech publication = 4, sponsored but disclosed = 3, vendor blog about own product = 2, vendor marketing page = 1 |

**Composite score** = Recency + Authority + Relevance + Independence (max 20)

The Independence dimension matters because vendor-published content systematically overstates their own product's capabilities. A vendor's benchmark of their own tool will almost always show better numbers than an independent benchmark of the same tool. This doesn't mean vendor sources are useless — they're often the most detailed — but the report needs to account for that bias.

Sort by composite score descending. Select the top sources — use your judgment on how many, but typically the top 5-8 that scored 13 or above. If fewer than 5 sources score well, include everything above 10. Ensure you have a mix of independent and vendor sources — don't filter out all vendor content, but make sure independent sources outnumber vendor ones.

Present this ranked table to the user briefly so they can see what you're working with, then proceed to Phase 3.

## Phase 3 — Parallel Deep Dive

This is where the real depth comes from. Take your prioritized sources and distribute them across multiple Researcher subagents running in parallel.

**How to split the work:**

- Group sources by theme or sub-topic rather than arbitrarily. If you have 6 sources and they naturally cluster into 3 themes, spawn 3 agents with 2 sources each.
- Each agent should get 2-4 sources maximum — enough to cross-reference but not so many that the agent loses focus.
- Aim for 2-4 parallel agents depending on how many quality sources survived Phase 2.

**Prompt each Researcher subagent with:**

> You are conducting deep research on: **{topic}**
>
> Your assigned sources to investigate thoroughly:
> {list of URLs with titles and publishers}
>
> For each source:
> 1. Fetch and read the full content using WebFetch
> 2. Extract all key findings, data points, claims, and insights relevant to the topic
> 3. Note any unique information this source provides that others might not
> 4. Flag any claims that seem questionable or contradict other sources
> 5. **Check for vendor bias**: If this source is published by a company with a commercial interest in the topic (e.g., a cloud provider writing about their own platform, a tool vendor publishing benchmarks of their own tool), explicitly note which claims serve the vendor's interests vs. which appear objective. For example, a vendor benchmark showing their product is "3x faster" should be flagged as vendor-claimed unless independently verified.
>
> Then synthesize across your assigned sources:
> - What are the key themes and findings?
> - Where do your sources agree?
> - Where do they disagree or contradict each other?
> - What gaps remain — what questions does this set of sources NOT answer?
> - Which claims are independently verified vs. single-source or vendor-only?
>
> Return your findings as structured markdown with clear section headings.

**Launch all agents in parallel** — use a single message with multiple Agent tool calls so they run concurrently.

## Phase 4 — Synthesis and Report

Once all Phase 3 agents have returned, you have deep findings from multiple angles. Now synthesize everything into a single coherent report.

**Cross-referencing discipline** — this is what makes the skill's output better than a single research pass:

- For every major claim in the report, cite which sources support it. If only one source makes a claim, explicitly note it as "single-source" so the reader knows the confidence level.
- When two sources report different numbers for the same metric (e.g., "bug detection rate"), present both with their provenance: "Source A (independent benchmark) reports X%, while Source B (vendor benchmark) reports Y%."
- Do not quietly pick one number and discard the other — the discrepancy itself is informative.

### Report Structure

```markdown
# Deep Research Report: {Topic}

*Generated: {date}*
*Sources analyzed: {count}*

## Executive Summary

{3-5 paragraphs covering the most important findings, key takeaways,
and any critical caveats. This should stand alone — someone reading
only this section should walk away informed.}

## Findings by Theme

### {Theme 1}

{Detailed findings, cross-referenced across sources. Include specific
data points, quotes, or examples where they add value. Note where
sources agree and where they diverge. When citing a specific data point,
indicate the source inline, e.g., "latency dropped 35% (Source: Vroble,
Nov 2025)" so readers can trace claims back to origins.}

### {Theme 2}

{...}

### {Theme N}

{...}

## Contradictions and Open Questions

{This section is not optional. Cover:
- Areas where sources directly disagreed (with specifics)
- Claims that could not be independently verified
- Questions that the research did not fully answer
- Vendor claims that lack independent corroboration
This tells the reader where the limits of this research are.}

## Sources

| # | Source | Type | Ind. | Score | Key Contribution |
|---|--------|------|------|-------|-----------------|
| 1 | [Title](URL) | Type | Yes/No | X/20 | What this source uniquely contributed |
| ... | ... | ... | ... | ... | ... |
```

The "Ind." column marks whether the source is independent (Yes) or vendor-published (No). This lets readers quickly assess the evidence base.

### Delivering the Report

Based on the user's Phase 0 choice:

- **Inline**: Output the full report directly in the conversation.
- **Save to file**: Write the report to `deep-research/{topic-slug}-{date}.md` using the Write tool (create the `deep-research/` directory in the current working directory if it doesn't exist). Then tell the user where the file was saved and provide a brief summary inline.
