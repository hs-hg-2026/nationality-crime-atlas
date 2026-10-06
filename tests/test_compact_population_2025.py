import copy

import pytest

import nationality_crime_atlas.compact_export as compact
from nationality_crime_atlas.errors import SchemaError


def _row(group="japanese_etc_residual", metric="cleared_persons"):
    japanese = group == "japanese_etc_residual"
    cases = metric == "cleared_cases"
    numerator = (278138 if cases else 189309) if japanese else (22917 if cases else 11354)
    denominator = 117405318 if japanese else 4125395
    source = "S27" if japanese else "S19_2025"
    flags = list(compact.CLEARANCE_POPULATION_GROUP_CONTRACTS[group]["required_flags"])
    if japanese:
        flags.remove("japanese_population_rounded_to_nearest_1000")
        flags.extend(("census_original_nationality_population", "census_nationality_unknown_excluded_from_japanese_denominator", "population_source_changed_to_census"))

    def component(role, value, source_row):
        return {"source_id": "S21", "source_table": "3-3-1", "source_sheet": "3-3-1", "source_row": source_row, "source_column": 14, "metric": metric, "value": value, "role": role}

    population = {"source_id": source, "source_table": "49-1" if japanese else "1", "source_sheet": "b49_01" if japanese else "25-12-01m", "source_row": 11 if japanese else 5, "source_column": 31 if japanese else 5, "metric": "population", "value": denominator, "published_value": denominator, "published_unit": "persons", "role": "denominator"}
    if japanese:
        population.update(value_basis="original", excluded_unknown_population=2105452)
    return {
        "year": 2025, "population_group": group, "metric": metric,
        "numerator_value": numerator, "denominator_value": denominator,
        "numerator_source_ids": ["S21"], "denominator_source_id": source,
        "calculation_status": "calculated", "refusal_reason": None,
        "population_scope": "japanese_population" if japanese else "resident_foreigner_population",
        "population_reference_date": "2025-10-01" if japanese else "2025-12-31",
        "denominator_rounding": "none" if japanese else "as_published_persons",
        "derivation_method": compact.CLEARANCE_POPULATION_GROUP_CONTRACTS[group]["derivation_method"],
        "derivation_formula": (f"(S21.all_persons.{metric} - S21.all_foreign.{metric}) / S27.population * 1000" if japanese else f"S21.all_foreign.{metric} / S19_2025.population * 1000"),
        "display_multiplier": 1000, "quotient": numerator / denominator,
        "display_value": numerator / denominator * 1000, "mismatch_flags": flags,
        "source_components": ([component("numerator_minuend", 301055 if cases else 200663, 4 if cases else 7), component("numerator_subtrahend", 22917 if cases else 11354, 5 if cases else 8), population] if japanese else [component("numerator", numerator, 5 if cases else 8), population]),
    }


@pytest.mark.parametrize("group", ["japanese_etc_residual", "all_foreign"])
@pytest.mark.parametrize("metric", ["cleared_cases", "cleared_persons"])
def test_accepts_reviewed_2025_binding(group, metric):
    compact._validate_2025_clearance_population_row(_row(group, metric))


@pytest.mark.parametrize("change", ["coordinate", "rounding", "basis", "unknown", "scope", "flags", "arithmetic"])
def test_rejects_changed_2025_binding(change):
    row = copy.deepcopy(_row())
    if change == "coordinate":
        row["source_components"][0]["source_row"] = 4
    elif change == "rounding":
        row["denominator_rounding"] = "nearest_1000_persons"
    elif change == "basis":
        row["source_components"][2]["value_basis"] = "official_imputed_reference"
    elif change == "unknown":
        del row["source_components"][2]["excluded_unknown_population"]
    elif change == "scope":
        row["numerator_source_ids"] = ["S08"]
    elif change == "flags":
        row["mismatch_flags"] = []
    else:
        row["display_value"] = 0
    with pytest.raises(SchemaError, match="semantic contract"):
        compact._validate_2025_clearance_population_row(row)
