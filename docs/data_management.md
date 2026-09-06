# Data management and acquisition

この文書は、公式統計を「いつ・どこへ・何と対応付けて」収集するかのliving policyである。sourceの科学的なavailability・定義比較は [source availability audit](./20260830_085603_source_availability_audit.md)、工程の現在地は [workflow](./workflow.md) に分ける。

## 現状

2026-08-30のbaseline 5 editionに、all-resident regional context用のS15／S16、日本人人口用のS17、さらに2020–2024年の警察庁詳細表と2015–2025年の人口系列を追加した。2026-09-06現在は9 series／34 immutable editionを公式HTTPS URLから正式収集し、すべてpinned SHA-256、parser、source-specific quality profileを通過してartifact catalogで`validated`となっている。

validated normalized dataからcanonical dimension mappingも再生成した。latest mappingは1,452 row（matched 1,270／ambiguous 142／unmatched 40）である。これはlabel/category crosswalkであり、分子・分母の統計的compatibility判定ではない。current all-resident runは`data/processed/_all_resident_context/20260901_225500_all_resident_context/`、日本人を含む全国籍comparison runは`data/processed/_nationality_comparison/20260903_074525_nationality_comparison/`、犯罪類型構成runは`data/processed/_offense_composition/20260903_222026_offense_composition/`、全国検挙構成比runは`data/processed/_clearance_share_trend/20260906_081400_clearance_share_trend/`、compact-export schema v7は`output/compact_export/20260906_081500_compact_export/`である。local visualizationはcompact exportとbyte-identicalな`web/public/data/dashboard_export.json`を読み、両fileのSHA-256は`38421caea476ba64c8ce38ecb1855eec5422db35cad4779b1fa66d6b972cd80f`で一致する。詳細は [all-resident baseline audit](./20260901_133313_all_resident_baseline_audit.md)、[all-resident / compact independent re-audit](./20260902_073831_all_resident_and_compact_independent_reaudit.md)、[日本人を含む全国籍比較・UI audit](./20260903_082238_japanese_nationality_comparison_and_ui_audit.md)、[時系列source inventory](./20260905_154001_time_series_source_inventory.md)を参照する。

以下の表はcurrent UIを直接構成する8 editionである。このほかhistorical panel用に`S08_2020`–`S08_2023`、`S09_2020`–`S09_2023`、`S15_2020`–`S15_2023`、`S17_2021`–`S17_2023`、`S18`、`S19_2016`–`S19_2025`の26 editionを保持する。editionと出典の完全な対応は`config/sources.json`と`data/processed/_catalog/artifacts.{jsonl,csv}`を正本とする。

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
                │   config/clearance_share_trend_contract.json
                │               │
                └───────┬───────┘
                        ▼
    data/processed/_indicators/<timestamp>_indicators/
    data/processed/_all_resident_context/<timestamp>_all_resident_context/
    data/processed/_nationality_comparison/<timestamp>_nationality_comparison/
    data/processed/_offense_composition/<timestamp>_offense_composition/
    data/processed/_clearance_share_trend/<timestamp>_clearance_share_trend/
                       │
                       ▼
              nca-build-compact-export
                ├─ S15内の認知件数−検挙件数を同年差分として導出
                └─ S08−S09を外国人区分の算術差分として保持
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
3. **initial/current baseline**: mapping・indicator計算より前に収集・quality passさせる。2026-08-30 baseline、2026-09-01 all-resident extension、2026-09-02 Japanese-population extension、2026-09-05 historical extensionは完了。
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
- `data/processed/_clearance_share_trend/`: S08の外国人全体、S09の来日外国人、S15の日本人等を含む全国総数から、2015–2024年の検挙件数／人員の構成比を作る。`S08−S09`はdirect公表値や居住者categoryではなく算術差分として保持し、scope label、source component、必須warningを`config/clearance_share_trend_contract.json`とcodeで固定する。
- `output/compact_export/`: indicator latest、all-resident latest、nationality-comparison latest、offense-composition latest、clearance-share latestから再生成するdashboard向けbundle。schema v7はS15内の認知−検挙同年差分と、全国検挙構成比60 rowを収録する。同一bytesをparse／hashし、source summaryとrecordsを照合し、clearance-shareのscope／source／算式／warningを再検証する。public source metadataだけをwhitelistしてlocal pathを除外し、atomic `latest.json`を公開する。generated local laneであり、正本はcode + input + configである。
- `web/public/data/dashboard_export.json`: reviewed compact exportのcurrent static publication copy。手編集は禁止し、`npm run sync:data`でschema／hash／private-pathを検証して同期し、`npm run verify:data`でCI再検証する。`dashboard_export.manifest.json`がexpected hashとrecord countを固定する。
- `references/`: 定義・細則・利用上の注意等、解析入力ではなく読むための外部資料。
- `inbox/`: user-provided material。公式dataのdownload先にはしない。

project rootはGit repositoryで、publication remoteは`https://github.com/hs-hg-2026/nationality-crime-atlas.git`とする。latest commitのpush／deployment完了はGitHub側のbranchとActionsで別途確認する。

## Verification boundary

current 34 editionはbinary・manifest・qualityまで検証済み。mapping runはcatalog/config hash、raw label/context、status、target、reasonを保持し、generated output hashも検証済み。ただしmappingの`matched`は名称・category対応だけで、indicatorやall-resident contextのpopulation scope・period・geography semanticsの整合性を保証しない。S15 / S16はall-resident descriptive context用であり、個別nationality × prefecture分子を補うものではない。S17は日本人人口を提供するが、日本国籍prefecture犯罪分子を提供しない。全国日本人分子と類型別内訳だけをS15 − S08のresidualとして明示的に導出し、都道府県へは按分しない。認知−検挙の同年差分はS15の同年・同地理だけをpairするが、事件cohortはlinkできないため未解決値とはしない。S08 − S09の差分も、定着居住者だけ・普段から住む外国人・在留外国人人口とは読み替えない。current compact bundleはsource/output hash closure、row-to-definition linkage、clearance-shareのscope／S08・S09・S15 binding／source component／必須warning／安全な解釈文言、public metadata sanitizationまで検証済みで、local UI copyもbyte identityとprivate path非露出を再確認した。2020–2024年の詳細panelは取得済みeditionをつなぐ次工程であり、年ごとのdefinition／schema差を確認してから公開する。
