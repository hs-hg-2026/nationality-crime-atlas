# Data management and acquisition

この文書は、公式統計を「いつ・どこへ・何と対応付けて」収集するかのliving policyである。sourceの科学的なavailability・定義比較は [source availability audit](./20260830_085603_source_availability_audit.md)、工程の現在地は [workflow](./workflow.md) に分ける。

## 現状

2026-08-30のbaseline 5 editionに、2026-09-01にall-resident regional context用のS15／S16、2026-09-02に日本人人口用のS17を追加し、current 8 editionを公式HTTPS URLから正式収集した。すべてpinned SHA-256、parser、source-specific quality profileを通過し、artifact catalogでは`validated`である。

validated normalized dataからcanonical dimension mappingも再生成した。720 distinct mappingの内訳はmatched 674／ambiguous 38／unmatched 8である。これはlabel/category crosswalkであり、分子・分母の統計的compatibility判定ではない。current all-resident runは`data/processed/_all_resident_context/20260901_225500_all_resident_context/`、日本人を含む全国籍comparison runは`data/processed/_nationality_comparison/20260903_074525_nationality_comparison/`、犯罪類型構成runは`data/processed/_offense_composition/20260903_222026_offense_composition/`、compact-export schema v5は`output/compact_export/20260903_231549_compact_export/`である。local visualizationはcompact exportとbyte-identicalな`web/public/data/dashboard_export.json`を読み、両fileのSHA-256は`102e2f6d589675a4fb45eac239212ff3f160048f5c0479bea62416da67ecb002`で一致する。詳細は [all-resident baseline audit](./20260901_133313_all_resident_baseline_audit.md)、[all-resident / compact independent re-audit](./20260902_073831_all_resident_and_compact_independent_reaudit.md)、[日本人を含む全国籍比較・UI audit](./20260903_082238_japanese_nationality_comparison_and_ui_audit.md)を参照する。

| Edition | Official data | Coverage | Records | Quality |
|---|---|---|---:|---|
| `S08` | 警察庁 表130・外国人の国籍別検挙 | 2024 | 33 | pass |
| `S09` | 警察庁 表131・来日外国人の国籍別検挙 | 2024 | 30 | pass |
| `S02` | 警察庁/e-Stat 確定値 表13・都道府県等別aggregate | 2024/2025 | 360 | pass |
| `S14_2024_12` | 出入国在留管理庁/e-Stat 表1 | 2024-12-31 | 444,173 | pass |
| `S14` | 出入国在留管理庁/e-Stat 表1 | 2025-12-31 | 468,641 | pass |
| `S15` | 警察庁 表3・全体の都道府県等別刑法犯 | 2024 | 60 | pass |
| `S16` | 警察庁 表144・10月1日総人口 | 2024-10-01 | 48 | pass |
| `S17` | 総務省統計局 人口推計 表2・日本人人口 | 2024-10-01 | 48 | pass |

ここでいう警察dataは現時点では主に**警察庁**の全国統計であり、東京都の**警視庁**固有dataや47都道府県警websiteの収集はenrichment trackとして未着手である。

## 四つの対応表

| 問い | 正本 | 役割 |
|---|---|---|
| 何を収集する予定か | `config/sources.json` | authored registry。seriesとimmutable edition、URL、period、definition、publication/revision、expected format/hash |
| 実際に何を取得したか | `data/raw/**/manifest.json` | artifact単位のURL、取得日時、HTTP metadata、filename、byte size、magic-byte format、SHA-256 |
| 収集済みdataと出典の全体対応 | `data/processed/_catalog/artifacts.jsonl` / `.csv` | raw manifestとprocessed quality/runをjoinしたgenerated inventory |
| source dimensionをどう対応したか | `config/dimension_mappings.json` ＋ `data/processed/_mappings/**` | authored alias/composite ruleと、matched／ambiguous／unmatchedを持つgenerated crosswalk audit |

catalogはraw manifestから再生成できるcurrent indexであり、手作業でrowを追加しない。JSONLはmachine-readable、CSVは人間が確認しやすい表示用である。

## Data flow

    config/sources.json (series + edition + pinned hash)
                       │
                       ▼
              nca-acquire --source-id ID
                       │
              temporary HTTP download
                       │
          size / HTTPS / format / SHA-256 gate
                       │
                       ▼
    data/raw/<series>/<edition>/<retrieved_timestamp>/
       official artifact + immutable manifest.json
                       │
                parse + quality gate
                ┌──────┴──────┐
                ▼             ▼
              PASS           FAIL
                │             └─ processedへ昇格しない
                ▼
    data/processed/<series>/<edition>/<retrieved_timestamp>/
       normalized.jsonl + artifact.manifest.json
       quality.json + run.json
                │
                ▼
    data/processed/_catalog/artifacts.{jsonl,csv}
                │
                ├───────────────┐
                │               │
                │   config/dimension_mappings.json
                │               │
                └───────┬───────┘
                        ▼
               nca-map-dimensions
                │
                ▼
    data/processed/_mappings/<timestamp>_dimension_mapping/
       dimension_mappings.{jsonl,csv} + summary.json
                │
                ├───────────────┐
                │               │
                │   config/indicator_contracts.json
                │   config/all_resident_context_contracts.json
                │   config/nationality_comparison_contract.json
                │   config/offense_composition_contract.json
                │               │
                └───────┬───────┘
                        ▼
    data/processed/_indicators/<timestamp>_indicators/
    data/processed/_all_resident_context/<timestamp>_all_resident_context/
    data/processed/_nationality_comparison/<timestamp>_nationality_comparison/
    data/processed/_offense_composition/<timestamp>_offense_composition/
                       │
                       ▼
              nca-build-compact-export
                └─ S15内の認知件数−検挙件数を同年差分として導出
                       │
                       ▼
    output/compact_export/<timestamp>_compact_export/
       public dashboard JSON + summary + atomic latest
                       │
              reviewed exact-byte copy
                       ▼
    web/public/data/dashboard_export.json
                       │
                       ▼
    local visualization + verified GitHub Pages artifact pipeline

