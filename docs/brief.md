# nationality-crime-atlas — brief (living / 叩き台)

進行中 project を育てる高速ドラフト＝成果・物語の lens。ここでは生データそのものを管理せず、背景・目的・判断・解釈をまとめる。取得data、immutable snapshot、processed、artifact catalogの保管方式は [data management and acquisition](./data_management.md) に固定した。背景はsurveyで更新し、目的は微修正可、milestoneは適宜組み替える。

## 背景 (Background)

全国・都道府県別・地域別に、どの国籍の人がどれくらい在住し、犯罪統計上の件数・人員がどれくらいなのかを、人口当たりの比率とともに見たい。しかし、国籍別人口と犯罪統計を同じ地理単位・期間・定義で結び、情報を誰が公表していて、どれが信頼できるかまで明示した可視化は、十分に見つけやすい形では提供されていないように見える。

この取り組みの背景には、国籍labelだけが定量的な集計や公正な比較なしに流通し、`何々の国籍だからxxxだ`という集団へのレッテル貼りや、真実に結びつかない印象操作へ使われることを避けたいという問題意識がある。日本に居住するすべての人を対象として数字を正しく集め、入手後も比較可能性と限界を示して公正に可視化し、事実ベースの対策につなげる。

特に、単に「犯罪件数」とまとめず、少なくとも次を区別する必要がある。

- `認知件数`: 警察が犯罪として把握した事件数
- `検挙件数`: 検挙した事件数
- `検挙人員`: 検挙された人数
- `認知件数−検挙件数`: 同じ年の公表flow同士の機械的差分。当年の検挙には前年以前の認知事件が含まれ得るため、strictな`未解決件数`／`未解決率`とはしない
- 犯罪類型構成: 検挙人員／検挙件数を6つの刑法犯区分へ分けたcategory内構成。人口当たりの犯罪量や危険度ではない
- 人口の分母: primary regional contextは日本人と外国人を含む日本の`総人口`。secondaryな全国nationality comparisonは国籍等別の対応人口を使い、日本国籍も欠落させず同じ表示軸に含める
- 国別区分: 国籍、出生国、在留資格のどれを指すかは要確定

`inbox/` には2026-08-30に、Claude Opus 5版とChatGPT 5.6 sol版のDeep Research結果が持ち込まれた。2本を既存auditと比較し、load-bearing claimだけを官庁の一次page・文書および取得済みbinaryで再確認した。実装材料は、現行binaryのSHA-256まで一致したChatGPT版を主に採用し、Claude版の地理・format等の過剰な断定は採用しない。全国一次資料のURL、提供粒度、主な定義、取得方法は代表年と現行dataで検証済みだが、全年度binaryと47都道府県警websiteの全件auditは追加調査に残す。詳細は [source availability audit](./20260830_085603_source_availability_audit.md) と [Deep Research比較・採否・実装影響](./20260830_183123_deep_research_comparison.md) を参照。

## 目的 (Objective)

信頼できる情報源を検証し、全国・都道府県別・地域別の国籍別在留人口と犯罪統計を継続的に収集・更新する仕組みを作る。その上で、件数と、利用可能な公表統計を単純に割った場合の参考比率をGitHub上で可視化する。参考比率はsource pairごとに別indicatorとし、分子・分母・算式・出典・不一致を毎回表示する。projectが導出した値をofficialまたは正確な`犯罪率`とは呼ばない。

目的に含める具体要件:

1. 公表主体と一次資料を特定し、信頼性・coverage・定義・更新頻度を記録する。
2. 国籍 × 都道府県（または入手可能な地域単位）× 時点／期間について、取得できるdimensionをsource別に保持し、存在しないjoint dimensionは推計しない。
3. raw countと、公表統計由来の参考比率を併記する。参考比率ごとにnumerator source、denominator source、算式、scale、期間・地理・母集団のmismatch flagを示す。
4. 定期取得・更新できるpipelineを作り、変更や欠損を検知する。
5. GitHubで閲覧可能な可視化を提供する。
6. primary viewは全住民の地域contextとし、nationality-specific viewは出典・非比較可能性を示すsecondary viewとして分離する。

## マイルストーン / 現在地

### M0. MVP publication policyを固定する — **完了**

M1のauditと2026-08-30のuser decisionにより、完全に一致した分子・分母の取得をproject goalやmilestoneにしない。正確なcrime rateの公的整備は国・政治側の課題として切り分け、このprojectは、世の中に表示された公的dataから再現可能に導いた一つの参考指標を提示する。

MVP gate decisions:

