# AGENTS.md — nationality-crime-atlas

Codex 用の作業指示（この repo 固有の *確定ルール* だけ）。共通の作業流儀は `~/.codex/AGENTS.md`（笹川 universal preference）で auto-load 済み——ここでは繰り返さず、project 固有だけを書く。**200 行以下**を保つ。

## この project の地図
- overview → `README.md` / `README.ja.md`
- 科学的 through-line（背景→目的→マイルストーン→結果→成果）→ `docs/brief.md`（研究 project の場合）
- 工程・現在地 → `docs/workflow.md`
- 判断・経緯・失敗 → `logbook.md`（append-only）
- ユーザー持ち込み資料 → `inbox/`

## Commands
- build: `.venv/bin/python -m pip install --no-build-isolation -e '.[dev]'`
- test: `.venv/bin/python -m pytest --cov=nationality_crime_atlas --cov-report=term-missing`
- acquire one registered edition: `.venv/bin/nca-acquire --source-id S08`
- acquire all-resident context inputs: `.venv/bin/nca-acquire --source-id S15`, `.venv/bin/nca-acquire --source-id S16`
- recheck a registered remote edition: `.venv/bin/nca-acquire --source-id S08 --refresh`
- regenerate canonical dimension audit: `.venv/bin/nca-map-dimensions`
- regenerate all-resident regional context: `.venv/bin/nca-build-all-resident-context`
- regenerate nationality offense composition: `.venv/bin/nca-build-offense-composition`
- regenerate national clearance-share trend: `.venv/bin/nca-build-clearance-share-trend`
- regenerate compact dashboard export: `.venv/bin/nca-build-compact-export`
- regenerate small-number sensitivity audit: `.venv/bin/nca-audit-small-numbers`
- regenerate pinned map module: `cd web && npm run generate:map`
- frontend quality gate: `cd web && npm run test:coverage && npm run typecheck && npm run lint && npm run build`
- local visualization: `cd web && npm run dev`
- run / inspect full offline pipeline: `.venv/bin/nca-pipeline --help`
- inspect low-level CLIs: `.venv/bin/nca-snapshot --help`, `.venv/bin/nca-ingest --help`, `.venv/bin/nca-validate --help`

