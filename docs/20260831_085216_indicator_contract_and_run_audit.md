# Indicator contract v2 / current production run audit

- Audit date: 2026-08-31 (Asia/Tokyo)
- Production run: `data/processed/_indicators/20260831_085216_indicators/`
- Status: **root processで検証済み。fresh independent review前**
- Publication name: `公表統計由来の参考比率` / `public-data-derived reference ratio`

## 結論

current same-year dataから、6つのconceptual numerator case（X/Y/Z × cases/persons）を10個のpublication contractとして固定し、最初のvalidated indicator data productを生成した。

- X/Yは国籍crosswalkについて`exact`と`as_published_mismatch`を別contractにしたため、各4 contract。
- Zは国籍aggregateで国籍crosswalkを使わないため、cases/personsの2 contract。
- 合計290 recordのうち250件を計算し、40件を理由付きで拒否した。
- Zは47都道府県 × cases/personsの94件をすべて計算した。
- すべてのrecordで、計算可否と統計的compatibilityを分離した。`calculation_status=calculated`でも`statistical_compatibility=not_established`であり、officialまたは正確な`犯罪率`ではない。

## Source pair / contract

| Case | Numerator | Denominator | Period | Publication contracts |
|---|---|---|---|---:|
| X cases/persons | S08 NPA 表130、`all_foreign`、国籍別・全国 | S14_2024_12 ISA T1、在留外国人 | 2024 annual flow ÷ 2024-12-31 stock | 4 |
| Y cases/persons | S09 NPA 表131、`visiting_foreign`、国籍別・全国 | S14_2024_12 ISA T1、在留外国人 | 2024 annual flow ÷ 2024-12-31 stock | 4 |
| Z cases/persons | S02 NPA 表13、刑法犯・特別法犯計、都道府県等別 | S14 ISA T1、居住都道府県別在留外国人 | 2025 annual flow ÷ 2025-12-31 stock | 2 |

contract schema v2は次を必須にする。

- `measure_kind=public_data_derived_reference_ratio`
- `canonical_formula=numerator_value / denominator_value`
- numerator / denominatorのsource ID、metric、population scope、period type、geography semantics
- source editionごとの`expected_numerator_row_count`（S08=24、S09=25、S02=47）
- `exact` / `as_published_mismatch` crosswalk policy
- raw quotientと分離したdisplay metadata
- 常時表示するmismatch flagsとUI caveat

`display_multiplier=1000`はDeep Researchで提案されたpresentation choiceを暫定採用したもので、data factではない。`display_scale_status=provisional`として保存し、canonical valueは無次元のquotientを維持する。UIの既定scaleは未決である。

## Output contract

計算済みrowは同一recordから次を追跡できる。

- raw `numerator_value` / `denominator_value`
- unscaled `quotient`
- `display_multiplier` / `display_value` / display unit
- numerator / denominator source IDとcontext
- canonical component ID / label
- `crosswalk_status` / `targets_complete`
- `mismatch_flags`
- `calculation_status`と`statistical_compatibility`
- UI caveat

source IDとartifactの対応表はrun `summary.json`の`source_artifacts`に埋め込んだ。publisher、official landing/download URL、source period/table、raw/processed path、retrieval time、revision、raw artifact SHA-256、normalized input SHA-256を含む。

## Hard gates

今回testで固定したindicator-layer gateは次のとおり。

1. contract schema v2と必須fieldを検証し、period endを厳密な`YYYY-MM-DD`として読む。
2. catalog inputは`processing_status=validated`に限定し、同一`source_id`の重複を停止する。各`normalized.jsonl`のSHA-256をprocessed `run.json.normalized_sha256`と再照合し、validation後の事後改変を停止する。
3. numeratorのobserved `population_scope`と、Zの`geography_semantics`がcontractと異なれば停止する。
4. editionごとの期待numerator row数が24 / 25 / 47から外れれば停止する。
5. numerator cellの重複、negative numerator、negative population cell、missing mappingを停止する。
6. numerator yearとdenominator year-endの暦年が一致しなければ停止する。
7. exact policyは`matched`、canonical component 1件、`targets_complete=true`をすべて満たすrowだけを計算する。
8. denominator componentがmissing / suppressed / non-positiveなら値を出さない。
9. Zはcanonical prefectureへ1対1対応する47 rowだけを対象にし、全国計、警察region、北海道方面等を含めない。
10. timestamp付きoutputを上書きせず、JSONL / CSV / summaryのSHA-256を`latest.json`でpinする。

normalized artifactのschema、duplicate、aggregate、anchor値は既存M2 quality gateで検証済みであり、indicator generatorはvalidated catalogだけを入力にする。

## Production result