- [x] `認知件数` / `検挙件数` / `検挙人員`を一つに統合せず、numerator caseごとに別indicator IDを与える。
- [x] `在留外国人` / `総在留外国人`等もdenominator caseごとに分け、source definitionを保持する。
- [x] 分子・分母が完全一致しなくても単純除算は許容する。ただし`公表統計由来の参考比率`と明記する。
- [x] indicatorごとに分子・分母・算式・scale・出典・期間・地理・母集団・mismatch flagを表示する。
- [x] project導出値をofficialまたは正確な`犯罪率`とは呼ばない。
- [x] 存在しない`個別国籍 × 都道府県`分子を推計・按分しない。
- [x] 日本に居住する全住民の地域contextをprimary baselineにする。そのうえでsecondaryな全国籍比較には日本国籍も含め、normativeな基準ではなく観測値の1 categoryとして同軸表示する。
- [x] 警察庁照会や都道府県警auditをdata enrichment trackとし、MVPのblockerにしない。

M2/M4で決めればよいnon-blocking design choices:

- [x] canonical dataでは無次元の`numerator / denominator`を保持し、人口1,000人当たり／10万人当たり等の倍率はdisplay metadataとして分離する。
- [x] UIのdefault scaleは全住民regional contextを人口10万人当たり、nationality indicatorを人口1,000人当たりとし、各contractのdisplay metadataから表示する。
- [x] 初期表示は全住民の`刑法犯認知件数`を人口10万人当たりで示すprimary regional viewとし、nationality viewはsecondaryに置く。
- [ ] 都道府県内地域をpopulation-only optional viewとして含める範囲。

### M1. 情報源のinventoryと信頼性audit — **完了**

- [x] 公表主体、一次資料URL、統計名、表番号、定義、coverage、更新頻度、改訂履歴、format、licenseをinventory化した。
- [x] 警察庁、e-Stat、出入国在留管理庁、既存研究・二次実装候補を実査した。
- [x] `国籍 × 都道府県 × 指標 × 期間`のavailability matrixを作成した。
- [x] 二次記事や集計サイトは一次資料へ遡れるかを確認し、ground truthには使わない整理を行った。
- [x] 公表されていない組み合わせを明示し、推計で埋めない方針を確定した。

成果物:

- [source availability audit](./20260830_085603_source_availability_audit.md)
- [raw research trace](../agent_logs/20260830_085603_source_audit/research_trace.md)

M1の要点:

- `国籍・地域 × 都道府県` の在留人口は取得可能。
- 全国の `国籍 × 罪種 × 検挙件数／検挙人員` は取得可能。
- 都道府県の犯罪統計は全体件数、または `来日外国人` aggregate までは取得可能。
- 2024年は警察庁表3のall-person criminal-code countsと表144の10月1日総人口を47都道府県で接続でき、nationality-neutralなregional contextを作れる。
- routine official source の `国籍 × 都道府県 × 検挙件数／検挙人員` は確認できなかった。
- `個別国籍 × 都道府県`の値は作れないが、取得できるsource pairについてはraw countと明示的な参考比率を作れる。

### M2. 取得・正規化pipelineのcurrent-edition baseline — **完了**

- [x] S14 population表1、S08/S09 national nationality crime、S02表13 prefecture aggregate、S15表3 all-person crime、S16表144 total population、S17日本人人口表2をtest-firstで実装した。
- [x] source ID、landing/download URL、取得日時、対象期間、byte size、file format、SHA-256をartifact manifestとして保持する。
- [x] registry/manifestにpublication/revision fieldを実装し、official metadataで確認できた日時を保存する。確認できないS08/S09のpublication timeは推測せず`null`とする。
- [x] 国籍、都道府県／police region、時間、欠損・秘匿、metric scope、source rowをsource-normalized recordとして保持する。
- [x] source間の国籍・地域code対応表とcanonical dimensionを実装し、`matched / ambiguous / unmatched`をraw label・context付きで生成する。mappingはlabel/category crosswalkに限定し、indicator compatibilityとは分離する。
- [x] artifactを`series × edition × timestamp`のimmutable `data/raw/` snapshotへpromoteする。同一editionの通常再実行はnetworkなしでreuseし、`--refresh`でも同一hashならsnapshotを増やさず、変更時は停止する。
- [x] snapshot → parse → quality validationをatomicに実行し、pass時だけ`data/processed/`へpromoteするoffline pipelineを実装する。
- [x] registryにpinしたofficial HTTPS direct URLからの安全なdownloadと、current 8 editionのformal production runを実装する。
- [x] raw manifestとprocessed quality/runをjoinしたartifact catalog（JSONL/CSV）を生成する。
- [ ] official catalogから新公表editionを自動発見するdiscoveryとschedule実行を実装する（M5 lifecycle trackへ移管。current MVP blockerではない）。
- [x] user-provided Deep Research 2本を比較し、現行binary identity、代表年の表番号・format transition、definition caveat、same-year pairingを一次資料でtriageした。
- [x] fixtureを使ったschema、型、error、source registry、snapshot、pipeline、CLI／manifest testを実装した。
- [x] current 8 artifactについてexpected row count、重複、合計、enum、distinct category数、anchor値、artifact hashをversioned profileで検証する。
- [ ] 新しい公表年を既存baselineと比較するyear-over-year schema/category drift運用を実装する（M5／historical backfill trackへ移管）。