## Conventions / gotchas（この repo 固有）
- `config/sources.json` schema v2は`series`（共通定義）と`editions`（period、URL、publication/revision、pinned hash）を分離する。新公表年は既存editionを上書きせず追加する。
- `nca-acquire`はregistered HTTPS URLからtemporary fileへdownloadし、size・format・pinned SHA-256を通ったものだけをpipelineへ渡す。通常の再実行は既存validated editionをnetworkなしでreuseし、`--refresh`でも同一hashならsnapshotを増やさない。hash変更は新revisionとしてreviewするまで停止する。
- `data/raw/<series>/<edition>/<retrieved_timestamp>/`のofficial artifactとmanifestはimmutableとして扱い、上書きしない。
- `data/processed/<series>/<edition>/<retrieved_timestamp>/`は再生成可能なnormalized data。大容量なのでgitignoreし、compactな`data/processed/_catalog/artifacts.{jsonl,csv}`だけを公開可能にする。
- `config/dimension_mappings.json`はauthored crosswalk rule。各ruleをreview済み`source_ids`へscopeし、未reviewの新sourceではsilent fallbackせず停止する。`nca-map-dimensions`はvalidated catalog全体からtimestamp付き`data/processed/_mappings/`を生成する。raw label/contextを保持し、fuzzy match・推計・按分をしない。
- dimension mappingの`matched`はlabel/category対応だけを表し、numerator／denominatorの統計的compatibilityを保証しない。NPA `中国`・`韓国・朝鮮`、source region total、警察region／subregionを単一categoryへ潰さない。
- `config/indicator_contracts.json`の`processed_input_pins`はrequired `normalized.jsonl`の独立したreview boundary。実file／processed `run.json`／contract pinのSHA-256三者一致を必須とし、新editionまたはnormalized representation変更時だけsource／parser／quality changeと一緒にreviewして更新する。
- `config/all_resident_context_contracts.json`の`processed_input_pins`も独立したreview boundaryであり、S15／S16の実file／processed `run.json`／contract pinのSHA-256三者一致を必須とする。
- catalogに同じ`source_id`の複数revisionがある場合、all-resident generatorはcontractの`normalized_sha256` pinへexactly one一致するrevisionだけを選ぶ。0件または複数一致では停止し、latestらしさでsilentに選ばない。
- `config/small_number_sensitivity.json`はcandidate thresholdの分析用で`policy_status=sensitivity_only`。結果をofficial reliability standardやcanonical warning ruleへ自動昇格せず、denominatorとnumeratorを別軸でreviewする。各sensitivity runは参照時点のindicator pointerを`indicator_input_manifest.json`としてrun内へsnapshotし、そのhashをsummaryへ固定する。
- `nca-pipeline`はlocal artifactをsnapshot → parse → validateし、quality pass時だけ`data/processed/`へatomic promotionする。同一runの内容・profile・hashが変わった場合は上書きせず停止する。
- `retrieved_at`はtimezone付きISO-8601を必須とする。同一`source_id × retrieved_at`へ異なるartifactを置かない。
- `config/quality_profiles.json`は特定artifact versionのbaseline。新しい公表年では既存profileを上書きせず、新source/versionとして追加する。
- parserのschema assumptionを変更するときは、fixtureとfailure testを先に追加し、RED → GREENを確認する。
- source pairごとのproject-derived valueは`公表統計由来の参考比率`と呼び、official／正確な`犯罪率`と呼ばない。
- primary regional baselineは日本国籍ではなく、日本に居住する全住民とする。nationality-specific viewはsecondaryに分離し、集団の本質・因果・個人riskを示すlabelとして扱わない。
- S15表3とS16表144は全住民のdescriptive regional context用。S15の警察地理をoffender residenceへ読み替えず、S16の千人単位丸めを補正・隠蔽しない。
- all-resident calculated rowでは`annual_flow_vs_point_in_time_population`と`numerator_residency_scope_not_established`を必須とし、calendar-year crime flowと10月1日時点population stock、未確立のnumerator residency scopeをUIで常設表示する。
- `_all_resident_context`では全国＋47都道府県のみをcalculatedとし、警察region／subregion、日本国籍prefecture分子、個別nationality × prefecture分子はrefusalとして保持する。
- public compact exportはschema v2以降を使い、全rowに`indicator_id`／`context_id`を残す。source fileは同じbytesからparseとhashを行い、summaryとrecordsを照合し、public source metadataをwhitelistしてlocal absolute pathを含めない。
- `web/public/data/dashboard_export.json`はreview済みcompact exportのstatic publication copyであり、source-of-truthではない。手編集せず、更新時はcompact outputとのbyte identity／SHA-256、row count、private path非露出を検証する。
- all-resident UIのraw unit／labelはnumerator semanticsから決める。`cleared_persons`は`人`／`人員`、case metricは`件`／`件数`とし、metricに関係なく`件`へhardcodeしない。
- `web/assets/maps/deformed-japan-prefecture-map.svg`はpinned CC0 asset。generatorはchecked-in SHA-256不一致時にoutputを書かず停止し、47 code／labelとgenerated moduleのbyte identityをtestする。
- generated productのroot `latest.json`はsame-directory unique temporary fileへ書き、`flush`／`fsync`後にatomic `replace`する。fixed temporary filenameを使わない。
- national total − all-foreignの算術残差はdirectな日本国籍公表値と呼ばず、明示的なderived valueとしてreviewされるまでpublishしない。
- 全国検挙構成比は`外国人区分の全国検挙値 ÷ 日本人等を含む全国検挙総数`であり、人口当たりの犯罪率ではない。`all_foreign`と`visiting_foreign`を別scopeとして混同しない。`all_foreign − visiting_foreign`は算術残差であり、定着居住者だけ／普段から住む外国人／在留外国人と呼ばない。
- 公表されていない`個別国籍 × 都道府県`分子は推計・按分しない。
- NPA表13のgeography semanticsは未解決。`geography_semantics=police_reporting_area_unresolved`を、居住地や発生地へ読み替えない。
- current registryはverified direct URLの取得まで対応済み。official catalogから新editionを自動発見する処理とschedule実行は未実装。
