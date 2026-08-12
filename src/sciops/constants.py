from __future__ import annotations

from pathlib import Path

STAGES = tuple(f"G{i}" for i in range(11))

REQUIRED_PATHS = (
    Path("research-state.yaml"),
    Path("memory/policy.yaml"),
    Path("memory/working-context.yaml"),
    Path("memory/semantic.yaml"),
    Path("memory/events.jsonl"),
    Path("00_research_intake.md"),
    Path("01_project_charter.md"),
    Path("02_search_log.csv"),
    Path("03_literature_matrix.csv"),
    Path("04_protocol.md"),
    Path("05_data_dictionary.csv"),
    Path("06_data_quality_report.md"),
    Path("07_experiment_registry.csv"),
    Path("08_reproducibility_README.md"),
    Path("09_claim_evidence_map.md"),
    Path("10_journal_scorecard.csv"),
    Path("11_submission_package/README.md"),
    Path("12_revision_log.md"),
    Path("stage-gates.yaml"),
    Path("manuscript/paper.qmd"),
    Path("manuscript/outline.md"),
    Path("manuscript/en/paper.qmd"),
    Path("manuscript/zh/paper.qmd"),
    Path("manuscript/bilingual-alignment.csv"),
    Path("manuscript/references.bib"),
    Path("archive/README.md"),
)

STAGE_ARTIFACTS: dict[str, tuple[Path, ...]] = {
    "G0": (
        Path("00_research_intake.md"),
        Path("01_project_charter.md"),
        Path("stage-gates.yaml"),
    ),
    "G1": (Path("01_project_charter.md"),),
    "G2": (Path("02_search_log.csv"), Path("03_literature_matrix.csv")),
    "G3": (Path("04_protocol.md"),),
    "G4": (Path("05_data_dictionary.csv"), Path("06_data_quality_report.md")),
    "G5": (Path("07_experiment_registry.csv"),),
    "G6": (Path("09_claim_evidence_map.md"),),
    "G7": (
        Path("08_reproducibility_README.md"),
        Path("09_claim_evidence_map.md"),
        Path("manuscript/outline.md"),
        Path("manuscript/en/paper.qmd"),
        Path("manuscript/zh/paper.qmd"),
        Path("manuscript/bilingual-alignment.csv"),
        Path("manuscript/paper.qmd"),
    ),
    "G8": (Path("10_journal_scorecard.csv"), Path("11_submission_package/README.md")),
    "G9": (Path("12_revision_log.md"),),
    "G10": (Path("archive/README.md"),),
}

ALLOWED_STAGE_STATUSES = {"pending", "in_progress", "blocked", "passed"}

SENSITIVE_NAMES = {
    ".env",
    ".sciops-active",
    ".sciops-local.toml",
    ".sciops-credentials.local.json",
    "credentials.json",
    "secrets.json",
    "token.json",
    "id_rsa",
    "id_ed25519",
}

EXCLUDED_DIR_NAMES = {
    ".codegraph",
    ".git",
    ".venv",
    ".tools",
    "__pycache__",
    ".pytest_cache",
    ".quarto",
    ".ruff_cache",
    "_site",
    "build",
    "dist",
    "raw",
    "interim",
    "models",
    "node_modules",
    "checkpoints",
    "workspace",
}