実装箇所:

- population: `parse_population_t1` in [population.py](../src/nationality_crime_atlas/population.py)
- national nationality crime: `parse_npa_nationality_totals` in [npa_nationality.py](../src/nationality_crime_atlas/npa_nationality.py)
- prefecture aggregate: `parse_npa_prefecture_table13` in [npa_prefecture.py](../src/nationality_crime_atlas/npa_prefecture.py)
- all-resident regional inputs: `parse_npa_overall_prefecture_crime` / `parse_npa_prefecture_population` in [npa_all_residents.py](../src/nationality_crime_atlas/npa_all_residents.py)
- normalized records: [models.py](../src/nationality_crime_atlas/models.py)
- SHA-256／format detection／manifest: [provenance.py](../src/nationality_crime_atlas/provenance.py)
- source registry: [sources.json](../config/sources.json) and [registry.py](../src/nationality_crime_atlas/registry.py)
- HTTPS acquisition: [acquisition.py](../src/nationality_crime_atlas/acquisition.py) and [acquisition_cli.py](../src/nationality_crime_atlas/acquisition_cli.py)
- generated artifact inventory: [catalog.py](../src/nationality_crime_atlas/catalog.py) and [artifacts.csv](../data/processed/_catalog/artifacts.csv)
- authored crosswalk rules: [dimension_mappings.json](../config/dimension_mappings.json)
- canonical mapping engine／CLI: [dimensions.py](../src/nationality_crime_atlas/dimensions.py) and [dimension_cli.py](../src/nationality_crime_atlas/dimension_cli.py)
- mapping audit: [20260830_214058_dimension_mapping_audit.md](./20260830_214058_dimension_mapping_audit.md)
- immutable raw snapshot: [snapshot.py](../src/nationality_crime_atlas/snapshot.py) and [snapshot_cli.py](../src/nationality_crime_atlas/snapshot_cli.py)
- versioned quality baseline: [quality_profiles.json](../config/quality_profiles.json)
- streaming quality gate: [quality.py](../src/nationality_crime_atlas/quality.py) and [quality_cli.py](../src/nationality_crime_atlas/quality_cli.py)
- atomic offline orchestration: [pipeline.py](../src/nationality_crime_atlas/pipeline.py) and [pipeline_cli.py](../src/nationality_crime_atlas/pipeline_cli.py)
- CLI: [cli.py](../src/nationality_crime_atlas/cli.py)
- test suite: [tests](../tests)

2026-08-30 verification:

- 63 testが成功、branch計測を有効にしたtotal coverage 85.71%、skip 0。
- ISA 2025-12 表1をstream parse: 468,641 record、`value`合計4,125,395、suppressed 0、period endはsheet名から`2025-12-31`と判定。
- ISA 2024-12 表1を公式URLから取得してstream parse: 444,173 record、`value`合計3,768,977、suppressed 0、period end `2024-12-31`、SHA-256 `c523f699fed40f1bc7d2a975199c0669918e374c408a7423ce510c60500b3fb4`。
- NPA 2024 表130: 33 record。中国は検挙件数4,891、検挙人員3,522。
- NPA 2024 表131: 30 record。中国は検挙件数3,131、検挙人員2,211。
- NPA 2025確定値 表13 legacy XLS: current/prior year × 3 offense scopeを含む360 record。geographyは`police_reporting_area_unresolved`として保持。
- parserとは独立にmagic byteでXLS／XLSXを判定し、実fileのSHA-256を記録した。
- S14 20,690,146-byte XLSXと、`.xlsx`名だが実体がlegacy XLSのS02をimmutable snapshotし、元fileとsnapshotのSHA-256一致、同一runのidempotent reuseを確認した。
- 2026-08-30時点の5 editionをregistered official URLから正式収集し、S14 468,641、S14_2024_12 444,173、S08 33、S09 30、S02 360 recordがすべてduplicate 0／quality error 0でpassした。
- artifact catalogは5 rowを持ち、全rowが`processing_status=validated`。S08では通常再実行とremote `--refresh`の両方が既存snapshotを`reused=True`で再利用し、raw manifest数が増えないことを実地確認した。
- canonical mappingは913,237 normalized rowから612 distinct dimension rowを生成し、matched 578／ambiguous 26／unmatched 8。47都道府県は全件matched、NPAの`中国`・`韓国・朝鮮`、5 source region total、7警察region、5北海道方面はambiguous、context別`その他`と`国籍不明`はunmatchedとして保持した。
- Deep Research結果から2015–2025のcandidate `statInfId` matrixを得た。2015/2019/2020/2024の全国表、2015/2025の都道府県表、2015/2021/2024/2025の人口表は代表確認済みだが、全年度binary fingerprintは未検証である。
- same-year pairを強制する。次のX/Yは2024年表130/131 × 2024年末T1、Zは2025年表13 × 2025年末T1とする。取得済み2025年末T1を2024年X/Yへ直接割り当てない。
- 2026-09-01にS15表3（60 record）とS16表144（48 record）をformal ingestionした。全47都道府県labelは一致し、S15のprefecture sumはnational anchorへ完全一致、S16はofficialな千人単位丸めによりprefecture sumがnationalより1,000人多い。
- canonical mappingを7 source／913,345 input rowへ更新し、720 mapping（matched 674／ambiguous 38／unmatched 8）を生成した。

