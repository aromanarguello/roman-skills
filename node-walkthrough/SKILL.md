---
name: node-walkthrough
description: Create sparse, dark, interactive node-workflow HTML diagrams with a guided walkthrough. Use when the user asks to diagram, visualize, map, or explain a process in the same compact node-canvas style; do not use for charts, general web pages, or static illustrations.
---

# Node Walkthrough

Create a self-contained HTML workflow diagram using the bundled renderer. Preserve the established visual language: compact desktop-style window, dark dotted canvas, small connected nodes, one optional fork/merge, and detailed explanations revealed only during the walkthrough.

## Workflow

1. Determine whether the diagram describes current behavior, a proposal, or a mixture. Label the state honestly.
2. Reduce the process to 5–9 nodes. Keep permanent node text terse:
   - title: usually 2–4 words
   - subtitle: usually 2–5 words
   - detail: the full plain-English explanation shown during the walkthrough
3. Use a single centered route unless parallel work is materially important. Use `left` and `right` lanes for at most one fork/merge.
4. Read [references/spec.md](references/spec.md), create a JSON spec, and run:

   ```bash
   python3 scripts/render_workflow.py --spec <spec.json> --output <diagram.html>
   ```

5. Save the HTML in the current task's writable visualization directory when available; otherwise use a user-approved output path or `/private/tmp`.
6. Render-check the output when browser automation is available. Verify the page loads without errors, all nodes appear, the walkthrough advances, and there is no horizontal overflow.
7. Open the result in Codex and return a clickable absolute file link.

## Content Rules

- Put explanation in walkthrough details, not on the idle canvas.
- Prefer seven or eight steps; use fewer when the process is genuinely simpler.
- Never add a hero, summary strip, side cards, legend, or paragraph below the canvas.
- Do not imply proposed behavior exists. Use `PROPOSED`, `CURRENT`, or another accurate state label.
- Keep facts source-grounded. When architecture is uncertain, phrase the step as a proposal or assumption.
- The boundary pill should communicate one important scope limit, status, or invariant in a single short sentence.
- Reuse the renderer instead of manually recreating the HTML/CSS.

## Output Standard

The finished artifact must remain self-contained and dependency-free, support keyboard navigation, respect reduced-motion preferences, and retain the same sparse appearance across requests.
