# 国籍別在留人口と犯罪統計の source availability audit

- 調査日: 2026-08-30
- 対象: 日本全国、都道府県、警察管区等、国籍・地域別
- 調査対象年: 現行公開表を中心に、比較用の過去表・既存研究も確認
- source inventory: 30 records（一次資料・一次研究を優先）
- 検証状態: root processが主要URLへのアクセス、代表ファイルのdownload、workbook/PDFのschema・脚注、SHA-256を確認済み。fresh reviewerによるclaim-by-claimの独立検証は未完了（§14.3）
- raw trace: [`agent_logs/20260830_085603_source_audit/research_trace.md`](../agent_logs/20260830_085603_source_audit/research_trace.md)

## Executive summary

### 結論

**M1の判定は conditional go（条件付きで次へ進む）**。

1. **[検証済み事実] 人口の `国籍・地域 × 都道府県` は取得可能。** 出入国在留管理庁の「在留外国人統計」表1は、国籍・地域、在留資格、性別、年齢、都道府県、在留外国人数を持つ。2025年12月末版のrow-level sheetを実査した。
2. **[検証済み事実] 全国の `国籍 × 罪種 × 検挙件数／検挙人員` は取得可能。** 警察庁の年次表130・131等が該当する。
3. **[検証済み事実] 都道府県の犯罪統計は、全体の `罪種 × 認知件数／検挙件数／検挙人員`、または `来日外国人`を一括した検挙件数・検挙人員までは取得可能。**
4. **[検証済み事実] routineの全国一次資料では、目的の分子である `個別国籍 × 都道府県 × 検挙件数／検挙人員` を確認できなかった。** 現行表は「国籍は全国集計」「都道府県は国籍を束ねた集計」に軸が分かれている。
5. **[検証済み事実] 例外的に、警察庁の2022年特集には `警察管区等 × 主要国籍 × 総検挙人員` の平成25年・令和4年比較表がある。** ただし47都道府県ではなく、2時点だけの特集表で、routine update sourceではない。
6. **[判断] `個別国籍 × 都道府県` の人口当たり値は算出不能。** joint numeratorがないためで、欠けたcellを推計・按分で埋めない。また、取得できる別の組合せを割った値もofficialまたは正確な`犯罪率`とは呼ばない。
7. **[2026-08-30 user decision] raw countに加え、取得できるsource pairの単純除算を`公表統計由来の参考比率`として表示する。** 完全一致する分子・分母の取得はproject milestoneやMVP gateにしない。indicatorごとに分子・分母・算式・出典・期間・地理・母集団の不一致を毎回示す。
8. **[判断] このpolicyならM2へgo。** 人口map、全国国籍別の検挙人員と参考比率、都道府県別の来日外国人aggregateと参考比率、限定的な警察管区等×主要国籍の特集表を、別indicatorとして表示できる。

### 最も重要な注意

警察庁の`来日外国人`と、出入国在留管理庁の`在留外国人`は同じ母集団ではない。前者は定着居住者等を除外する一方、短期滞在者を含み得る。後者は基準日時点のresident stock（在留者数）である。たとえ全国レベルで国籍別の分子・分母が揃っても、その単純な割り算は厳密な`crime rate`ではない。

## 1. Research questions and scope

本auditは次を調べた。

1. 誰が人口・犯罪統計を公表しているか。
2. `国籍 × 地理 × 年 × 指標`のどのcellが取得できるか。
3. 分子と分母の定義・時間・地理・categoryをjoinできるか。
4. 既存の研究・dashboard・codeが目的を満たしているか。
5. 定期更新pipelineをどのofficial surfaceから構成できるか。

優先順位は、警察庁・e-Stat・出入国在留管理庁の一次資料、peer-reviewed primary research、再現可能なcode、一般の二次可視化の順とした。都道府県警47組織のwebsiteは網羅auditしていないため、local supplementary dataの不在までは断定しない。

## 2. Evidence labels

- **[検証済み事実]**: URLにアクセスし、metadata、PDF本文、またはdownload fileの内容を確認した。
- **[推論]**: 複数の検証済み事実から導いたが、sourceが直接そう述べてはいない。
- **[判断]**: このprojectで採用すべき設計・publication policy。
- **[未確認]**: 今回のscopeでは一次資料まで確認できていない。