### M3. 参考比率の定義・計算・quality review — **完了**

- [x] numerator case × denominator caseごとにindicator registryを作り、6 conceptual caseを10 publication contractとして別ID・別display nameへ展開する。
- [x] `exact crosswalk indicator`と`as-published mismatch indicator`を分ける。後者はraw label、denominator構成、mismatch flagを必須とし、fuzzy match・推計・按分はしない。
- [x] canonical layerではraw numerator、raw denominator、無次元のquotientを保持し、表示倍率を`display_scale_status=provisional`のmetadataとして適用する。
- [x] hard gate（欠損・非数値、分母0以下、period不明、schema不明、duplicate、Zの不正地理）とsoft flag（population scope、flow/stock、geography semantics、nationality grouping）を実装する。
- [x] 検挙人員に旅行者等の非居住者が含まれる場合など、在留人口との不一致をmismatch flagと説明文で明示する。
- [x] denominator／numerator thresholdのsensitivity analyzerを実装し、record数と重複除外後のobservation数を別々に比較する。
- [x] 小さい人口・少数countによる参考比率の不安定性をflagする基準を決める。
- [x] raw numerator、raw denominator、derived ratio、算式、欠損、`statistical_compatibility=not_established`を同時に出力する。
- [x] 地域差を因果関係や個人属性の説明として解釈しないための注記を作る。
- [x] S15 / S16をpinした`all_resident_regional_context` data productを作る。
- [x] S08 / S15をpinし、日本を残差参考値として含む26 category × 6区分のoffense-composition data productを作る。
- [x] S15の同年・同公表地理の認知件数と検挙件数をpairし、未解決cohortではない符号付き差分と割合をcompact exportで導出する。
- [x] S08 / S09 / S15の2015–2024年全国合計をpinし、検挙件数／検挙人員について、外国人全体／来日外国人／`外国人全体 − 来日外国人`の算術残差が、日本人等を含む全国検挙総数に占める構成比を別scopeで導出する。残差は在留外国人または普段から住む外国人とは呼ばない。

実装・検証結果:

