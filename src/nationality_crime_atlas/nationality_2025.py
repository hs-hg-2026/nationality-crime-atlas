"""A separately pinned 2025 product; never replace the full 2024 composition."""

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from .errors import SchemaError
from .offense_composition import _cluster_order, _select_source_input
from .nationality_2025_csv import GROUPS, COUNTRIES


METRICS = ("cleared_cases", "cleared_persons")
SCOPES = ("all_foreign", "visiting_foreign")
WARNING_LABELS = {
    "annual_flow_vs_population_stock": "1年間の検挙と時点人口の割り算です。犯罪を行う確率ではありません。",
    "residency_scope_mismatch": "検挙対象には分母の在留外国人数に含まれない人が含まれ得ます。",
    "visiting_scope_vs_all_resident_foreign_population": "来日外国人の検挙を在留外国人全体の人口で割っています。対象範囲は一致しません。",
    "china_category_scope_mismatch": "中国の分子は台湾・香港等を除外しますが、在留人口の中国は香港を内数に含みます。",
    "korea_population_aggregation": "韓国・朝鮮の人口は公表人口の韓国＋朝鮮の合計です。対象区分の厳密な一致は保証しません。",
    "japanese_residual_reference": "日本は全国総数−外国人全体の算術残差による参考値で、直接公表された日本国籍値ではありません。",
    "japanese_original_population_unknown_excluded": "日本の分母は2025年10月1日の国勢調査原数値。不詳2,105,452人は除外しています。2024年の人口推計とは資料・定義が異なります。",
    "different_population_reference_dates": "日本の人口は10月1日、外国人の人口は12月31日で基準日が異なります。",
}
REASON_LABELS = {
    "numerator_not_published": "この資料に対応する分子の掲載なし（ゼロではありません）",
    "population_not_available": "対応する人口分母を取得できないため未算出",
    "japan_not_in_visiting_scope": "日本は来日外国人の対象外。全国−来日外国人では他の外国人が残るため算出しません。",
}


def _one(rows, **where):
    selected = [row for row in rows if all(row.get(key) == value for key, value in where.items())]
    if len(selected) != 1:
        raise SchemaError("Expected exactly one cell for %r, found %d" % (where, len(selected)))
    return selected[0]


def _component(row, metric, *, role="published", person_offset=0):
    column = row.get("source_column", row.get("source_cases_column"))
    if metric == "cleared_persons":
        column = row.get("source_persons_column", column)
    value = row.get(metric, row.get("value"))
    return {"source_id": row["source_id"], "source_table": row["source_table"],
            "sheet": row["source_sheet"], "row": row["source_row"] + person_offset,
            "column": column, "value": value, "role": role}


