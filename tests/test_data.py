from pathlib import Path

import pytest

from sciops.data import DataValidationError, validate_csv


def test_validate_csv(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
strict: true
columns:
  sample_id: {dtype: string, unique: true}
  value: {dtype: float, min: 0, max: 10}
""".strip(),
        encoding="utf-8",
    )
    valid = tmp_path / "valid.csv"
    valid.write_text("sample_id,value\na,1.5\nb,2.0\n", encoding="utf-8")
    result = validate_csv(valid, schema)
    assert result.rows == 2

    invalid = tmp_path / "invalid.csv"
    invalid.write_text("sample_id,value\na,20\na,2\n", encoding="utf-8")
    with pytest.raises(DataValidationError):
        validate_csv(invalid, schema)