- contract: [indicator_contracts.json](../config/indicator_contracts.json)
- generator / CLI: [indicators.py](../src/nationality_crime_atlas/indicators.py), [indicator_cli.py](../src/nationality_crime_atlas/indicator_cli.py)
- latest local output pointers: `data/processed/_indicators/latest.json`, `data/processed/_all_resident_context/latest.json`, `data/processed/_nationality_comparison/latest.json`, `data/processed/_offense_composition/latest.json`（generated／gitignore対象）
- latest compact dashboard export: `output/compact_export/20260906_081500_compact_export/`（schema v7、generated local bundle）
- audit: [20260831_085815_indicator_contract_and_run_audit.md](./20260831_085815_indicator_contract_and_run_audit.md)
- independent review: [20260831_090540_indicator_independent_review.md](./20260831_090540_indicator_independent_review.md)
- sensitivity config / generator: [small_number_sensitivity.json](../config/small_number_sensitivity.json), [small_numbers.py](../src/nationality_crime_atlas/small_numbers.py), [small_number_cli.py](../src/nationality_crime_atlas/small_number_cli.py)
- sensitivity audit: [20260831_205122_small_number_sensitivity_audit.md](./20260831_205122_small_number_sensitivity_audit.md)
- sensitivity provenance re-audit: [20260831_225300_small_number_sensitivity_provenance_reaudit.md](./20260831_225300_small_number_sensitivity_provenance_reaudit.md)
- applied warning-policy audit: [20260831_215800_indicator_warning_policy_audit.md](./20260831_215800_indicator_warning_policy_audit.md)
- all-resident / compact independent re-audit: [20260902_073831_all_resident_and_compact_independent_reaudit.md](./20260902_073831_all_resident_and_compact_independent_reaudit.md)
- interpretation note: [interpretation_note.md](./interpretation_note.md)
- 290 recordのうち250 calculated／40 refused。X/Yは2024 annual flow × 2024-12-31 stock、Zは2025 annual flow × 2025-12-31 stock。Zは47都道府県×2 metricの94件を計算した。
- formula再計算不一致0、atomic T1からのdenominator再集計不一致0、refused rowの値残存0。processed inputは実file／run manifest／version-controlled contract pinのSHA-256三者一致を必須とし、negative population cellも停止する。new catalog／mappingで再生成した`20260901_133239_indicators`はprevious canonical indicator JSONLとbyte-identical。current full suiteは106 test、skip 0、branch計測total coverage 84.07%。
- candidate denominator thresholdは`<500`／`<1,000`／`<2,000`で同じ`無国籍`468人（8 record）のみ、`<5,000`で`イラン`4,399人が追加される。candidate numerator `<20`は12 unique observation／20 record。dual warning案のunionは20 / 250 calculated record。
- official guidanceとlocal sensitivityから、`denominator <1,000`を`small_denominator_base`、`numerator <20`を`sparse_numerator_count`として別flagにするnon-suppressing policyを実装した。supplementary indicator productは従来の`default_ranking_behavior=exclude_flagged`を保持する一方、current全国籍比較はuser decisionにより`include_all_with_warnings`とし、値を隠さずwarningを同時表示する。いずれもofficial reliability standardではない。
- fresh independent reviewerはblocking／high／medium finding 0で、processed inputとsibling manifestのcoordinated edit gapがclosedしたことを確認した。contract pin変更そのものは新edition／parser／quality changeと一緒にreviewするgovernance boundaryとする。
- `all_resident_context_contracts.json`、`all_resident_context.py`、`nca-build-all-resident-context`を追加し、S15 / S16からcurrent `20260901_225500_all_resident_context`を生成した。186 recordのうち144 calculated／42 refusedで、認知件数／検挙件数／検挙人員それぞれに全国＋47都道府県を計算した。全calculated rowはannual flowと10月1日時点population stockの差、およびnumerator residency scope未確立を明示する。警察region／subregion 12 rowと、日本国籍prefecture分子・個別国籍 × 都道府県分子の非公表はmachine-readable refusalとして同じrunに残した。summaryでは3 metricすべてでnumerator difference 0、denominator difference -1,000を固定した。東京の認知件数はabsolute countで埼玉より多いが、全住民10万人当たりでは東京668.30、埼玉704.68で順序が逆転することを再確認した。
- offense-composition productは156 cell（26 category × 6 mutually exclusive区分）。日本の検挙人員totalは`191,826 − 10,464 = 181,362`、検挙件数totalは`287,273 − 18,861 = 268,412`で、各類型もS15 − S08のsource row付き残差として保持する。`凶悪犯`はofficial high-severity categoryだが、残る5区分をproject独自の`軽犯罪`とはしない。構成比clusterはJensen–Shannon distance（base 2）＋average linkageで、順位・危険度ではない。
- compact export schema v7は290 + 186 + 26 + 156のsource-product rowにdefinition IDを保持し、S15から62行の認知−検挙同年差分（60 calculated／2 refused）、S08 / S09 / S15から60行の全国検挙構成比を導出する。same-byte parse/hash、source summary reconciliation、8件のpublic source metadata、local path非公開、atomic latest publicationを固定した。26行の全国籍比較は22 calculated／4 refusedで、日本人の検挙人員を`191,826 − 10,464 = 181,362`、検挙件数を`287,273 − 18,861 = 268,412`、分母をS17の120,296,000人として残差・丸め・source date差を明示する。2024年の全国検挙構成比は、検挙件数が外国人全体6.57%／来日外国人4.67%／両者の差分1.90%、検挙人員が5.45%／3.32%／差分2.14%である。

### M4. GitHub上の可視化 — **進行中**