| Indicator ID | Calculated | Refused |
|---|---:|---:|
| `x_cleared_cases_exact` | 18 | 6 |
| `x_cleared_cases_as_published_mismatch` | 20 | 4 |
| `x_cleared_persons_exact` | 18 | 6 |
| `x_cleared_persons_as_published_mismatch` | 20 | 4 |
| `y_cleared_cases_exact` | 19 | 6 |
| `y_cleared_cases_as_published_mismatch` | 21 | 4 |
| `y_cleared_persons_exact` | 19 | 6 |
| `y_cleared_persons_as_published_mismatch` | 21 | 4 |
| `z_cleared_cases_prefecture` | 47 | 0 |
| `z_cleared_persons_prefecture` | 47 | 0 |
| **Total** | **250** | **40** |

refusal理由は次の2種類だった。

- `crosswalk_not_exact`: 24 record。exact laneで`中国`、`韓国・朝鮮`、context別`その他`、`国籍不明`を計算しなかった。
- `no_canonical_denominator_components`: 16 record。as-published laneでもdenominator componentが公表区分から確定できない`その他`と`国籍不明`は計算しなかった。

as-published laneでは、NPA `中国`をISA `中国`＋`台湾`で単純除算したrowを`canonical_target_incomplete`付きで出力した。NPA注記の「香港等」までcomponent集合を確定できていないためである。`韓国・朝鮮`はISA `韓国`＋`（朝鮮）`のcomponentを明示し、`nationality_grouping_mismatch`付きで出力した。これは推計・按分ではなく、contractに明記した公表category間の単純除算である。

exact laneとas-published laneでは、exact categoryの値が意図的に重複する。両laneはcrosswalk policyを選ぶ代替viewであり、相互に加算しない。

## Mismatch inventory

全290 rowに`annual_flow_vs_point_in_time_stock`が付く。ほかの主要flagは次のとおり。

- X: `all_foreign_vs_resident_population_mismatch`
- Y/Z: `visitor_vs_resident_population_mismatch`
- persons: `cleared_person_records_not_unique_risk_population`
- Z: `aggregate_nationality_numerator`、`police_reporting_area_unresolved`、`police_reporting_area_vs_registered_residence`
- as-published composite: `nationality_grouping_mismatch`、必要時`canonical_target_incomplete`

Table 13の地理は引き続き`police_reporting_area_unresolved`である。都道府県名が一致しても、犯罪発生地、被疑者居住地、または単一の取扱地semanticへ読み替えない。

## Integrity evidence

| Artifact | SHA-256 |
|---|---|
| `summary.json` | `5c09e89de04d1c75af7281ba162333f38b3fa6674aef43476ad69e460a70ecd4` |
| `indicator_records.jsonl` | `de5c6510f9089fab13ab2c3e87bbf52cacd1a06d54e0c7e8b93b4df0316ba699` |
| `indicator_records.csv` | `906ce56e3aaf715d06f45014e310e109f86e5f55525c88bf25accaac30fdc90e` |
| `config/indicator_contracts.json` | `691ed8acf89d5673f86ee55445c8db8f02574d50dbae89f91eabbd03cfa7cf5d` |
| artifact catalog | `01684f9d0595089062239bcfa84a669396917dabc35b63034b43fb70c3aa09b7` |
| mapping latest | `71099547ce1b21be026a89260644027e496603a08e4f97d48473221d7455c998` |

`latest.json`の3 output hashと実fileは一致した。290 JSONL row、CSVはheader込み291 line。formula再計算不一致0、refused rowの値残存0、invalid exact calculation 0、Zのunique prefecture IDは47だった。

`20260831_084201_indicators`は新field追加後にoutput schema versionを旧`1`のまま生成したpre-fix runである。`20260831_084358_indicators`はschema v2だが、processed normalized inputをrun manifestのhashへ再照合するgateを追加する前のrunである。両方ともlatestではなく、processed-input integrity gateを通した本runがcurrent canonical outputである。旧runはtimestamp付きの再生成可能artifactとして残すが、公開対象にしない。

## Test verification

- Indicator-focused: 12 test passed。
- Full suite: 75 test passed、skip 0。
- Branch計測を含むtotal coverage: 84.36%（required 80%をpass）。
- 新規failure tests: invalid period、population-scope drift、duplicate numerator cell、missing prefecture、incomplete exact mapping、duplicate catalog source、processed input hash mismatch、negative population cell。

## 未決・次の判断

1. **UI既定scale**: per 1,000はprovisional。倍率は統計的不安定性を変えない。
2. **small denominator flag**: threshold未決。candidate thresholdを1,000人未満とした場合、current dataでは`無国籍`のdenominator 468が該当する（policy / metric重複を含む8 record）。threshold合意前なのでflagはまだ付けない。
3. **interpretation note**: 地域差や国籍差を因果関係、個人risk、集団特性として説明しない常設文書が必要。
4. **UI policy**: exact laneとas-published laneのどちらをprimaryにするか未決。
5. **automation / history**: official catalog discovery、schedule、2015–latestのbinary-level backfillは未実装。
6. **public export**: `data/processed/_indicators/`はgenerated dataとして現在gitignore対象。M4でGitHub用compact exportまたはCI build artifactの正本を決める。
