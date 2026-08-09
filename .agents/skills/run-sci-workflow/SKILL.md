---
name: run-sci-workflow
description: Run or resume an end-to-end scholarly research project in SCI Workflow OS. Use when the user gives a research direction, asks to search literature, refine a topic, design a study, analyze evidence, draft or standardize a manuscript, select a journal, submit, revise, or continue any G0-G10 research stage.
---

# Run SCI Workflow

## Resume before acting

1. Run `uv run --frozen sciops codex resume --json` from the repository root.
2. Use the reported active project and current stage. Read only `entry_files` plus files needed for the immediate action.
3. If the user explicitly requests a new paper, project, or unrelated direction, create a separate workspace after intake even when another project is active. Never overwrite or silently repurpose an existing project.
4. If the active project is complete through G10, preserve it as an archive and ask for the next broad research direction before creating a separate workspace.
5. If no active project exists and the user supplied a research direction, create `workspace/<short-slug>` with `sciops init`, activate it, record the direction in `00_research_intake.md` and `research-state.yaml`, and continue G0.
6. If no project and no direction exist, ask for the broad research field or direction and any available data or resource constraints. Never reuse another project's topic, data, method, references, or conclusions as the new default.
7. If several project candidates exist and the request does not identify one, ask the user to select it.

## Repair the environment

1. Inspect the `environment` and `missing_required` fields from the resume report.
2. In `trusted` mode, install missing project-local dependencies and initialize or sync CodeGraph without another question.
3. In `guided` mode, explain the smallest required installation and request approval when it changes the machine.
4. Never place credentials in tracked files. Ask for a missing credential only when the next action truly requires it; prefer keyless sources when suitable.

## Execute the active gate

Follow `SCI.md` and the active project's `stage-gates.yaml`.

- G0-G1: collect the new project's direction, generate and score candidate topics, then convert the selected topic into a bounded charter, feasibility constraints, and stop rules.
- G2: build reproducible English and Chinese searches, candidate records, screening decisions, and a claim-oriented literature matrix.
- G3-G4: define estimand or prediction target, variables, baselines, splits, statistics, leakage controls, data provenance, and preregistered checks.
- G5-G6: execute frozen experiments, uncertainty analysis, robustness, ablation, error analysis, and external or grouped validation.
- G7: freeze `09_claim_evidence_map.md` and `manuscript/outline.md`; draft complete Chinese and English manuscripts; align their claims, numbers, units, equations, figures, tables, citations, and scope in `manuscript/bilingual-alignment.csv`; then freeze the target-journal copy in `manuscript/paper.qmd`.
- G8: verify current journal scope, indexing, quartile, warnings, fees, format, ethics, and submission materials using authoritative sources.
- G9-G10: maintain response matrices, revision logs, proof checks, and reproducible archives.

Do not advance a gate because text exists. Advance only when its evidence and exit criteria are satisfied.

## Preserve evidence integrity

- Store title, abstract, DOI or canonical landing page, source, query, and retrieval date before downloading.
- Treat abstract-only records as candidates. Read and verify original sources before citation.
- Bind quantitative claims to a table, figure, analysis output, or verified source.
- Mark uncertainty and conflicting evidence explicitly.
- Do not invent missing facts, results, citations, or journal status.

## Write and hand off

1. Use one shared argument chain for both languages: claim, evidence, experiment or analysis, tested proposition, result with uncertainty, role in the paper, and bounded scientific or practical significance.
2. Apply `standardize-academic-writing` when drafting or revising scholarly text. Translation must not add evidence, alter numbers, or strengthen claims.
3. Run strict writing lint on `manuscript/en/paper.qmd`, `manuscript/zh/paper.qmd`, and the frozen `manuscript/paper.qmd` before G7 passes.
4. Treat both full manuscripts, the full-paper outline, the argument chain, and the completed bilingual alignment table as mandatory outputs rather than optional translations.
5. After each meaningful milestone, run `sciops codex checkpoint` with the completed action and ordered next actions.
6. Leave the active project with one concrete first next action so a new Codex session can resume immediately.