download中のpartial fileはsystem temporary directoryに置き、成功前に`data/raw`へ残さない。`data/raw`を直接download stagingとして使わない。

## 収集タイミング

1. **新series追加時**: 一次資料でpublisher、definition、license、dimensionsを確認し、seriesを登録する。
2. **新edition公表時**: period、stable ID、landing/direct URL、publication/revision、formatを確認する。binaryを取得してSHA-256とquality profileをpinし、既存editionを上書きせず追加する。
3. **initial/current baseline**: mapping・indicator計算より前に収集・quality passさせる。2026-08-30 baseline、2026-09-01 all-resident extension、2026-09-02 Japanese-population extensionは完了。
4. **定期確認**: ISA populationはJune/December snapshot、NPAはannual publicationを監視対象とする。exact schedule/discovery jobはM5で実装する。
5. **schema/hash変更時**: publicationを停止し、新revisionかsource-side driftかをreviewする。既存validated outputを上書きしない。

通常の`nca-acquire --source-id ID`は既存validated editionをnetworkなしでreuseする。remoteを明示的に再確認する場合だけ`--refresh`を付ける。同じhashなら既存snapshotをreuseし、異なるhashなら停止する。

## Storage and Git

- `data/raw/`: official binaryのlocal immutable snapshot。外部公表元が正本であり、容量も大きいためgitignore。
- `data/processed/`: code + raw + configから再生成できるdata product。current baselineは約372 MBのためgitignore。
- `data/processed/_catalog/`: compactな出典対応表。raw/processed本体を公開しなくてもprovenanceを辿れるため、Git追跡可能な例外とする。
- `data/processed/_mappings/`: normalized data＋authored ruleから再生成するtimestamp付きcrosswalk audit。生成物なのでgitignoreし、固定ルールと解釈上の結論は`config/dimension_mappings.json`と`docs/20260830_214058_dimension_mapping_audit.md`で保持する。
- `data/processed/_indicators/`: nationality-oriented reference-ratio product。生成物なのでgitignoreし、contractと解釈ルールは`config/indicator_contracts.json`と`docs/`へ残す。
- `data/processed/_all_resident_context/`: S15 / S16から作る全住民regional-context product。生成物なのでgitignoreし、contractとrefusal boundaryは`config/all_resident_context_contracts.json`、initial audit、[independent re-audit](./20260902_073831_all_resident_and_compact_independent_reaudit.md)で保持する。
- `data/processed/_nationality_comparison/`: S08 / S14_2024_12 / S15 / S17から作る、日本人を含む全国籍comparison product。生成物なのでgitignoreし、contractとresidual boundaryは`config/nationality_comparison_contract.json`とaudit文書で保持する。
- `data/processed/_offense_composition/`: S08 / S15から作る26 category × 6犯罪類型の構成product。日本は各類型でもS15全人値−S08全外国人値の残差であり、source rowとpinを保持する。生成物なのでgitignoreし、正本は`config/offense_composition_contract.json`、code、validated inputである。
- `output/compact_export/`: indicator latest、all-resident latest、nationality-comparison latest、offense-composition latestから再生成するdashboard向けbundle。schema v5はS15内の認知−検挙同年差分も明示的なderived contextとして追加する。同一bytesをparse／hashし、source summaryとrecordsを照合し、public source metadataだけをwhitelistしてlocal pathを除外し、atomic `latest.json`を公開する。generated local laneであり、正本はcode + input + configである。
- `web/public/data/dashboard_export.json`: reviewed compact exportのcurrent static publication copy。手編集は禁止し、`npm run sync:data`でschema／hash／private-pathを検証して同期し、`npm run verify:data`でCI再検証する。`dashboard_export.manifest.json`がexpected hashとrecord countを固定する。
- `references/`: 定義・細則・利用上の注意等、解析入力ではなく読むための外部資料。
- `inbox/`: user-provided material。公式dataのdownload先にはしない。

project rootはGit repositoryで、publication remoteは`https://github.com/hs-hg-2026/nationality-crime-atlas.git`とする。latest commitのpush／deployment完了はGitHub側のbranchとActionsで別途確認する。

## Verification boundary

current 8 editionはbinary・manifest・qualityまで検証済み。mapping runはcatalog/config hash、raw label/context、status、target、reasonを保持し、generated output hashも検証済み。ただしmappingの`matched`は名称・category対応だけで、indicatorやall-resident contextのpopulation scope・period・geography semanticsの整合性を保証しない。S15 / S16はall-resident descriptive context用であり、個別nationality × prefecture分子を補うものではない。S17は日本人人口を提供するが、日本国籍prefecture犯罪分子を提供しない。全国日本人分子と類型別内訳だけをS15 − S08のresidualとして明示的に導出し、都道府県へは按分しない。認知−検挙の同年差分はS15の同年・同地理だけをpairするが、事件cohortはlinkできないため未解決値とはしない。current compact bundleはsource/output hash closure、row-to-definition linkage、public metadata sanitizationまで検証済みで、local UI copyもbyte identityとprivate path非露出を再確認した。2015–2025のhistorical candidate matrixは代表年のみ一次確認済みで、各年をregistryへ追加する際にbinary hashとschema fingerprintを個別確認する。
