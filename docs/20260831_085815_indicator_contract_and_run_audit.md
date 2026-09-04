# Indicator contract v2 / current production run audit

- Audit date: 2026-08-31 (Asia/Tokyo)
- Production run: `data/processed/_indicators/20260831_085815_indicators/`
- Status: **root processとfresh independent reviewerで検証済み。blocking / high / medium finding 0**
- Independent review: [20260831_090540_indicator_independent_review.md](./20260831_090540_indicator_independent_review.md)
- Publication name: `公表統計由来の参考比率` / `public-data-derived reference ratio`

## 結論

current same-year dataから、6つのconceptual case（X/Y/Z × cases/persons）を10個のpublication contractとして固定し、validated indicator data productを生成した。

- X/Yは国籍crosswalkについて`exact`と`as_published_mismatch`を別contractにしたため、各4 contract。
- Zは国籍aggregateで国籍crosswalkを使わないため、cases/personsの2 contract。
- 合計290 recordのうち250件を計算し、40件を理由付きで拒否した。
- Zは47都道府県 × cases/personsの94件をすべて計算した。
- `calculation_status=calculated`でも`statistical_compatibility=not_established`であり、officialまたは正確な`犯罪率`ではない。
- required processed inputは、実file、processed `run.json`、version-controlled contract pinのSHA-256三者一致を必須にした。

## Source pair / contract

| Case | Numerator | Denominator | Period | Publication contracts |
|---|---|---|---|---:|
| X cases/persons | S08 NPA 表130、`all_foreign`、国籍別・全国 | S14_2024_12 ISA T1、在留外国人 | 2024 annual flow ÷ 2024-12-31 stock | 4 |
| Y cases/persons | S09 NPA 表131、`visiting_foreign`、国籍別・全国 | S14_2024_12 ISA T1、在留外国人 | 2024 annual flow ÷ 2024-12-31 stock | 4 |
| Z cases/persons | S02 NPA 表13、刑法犯・特別法犯計、都道府県等別 | S14 ISA T1、居住都道府県別在留外国人 | 2025 annual flow ÷ 2025-12-31 stock | 2 |

contract schema v2は、source pair、metric、population scope、period、geography semantics、edition固有の期待numerator row数（S08=24、S09=25、S02=47）、crosswalk policy、mismatch flag、display metadata、およびrequired processed input hash pinを保持する。

canonical formulaは常に`numerator_value / denominator_value`である。`display_multiplier=1000`は暫定presentation choiceであり、`display_scale_status=provisional`としてunscaled quotientから分離した。UIの既定scaleは未決である。

## Output contract / provenance

各recordはraw numerator／denominator、unscaled quotient、display metadata、source ID、period／scope／geography context、canonical component、crosswalk status、mismatch flag、calculation／refusal status、UI caveatを同時に持つ。

run `summary.json`の`source_artifacts`からpublisher、official URL、source period/table、raw／processed path、retrieval time、revision、raw artifact SHA-256、normalized input SHA-256を追跡できる。`processed_input_pins`にも計算時に承認した5 input hashを埋め込んだ。

## Hard gates

1. contract schema v2と必須fieldを検証し、period endを厳密な`YYYY-MM-DD`として読む。
2. catalog inputは`processing_status=validated`に限定し、duplicate sourceを停止する。
3. required `normalized.jsonl`のSHA-256を、processed `run.json.normalized_sha256`とcontract `processed_input_pins`の両方へ照合する。三者の一つでも異なれば停止する。
4. numeratorのobserved population scopeと、Zのgeography semanticsがcontractと異なれば停止する。
5. editionごとの期待numerator row数24 / 25 / 47、duplicate cell、negative numerator、negative population cell、missing mappingを検証する。
6. numerator yearとdenominator year-endの暦年が一致しなければ停止する。
7. exact policyは`matched`、canonical component 1件、`targets_complete=true`をすべて満たすrowだけを計算する。
8. denominator componentがmissing / suppressed / non-positiveなら値を出さない。
9. Zはcanonical prefectureへ1対1対応する47 rowだけを対象にし、全国計、警察region、北海道方面等を含めない。
10. timestamp付きoutputを上書きせず、JSONL / CSV / summaryのSHA-256を`latest.json`でpinする。

normalized artifactのschema、duplicate、aggregate、anchor値は既存M2 quality gateで検証済みである。

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

