# all-resident regional-context product audit

Date: 2026-09-01
Status: verified against the local generated product and official pinned inputs

## Scope

This audit covers the new `all_resident_regional_context` product built from:

- `S15`: NPA Table 3, all-person criminal-code counts by published geography
- `S16`: NPA Table 144, October 1 total population by prefecture
- latest reviewed geography mapping: `data/processed/_mappings/20260901_133220_dimension_mapping/`

Generated product:

- `data/processed/_all_resident_context/20260901_153100_all_resident_context/`

## Verified facts

- `regional_context_records.jsonl` contains `186` rows: `144 calculated`, `42 refused`.
- Each of the three metrics has `48 calculated` rows: `1 national + 47 prefectures`.
- Each metric also has `14 refused` rows: `12 published police-region/subregion rows without an exact total-population denominator`, plus `2 unsupported request-scope rows`.
- `summary.json` records `numerator_difference = 0` for all three metrics, confirming that the 47 prefecture numerators sum to the national numerator published in Table 3.
- `summary.json` records `denominator_difference = -1000` for all three metrics, preserving the published Table 144 rounding gap where the prefecture sum is 1,000 persons above the national total.
- The product carries machine-readable refusals for:
  - `japanese_prefecture_numerator_unpublished`
  - `individual_nationality_prefecture_numerator_unpublished`
  - `geography_not_exact_prefecture_or_national`

## Example checks

- `all_resident_recognized_cases`:
  - Tokyo: `94,752 / 14,178,000 = 668.3030` per 100,000 residents
  - Saitama: `51,667 / 7,332,000 = 704.6781` per 100,000 residents
  - This confirms the user-facing point that absolute counts and population-normalized context can reverse the ordering.
- `all_resident_cleared_cases`:
  - Tokyo: `33,961 / 14,178,000 = 239.5331`
  - Saitama: `16,691 / 7,332,000 = 227.6459`
- `all_resident_cleared_persons`:
  - Tokyo: `23,731 / 14,178,000 = 167.3790`
  - Saitama: `10,054 / 7,332,000 = 137.1249`

## Interpretation boundary

- These values are `公表統計由来の参考比率`, not official or exact crime rates.
- Prefecture rows still retain `police_reporting_area_unresolved` and `police_reporting_area_vs_population_estimate_prefecture`.
- The product does not invent Japanese-nationality prefecture numerators or individual-nationality-by-prefecture numerators.

## Verification notes

- Verified by generating the product locally with:
  - `.venv/bin/nca-build-all-resident-context --generated-at 2026-09-01T15:31:00+09:00`
- Verified against:
  - `data/processed/_all_resident_context/20260901_153100_all_resident_context/summary.json`
  - `data/processed/_all_resident_context/20260901_153100_all_resident_context/regional_context_records.jsonl`
  - `data/processed/npa-all-persons-prefecture-crime/S15/20260901_133201_s15/normalized.jsonl`
  - `data/processed/npa-total-population-prefecture/S16/20260901_133212_s16/normalized.jsonl`
