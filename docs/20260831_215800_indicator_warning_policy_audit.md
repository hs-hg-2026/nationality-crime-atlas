# Indicator warning-policy audit

- Audit date: 2026-08-31 (Asia/Tokyo)
- Generated run: `data/processed/_indicators/20260831_215800_indicators/`
- Status: **approved project warning heuristic applied**
- Interpretation note: [interpretation_note.md](./interpretation_note.md)

## Outcome

The canonical indicator output now carries an approved, versioned non-suppressing warning heuristic:

- `small_number_warning_policy_version = 1`
- `small_number_warning_policy_status = approved_project_heuristic`
- `small_denominator_base`: `denominator_value < 1,000`
- `sparse_numerator_count`: `numerator_value < 20`
- `default_ranking_behavior = exclude_flagged`

This is not an official crime-statistics reliability standard. It is a project-side UI and interpretation guard for public-data-derived reference ratios.

## Verified counts

- Indicator records: 290
- Calculated: 250
- Refused: 40
- `small_denominator_base`: 8 calculated records
- `sparse_numerator_count`: 20 calculated records
- `either_warning`: 20 calculated records
- `default_ranking_excluded`: 20 calculated records

Representative verified rows:

- `x_cleared_cases_exact` / `無国籍`: numerator 4, denominator 468, warnings = both
- `x_cleared_cases_exact` / `イラン`: numerator 79, denominator 4,399, warnings = none
- `z_cleared_persons_prefecture` / `秋田県`: numerator 18, denominator 6,333, warnings = `sparse_numerator_count`

## Contract / output guarantees

- The warning policy is loaded from `config/indicator_contracts.json`, not from the sensitivity-only config.
- Generation stops if the warning policy drifts across contracts.
- Warning flags are added only to `calculated` rows; refused rows keep `small_number_warning_flags = []`.
- The heuristic does not suppress values or change `calculation_status`.
- `default_ranking_excluded` is a machine-readable UI hint and does not remove rows from the output.

## Reproducibility

- command: `.venv/bin/nca-build-indicators --generated-at 2026-08-31T21:58:00+09:00`
- contracts SHA-256: `bf855e3a91113bf9a9a74d08eb50b9570105b7a3f05a429ca2334781f28f4ef7`
- catalog SHA-256: `01684f9d0595089062239bcfa84a669396917dabc35b63034b43fb70c3aa09b7`
- indicator JSONL SHA-256: `b0c352488852ff820f62339616563220ba62a575e0891899d6cb4c977d6f5c9c`
- indicator CSV SHA-256: `e346b242afe05abaaf9047e7f135a22135a5b91dc992b84dee683c5cfcf586ee`
- summary SHA-256: `9e9f440f81c207ca6f769800b6f3d577dbfac110ac23be2725086463ea017dd8`

## Verification

- RED: new indicator tests failed because the warning-policy fields and contract metadata were absent.
- GREEN: focused indicator tests passed after implementation, including contract drift rejection and refused-row behavior.
- Full suite: 81 passed, 0 skipped
- Coverage: 84.32%
