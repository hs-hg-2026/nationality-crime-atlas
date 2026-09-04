import json
from pathlib import Path

import pytest

from nationality_crime_atlas.errors import IntegrityError, SchemaError
from nationality_crime_atlas.provenance import sha256_file
from nationality_crime_atlas.small_number_cli import main as small_number_main
from nationality_crime_atlas.small_numbers import (
    generate_small_number_sensitivity_report,
    load_small_number_config,
)


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _calculated_row(
    *,
    indicator_id: str,
    crosswalk_policy: str,
    published_label: str,
    numerator_metric: str,
    numerator_value: int,
    denominator_value: int,
    canonical_component_id: str,
) -> dict:
    return {
        "indicator_run_schema_version": 2,
        "indicator_id": indicator_id,
        "calculation_status": "calculated",
        "crosswalk_policy": crosswalk_policy,
        "entity_dimension": "nationality",
        "published_label": published_label,
        "geography_id": "jp:all",
        "geography_label": "日本全国",
        "year": 2024,
        "numerator_source_id": "S08",
        "numerator_metric": numerator_metric,
        "numerator_value": numerator_value,
        "numerator_context": {
            "population_scope": "all_foreign",
            "row_kind": "country",
        },
        "denominator_source_id": "S14_2024_12",
        "denominator_value": denominator_value,
        "canonical_component_ids": [canonical_component_id],
        "canonical_component_labels": [published_label],
    }


def _fixture(tmp_path: Path):
    indicator_root = tmp_path / "indicators"
    run_dir = indicator_root / "20260831_000000_indicators"
    records = [
        _calculated_row(
            indicator_id="x_cleared_cases_exact",
            crosswalk_policy="exact",
            published_label="無国籍",
            numerator_metric="cleared_cases",
            numerator_value=2,
            denominator_value=468,
            canonical_component_id="isa-nationality:07_000",
        ),
        _calculated_row(
            indicator_id="x_cleared_cases_as_published_mismatch",
            crosswalk_policy="as_published_mismatch",
            published_label="無国籍",
            numerator_metric="cleared_cases",
            numerator_value=2,
            denominator_value=468,
            canonical_component_id="isa-nationality:07_000",
        ),
        _calculated_row(
            indicator_id="x_cleared_persons_exact",
            crosswalk_policy="exact",
            published_label="無国籍",
            numerator_metric="cleared_persons",
            numerator_value=10,
            denominator_value=468,
            canonical_component_id="isa-nationality:07_000",
        ),
        _calculated_row(
            indicator_id="x_cleared_cases_iran",
            crosswalk_policy="exact",
            published_label="イラン",
            numerator_metric="cleared_cases",
            numerator_value=21,
            denominator_value=4399,
            canonical_component_id="isa-nationality:01_006",
        ),
        {
            **_calculated_row(
                indicator_id="x_refused",
                crosswalk_policy="exact",
                published_label="国籍不明",
                numerator_metric="cleared_cases",
                numerator_value=1,
                denominator_value=1,
                canonical_component_id="isa-nationality:unknown",
            ),
            "calculation_status": "refused",
            "denominator_value": None,
        },
    ]
    records_path = run_dir / "indicator_records.jsonl"
    csv_path = run_dir / "indicator_records.csv"
    summary_path = run_dir / "summary.json"
    _write_jsonl(records_path, records)
    csv_path.write_text("fixture\n", encoding="utf-8")
    _write_json(
        summary_path,
        {
            "indicator_run_schema_version": 2,
            "indicator_record_count": 5,
            "status_counts": {"calculated": 4, "refused": 1},
        },
    )
    latest_path = indicator_root / "latest.json"
    _write_json(
        latest_path,
        {
            "indicator_run_schema_version": 2,
            "run_relpath": run_dir.name,
            "summary_sha256": sha256_file(summary_path),
            "indicator_records_sha256": sha256_file(records_path),
            "indicator_records_csv_sha256": sha256_file(csv_path),
        },
    )
    config_path = tmp_path / "small_number_sensitivity.json"
    _write_json(
        config_path,
        {
            "schema_version": 1,
            "policy_status": "sensitivity_only",
            "comparison_operator": "strictly_less_than",
            "denominator_thresholds": [500, 5000],
            "numerator_thresholds": [5, 20],
        },
    )
    return {
        "indicator_latest_path": latest_path,
        "records_path": records_path,
        "config_path": config_path,
        "output_root": tmp_path / "sensitivity",
    }


