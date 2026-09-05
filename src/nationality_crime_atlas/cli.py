"""Command-line entrypoint for reproducible source ingestion."""

import argparse
import json
from dataclasses import asdict
from itertools import chain
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .npa_all_residents import (
    parse_npa_overall_prefecture_crime,
    parse_npa_prefecture_population,
    parse_statistics_bureau_intercensal_population,
    parse_statistics_bureau_japanese_population,
)
from .npa_nationality import parse_npa_nationality_totals
from .npa_prefecture import parse_npa_prefecture_table13
from .population import parse_population_t1
from .provenance import build_manifest


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--landing-url", required=True)
    parser.add_argument("--download-url", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-ingest")
    commands = parser.add_subparsers(dest="command", required=True)

    population = commands.add_parser("population-t1")
    _common_arguments(population)
    population.add_argument("--period-end")

    nationality = commands.add_parser("npa-nationality")
    _common_arguments(nationality)
    nationality.add_argument("--table-id", choices=("130", "131"), required=True)

    prefecture = commands.add_parser("npa-prefecture-table13")
    _common_arguments(prefecture)

    overall_prefecture = commands.add_parser("npa-overall-prefecture-crime")
    _common_arguments(overall_prefecture)

    prefecture_population = commands.add_parser("npa-prefecture-population")
    _common_arguments(prefecture_population)

    japanese_population = commands.add_parser(
        "statistics-bureau-japanese-population"
    )
    _common_arguments(japanese_population)

    intercensal_population = commands.add_parser(
        "statistics-bureau-intercensal-population"
    )
    _common_arguments(intercensal_population)
    return parser


def _write_jsonl(records: Iterable[object], output: Path) -> int:
    count = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            count += 1
    return count


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse one official artifact and write normalized JSONL plus a manifest."""

    arguments = _argument_parser().parse_args(argv)
    if arguments.command == "population-t1":
        records = parse_population_t1(
            arguments.input,
            source_id=arguments.source_id,
            period_end=arguments.period_end,
        )
    elif arguments.command == "npa-nationality":
        records = parse_npa_nationality_totals(
            arguments.input,
            table_id=arguments.table_id,
            source_id=arguments.source_id,
        )
    elif arguments.command == "npa-prefecture-table13":
        records = parse_npa_prefecture_table13(
            arguments.input,
            source_id=arguments.source_id,
        )
    elif arguments.command == "npa-overall-prefecture-crime":
        records = parse_npa_overall_prefecture_crime(
            arguments.input,
            source_id=arguments.source_id,
        )
    elif arguments.command == "npa-prefecture-population":
        records = parse_npa_prefecture_population(
            arguments.input,
            source_id=arguments.source_id,
        )
    elif arguments.command == "statistics-bureau-japanese-population":
        records = parse_statistics_bureau_japanese_population(
            arguments.input,
            source_id=arguments.source_id,
        )
    else:
        records = parse_statistics_bureau_intercensal_population(
            arguments.input,
            source_id=arguments.source_id,
        )

    record_iterator = iter(records)
    first_record = next(record_iterator, None)
    if first_record is None:
        records_to_write = ()
    else:
        records_to_write = chain((first_record,), record_iterator)
    record_count = _write_jsonl(records_to_write, arguments.output)
    period_end = getattr(arguments, "period_end", None)
    if period_end is None and first_record is not None:
        period_end = getattr(first_record, "period_end", None)
    manifest = build_manifest(
        arguments.input,
        source_id=arguments.source_id,
        landing_url=arguments.landing_url,
        download_url=arguments.download_url,
        retrieved_at=arguments.retrieved_at,
        period_end=period_end,
    )
    manifest["record_count"] = record_count
    arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
    arguments.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0
