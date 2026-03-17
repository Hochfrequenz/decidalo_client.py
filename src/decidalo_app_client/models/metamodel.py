"""Pydantic models and helpers for the decidalo metamodel response patterns.

Two patterns are used by the App API:

Pattern 1 — viewMetamodelResult:
    { "viewMetamodelResult": [{ "columnName": "FirstName", "columnID": 42, "data": "Max", ... }] }
    Used by: Profile/Header, Profile/EmployeeInfoSection, ProjectReference/Header, etc.

Pattern 2 — integer-keyed data:
    { "entityColumns": [{ "viewMetamodelEntryID": 154, "column": {"columnName": "ProjectName"} }],
      "data": [{ "154": "Projekt XYZ" }] }
    Used by: Profile/ProjectsSection, Profile/ProfessionalExperienceSection, etc.

resolve_row() handles Pattern 2. Pattern 1 is exposed as ViewMetamodelEntry lists.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MetamodelColumn(BaseModel):
    """Column definition inside entityColumns."""

    columnName: str
    columnID: int | None = None


class EntityColumn(BaseModel):
    """One entry in the entityColumns array (Pattern 2)."""

    viewMetamodelEntryID: int
    column: MetamodelColumn


class ViewMetamodelEntry(BaseModel):
    """One entry in the viewMetamodelResult array (Pattern 1)."""

    columnName: str
    columnID: int
    data: Any = None
    label: str | None = None
    dataType: Any = None
    isEditable: bool | None = None


class MetamodelGrid(BaseModel):
    """Parsed result of a Pattern 2 (integer-keyed data) response."""

    rows: list[dict[str, Any]]  # each row: columnName -> value
    total_count: int


def resolve_row(columns: list[EntityColumn], row: dict[str, Any]) -> dict[str, Any]:
    """Map integer string keys in a data row to their columnName values.

    Args:
        columns: The entityColumns from the same API response.
        row: One item from the data array (keys are viewMetamodelEntryID as strings).

    Returns:
        Dict mapping columnName -> value for each key in row.

    Raises:
        KeyError: If a key in row has no matching viewMetamodelEntryID in columns.
    """
    id_to_name = {str(col.viewMetamodelEntryID): col.column.columnName for col in columns}
    return {id_to_name[k]: v for k, v in row.items()}