def test_report_counts_records_and_deduplicated_observations(tmp_path: Path):
    fixture = _fixture(tmp_path)

    report = generate_small_number_sensitivity_report(
        indicator_latest_path=fixture["indicator_latest_path"],
        config_path=fixture["config_path"],
        output_root=fixture["output_root"],
        generated_at="2026-08-31T09:15:00+09:00",
    )

    summary = json.loads(report.summary_path.read_text(encoding="utf-8"))
    assert report.record_count == 6
    assert summary["policy_status"] == "sensitivity_only"
    assert summary["calculated_indicator_record_count"] == 4
    assert summary["refused_indicator_record_count"] == 1
    assert summary["threshold_summaries"] == {
        "denominator": [
            {
                "affected_indicator_record_count": 3,
                "threshold": 500,
                "unique_observation_count": 1,
            },
            {
                "affected_indicator_record_count": 4,
                "threshold": 5000,
                "unique_observation_count": 2,
            },
        ],
        "numerator": [
            {
                "affected_indicator_record_count": 2,
                "threshold": 5,
                "unique_observation_count": 1,
            },
            {
                "affected_indicator_record_count": 3,
                "threshold": 20,
                "unique_observation_count": 2,
            },
        ],
    }

    rows = [
        json.loads(line)
        for line in report.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    denominator_500 = [
        row
        for row in rows
        if row["threshold_kind"] == "denominator" and row["threshold"] == 500
    ]
    assert len(denominator_500) == 1
    assert denominator_500[0]["observed_value"] == 468
    assert denominator_500[0]["published_label"] == "無国籍"
    assert denominator_500[0]["affected_indicator_record_count"] == 3
    assert denominator_500[0]["indicator_ids"] == [
        "x_cleared_cases_as_published_mismatch",
        "x_cleared_cases_exact",
        "x_cleared_persons_exact",
    ]

    latest = json.loads(report.latest_path.read_text(encoding="utf-8"))
    assert latest["run_relpath"] == "20260831_091500_small_number_sensitivity"
    assert latest["sensitivity_records_sha256"] == sha256_file(report.jsonl_path)
    assert latest["sensitivity_records_csv_sha256"] == sha256_file(report.csv_path)
    assert latest["summary_sha256"] == sha256_file(report.summary_path)


def test_report_rejects_indicator_records_changed_after_latest(tmp_path: Path):
    fixture = _fixture(tmp_path)
    with fixture["records_path"].open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    with pytest.raises(IntegrityError, match="indicator_records"):
        generate_small_number_sensitivity_report(
            indicator_latest_path=fixture["indicator_latest_path"],
            config_path=fixture["config_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-31T09:16:00+09:00",
        )


def test_report_snapshots_indicator_latest_for_immutable_provenance(tmp_path: Path):
    fixture = _fixture(tmp_path)
    original_latest = json.loads(
        fixture["indicator_latest_path"].read_text(encoding="utf-8")
    )

    report = generate_small_number_sensitivity_report(
        indicator_latest_path=fixture["indicator_latest_path"],
        config_path=fixture["config_path"],
        output_root=fixture["output_root"],
        generated_at="2026-08-31T09:16:30+09:00",
    )

    manifest_path = report.output_dir / "indicator_input_manifest.json"
    summary = json.loads(report.summary_path.read_text(encoding="utf-8"))
    latest = json.loads(report.latest_path.read_text(encoding="utf-8"))
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == original_latest
    assert summary["indicator_input_manifest_relpath"] == manifest_path.name
    assert summary["indicator_input_manifest_sha256"] == sha256_file(manifest_path)
    assert latest["indicator_input_manifest_sha256"] == sha256_file(manifest_path)

    _write_json(
        fixture["indicator_latest_path"],
        {**original_latest, "run_relpath": "newer_indicator_run"},
    )
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == original_latest
    assert summary["indicator_input_manifest_sha256"] == sha256_file(manifest_path)


def test_config_rejects_nonincreasing_thresholds(tmp_path: Path):
    path = tmp_path / "invalid.json"
    _write_json(
        path,
        {
            "schema_version": 1,
            "policy_status": "sensitivity_only",
            "comparison_operator": "strictly_less_than",
            "denominator_thresholds": [1000, 500],
            "numerator_thresholds": [5, 20],
        },
    )

    with pytest.raises(SchemaError, match="strictly increasing"):
        load_small_number_config(path)


def test_cli_writes_machine_readable_result(tmp_path: Path, capsys):
    fixture = _fixture(tmp_path)

    exit_code = small_number_main(
        [
            "--indicator-latest",
            str(fixture["indicator_latest_path"]),
            "--config",
            str(fixture["config_path"]),
            "--output-root",
            str(fixture["output_root"]),
            "--generated-at",
            "2026-08-31T09:17:00+09:00",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["record_count"] == 6
    assert output["output_dir"].endswith(
        "20260831_091700_small_number_sensitivity"
    )