- [x] primary viewを全住民contextとする全国overviewと47都道府県mapを作る。
- [x] 全住民の3 indicatorに加え、secondaryな全国比較へ日本を含む全26 categoryを掲載する。
- [x] 全国籍比較は高い側／低い側の抜粋を廃止し、算出できる全categoryを参考比率の降順、算出不能を末尾に並べる横棒plotにする。日本は別色で示し、全件表にはcountと参考比率の両方を残す。
- [ ] historical detail editionをyear-normalized panelへ接続し、year filterを実装する。都道府県より細かい地域粒度はavailabilityに応じて別途判断する。
- [x] 分子・対象範囲を切り替え、分子・分母・参考比率・算式・source・mismatch noteを同じ画面から辿れるようにする。全国籍plotで重複していたcount／ratio表示切替は廃止する。
- [x] 欠損と「公表なし」を0と区別し、refused rowと理由を表示する。
- [x] gitignore対象のlocal generated productから、dashboard向けcompact exportを作る。
- [x] all-resident contextとcompact exportをfresh reviewerがread-onlyで再監査し、open finding 0を確認する。
- [x] compact bundleとbyte-identicalなstatic copyを読むlocal visualization MVPを実装し、frontend gateとlocal HTTPで検証する。
- [x] visualization MVPをfresh reviewerが監査し、検出したHigh／Medium findingを修正後にclosed、新規finding 0を確認する。
- [x] `output/compact_export/`をhash検証付きでchecked-in static bundleへ同期し、GitHub Pages workflowへ接続する。
- [x] 日本人を含むnew comparison productとUIをfresh reviewerが独立監査し、scoped finding 0を確認する。
- [x] 旧UIにあったnationality numerator selectorを復旧し、日本人を計算できないmetricでもrowを消さずrefusal表示する。
- [x] 日本を含む26 category × 6犯罪類型を、検挙人員／検挙件数、heatmap／100%積み上げ、公表順／階層cluster順で可視化する。
- [x] 認知−検挙の同年差分件数／割合を全住民regional contextへ追加し、strict未解決ではない注記、負値保持、認知0でのratio refusalを実装する。
- [x] 犯罪類型構成と認知−検挙同年差分をfresh reviewerが独立監査し、scope内open finding 0を確認する。
- [x] 一般読者向けに、サイトの目的、分かること／分からないこと、用語説明、ページ内導線、日本語READMEへのリンクを冒頭へ置き、画面上の英語混じりの内部用語を平易な日本語へ改める。
- [x] 2015–2024年について、外国人全体／来日外国人／両者の算術差分が日本人等を含む全国検挙総数に占める割合を、検挙件数／検挙人員のline chartと全件表で表示する。人口当たりの犯罪率ではなく、残差も在留外国人とは同義でないことを常設する。
- [ ] reviewed commitをpushし、GitHub Pagesのdeployed URLを実地確認する。

Local MVP実装・検証結果:

- app／data model: [web](../web), [dashboard.ts](../web/lib/dashboard.ts), [crime-atlas-dashboard.tsx](../web/components/crime-atlas-dashboard.tsx)
- map provenance／generator: [map asset README](../web/assets/maps/README.md), [generate-japan-map-data.mjs](../web/scripts/generate-japan-map-data.mjs)
- audits: [20260902_200948_visualization_mvp_audit.md](./20260902_200948_visualization_mvp_audit.md), [20260903_082238_japanese_nationality_comparison_and_ui_audit.md](./20260903_082238_japanese_nationality_comparison_and_ui_audit.md)
- input: `web/public/data/dashboard_export.json`はcurrent compact exportとbyte-identical。schema v7、SHA-256 `38421caea476ba64c8ce38ecb1855eec5422db35cad4779b1fa66d6b972cd80f`。
- primary view: 全住民、全国＋47都道府県、認知件数／検挙件数／検挙人員／認知−検挙同年差分、count／人口10万人当たりまたは同年差分率、東京・埼玉normalization、top-10 chart、deformed choropleth、source／warning／refusal panels。同年差分は全国450,406件／61.0572%、東京60,791件／64.1580%、埼玉34,976件／67.6950%で、いずれも未解決cohortとは表示しない。
- secondary view: 日本を含む刑法犯検挙人員／検挙件数比較と8つの公表外国人perspectiveをselectorで切り替える。compatibleな日本人分子がないviewでも日本rowをexplicit refusalとして残す。全categoryの参考比率を降順の横棒plotで表示し、日本を別色、算出不能を末尾に置く。全件表にはraw分子・分母・参考比率、source、残差、warning、refusal／mismatchを併記する。個別国籍 × 都道府県は推計しない。
- composition view: 日本を含む全26 categoryと6犯罪類型をheatmap／100%積み上げで表示し、検挙人員／検挙件数と公表順／階層cluster順を切り替える。cellは構成比と実数を併記し、total 0は`構成比算出不能`とする。
- time-series view: 2015–2024年の全国検挙構成比60行を、検挙件数／検挙人員を切り替えるline chartと全件表で表示する。外国人全体／来日外国人／両者の算術差分を別系列とし、日本人等を含む全国総数を分母にする。人口当たりの犯罪率ではなく、残差は普段から住む外国人というcategoryではない。
- verification: frontend 91 test、statement coverage 89.23%、branch coverage 83.08%、typecheck／lint／data hash verification／production buildをpass。Chromeで幅1440 px／390 pxを目視し、全26 categoryのlabel、日本の別色、未算出行、時系列chart、mobile横overflowなしを確認した。Pythonは162 test、skip 0、coverage 83.20%。
- publication: GitHub Pagesの公開版はv0.1.0。今回のschema v7／UI変更はlocalで検証中で、まだpush／deployしていない。