def derive_supplement(inputs, contract=None):
    """Derive explicit arithmetic and preserve absent counts as null, never zero."""
    if contract is None:
        contract = json.loads(Path("config/nationality_2025_contract.json").read_text())
    comparison = []
    for metric in METRICS:
        for scope in SCOPES:
            for entity in contract["entities"]:
                label = entity["label"]
                warnings = ["annual_flow_vs_population_stock", "different_population_reference_dates"]
                numerator_components, denominator_components = [], []
                numerator = denominator = None
                reason = derivation = None
                if label == "日本":
                    population = _one(inputs["S27"], geography="日本", nationality_code="2", year=2025)
                    denominator = population["population"]
                    denominator_components = [_component(population, "population")]
                    warnings += ["japanese_residual_reference", "japanese_original_population_unknown_excluded"]
                    if scope == "all_foreign":
                        minuend = _one(inputs["S21"], population_scope="all_persons", year=2025)
                        subtrahend = _one(inputs["S21"], population_scope="all_foreign", year=2025)
                        offset = 3 if metric == "cleared_persons" else 0
                        numerator_components = [_component(minuend, metric, role="minuend", person_offset=offset), _component(subtrahend, metric, role="subtrahend", person_offset=offset)]
                        numerator = minuend[metric] - subtrahend[metric]
                        if numerator < 0:
                            raise SchemaError("Japanese residual must be non-negative")
                        derivation = "national_total_minus_all_foreign"
                    else:
                        reason = "japan_not_in_visiting_scope"
                else:
                    warnings += ["residency_scope_mismatch"]
                    if scope == "visiting_foreign":
                        warnings.append("visiting_scope_vs_all_resident_foreign_population")
                    if label == "中国":
                        warnings.append("china_category_scope_mismatch")
                    if label == "韓国・朝鮮":
                        warnings.append("korea_population_aggregation")
                    countries = entity["population_components"]
                    populations = [row for row in inputs["S19_2025"] if row.get("nationality") in countries and row.get("row_kind") == "country_or_area" and row.get("period_end") == "2025-12-31"]
                    if countries and len(populations) == len(countries) and len({r["nationality"] for r in populations}) == len(countries):
                        denominator = sum(row["population"] for row in populations)
                        denominator_components = [_component(row, "population") for row in populations]
                    selected = [row for row in inputs["S22"] if row["nationality"] == entity["npa_label"] and row["metric"] == metric and row["population_scope"] == scope and row["year"] == 2025]
                    if selected:
                        row = _one(selected)
                        numerator = row["value"]
                        numerator_components = [_component(row, metric)]
                    else:
                        reason = "numerator_not_published"
                    if numerator is not None and (denominator is None or denominator <= 0):
                        reason = "population_not_available"
                comparison.append({"label": label, "year": 2025, "scope": scope, "metric": metric,
                    "numerator": numerator, "denominator": denominator,
                    "value": numerator / denominator * 1000 if reason is None else None,
                    "status": "calculated" if reason is None else "refused", "reason": reason,
                    "japanese_reference": label == "日本", "derivation": derivation,
                    "warnings": warnings, "numerator_components": numerator_components,
                    "denominator_components": denominator_components})
    composition = []
    orders = {}
    for metric in METRICS:
        vectors = []
        for country_index, country in enumerate(COUNTRIES):
            label = country or "来日外国人総数"
            records = [row for row in inputs["S30"] if row["year"] == 2025 and row["nationality"] == country]
            total = _one(records, offense_id="criminal_code_total")[metric]
            cells = []
            for _, offense_id, _, _ in GROUPS[1:]:
                row = _one(records, offense_id=offense_id)
                count = row[metric]
                if total <= 0:
                    raise SchemaError("Composition total must be positive")
                cells.append({"category_id": offense_id, "count": count, "share": count / total * 100,
                              "source": _component(row, metric, person_offset=1 if metric == "cleared_persons" else 0)})
            if sum(cell["count"] for cell in cells) != total:
                raise SchemaError("Composition does not reconcile")
            if country is None and total != _one(inputs["S21"], year=2025, population_scope="visiting_foreign")[metric]:
                raise SchemaError("CSV aggregate differs from S21 independent total")
            composition.append({"label": label, "metric": metric, "scope": "visiting_foreign", "total": total,
                                "status": "calculated", "reason": None, "cells": cells})
            if country is not None:
                vectors.append((label, country_index, [cell["share"] for cell in cells]))
        orders[metric] = list(_cluster_order(vectors))
        composition.append({"label": "日本", "metric": metric, "scope": "visiting_foreign", "total": None,
                            "status": "refused", "reason": "japan_not_in_visiting_scope",
                            "cells": [{"category_id": offense_id, "count": None, "share": None, "source": None} for _, offense_id, _, _ in GROUPS[1:]]})
    return {"schema_version": 1, "year": 2025, "scale": 1000,
            "definitions": {"entities": [r["label"] for r in contract["entities"]],
                            "categories": [{"id": offense_id, "label": label} for _, offense_id, label, _ in GROUPS[1:]],
                            "warning_labels": WARNING_LABELS, "reason_labels": REASON_LABELS,
                            "notes": contract["notes"], "clustering": "Jensen-Shannon distance / average linkage; five countries only"},
            "comparison": comparison, "composition": composition, "cluster_orders": orders}


def build_supplement(root=Path("."), contract_path=None):
    """Require independent raw/run/normalized pins before any calculation."""
    root = Path(root)
    path = Path(contract_path) if contract_path else root / "config/nationality_2025_contract.json"
    contract_bytes = path.read_bytes()
    contract = json.loads(contract_bytes)
    if contract.get("schema_version") != 1 or contract.get("year") != 2025:
        raise SchemaError("Unsupported supplement contract")
    catalog = [json.loads(line) for line in (root / "data/processed/_catalog/artifacts.jsonl").read_text().splitlines()]
    inputs, sources = {}, {}
    for source_id, pin in contract["input_pins"].items():
        source = _select_source_input(catalog_rows=catalog, source_id=source_id,
            artifact_pin=pin["artifact_sha256"], processed_pin=pin["normalized_sha256"],
            raw_root=root / "data/raw", processed_root=root / "data/processed")
        inputs[source_id] = [json.loads(line) for line in source.normalized_path.read_text().splitlines()]
        public_fields = ("publisher", "dataset", "source_table", "landing_url", "download_url", "sha256", "retrieved_at", "revision")
        sources[source_id] = {key: source.catalog_row[key] for key in public_fields}
        sources[source_id]["normalized_sha256"] = source.normalized_sha256
    product = derive_supplement(inputs, contract)
    product["sources"] = sources
    product["contract_sha256"] = hashlib.sha256(contract_bytes).hexdigest()
    return product


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)
    root = arguments.root
    product = build_supplement(root)
    content = (json.dumps(product, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    directory = root / "output/nationality_2025" / (timestamp + "_" + digest[:12])
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "nationality_2025.json").write_bytes(content)
    pointer = {"schema_version": 1, "sha256": digest, "product_path": str((directory / "nationality_2025.json").relative_to(root)), "contract_sha256": product["contract_sha256"], "comparison_count": len(product["comparison"]), "composition_count": len(product["composition"])}
    pointer_dir = root / "output/nationality_2025"
    with tempfile.NamedTemporaryFile(dir=pointer_dir, prefix=".latest-", delete=False, mode="w", encoding="utf-8") as handle:
        temporary = Path(handle.name)
        json.dump(pointer, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, pointer_dir / "latest.json")
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps(pointer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
