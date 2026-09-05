import json
from dataclasses import asdict

from nationality_crime_atlas.npa_nationality import parse_npa_nationality_totals
from nationality_crime_atlas.models import (
    OverallPrefectureCrimeRecord,
    PrefecturePopulationRecord,
)
from nationality_crime_atlas.npa_prefecture import parse_npa_prefecture_table13
from nationality_crime_atlas.population import parse_population_t1
from nationality_crime_atlas.quality import load_quality_profiles, validate_jsonl


def _write_records(path, records):
    path.write_text(
        "".join(
            json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _population_profile(record_count=2):
    return {
        "record_type": "population",
        "expected_record_count": record_count,
        "expected_periods": ["2025-12-31"],
        "allowed_values": {"sex": ["男", "女"]},
        "expected_distinct_counts": {
            "nationality": 2,
            "residence_status": 2,
            "sex": 2,
            "age_group": 2,
            "prefecture": 2,
        },
        "expected_sums": {"value": 15},
        "anchors": [
            {
                "where": {"nationality": "韓国", "prefecture": "岐阜県"},
                "expect": {"value": 15, "suppressed": False},
                "expected_matches": 1,
            }
        ],
    }


def test_valid_population_jsonl_passes_all_profile_checks(
    population_t1_file,
    tmp_path,
):
    records = list(parse_population_t1(population_t1_file, source_id="S14"))
    normalized = tmp_path / "population.jsonl"
    _write_records(normalized, records)

    report = validate_jsonl(
        normalized,
        source_id="S14",
        profile=_population_profile(),
        artifact_manifest={"source_id": "S14", "record_count": 2},
    )

    assert report["passed"] is True
    assert report["record_count"] == 2
    assert report["duplicate_count"] == 0
    assert report["observed_periods"] == ["2025-12-31"]
    assert report["observed_values"]["sex"] == ["女", "男"]
    assert report["distinct_counts"]["nationality"] == 2
    assert report["sums"] == {"value": 15}
    assert report["anchors_checked"] == 1
    assert report["errors"] == []


def test_duplicate_dimensions_fail_even_when_source_rows_differ(
    population_t1_file,
    tmp_path,
):
    record = asdict(next(parse_population_t1(population_t1_file, source_id="S14")))
    duplicate = dict(record)
    duplicate["source_row"] = record["source_row"] + 100
    normalized = tmp_path / "duplicate.jsonl"
    normalized.write_text(
        json.dumps(record, ensure_ascii=False) + "\n"
        + json.dumps(duplicate, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    report = validate_jsonl(
        normalized,
        source_id="S14",
        profile={
            **_population_profile(),
            "expected_sums": {"value": 30},
            "anchors": [],
        },
    )

    assert report["passed"] is False
    assert report["duplicate_count"] == 1
    assert any("duplicate dimensions" in error for error in report["errors"])


def test_schema_unknown_category_negative_value_and_suppression_errors_are_reported(
    population_t1_file,
    tmp_path,
):
    record = asdict(next(parse_population_t1(population_t1_file, source_id="S14")))
    record["sex"] = "unknown-new-category"
    record["value"] = -1
    record["suppressed"] = True
    record["unexpected_column"] = "schema drift"
    normalized = tmp_path / "invalid.jsonl"
    normalized.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    report = validate_jsonl(
        normalized,
        source_id="S14",
        profile={
            **_population_profile(record_count=1),
            "expected_sums": {"value": -1},
            "anchors": [],
        },
    )

    assert report["passed"] is False
    assert any("schema fields" in error for error in report["errors"])
    assert any("unknown allowed value" in error for error in report["errors"])
    assert any("non-negative integer" in error for error in report["errors"])
    assert any("suppressed record must have a null value" in error for error in report["errors"])


def test_manifest_hash_count_and_anchor_mismatches_fail(
    population_t1_file,
    tmp_path,
):
    records = list(parse_population_t1(population_t1_file, source_id="S14"))
    normalized = tmp_path / "population.jsonl"
    _write_records(normalized, records)
    profile = {
        **_population_profile(),
        "expected_artifact_sha256": "expected-hash",
        "anchors": [
            {
                "where": {"nationality": "韓国"},
                "expect": {"value": 999},
                "expected_matches": 1,
            }
        ],
    }

    report = validate_jsonl(
        normalized,
        source_id="S14",
        profile=profile,
        artifact_manifest={
            "source_id": "S14",
            "record_count": 99,
            "sha256": "different-hash",
        },
    )

    assert report["passed"] is False
    assert any("artifact SHA-256" in error for error in report["errors"])
    assert any("manifest record_count" in error for error in report["errors"])
    assert any("anchor expected" in error for error in report["errors"])


def test_nationality_and_prefecture_record_types_have_distinct_duplicate_keys(
    nationality_table130_file,
    prefecture_table13_file,
    tmp_path,
):
    nationality_records = parse_npa_nationality_totals(
        nationality_table130_file,
        table_id="130",
        source_id="S08",
    )
    prefecture_records = parse_npa_prefecture_table13(
        prefecture_table13_file,
        source_id="S02",
    )
    nationality_path = tmp_path / "nationality.jsonl"
    prefecture_path = tmp_path / "prefecture.jsonl"
    _write_records(nationality_path, nationality_records)
    _write_records(prefecture_path, prefecture_records)

    nationality_report = validate_jsonl(
        nationality_path,
        source_id="S08",
        profile={
            "record_type": "nationality_crime",
            "expected_record_count": len(nationality_records),
            "expected_years": [2024],
            "allowed_values": {
                "population_scope": ["all_foreign"],
                "row_kind": ["region_total", "country", "subcategory"],
            },
            "expected_sums": {},
            "anchors": [],
        },
    )
    prefecture_report = validate_jsonl(
        prefecture_path,
        source_id="S02",
        profile={
            "record_type": "prefecture_crime",
            "expected_record_count": len(prefecture_records),
            "expected_years": [2024, 2025],
            "allowed_values": {
                "population_scope": ["visiting_foreign"],
                "offense_scope": [
                    "criminal_and_special_law",
                    "criminal_code",
                    "special_law",
                ],
                "geography_type": [
                    "national",
                    "police_region",
                    "police_subregion",
                    "prefecture",
                ],
            },
            "expected_sums": {},
            "anchors": [],
        },
    )

    assert nationality_report["passed"] is True
    assert prefecture_report["passed"] is True


def test_quality_profile_loader_preserves_versioned_source_profiles(tmp_path):
    path = tmp_path / "quality_profiles.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profiles": {"S14": _population_profile()},
            }
        ),
        encoding="utf-8",
    )

    profiles = load_quality_profiles(path)

    assert profiles["S14"]["record_type"] == "population"
    assert profiles["S14"]["expected_record_count"] == 2


def test_project_quality_profiles_pin_japanese_population_and_criminal_code_fields():
    profiles = load_quality_profiles("config/quality_profiles.json")

    assert profiles["S17"] == {
        "description": "Statistics Bureau 2024 Population Estimates Table 2 Japanese-national population",
        "record_type": "prefecture_population",
        "expected_artifact_sha256": "171c9930a3c881c42ded00fbaace83b4e6dd226d1a90cfddecd1daca2e376e82",
        "expected_record_count": 48,
        "expected_years": [2024],
        "allowed_values": {
            "reference_date": ["2024-10-01"],
            "population_scope": ["japanese_population"],
            "geography_type": ["national", "prefecture"],
            "geography_semantics": [
                "national_aggregate",
                "population_estimate_prefecture",
            ],
            "source_unit": ["1000_persons"],
            "rounding": ["nearest_1000_persons"],
        },
        "expected_distinct_counts": {
            "year": 1,
            "reference_date": 1,
            "geography": 48,
            "geography_type": 2,
            "parent_region": 1,
        },
        "expected_sums": {},
        "anchors": [
            {
                "where": {"year": 2024, "geography": "日本"},
                "expect": {"population": 120296000, "source_value": 120296},
                "expected_matches": 1,
            },
            {
                "where": {"year": 2024, "geography": "東京都"},
                "expect": {"population": 13463000, "source_value": 13463},
                "expected_matches": 1,
            },
        ],
    }
    s08_china = profiles["S08"]["anchors"][0]["expect"]
    assert s08_china["criminal_code_cleared_cases"] == 3374
    assert s08_china["criminal_code_cleared_persons"] == 2393


def test_project_quality_profiles_pin_historical_npa_detail_editions():
    profiles = load_quality_profiles("config/quality_profiles.json")
    expected = {
        "S15_2020": (2020, "308cecb15fa3c33b13ecd4e5d5eaf08890aab326a796f5aed6dc8b7dc6bff956", 60),
        "S15_2021": (2021, "2f007c3d6ef700c3fbbe28f63f3f9ce7abadb67eb86e2207ef4344ed9b2e1270", 60),
        "S15_2022": (2022, "e05be7dcc58815eb894eafba4e24df5204ae67e78ba849c1750b7e786487d053", 60),
        "S15_2023": (2023, "4dfa94cfd558fc98fd571e79fb8a4e79c2ceebe2e8b2e12c5d14b75c1d50915a", 60),
        "S08_2020": (2020, "5e6ceb16a748f9d4be6313e9b4d3b5aed50e026cbf19e0677891c66ae86a2efd", 33),
        "S08_2021": (2021, "45a4bf1c58d5d0cb4b933d4bc9db5068f12fd66646acd401221fabc71df5f36f", 33),
        "S08_2022": (2022, "901cc0c472411468ba21e88de99d7aa9b3442fe4e6047360e6d3234744ead5ba", 33),
        "S08_2023": (2023, "b1a4a6c9351f77171fc40c57cfbdce4e9fb1e90a68156cab7fefd7cf33a8f9e5", 33),
        "S09_2020": (2020, "91c91a661e67f0ecf593766e45ecd8d29a4b8d06dbf858f72696ac11c995a519", 30),
        "S09_2021": (2021, "eabb1b97c0874adb8bb3227cb320aa828fbec3a8d7b954a4d4cc10743048f9ea", 30),
        "S09_2022": (2022, "585e3a413906349261b971485c95640582e916943e80d05bf910aa9eb5ca879c", 30),
        "S09_2023": (2023, "c4c29c849239552b14a9c9ba339c42fd661a3b39b2231cb14a7050f7397f27bb", 30),
    }

    for source_id, (year, artifact_hash, record_count) in expected.items():
        profile = profiles[source_id]
        assert profile["expected_artifact_sha256"] == artifact_hash
        assert profile["expected_record_count"] == record_count
        assert profile["expected_years"] == [year]
        assert profile["anchors"][0]["where"]["year"] == year


def test_project_quality_profiles_pin_historical_japanese_population_editions():
    profiles = load_quality_profiles("config/quality_profiles.json")
    expected = {
        "S17_2021": (
            2021,
            "5acd98b56ab29648d39c780098826c8916cd5daddf663bcf72d1198e32aef226",
            122780,
            13459,
        ),
        "S17_2022": (
            2022,
            "c91ad5d7dd29f067f0d20d27575e8fcc1ab1fb8dc7871b1393080a3b5e682fc2",
            122031,
            13443,
        ),
        "S17_2023": (
            2023,
            "53a63aea1b02c672f25a9e9e563f9c698901a52e651dd8d2e81c2ef1092d1a47",
            121193,
            13448,
        ),
    }

    for source_id, (year, artifact_hash, national, tokyo) in expected.items():
        profile = profiles[source_id]
        assert profile["expected_artifact_sha256"] == artifact_hash
        assert profile["expected_record_count"] == 48
        assert profile["expected_years"] == [year]
        assert profile["anchors"][0]["expect"]["source_value"] == national
        assert profile["anchors"][1]["expect"]["source_value"] == tokyo


def test_project_quality_profile_pins_intercensal_population_edition():
    profiles = load_quality_profiles("config/quality_profiles.json")

    profile = profiles["S18"]
    assert profile["expected_artifact_sha256"] == (
        "9e28da4c0ef8c2680577ad5ef0b0a78023d389113f66c85ab9e52bdbed89a1fc"
    )
    assert profile["expected_record_count"] == 576
    assert profile["expected_years"] == [2015, 2016, 2017, 2018, 2019, 2020]
    assert profile["expected_distinct_counts"]["population_scope"] == 2
    assert profile["anchors"][0]["expect"]["source_value"] == 126146
    assert profile["anchors"][1]["expect"]["source_value"] == 123399


def test_all_resident_context_record_types_pass_quality_validation(tmp_path):
    crime_records = [
        OverallPrefectureCrimeRecord(
            year=2024,
            population_scope="all_persons",
            offense_scope="criminal_code_excluding_traffic_negligence",
            geography="東京都",
            geography_type="prefecture",
            parent_region="東京都",
            geography_semantics="police_reporting_area_unresolved",
            recognized_cases=30,
            cleared_cases=14,
            cleared_persons=10,
            source_id="S15",
            source_table="3",
            source_sheet="刑法犯総数",
            source_row=16,
        )
    ]
    population_records = [
        PrefecturePopulationRecord(
            year=2024,
            reference_date="2024-10-01",
            population_scope="total_population",
            geography="東京都",
            geography_type="prefecture",
            parent_region=None,
            geography_semantics="population_estimate_prefecture",
            population=14100000,
            source_value=14100,
            source_unit="1000_persons",
            rounding="nearest_1000_persons",
            source_id="S16",
            source_table="144",
            source_sheet="01",
            source_row=9,
        )
    ]
    crime_path = tmp_path / "crime.jsonl"
    population_path = tmp_path / "total_population.jsonl"
    _write_records(crime_path, crime_records)
    _write_records(population_path, population_records)

    crime_report = validate_jsonl(
        crime_path,
        source_id="S15",
        profile={
            "record_type": "overall_prefecture_crime",
            "expected_record_count": 1,
            "expected_years": [2024],
            "allowed_values": {"population_scope": ["all_persons"]},
            "expected_distinct_counts": {"geography": 1},
            "expected_sums": {},
            "anchors": [],
        },
    )
    population_report = validate_jsonl(
        population_path,
        source_id="S16",
        profile={
            "record_type": "prefecture_population",
            "expected_record_count": 1,
            "expected_years": [2024],
            "allowed_values": {"population_scope": ["total_population"]},
            "expected_distinct_counts": {"geography": 1},
            "expected_sums": {},
            "anchors": [],
        },
    )

    assert crime_report["passed"] is True
    assert population_report["passed"] is True