### M5. 過去年整備・定期更新・監視 — **進行中**

- [x] 9 series／34 editionをregistryへ登録し、R02–R05詳細表、2015–2024年の総人口／日本人人口、2016–2025年の国籍等別人口を取得・検証する。
- [x] S08 / S09 / S15から2015–2024年の全国検挙構成比60行（2 metric × 3 scope）を生成し、dashboardへ接続する。
- [ ] R02–R06各editionの内訳を連結し、地域別・国籍等別・犯罪種類別の2020–2024年5点panelを作る。

- [ ] sourceごとの公開scheduleに合わせた更新頻度を決める（要確定）。
- [ ] GitHub Actions等による定期実行方式を決める（要確定）。
- [ ] source URL、schema、category、公開日の変更を検知する。
- [ ] 最終成功日時、対象期間、失敗sourceを可視化側に表示する。
- [ ] 新規dataの検証に失敗した場合、前回の検証済み版を公開し続ける。

## 結果（解釈レベル）

- 2026-08-29: project scaffoldと本briefの叩き台を作成した。
- 2026-08-30: source auditを完了し、人口側の `国籍・地域 × 都道府県` は取得可能、犯罪側の `国籍 × 都道府県` joint numerator はroutine official sourceでは未確認と判定した。詳細は `docs/20260830_085603_source_availability_audit.md`。
- 2026-08-30: user decisionにより、完全一致する分子の取得をmilestoneにせず、利用可能な公表統計の組合せごとに出典と不一致を明示した参考比率を作る方針を確定した。items 2–5（3 parser、正規化、count＋indicator MVP、警察庁照会track）は妥当として承認された。
- 2026-08-30: M2 parser coreをtest-firstで実装し、17 test／88.06% coverageと4種の実official workbookで動作確認した。並行調査は [focused Deep Research prompt](./20260830_135535_parallel_deep_research_prompt.md) に切り出した。
- 2026-08-30: Deep Researchと独立に進められるM2 offline laneとして、immutable snapshot、versioned quality profile、atomic offline pipelineを追加した。38 test／86.71% coverageと実4 artifactのintegrated runで検証した。
- 2026-08-30: inboxのDeep Research 2本を比較し、一次資料とbinaryで主要主張を再確認した。表13の地理semanticは未解決のため`police_reporting_area_unresolved`を維持し、UIでは「都道府県等別（警察統計上の集計区分）」と安全に表示する。China grouping mismatchは国籍dimensionを持つX/Yには影響するが、aggregateのZには影響しない。
- 2026-08-30: registry v2、`nca-acquire`、artifact catalogをtest-firstで実装し、当時の5 editionを`data/raw`／`data/processed`へ正式収集した。data lifecycleは [data management and acquisition](./data_management.md) に固定した。
- 2026-08-30: canonical mappingをtest-firstで実装し、612 distinct mappingをmatched 578／ambiguous 26／unmatched 8に分類した。同名でもsemanticが複合するNPA `中国`はexact matchにせず、mappingとindicator compatibilityを分離した。
- 2026-08-31: indicator contract schema v2とfirst validated data productをtest-firstで実装した。10 contract／290 record、250 calculated／40 refused。計算可否と統計的compatibilityを分離し、source artifact provenanceとmismatchを各runから辿れるようにした。
- 2026-09-01: userの背景説明を受け、日本国籍ではなく日本に居住する全住民をprimary regional baselineにすると確定した。警察庁表3／144をS15／S16としてtest-firstで実装・正式取得し、source／compatibility／refusal boundaryを[all-resident baseline audit](./20260901_133313_all_resident_baseline_audit.md)へ固定した。
- 2026-09-01: S15 / S16をpinした`all_resident_regional_context` productを実装し、[all-resident context product audit](./20260901_153000_all_resident_context_product_audit.md)を作成した。全国＋47都道府県の3 metric contextと、警察region／subregion、日本国籍prefecture分子、個別国籍 × 都道府県分子のrefusal境界をmachine-readableに固定した。
- 2026-09-01: `compact_export.py`と`nca-build-compact-export`を追加し、[compact export audit](./20260901_211700_compact_export_audit.md)を作成した。indicatorとall-residentのresolved latest manifestをhash付きで固定し、10 indicator definition、3 context definition、290 + 186 rowを1つのdashboard bundleへ圧縮した。
- 2026-09-02: [all-resident / compact independent re-audit](./20260902_073831_all_resident_and_compact_independent_reaudit.md)を完了した。旧findingを修正したcurrent runsは`20260901_225500_all_resident_context`と`20260901_232700_compact_export`。fresh reviewerは全findingをclosedとし、scope内open finding 0と判定した。
- 2026-09-02: [local visualization MVP](./20260902_200948_visualization_mvp_audit.md)を実装・検証した。fresh reviewerのHigh（検挙人員を件と表示）とMedium（map asset hash未強制）をtest-firstで修正し、両方closed、新規finding 0と確認した。
- 2026-09-03: S17日本人人口を追加し、全国の日本人刑法犯検挙人員をS15 − S08の残差として明示するcomparison productを実装した。日本を含む全26 row、高い側／低い側各5件、warning付き全件表示をcompact export schema v3とUIへ接続した。
- 2026-09-03: [fresh independent review](./20260903_182500_japanese_nationality_comparison_independent_review.md)で日本人residual、26-row completeness、高低対称性、warning／refusal、provenance／publication gateを再検証し、scoped finding 0を確認した。その後userが旧nationality numerator selectorの消失を発見したため、算術とは別のproduct-design regressionとして未完了に戻した。
- 2026-09-03〜04: nationality perspective selectorを復旧し、日本人分子がcompatibleでないviewでは日本をexplicit refusalとして保持した。日本を含む26 × 6の犯罪類型構成と階層cluster、S15の認知−検挙同年差分を追加し、compact exportをschema v5へ更新した。browser検証で同年差分率をcount unit `件`と表示するbugを検出し、RED test追加後に`%`へ修正した。
- 2026-09-04: [fresh independent review](./20260904_082803_offense_composition_and_same_year_gap_independent_review.md)で26 × 6構成、日本残差、cluster順、同年差分62 row、selector refusal、publication hash、一次定義を再検証し、Blocking／High／Medium／Low 0、scope内open finding 0を確認した。
- 2026-09-04: サイトの目的が見えず、`cohort`や`nationality-neutral`など英語混じりの内部用語が読みにくいというuser指摘を受け、冒頭案内、用語説明、ページ内メニュー、日本語README／解釈方針へのリンクを追加した。表示上の注意コードと出典名も平易な日本語にし、元のコードやhashは追跡可能な形で保持した。
- 2026-09-05: R02–R05詳細表、historical populationを正式取得し、2015–2024年の全国検挙構成比40行を実装した。日本人を含む全国検挙件数／人員に対する外国人全体／来日外国人の割合を別scopeで表示し、人口当たりの犯罪率ではないと明示した。
- 2026-09-05: 全国籍比較の高い側／低い側各5件と重複するcount／ratio切替を廃止し、全categoryを参考比率の降順で並べる横棒plotへ変更した。日本は別色、算出不能は末尾、countとratioは全件表に保持し、desktop／mobileで目視確認した。
- 2026-09-06: userの指摘を受け、外国人全体−来日外国人を第三系列として追加した。警察庁定義を確認すると差分は定着居住者だけでなく在日米軍関係者・在留資格不明者も含み得るため、「在日外国人」「普段から住む外国人」とは表示せず、算術差分・direct非公表と明示した。
- 現段階の結論: 全住民regional context、日本を欠落させない選択式全国籍比較、全件order plot、犯罪類型構成、未解決率とは呼ばない同年差、2015–2024年の3-scope全国検挙構成比、dashboard-ready compact export v7、responsive visualization、GitHub Pages workflowまで成立した。次は2020–2024年の地域別・国籍等別・犯罪種類別の詳細panelであり、今回の変更はpush／deploy前である。

## 想定される成果 (Outcome)

以下は背景から推定したplaceholderであり、**要確定**。

1. **公開dashboard / atlas**: 最初に全住民の地域contextを表示し、国籍・都道府県／地域・年・指標でcountと、公表統計由来の参考比率を確認できるGitHub上の可視化。nationality viewはsecondaryに分け、参考比率には常にnumerator/denominator provenanceとmismatch noteを伴う。
2. **再現可能なdataset**: source provenance、定義、欠損・非比較可能flagを含むnormalized data product。
3. **定期更新pipeline**: 新規公表dataの取得、検証、可視化更新、失敗検知を自動化する仕組み。
4. **source audit report**: 誰がどの統計を出し、どの粒度が利用でき、何が比較不能かをまとめた文書。
5. **methods / interpretation note**: 参考比率の分子・分母・算式・限界と、official crime rateではないことを説明する文書。

論文、data paper、一般向け解説のどれを最終成果に含めるかは**要確定**。
