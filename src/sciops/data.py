from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class ValidationResult:
    rows: int
    columns: int


class DataValidationError(ValueError):
    def __init__(self, message: str, failure_cases: list[dict] | None = None) -> None:
        super().__init__(message)
        self.failure_cases = failure_cases or []


def _dtype(name: str):
    import pandera.pandas as pa

    types = {
        "string": pa.String,
        "str": pa.String,
        "int": pa.Int64,
        "integer": pa.Int64,
        "float": pa.Float64,
        "number": pa.Float64,
        "bool": pa.Bool,
        "boolean": pa.Bool,
        "datetime": pa.DateTime,
    }
    try:
        return types[name.strip().lower()]
    except KeyError as exc:
        raise DataValidationError(f"不支持的数据类型: {name}") from exc


def validate_csv(data_path: Path, schema_path: Path) -> ValidationResult:
    try:
        import pandas as pd
        import pandera.pandas as pa
    except ImportError as exc:
        raise DataValidationError("请安装 data 依赖: uv sync --extra data") from exc

    try:
        config = yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise DataValidationError(f"无法读取 schema: {exc}") from exc
    columns_config = config.get("columns")
    if not isinstance(columns_config, dict) or not columns_config:
        raise DataValidationError("schema 必须包含非空 columns 映射")

    columns = {}
    for name, settings in columns_config.items():
        settings = settings or {}
        checks = []
        if "min" in settings:
            checks.append(pa.Check.ge(settings["min"]))
        if "max" in settings:
            checks.append(pa.Check.le(settings["max"]))
        if "allowed" in settings:
            checks.append(pa.Check.isin(settings["allowed"]))
        if "str_matches" in settings:
            checks.append(pa.Check.str_matches(settings["str_matches"]))
        columns[name] = pa.Column(
            _dtype(str(settings.get("dtype", "string"))),
            nullable=bool(settings.get("nullable", False)),
            unique=bool(settings.get("unique", False)),
            required=bool(settings.get("required", True)),
            checks=checks,
        )

    schema = pa.DataFrameSchema(
        columns,
        strict=bool(config.get("strict", False)),
        coerce=bool(config.get("coerce", True)),
    )
    frame = pd.read_csv(data_path)
    try:
        validated = schema.validate(frame, lazy=True)
    except pa.errors.SchemaErrors as exc:
        failures = exc.failure_cases.head(100).to_dict(orient="records")
        message = f"数据验证失败，共 {len(exc.failure_cases)} 个失败项"
        raise DataValidationError(message, failures) from exc
    return ValidationResult(rows=len(validated), columns=len(validated.columns))
