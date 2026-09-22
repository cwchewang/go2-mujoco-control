# Experiment template

Use with the [short task](research/TASK_TEMPLATE.md) and [SOP](research/SOP.md)
when an experiment is actually needed. Define design before execution; fill
results afterwards without rewriting the frozen design. Keep parameters in one
protocol and link it here. A template or old example is not start permission.

## EXP-XX — title

- **Status:** `open` / `accepted` / `superseded` / `rejected` / `diagnostic`
- **Date:** YYYY-MM-DD
- **Question:**
- **Decision served / link to project goal:**
- **Why this comparison now / cheaper evidence already checked:**
- **Acceptance criterion:**
- **Parameter/threshold basis:** requirement, source reproduction, or explicit exploratory assumption.
- **Code revision:**
- **Configuration / data / reference:**
- **Evaluator / protocol:**
- **Seeds:**
- **Budget, stopping and exclusions:** distinguish safety/integrity failure from expected performance failure; specify continuation of matrix cases.
- **Outcome to decision:** what PASS, performance FAIL and INVALID each change.

### Reference and comparison validity

Identify the exact public artifact, source configuration, claimed experiment
mapping and unresolved provenance. Separate original-condition reproduction from
transfer. Name changed/fixed model, reset, observations/actions, timing,
information and compute conditions. Distinguish deterministic repeatability from
independent trials; define uncertainty when the claim needs it. Do not invent a
comparison requirement merely to fill fields.

### Intervention or method

State what changes relative to the comparison condition. Separate intended experimental variables from incidental implementation changes.

### Result

Report the primary metric(s), completion/failure status, and uncertainty or repeated-run information where applicable. Do not convert incomplete or failed trajectories into primary metrics unless the protocol explicitly defines that behavior.

### Interpretation

State the narrow conclusion supported by the result and the important conclusions it does not support.

### Deviations and known issues

Record protocol deviations, implementation defects discovered after the run, missing artifacts, or other limitations that affect interpretation.

### Evidence

- Code / commit:
- Config:
- Input/reference hash:
- Result artifact:
- Plot / CSV / log:
- Related experiment(s):
