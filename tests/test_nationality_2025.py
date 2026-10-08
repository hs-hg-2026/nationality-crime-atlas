"""Tests for the separately scoped 2025 supplement, including missing cells."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from nationality_crime_atlas.errors import SchemaError
from nationality_crime_atlas.nationality_2025_csv import parse_visiting_offense_csv


def inputs():
    selected = [
        {"nationality": "ベトナム", "population_scope": "all_foreign", "metric": "cleared_cases", "value": 7447, "year": 2025, "source_id": "S22", "source_table": "3-3-3", "source_sheet": "3-3-3", "source_row": 12, "source_column": 14},
        {"nationality": "中国", "population_scope": "all_foreign", "metric": "cleared_cases", "value": 3321, "year": 2025, "source_id": "S22", "source_table": "3-3-3", "source_sheet": "3-3-3", "source_row": 8, "source_column": 14},
    ]
    totals = [dict(year=2025, population_scope=scope, cleared_cases=cases, cleared_persons=persons, source_id="S21", source_table="3-3-1", source_sheet="3-3-1", source_row=row, source_cases_column=14, source_persons_column=14) for scope, cases, persons, row in [("all_persons", 301055, 200663, 4), ("all_foreign", 22917, 11354, 5), ("visiting_foreign", 17614, 7333, 6)]]
    population = [dict(nationality=label, row_kind="country_or_area", population=value, period_end="2025-12-31", source_id="S19_2025", source_table="1", source_sheet="25-12-01m", source_row=i+1, source_column=5) for i, (label,value) in enumerate([("ベトナム",681100),("中国",930428)])]
    japanese = [dict(year=2025, geography="日本", nationality_code=code, population=value, source_id="S27", source_table="49-1", source_sheet="b49_01", source_row=11, source_column=column) for code,value,column in [("2",117405318,31),("3",2105452,32)]]
    offenses = [asdict(r) for r in parse_visiting_offense_csv(Path("data/testdata/subset/npa_2025/r7toukeisotai0313.csv"), source_id="S30")]
    return {"S22": selected, "S21": totals, "S19_2025": population, "S27": japanese, "S30": offenses}


def test_reference_ratios_preserve_missing_and_explicit_residual():
    from nationality_crime_atlas.nationality_2025 import derive_supplement

    data = derive_supplement(inputs())
    rows = data["comparison"]
    japan = next(r for r in rows if r["label"] == "日本" and r["scope"] == "all_foreign" and r["metric"] == "cleared_cases")
    assert japan["numerator"] == 278138
    assert japan["denominator"] == 117405318
    assert japan["value"] == pytest.approx(278138/117405318*1000)
    assert japan["derivation"] == "national_total_minus_all_foreign"
    assert [c["role"] for c in japan["numerator_components"]] == ["minuend", "subtrahend"]
    missing = next(r for r in rows if r["label"] == "ベトナム" and r["metric"] == "cleared_persons" and r["scope"] == "all_foreign")
    assert missing["numerator"] is None and missing["value"] is None
    assert missing["reason"] == "numerator_not_published"
    assert missing["denominator"] == 681100
    china = next(r for r in rows if r["label"] == "中国" and r["metric"] == "cleared_cases" and r["scope"] == "all_foreign")
    assert "china_category_scope_mismatch" in china["warnings"]
    assert china["denominator"] == 930428
    assert len(rows) == 120
    assert len(set(r["label"] for r in rows)) == 30


def test_composition_is_visiting_only_with_japan_unavailable_and_true_zero():
    from nationality_crime_atlas.nationality_2025 import derive_supplement

    data = derive_supplement(inputs())
    assert len(data["composition"]) == 14
    for row in data["composition"]:
        assert row["scope"] == "visiting_foreign"
        if row["label"] == "日本":
            assert row["total"] is None
            assert all(cell["count"] is None for cell in row["cells"])
        else:
            assert sum(cell["count"] for cell in row["cells"]) == row["total"]
            assert sum(cell["share"] for cell in row["cells"]) == pytest.approx(100)
    cambodia = next(r for r in data["composition"] if r["label"] == "カンボジア" and r["metric"] == "cleared_cases")
    assert next(cell for cell in cambodia["cells"] if cell["category_id"] == "morals")["count"] == 0
    assert set(data["cluster_orders"]["cleared_cases"]) == {"ベトナム","中国","タイ","ブラジル","カンボジア"}


def test_duplicate_published_cell_is_rejected():
    from nationality_crime_atlas.nationality_2025 import derive_supplement

    records = inputs()
    records["S22"].append(records["S22"][0])
    with pytest.raises(SchemaError, match="exactly one"):
        derive_supplement(records)


def test_composition_total_must_agree_with_independent_national_series():
    from nationality_crime_atlas.nationality_2025 import derive_supplement

    records = inputs()
    records["S21"][2]["cleared_cases"] += 1
    with pytest.raises(SchemaError, match="S21"):
        derive_supplement(records)


def product_root(tmp_path):
    import hashlib

    contract = json.loads(Path("config/nationality_2025_contract.json").read_text())
    catalog = []
    for source_id, records in inputs().items():
        raw = tmp_path / "data/raw" / source_id / "fixture.csv"
        processed = tmp_path / "data/processed" / source_id
        raw.parent.mkdir(parents=True)
        processed.mkdir(parents=True)
        raw.write_bytes(("synthetic fixture " + source_id).encode())
        normalized = processed / "normalized.jsonl"
        normalized.write_text("".join(json.dumps(row) + "\n" for row in records))
        raw_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
        normalized_hash = hashlib.sha256(normalized.read_bytes()).hexdigest()
        contract["input_pins"][source_id] = {"artifact_sha256": raw_hash, "normalized_sha256": normalized_hash}
        (processed / "run.json").write_text(json.dumps({"source_id": source_id, "quality_passed": True, "raw_artifact_sha256": raw_hash, "normalized_sha256": normalized_hash}))
        catalog.append({"source_id": source_id, "sha256": raw_hash, "raw_relpath": str(raw.relative_to(tmp_path / "data/raw")), "processed_relpath": source_id,
                        "publisher": "test", "dataset": "synthetic", "source_table": "test", "landing_url": "https://example.test", "download_url": "https://example.test/file", "retrieved_at": "2026-10-08T00:00:00+09:00", "revision": "fixture"})
    directory = tmp_path / "data/processed/_catalog"
    directory.mkdir()
    (directory / "artifacts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in catalog))
    (tmp_path / "config").mkdir()
    (tmp_path / "config/nationality_2025_contract.json").write_text(json.dumps(contract))
    return tmp_path


def test_build_pins_sources_and_atomic_latest_pointer(tmp_path, capsys):
    from nationality_crime_atlas.nationality_2025 import build_supplement, main

    root = product_root(tmp_path)
    data = build_supplement(root)
    assert set(data["sources"]) == {"S21", "S22", "S27", "S30", "S19_2025"}
    assert str(tmp_path) not in json.dumps(data)
    assert main(["--root", str(root)]) == 0
    pointer = json.loads((root / "output/nationality_2025/latest.json").read_text())
    assert pointer["comparison_count"] == 120
    assert json.loads((root / pointer["product_path"]).read_text())["comparison"] == data["comparison"]


@pytest.mark.parametrize("target", ["raw", "normalized", "run", "contract"])
def test_any_input_integrity_change_stops_generation(tmp_path, target):
    from nationality_crime_atlas.nationality_2025 import build_supplement
    from nationality_crime_atlas.errors import IntegrityError

    root = product_root(tmp_path)
    if target == "raw":
        (root / "data/raw/S22/fixture.csv").write_bytes(b"changed")
    elif target == "normalized":
        with (root / "data/processed/S22/normalized.jsonl").open("a") as handle:
            handle.write("{}\n")
    else:
        path = root / ("data/processed/S22/run.json" if target == "run" else "config/nationality_2025_contract.json")
        data = json.loads(path.read_text())
        if target == "run":
            data["quality_passed"] = False
        else:
            data["input_pins"]["S22"]["normalized_sha256"] = "0" * 64
        path.write_text(json.dumps(data))
    with pytest.raises((IntegrityError, SchemaError)):
        build_supplement(root)
