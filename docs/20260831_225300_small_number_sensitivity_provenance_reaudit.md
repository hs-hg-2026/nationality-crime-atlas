# Small-number sensitivity provenance re-audit

- Audit date: 2026-08-31 (Asia/Tokyo)
- Indicator input: `data/processed/_indicators/20260831_215800_indicators/`
- Sensitivity output: `data/processed/_indicator_sensitivity/20260831_225300_small_number_sensitivity/`
- Status: **verified after provenance remediation**

## Outcome

The threshold results are unchanged, but the run is now self-contained with respect to the mutable indicator pointer. A fresh review found that the first sensitivity run recorded the path and SHA-256 of `data/processed/_indicators/latest.json`, while that pointer could later move to another indicator run. The analyzer now writes the exact resolved pointer payload to `indicator_input_manifest.json` inside every immutable sensitivity run and binds its SHA-256 in both `summary.json` and the sensitivity `latest.json`.

The new run resolves the current canonical indicator output `20260831_215800_indicators`. Its 12 threshold summaries and 119 sensitivity records are identical to the initial run based on `20260831_085815_indicators`, because the later indicator run added warning metadata without changing any numerator, denominator, quotient, context, or calculation status.

## Verified sensitivity results

| Candidate rule | Affected indicator records | Unique observations |
|---|---:|---:|
| denominator `<100` | 0 | 0 |
| denominator `<500` | 8 | 1 |
| denominator `<1,000` | 8 | 1 |
| denominator `<2,000` | 8 | 1 |
| denominator `<5,000` | 16 | 2 |
| denominator `<10,000` | 42 | 9 |
| denominator `<50,000` | 146 | 40 |
| numerator `<1` | 2 | 1 |
| numerator `<5` | 6 | 3 |
| numerator `<10` | 11 | 6 |
| numerator `<20` | 20 | 12 |
| numerator `<50` | 64 | 43 |

The approved project heuristic remains:

- `small_denominator_base`: `denominator_value < 1,000`
- `sparse_numerator_count`: `numerator_value < 20`
- no suppression; show the raw numerator and denominator
- exclude flagged rows from default rankings and top/bottom callouts, while retaining filter access

This is a project-side UI and interpretation guard, not an official crime-statistics reliability threshold. The evidence boundary and rationale remain in the [initial sensitivity audit](./20260831_205122_small_number_sensitivity_audit.md). The primary evidence includes [MHLW small-area statistics guidance](https://www.mhlw.go.jp/toukei/saikin/hw/jinkou/tokusyu/hoken04/1.html), [NCHS presentation standards](https://wonder.cdc.gov/controller/pdf/presentation-standards-mortality-2024.pdf), [CDC analysis guidance](https://www.cdc.gov/asthma/data-analysis-guidance/ucd-data.htm), and [ONS reliability guidance](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/measuringandreportingreliabilityoflabourforcesurveyandannualpopulationsurveyestimates). These sources establish relevant practices in other statistical contexts; they do not establish an official threshold for this crime-statistics project.

## Integrity evidence

- indicator input manifest SHA-256: `ec5b44f2a2856dfed16946e9e27115f3286c39af002ae8a8745be00e6098e64b`
- indicator JSONL SHA-256: `b0c352488852ff820f62339616563220ba62a575e0891899d6cb4c977d6f5c9c`
- indicator CSV SHA-256: `e346b242afe05abaaf9047e7f135a22135a5b91dc992b84dee683c5cfcf586ee`
- indicator summary SHA-256: `9e9f440f81c207ca6f769800b6f3d577dbfac110ac23be2725086463ea017dd8`
- sensitivity config SHA-256: `12c49a60030820173af1876673c74850d9daf0087f1aa4ba95c0b319ac08787b`
- sensitivity JSONL SHA-256: `bc97f2c0c162b96641722b67b807c952d58b59e74c077a5e60c01fc69840397f`
- sensitivity CSV SHA-256: `493b4278f1d3b7b09af6ffb3e67d4e1a1ed13b2025cba351b70341f28e2c2b7e`
- sensitivity summary SHA-256: `b39be434bb4d47c7cbe639910da7bbf2ffd5961d901864a0d96408c5accc7adc`

Independent checks performed after generation:

- the embedded input manifest is byte-identical to the indicator pointer resolved at generation time;
- all output hashes match their manifests;
- old and new sensitivity threshold summaries are equal;
- removing the five warning-policy fields from the new indicator records makes all 290 rows exactly equal to the preceding canonical run;
- recomputing strict `<1,000` and `<20` predicates gives 8 and 20 flagged records, with union 20; stored-flag mismatches, refused-row flags, and ranking-hint mismatches are all zero.

## TDD and verification

- RED: the new regression test failed with `FileNotFoundError` because no immutable input manifest existed.
- GREEN: the analyzer writes and hashes `indicator_input_manifest.json`; all 5 focused small-number tests pass.
- Full suite: 82 passed, 0 skipped.
- Branch-measured total coverage: 84.33%.
- Post-fix fresh review: the original Medium finding is closed; no remaining correctness, provenance, or documentation findings were identified in the reviewed scope.

## Remaining boundary

The sensitivity config remains `policy_status=sensitivity_only`; running `nca-audit-small-numbers` cannot alter or approve the canonical warning policy. The canonical policy is versioned separately in `config/indicator_contracts.json` and documented in the [warning-policy audit](./20260831_215800_indicator_warning_policy_audit.md) and [interpretation note](./interpretation_note.md).