「見つからなかった」は「存在しない」と同義にしない。本報告のno-goは、**auditしたroutine national official tablesだけでは作れない**という意味である。

## 3. Metric dictionary

| term | statistical unit | official meaning / project treatment | use in this project |
|---|---|---|---|
| `認知件数` | event | 警察が発生を認知した事件数 | 地域全体のcrime volumeには使える。offender nationalityは原則まだ確定しないため、国籍別分子には使わない |
| `検挙件数` | event | 警察が検挙した事件数。前年以前に認知した事件を含み得る | countとして表示可。calendar-year populationとの単純対応に注意 |
| `検挙人員` | person record | 検挙した被疑者の人員 | 国籍別表のprimary metric候補。ただしresident unique offenderや有罪者数ではない |
| `検挙率` | ratio | 検挙件数 ÷ 認知件数。前年以前の事件を含むため100%超もあり得る | population-based rateとは別物。名称を混同しない |
| `外国人` | nationality category | 日本国籍を有しない者等を含む警察統計上のcategory | 表ごとの脚注を保存する |
| `来日外国人` | police category | 警察庁定義。定着居住者、在日米軍関係者、在留資格不明者等を除く | `在留外国人`と同一視しない |
| `在留外国人` | resident stock | 中長期在留者＋特別永住者 | population mapの標準分母候補 |
| `総在留外国人` | resident-related stock | 上記に短期滞在等を加えた別category | police numeratorへの近似にも直ちには使わない |
| `public-data-derived reference ratio` | source-defined numerator / source-defined denominator | `official numerator ÷ official denominator × scale` | source pairごとに別indicator。mismatchを開示し、`crime rate`とは呼ばない |

### 推奨する名称

**[判断]** UI・dataset column・documentationで`犯罪率`を既定名称にしない。例えば`公表統計由来：在留外国人10万人当たり検挙人員（参考比率）`とし、numerator、denominator、算式、対象期間、地理、母集団、既知の不一致を同じ画面に出す。

## 4. Source inventory

Reliabilityは、`A` = first-party official、`B` = peer-reviewed / primary research、`C` = reproducible secondary、`D` = discovery only とした。C/Dはground truthに使わない。