refusalは`crosswalk_not_exact` 24 recordと`no_canonical_denominator_components` 16 recordである。exact laneでは`中国`、`韓国・朝鮮`、context別`その他`、`国籍不明`を計算しない。as-published laneでもcomponent不明の`その他`と`国籍不明`は計算しない。

as-published laneのNPA `中国`はISA `中国`＋`台湾`で単純除算するが、NPA注記の「香港等」まで確定できないため`canonical_target_incomplete`を付ける。`韓国・朝鮮`はISA `韓国`＋`（朝鮮）`を明示し、`nationality_grouping_mismatch`を付ける。これは推計・按分ではない。exact laneとas-published laneは代替viewであり、重複するexact categoryを相互に加算しない。

## Mismatch inventory

全290 rowに`annual_flow_vs_point_in_time_stock`が付く。Xは`all_foreign_vs_resident_population_mismatch`、Y/Zは`visitor_vs_resident_population_mismatch`、personsは`cleared_person_records_not_unique_risk_population`を持つ。Zはさらに`aggregate_nationality_numerator`、`police_reporting_area_unresolved`、`police_reporting_area_vs_registered_residence`を持つ。

Table 13の地理は引き続き`police_reporting_area_unresolved`である。都道府県名が一致しても、犯罪発生地、被疑者居住地、または単一の取扱地semanticへ読み替えない。

## Integrity evidence

| Artifact | SHA-256 |
|---|---|
| `summary.json` | `7d38eafbac38973cbc48ad803dde26c413fd8070232bef81459db4bcb6b6a7dd` |
| `indicator_records.jsonl` | `de5c6510f9089fab13ab2c3e87bbf52cacd1a06d54e0c7e8b93b4df0316ba699` |
| `indicator_records.csv` | `906ce56e3aaf715d06f45014e310e109f86e5f55525c88bf25accaac30fdc90e` |
| `config/indicator_contracts.json` | `4b49c2bce3d21c722aeaf99fb0d12ef580b0d40afbddeca0345f50f30369b8d6` |
| artifact catalog | `01684f9d0595089062239bcfa84a669396917dabc35b63034b43fb70c3aa09b7` |
| mapping latest | `71099547ce1b21be026a89260644027e496603a08e4f97d48473221d7455c998` |

`latest.json`の3 output hashと実fileは一致した。独立した再集計では、5 inputの実file／run manifest／contract pin不一致0、250 calculated rowのformula不一致0、atomic T1から再集計したdenominator不一致0、refused rowへの値残存0、Zのunique prefecture ID 47だった。T1 atomic totalはS14_2024_12が3,768,977、S14が4,125,395。S14の都道府県code 01–47は4,118,167、code 48の未定地は7,228であり、Z denominatorからcode 48を除外している。

過去runはimmutableな再生成可能artifactとして残すが、公開対象にしない。`20260831_001500`と`20260831_084201`はoutput schema v1、`20260831_084358`はprocessed input再照合前、`20260831_085216`はrun manifest再照合済みだが独立contract pin追加前である。current canonical outputは`20260831_085815`である。

## Test verification

- Indicator-focused: 13 test passed。
- Full suite: 76 test passed、skip 0。
- Branch計測を含むtotal coverage: 84.37%（required 80%をpass）。
- 新規failure testは、normalized inputとsibling run hashを同時に変えてもcontract pinとの差で停止することを確認した。
- fresh reviewer側でもindicator 13件、full suite 76件、coverage 84.37%、5 sourceの三者hash一致、290 / 250 / 40、Z 47地域を再確認し、先行Medium findingをclosedと判定した。

## 未決・次の判断

1. **UI既定scale**: per 1,000はprovisional。倍率は統計的不安定性を変えない。
2. **small denominator flag**: threshold未決。candidate thresholdを1,000人未満とした場合、current dataでは`無国籍`のdenominator 468が該当する（policy / metric重複を含む8 record）。
3. **interpretation note**: 地域差や国籍差を因果関係、個人risk、集団特性として説明しない常設文書が必要。
4. **UI policy**: exact laneとas-published laneのどちらをprimaryにするか未決。
5. **automation / history**: official catalog discovery、schedule、2015–latestのbinary-level backfillは未実装。
6. **public export**: `data/processed/_indicators/`はgenerated dataとしてgitignore対象。M4でGitHub用compact exportまたはCI build artifactの正本を決める。

Integrity上の残る境界はgovernanceである。contract pin自体を変更する主体をruntimeでは防げないため、新editionまたはnormalized representation変更時のpin更新はsource／parser／quality changeと一緒にreviewする。
