# compact export audit

This note fixes the first M4 deliverable: a compact dashboard bundle that can be rebuilt from the current immutable products without reading `data/processed/*` directly from a future UI.

## Scope

Inputs:

- `data/processed/_indicators/latest.json`
- `data/processed/_all_resident_context/latest.json`

Implementation:

- `src/nationality_crime_atlas/compact_export.py`
- `src/nationality_crime_atlas/compact_export_cli.py`
- `tests/test_compact_export.py`

Current generated bundle:

- `output/compact_export/20260901_212000_compact_export/`

## What the bundle fixes

1. It resolves the mutable `latest.json` pointers immediately and embeds the exact pointer payload plus SHA-256 values in the export summary.
2. It normalizes repeated record metadata into `definitions.indicator_ids` and `definitions.context_ids`, leaving row-level fields only where variation actually exists.
3. It keeps the publication policy explicit: primary view is `all_resident_context`, secondary view is `nationality_indicators`, and project-derived values are not official crime rates.

## Current payload shape

- `dashboard_export.json`
  - `publication_policy`
  - `source_runs`
  - `definitions`
  - `records`
- `summary.json`
  - export hash
  - record counts
  - definition counts
  - resolved source-run manifests and hashes
- `latest.json`
  - immutable run pointer for the compact export itself

Current counts:

- `nationality_indicators`: 290 rows
- `all_resident_context`: 186 rows
- definition rows: 10 `indicator_id`, 3 `context_id`

## Verification

- RED: `tests/test_compact_export.py` failed before implementation because `compact_export` modules did not exist.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_compact_export.py`
- Full verification: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest --cov=nationality_crime_atlas --cov-report=term-missing`
  - `98 passed`
  - total coverage `84.24%`

## Remaining gap

The bundle is currently written under `output/compact_export/`, which is a generated local lane. The next M4 step is to connect this bundle to a GitHub-visible visualization artifact or CI publication path without weakening the immutable-source boundary.
