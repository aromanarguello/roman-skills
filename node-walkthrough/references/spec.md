# Workflow Specification

Create a UTF-8 JSON file with this shape:

```json
{
  "title": "Request → Verified Change",
  "state": "PROPOSED",
  "boundary": "Repository-local · human approval before merge",
  "nodes": [
    {
      "id": "request",
      "title": "Request received",
      "subtitle": "scope is explicit",
      "detail": "Capture the requested outcome and its acceptance boundary.",
      "icon": "trigger",
      "row": 0,
      "lane": "center",
      "status": "done"
    },
    {
      "id": "verified",
      "title": "Change verified",
      "subtitle": "evidence is recorded",
      "detail": "Run the relevant checks and report what remains unproven.",
      "icon": "check",
      "row": 1,
      "lane": "center",
      "status": "next"
    }
  ],
  "edges": [["request", "verified"]]
}
```

## Fields

- `title`: Window title. Keep it short.
- `state`: Short uppercase state such as `CURRENT`, `PROPOSED`, or `DESIGN`.
- `boundary`: Optional short pill above the walkthrough controls.
- `nodes`: Two to ten nodes, in walkthrough order.
  - `id`: Unique lowercase identifier using letters, numbers, `_`, or `-`.
  - `title`: Short permanent node label.
  - `subtitle`: Short permanent secondary label.
  - `detail`: Full walkthrough explanation.
  - `icon`: One of `trigger`, `clock`, `file`, `search`, `quote`, `sparkle`, `check`, `git`, `brain`, `shield`, `link`, `person`, or `database`.
  - `row`: Non-negative integer. Nodes sharing a row appear in parallel.
  - `lane`: `center`, `left`, or `right`. Use left/right only for a meaningful fork.
  - `status`: `done`, `next`, or `pending`.
- `edges`: Directed `[source_id, target_id]` pairs. Every referenced ID must exist.

## Layout Guidance

- A linear flow uses `center` for every node and increments `row` by one.
- A fork uses one center node, two nodes sharing the next row in `left` and `right`, then a center merge node on the following row.
- Avoid more than one fork/merge. The renderer is intentionally optimized for a readable concept walkthrough, not arbitrary graph visualization.