| ID | source | publisher / type | available dimensions or purpose | cadence / format | reliability |
|---|---|---|---|---|---|
| S01 | [犯罪統計資料（捜査活動に関する統計等）](https://www.npa.go.jp/publications/statistics/sousa/statistics.html) | 警察庁 | 年次確定値・暫定値の入口 | annual / HTML, files | A |
| S02 | [2025年 犯罪統計資料（確定値）](https://www.e-stat.go.jp/stat-search/files?stat_infid=000040410682) | 警察庁・e-Stat | 全国、都道府県、罪種、認知・検挙・人員、外国人関連表 | annual / XLS, CSV, PDF | A |
| S03 | [2025年 犯罪統計資料](https://www.npa.go.jp/toukei/keiji35/new_hanzai07.htm) | 警察庁 | 現行表と`来日外国人`の定義 | annual / HTML | A |
| S04 | [令和6年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm) | 警察庁 | 詳細統計表のofficial index | annual / HTML, XLSX | A |
| S05 | [令和6年の刑法犯に関する統計資料](https://www.npa.go.jp/toukei/seianki/R06/r06keihouhantoukeisiryou.pdf) | 警察庁 | metric definitions、注記、population reference | annual / PDF | A |
| S06 | [表3 都道府県別・罪種別](https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_003.xlsx) | 警察庁 | 年×都道府県×罪種×認知・検挙・人員 | annual / XLSX | A |
| S07 | [表129 外国人区分別](https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_129.xlsx) | 警察庁 | 全国×罪種×外国人総数／来日／その他 | annual / XLSX | A |
| S08 | [表130 外国人の国籍別](https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_130.xlsx) | 警察庁 | 全国×罪種×国籍×検挙件数・人員 | annual / XLSX | A |
| S09 | [表131 来日外国人の国籍別](https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_131.xlsx) | 警察庁 | 全国×罪種×国籍×検挙件数・人員 | annual / XLSX | A |
| S10 | [令和4年における組織犯罪の情勢](https://www.npa.go.jp/sosikihanzai/R04sotaijousei/R4jousei.pdf) | 警察庁 | 警察管区等×主要国籍×総検挙人員、H25/R4 | one-off comparison / PDF | A |
| S11 | [令和7年における組織犯罪の情勢](https://www.npa.go.jp/publications/statistics/kikakubunseki/r7jyousei_shuusei.pdf) | 警察庁 | 現行のnational nationality・罪種・在留資格等 | annual / PDF | A |
| S12 | [統計データ利用に関する問合せ](https://www.npa.go.jp/npa_goiken/opinion-0002.html) | 警察庁 | 未公開joint tableの照会・提供相談先 | form | A |
| S13 | [在留外国人統計 dataset list](https://www.e-stat.go.jp/stat-search/files?layout=dataset&toukei=00250012&tstat=000001018034) | 出入国在留管理庁・e-Stat | 現行・過去の在留外国人統計 | observed semiannual / XLSX, PDF | A |
| S14 | [2025年12月末 表1](https://www.e-stat.go.jp/stat-search/files?layout=dataset&stat_infid=000040472265&toukei=00250012&tstat=000001018034) | 出入国在留管理庁・e-Stat | 国籍・地域×在留資格×都道府県×年齢×性別 | semiannual snapshot / XLSX | A |
| S15 | [2025年12月末 表2](https://www.e-stat.go.jp/stat-search/files?layout=dataset&stat_infid=000040472266&toukei=00250012&tstat=000001018034) | 出入国在留管理庁・e-Stat | 国籍・地域×在留資格×市区町村、条件付き年齢・性別 | semiannual snapshot / XLSX | A |
| S16 | [在留外国人統計 用語の解説](https://www.e-stat.go.jp/stat-search/file-download?fileKind=2&statInfId=000040472267) | 出入国在留管理庁・e-Stat | 中長期在留者、在留外国人、総在留外国人の定義 | PDF | A |
| S17 | [在留外国人統計 利用上の注意](https://www.e-stat.go.jp/stat-search/file-download?fileKind=2&statInfId=000040472268) | 出入国在留管理庁・e-Stat | category change、基準日、表追加、注記 | PDF | A |
| S18 | [国籍・地域別 都道府県別 在留外国人](https://www.e-stat.go.jp/stat-search/database?layout=dataset&statdisp_id=0003147229&toukei=00250012) | 出入国在留管理庁・e-Stat | historical prefecture×nationality database | semiannual / DB/API | A |
| S19 | [e-Stat API 利用ガイド](https://www.e-stat.go.jp/api/api-info/api-guide) | 総務省統計局 | application ID、API利用開始手順 | living docs | A |
| S20 | [e-Stat API 仕様](https://www.e-stat.go.jp/api/index.php/api-info/api-spec) | 総務省統計局 | XML/JSON/CSV、catalog、updatedDate、download link | living docs | A |
| S21 | [e-Stat 利用規約](https://www.e-stat.go.jp/terms-of-use) | 総務省統計局 | attribution、加工表示、数値dataの扱い | living docs | A |
| S22 | [令和7年警察白書 来日外国人犯罪](https://www.npa.go.jp/hakusyo/r07/honbun/html/bb4432000.html) | 警察庁 | 全国国籍構成とcontext population | annual / HTML | A |
| S23 | [令和3年警察白書 dataset](https://data.e-gov.go.jp/data/en/dataset/npa_20220530_0031) | 警察庁・e-Gov | prefecture crime visualizationと外国人国籍表の既存公開例 | archived / files, Tableau links | A |
| S24 | [地域犯罪と外国人に関する実証分析](https://www.jstage.jst.go.jp/article/ncs/15/0/15_84/_pdf) | 功刀・岩田・宮澤 / peer-reviewed article | 1996–2011 prefecture panel、ecological modelと限界 | 2015 / PDF | B |
| S25 | [Ecological Correlations and the Behavior of Individuals](https://fisher.stats.uwo.ca/faculty/aim/2015/9938/articles/Robinson1950AmericanSociologicalReview.pdf) | W. S. Robinson / primary methods article | ecological fallacyの古典的根拠 | 1950 / PDF | B |
| S26 | [Crime Rates among Foreigners in Japan](https://doi.org/10.7910/DVN/FQHUDI) | Harvard Dataverse deposit | 2007–2024の在留資格別national workbook | versioned XLSX | C |
| S27 | [foreign-resident-map](https://github.com/AmashimaCreate/foreign-resident-map) | open-source project | 現行の国籍別在留人口mapの実装例 | code / data | C |
| S28 | [e-stat-api/adaptor](https://github.com/e-stat-api/adaptor) | e-Stat API / GitHub | API integrationの参考実装 | code | C |
| S29 | [MIERUNE/e_stat_api_tools](https://github.com/MIERUNE/e_stat_api_tools) | MIERUNE / GitHub | e-Stat geospatial toolingの参考 | code | C |
| S30 | [japan-choropleth](https://github.com/kyodo-official/japan-choropleth) | Kyodo News / GitHub | 日本地図choropleth asset・implementation候補 | code | C |

## 5. Availability matrix

記号: `✓` = routine public sourceで確認、`△` = 制約付き／one-off、`—` = 今回auditしたroutine national sourceでは未確認。

### 5.1 Population

| geography | nationality | time | other dimensions | availability | source / caveat |
|---|---|---|---|---|---|
| Japan | country/region | June/December snapshot | status, age, sex | ✓ | S13–S17 |
| prefecture | country/region | June/December snapshot | status, age, sex | ✓ | S14。2025-12 row-level sheetを確認 |
| municipality | country/region | June/December snapshot | status; age/sex are conditional | △ | S15。小規模自治体はsuppressionあり |
| prefecture | country/region | historical series | total | ✓ | S18 |

2025年12月末表1の実査schemaは次の通り。

```text
国籍・地域
在留資格
性別
年齢（５歳階級）
年齢
都道府県
在留外国人数
```

hidden row-level sheetは468,642 rowsだった。これはfile structureの観察値であり、将来版で固定と仮定しない。

### 5.2 Crime statistics

| geography | nationality dimension | metric | availability | source / caveat |
|---|---|---|---|---|
| Japan | individual nationality | 検挙件数・検挙人員 by offense | ✓ | S08、S09 |
| Japan | foreign total / visiting / other | 検挙件数・検挙人員 by offense | ✓ | S07 |
| prefecture | none / total population | 認知件数・検挙件数・検挙人員 by offense | ✓ | S06 |
| prefecture | `来日外国人` aggregate | 刑法犯・特別法犯の検挙件数・人員 | ✓ | S02の表13。individual nationalityなし |
| police region etc. | major individual nationality | 総検挙人員 | △ | S10のH25/R4比較のみ。47都道府県でなくroutineでもない |
| prefecture | individual nationality | 検挙件数・検挙人員 | — | audited routine national tablesでは未確認 |
| prefecture | individual nationality | 認知件数 | — | audited tablesでは未確認。認知時点ではoffender identityが未確定の場合がある |
| municipality | individual nationality | any crime metric | — | national official sourceでは未確認 |

### 5.3 Requested products

| requested output | status | reason |
|---|---|---|
| 国籍別・都道府県別の在留人口map | **GO** | S14/S18で直接取得可能 |
| 全国の国籍別検挙件数・検挙人員trend | **GO** | S08/S09で直接取得可能 |
| 都道府県別の来日外国人検挙件数・人員map | **GO with label** | individual nationalityではなくaggregateであることを明示 |
| 警察管区等×主要国籍のhistorical comparison | **GO as archival exhibit** | H25/R4のみ。更新対象の主系列にしない |
| 国籍×都道府県のraw crime count | **NO-GO now** | joint numerator未確認 |
| 国籍×都道府県のpopulation-based crime rate | **NO-GO now** | joint numeratorなし。さらにpopulation mismatchあり |
| 全国の国籍別の参考比率 | **GO with explicit mismatch** | S08/S09のnumeratorをS14のnationality populationで割る。`crime rate`とは呼ばない |
| 都道府県別の来日外国人aggregate参考比率 | **GO with explicit mismatch** | S02表13をS14の都道府県別在留外国人数で割る。地理・母集団の不一致を表示 |

## 6. Joinability audit

### 6.1 Numerator–denominator alignment

| axis | crime numerator | population denominator | match? | treatment |
|---|---|---|---|---|
| unit | 検挙件数=events、検挙人員=persons | persons at a date | △ | `検挙人員`だけをperson-based proxy候補にする |
| population scope | `来日外国人`等のpolice category | `在留外国人`または`総在留外国人` | × | 参考比率としてのみ単純除算可。`population_scope_mismatch`を必須化 |
| residence | crimeが起き、警察が処理した側の地理 | registered residence | × / unresolved | 参考比率には`geography_mismatch`を付け、residence-based riskと解釈しない |
| nationality | police table categories and footnotes | ISA country/region categories | △ | versioned crosswalkとnon-comparable flagが必要 |
| time | Jan–Dec flow | June/December stock | △ | raw valuesを併記し、参考比率にはdenominator reference dateを明記 |
| case timing | earlier-year incidentのclearanceを含み得る | current-year population stock | △ | year labelだけでcohort一致と見なさない |
| small cells | crime tableの公開・丸め・秘匿条件 | municipality tableのsuppression | △ | suppressionを0に変換しない |

### 6.2 Nationality category drift

**[検証済み事実]** 在留外国人統計は、台湾を中国から分離した時期、韓国・朝鮮の分離、香港関連categoryの追加など、年をまたぐcategory changeを利用上の注意に記載している。警察統計側の表脚注と常に同一ではない。

**[判断]** `nationality_crosswalk.csv`は静的な名前置換にせず、次を持つversioned mappingにする。

```text
source_id
source_period_start
source_period_end
source_label
canonical_label
comparability_status   # exact / aggregated / split / unknown
note
```

split categoryを比率配分して埋めない。両sourceが共通にaggregationできる上位categoryへ揃えるか、`non_comparable`にする。

### 6.3 Geography

S10は明示的に`発生地域（管区等）`を使う。一方、current prefecture tableの数値を「被疑者の居住都道府県」と解釈できる根拠は今回確認できなかった。

**[判断]** schemaでは`prefecture`だけでなく、少なくとも次を分ける。

```text
geography_type          # prefecture / police_region / national
geography_code
geography_label
geography_semantics     # occurrence / reporting / processing / residence / unresolved
```

`geography_semantics=unresolved`のまま単純除算する場合は、**official crime rateまたはresidence-based riskとして解釈しない**。`geography_semantics=unresolved`とmismatch noteをderived valueに付随させる。

### 6.4 Indicator provenance contract

numeratorがXの場合、Yの場合、denominatorがZの場合、Wの場合を一つのrateへ統合しない。組合せごとに次のcontractを持つ。

```text
indicator_id
display_name
numerator_value
numerator_metric
numerator_source_id
numerator_table
numerator_definition
numerator_period
numerator_geography_semantics
denominator_value
denominator_metric
denominator_source_id
denominator_table
denominator_definition
denominator_as_of
denominator_geography_semantics
formula
scale
mismatch_flags[]
derived_by_project = true
official_crime_rate = false
```

MVP candidate indicator cases:

| case | numerator | denominator | mandatory label / mismatch |
|---|---|---|---|
| X | S08: 全国・国籍別の外国人検挙人員 | S14: 同国籍の全国在留外国人数 | annual flow ÷ resident stock; category/time mismatch |
| Y | S09: 全国・国籍別の来日外国人検挙人員 | S14: 同国籍の全国在留外国人数 | visiting-foreigner ÷ resident stock; strong population mismatch |
| Z | S02表13: 都道府県別の来日外国人検挙人員aggregate | S14: 都道府県別の在留外国人数aggregate | police geography unresolved; population mismatch; no individual nationality |

これらはcandidate formulaであり、M2 parserのsample値とofficial totalを検証してから確定する。

## 7. Existing work and what it does not solve

### 7.1 Research

S24は1996–2011年の都道府県panelで、地域全体のcrime incidenceをoutcome、国籍別のresident share等をpredictorとしている。これは`国籍別の犯罪件数 ÷ 同国籍人口`を作った研究ではない。著者ら自身も、短期滞在者を含まないこと、endogeneity、individual-level dataの必要性を限界として挙げている。

S25が示す通り、地域集計の相関から個人のbehaviorを推定するのはecological fallacy（生態学的誤謬）になる。例えば「ある国籍のresident shareが高い都道府県でcrime countが高い」という関係が見えても、その国籍の個人が犯罪を行ったとは結論できない。

### 7.2 Public datasets and dashboards

- S23には、都道府県別crime visualizationと全国の外国人国籍別表が別resourceとして存在する。joint tableではない。
- S26のmetadataはnationalityを想起させるが、downloadしたworkbookを実査すると2007–2024年のnational visa-status seriesが中心で、prefecture fieldもcountry fieldもなかった。再現可能なsecondary workではあるが、目的のjoint data sourceではない。
- S27は国籍別在留人口mapの実装例で、population側のMVPには参考になるがcrime numeratorを持たない。
- S28–S30は取得・地理可視化のimplementation referenceで、統計値のground truthではない。

**[スコープ付き結論]** 日本の`国籍 × 都道府県 × crime count × population`をofficial provenance付きで一体表示する公開repoは、今回の日本語・英語・GitHub scoped searchでは確認できなかった。これはweb全体での不存在証明ではない。

## 8. Recommended MVP

### 8.1 Publishable panels

**[判断]** M2–M4のMVPを次の4 panelに分ける。

1. **Foreign-resident population atlas**
   - `国籍・地域 × 都道府県 × 年末／6月末`
   - source: S14/S18
   - count、share、source period、definitionを表示
2. **National arrest-count trend by nationality**
   - `国籍 × 年 × 罪種 × 検挙件数／検挙人員`
   - source: S08/S09
   - raw countに加え、X/Yのsource pair別参考比率を任意表示する
3. **Prefectural visiting-foreign aggregate**
   - `都道府県 × 年 × 来日外国人の検挙件数／検挙人員`
   - source: S02 table 13
   - Zの参考比率を表示可能。ただし`individual nationality unavailable`とmismatch badgeを表示
4. **Limited regional historical exhibit**
   - `警察管区等 × 主要国籍 × 総検挙人員`のH25/R4比較
   - source: S10
   - `one-off / non-routine / non-prefectural` badgeを表示

異なるpanelを暗黙にjoinしない。計算するsource pairをindicator registryへ明示的に登録し、raw numerator・raw denominator・derived valueを同時に表示する。

### 8.2 Data request track

S12を通じて、少なくとも次を具体的に照会する。

1. 年次の`都道府県（または取扱警察）× 個別国籍 × 刑法犯／特別法犯 × 検挙件数・検挙人員`が提供可能か。
2. geographyは発生地、検挙地、取扱所属、被疑者住所のどれか。
3. `検挙人員`の同一人物の重複計上rule。
4. 居住／非居住、在留資格、定着居住者、短期滞在者の区別が可能か。
5. small-cell suppression、revision、遡及提供年、license・再配布条件。

回答はsource coverageを改善し得るが、MVPのblockerにはしない。新しいnumeratorを得た場合は新indicator caseとして追加し、既存の参考比率を黙って置換しない。

## 9. Update architecture

### 9.1 Acquisition

```text
e-Stat catalog / official landing pages
                │
                ▼
      discover current resource IDs
                │
                ▼
      download official files as raw
                │
                ▼
 timestamp + URL + publication date + SHA-256
                │
                ▼
 parse → normalize → validate → publish
```

**[判断]** e-Statのfile datasetは「statistics APIで全rowを必ず取れる」と仮定しない。S19/S20のcatalog APIでcurrent `statInfId`、title、updated date、download linkをdiscoverし、official fileをdownloadする。application IDが使えない場合だけofficial listingをfallbackとする。

### 9.2 Provenance manifest

各raw artifactに最低限次を保存する。

```yaml
source_id: S14
publisher: Immigration Services Agency of Japan
landing_url: ...
download_url: ...
retrieved_at: ...
published_at: ...
period_end: 2025-12-31
stat_inf_id: "000040472265"
sha256: ...
media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
parser_version: ...
license_url: https://www.e-stat.go.jp/terms-of-use
```

### 9.3 Validation gates

1. HTTP success、content type、file signatureを確認する。
2. expected sheet/columnを確認する。
3. row countの急変、unknown category、duplicate keyを検知する。
4. 都道府県・国籍totalがofficial totalと整合するか確認する。
5. suppression (`-`) とmissingとzeroを別valueにする。
6. source category changeを検知したらpublicationを止める。
7. 前回検証済みartifactを保持し、失敗版を公開しない。

### 9.4 Cadence

- crime: annual finalized dataを主系列とし、provisional dataは別statusで扱う。
- population: observed release patternはJune/December snapshot。e-Stat metadataのfrequency表現との不一致を監視する。
- scheduler: 毎月discover checkを行い、新resourceを検出した時だけingestionする方式が安全。

## 10. Ordered backlog

### P0 — M0 publication rules — **approved 2026-08-30**

1. exact numerator–denominator alignmentをproject goalまたはMVP blockerにしない。
2. numerator/denominator caseごとに別indicator IDを作る。
3. 公表統計の単純除算を参考比率として表示してよいが、officialまたは正確な`犯罪率`とは呼ばない。
4. source、table、definition、formula、period、geography、mismatch flagを毎回表示する。
5. 存在しないjoint numeratorを推計しない。

### P1 — M2 minimum ingestion prototype

6. S14のpopulation表1 parserを作る。
7. S08/S09のnational nationality crime parserを作る。
8. S02 table 13のprefecture visiting-foreign aggregate parserを作る。
9. source registry、raw manifest、SHA-256、schema testsを実装する。

### P2 — Harmonization and quality

10. versioned nationality crosswalkを作る。
11. prefecture/police-region code tableとgeography semanticsを作る。
12. missing/suppressed/not-published/non-comparableを区別する。
13. small sampleでofficial totalsとのreconciliation testを通す。

### P3 — Visualization

14. population atlasを先に作る。
15. national nationality count trendを別panelで追加する。
16. prefecture aggregateとone-off police-region exhibitを制約badge付きで追加する。
17. source、definition、period、download hashまで辿れるUIを付ける。

### P4 — Optional data enrichment

18. S12へjoint tableの提供可否を照会する。
19. 必要なら都道府県警のlocal open-dataを47組織横断でauditする。
20. 新規dataが得られたら既存indicatorを上書きせず、新しいsource pairとして比較可能性を評価する。

## 11. Evidence gaps

1. 47都道府県警のwebsiteを全件auditしていない。local tablesが存在する可能性は残る。
2. current prefecture crime tableのgeography semantics（発生地・検挙地・取扱所属等）を一次定義で確定できていない。
3. 警察庁が非公開のjoint tableをrequestに応じて提供するかは未確認。
4. 国籍別検挙人員と在留者registryをindividual-levelでlinkできるdataは調査scope外で、公開aggregateからは確認できない。
5. historical fileのschema driftを全期間でまだtestしていない。
6. source listingのmetadata上のfrequencyとobserved release patternにずれがあるため、automationはhard-coded cadenceだけに依存できない。

## 12. Ethics and interpretation guardrails

1. arrest/clearance dataをindividual propensity、conviction、causal effectと表現しない。
2. raw countとpopulationを必ず同時に表示し、small denominatorを目立たせる。
3. `0`、`missing`、`suppressed`、`not published`、`non-comparable`を色・値とも区別する。
4. rankだけを強調するleague-table表示を避け、uncertaintyとdefinitionを先に見せる。
5. nationalityの地域shareと地域全体のcrimeの相関を、同国籍個人のbehaviorへ還元しない。
6. source更新・category changeで比較不能になった年をlineでつながない。

## 13. Licensing and publication

S21によれば、e-Stat dataは出典を明示し、加工した場合は加工内容を示し、政府作成物と誤認させない形で利用する。数値・単純表の扱いと、個別resourceの注記を確認する。repositoryでは次を実施する。

- chart footerとdataset metadataにpublisher、統計名、period、landing URLを表示する。
- normalized dataには`processed by this project`と変換内容を記載する。
- raw fileの再配布可否はsource別に確認し、既定ではURL・hash・取得scriptをversion controlする。
- third-party map/codeは各licenseを別途確認する。

## 14. Verification appendix

### 14.1 Downloaded files and SHA-256

| artifact | SHA-256 | check |
|---|---|---|
| 2025 population table 1 | `3a7c603c42927fc441ba0c062777223754d238df904bd15a034220dffd229a86` | OOXML、row-level schema確認 |
| 2025 population table 2 | `d7cdb7d22ba02008a08fc0087b789a7c018f760ecfe1a4ef51d378ed3ec01326` | OOXML、suppression notes確認 |
| R06 table 3 | `f1c597114874c1a0ba6b87e9a7d7fcbb48041defb7cb16a874c2c9542991d75b` | prefecture/offense schema確認 |
| R06 table 129 | `38d1c85184ba9fc9d5ebc9bc3dca666ba3a6d68e71b90152db60578b586baad1` | foreign category rows確認 |
| R06 table 130 | `23ccb60d89c9b4bdaa898105753506a61d8354a0ae87b01598f6c97f4efd6a83` | nationality/offense schema、prefecture fieldなし |
| R06 table 131 | `70d180220c3b53cd5d832acb1c86460b005c47215c0409c7b14ea0f0057a2e30` | visiting-foreign nationality schema、prefecture fieldなし |
| 2025 finalized crime workbook | `0404e10b0ab45b35f9be86c7b748bb039469cff2efc63584b2ac9660056b7323` | old OLE Excel file signature確認 |
| Harvard Dataverse workbook | `c789c765f670b827978cfc44da85e565f0c81667787e70fb5b8e9cd32708a8b4` | sheets/strings/schema確認 |
| Harvard Dataverse metadata | `33cc2629559a48c251370eb9284ca44db6749cfdb6a2d9e6b3ccf81b12290f89` | DOI metadata確認 |

### 14.2 Representative falsification checks

- R06表3に国籍axisがあるか: **なかった**。
- R06表130/131に都道府県axisがあるか: **なかった**。
- 2022組織犯罪reportに地域×国籍のjoint tableがあるか: **あったが警察管区等・2時点だけ**。
- current 2025組織犯罪reportに同等のroutine geographic tableがあるか: document内の該当語と目次を確認した範囲で**確認できなかった**。
- Dataverse workbookにprefecture/country variableがあるか: workbook全体のsheet・shared stringsを確認し、**確認できなかった**。
- 2025 population table 1に直接使えるprefecture/nationality rowsがあるか: **確認した**。

### 14.3 Independent-review status

High-stakes claimを生成していないfresh reviewerへ2回、A–Hのclaim-by-claim反証とURL/file evidenceを依頼した。しかし、いずれも指定した検証matrixではなくproject要約を返したため、**独立adversarial reviewとしては採用していない**。したがって本報告の`検証済み`は、root processによる一次資料の再open、download fileのschema inspection、hash確認を意味する。

独立reviewの状態は**未完了**であり、M2でparserを実装した後、source fixtureとexpected schemaを使った機械的な再検証を別reviewerに依頼する。これは本auditのconditional goを取り消すものではないが、「別agentでも反証済み」とは主張しない。

## 15. Final decision

**[判断] Go:** M2へ進む。作るものは`raw-count + public-data-derived reference-ratio, provenance-first atlas`であり、officialまたは正確な`犯罪率`ではない。完全に一致する分子の取得はmilestoneにしない。

Go条件:

1. unavailable combinationを推計で補わない。
2. 単純除算するsource pairをindicator IDとして固定し、raw numerator・raw denominatorも表示する。
3. count、person、reference ratio、geography semanticsを混ぜず、mismatch flagを付ける。
4. source、table、definition、formulaを各value/chartから辿れるようにする。
5. exact joint dataの取得はoptional enrichmentとし、新sourceを得た場合も別indicatorとしてversioningする。
