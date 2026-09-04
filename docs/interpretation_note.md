# Interpretation note for public-data-derived reference ratios

このprojectが出力する値は、official sourceが公表した分子と分母を、その定義差を残したまま単純除算した`公表統計由来の参考比率`である。officialまたは正確な`犯罪率`ではない。

## comparison baseline

- primary regional contextは`日本国籍`ではなく、日本に居住する`総人口`を基準にする。
- nationality viewはsecondaryな記述表示とし、特定nationalityを正常／異常、内側／外側のdefault comparatorにしない。
- nationality viewから日本国籍を欠落させない。current全国比較では日本も他categoryと同じ人口1,000人当たりの軸へ置くが、normal／abnormalを判定する基準とはしない。
- current日本人分子181,362人はdirect公表値ではなく、S15の全体191,826人からS08の全外国人10,464人を差し引いたproject-derived residualである。分母120,296,000人はS17の千人単位に丸められた日本人人口で、分子sourceとはreference dateも異なる。UIでは`残差参考値`、算式、全source IDを表示する。
- current dataに存在しない`個別国籍 × 都道府県`犯罪分子は推計・按分しない。

## 常に併記する前提

- 分子source、分母source、算式、対象年、地理、population scopeを明示する。
- `exact`と`as_published_mismatch`を混ぜない。
- `mismatch_flags`、`ui_caveat`、small-number warningを同じ画面で表示する。
- 全国籍比較では高い側5件と低い側5件を同じcalculated setから対称に選び、26 categoryの全表と4件のrefusalも併記する。高い側だけを切り出さない。
- nationality perspectiveを切り替えたとき、compatibleな日本人分子がないviewでは日本rowを消さず、`japanese_numerator_scope_not_available_for_selected_perspective`のrefusalとして残す。
- 犯罪類型構成は、日本を含む26 category × `凶悪犯`／`粗暴犯`／`窃盗犯`／`知能犯`／`風俗犯`／`その他の刑法犯`の6区分を表示する。構成比は各category内の検挙人員または検挙件数に占める割合であり、人口当たりの多寡ではない。`凶悪犯`以外をproject独自に`軽犯罪`とは分類しない。
- 犯罪類型の階層cluster順は、6区分の構成比にJensen–Shannon distance（base 2）とaverage linkageを適用した探索的な並びである。優劣、危険度、因果、集団の本質を表す順位ではない。total 0で構成比を定義できないrowはclusterへ入れず、`構成比算出不能`と表示する。
- 全住民contextでは、警察region／subregionのjoin不能行と、非公表の日本国籍prefecture分子・個別nationality × prefecture分子をrefusalとして見える形で残す。
- 全住民contextの分子は1暦年間に記録されたcrimeのflow、分母は同年10月1日時点のpopulation stockであり、同一時点の値ではない。`annual_flow_vs_point_in_time_population`を隠さない。
- 全住民contextの犯罪分子から、対象者のresidency scopeは確立できない。`numerator_residency_scope_not_established`を表示し、分子を「その都道府県の居住者による件数」と読み替えない。
- 全住民populationは千人単位へ丸められた公表値であり、推計で丸めを戻さない。
- `認知件数−検挙件数`は、同じS15の年・公表地理をpairし、符号付きの`同年差分件数`と`(認知件数−検挙件数) / 認知件数 × 100`を機械的に計算した値である。当年の検挙件数には前年以前に認知した事件の検挙が含まれ得るため、同一事件cohortを追跡した`未解決件数`／`未解決率`ではない。負値を0へclampせず、認知件数0では割合をrefuseする。

## してはいけない解釈

- 国籍差や地域差を、集団の本質的特性や個人riskの大小として読むこと。
- nationality labelだけを全住民contextから切り離し、集団へのレッテルや因果説明として用いること。
- 観測差を、そのまま因果関係の証拠として扱うこと。
- `来日外国人`の分子と`在留外国人`の分母の不一致、flow / stockの不一致、地理semanticの未解決を無視して、比較可能なofficial rateだとみなすこと。
- 小さい分母や少数件数で振れやすいrecordを、rankingやtop / bottom calloutで強調して断定的に説明すること。
- `認知件数−検挙件数`またはその割合を、その年に発生して未解決のまま残った事件数／率と読み替えること。
- 犯罪類型の構成比またはcluster順を、犯罪量、重大性、危険度、国籍集団の性質の順位と読むこと。

## この差に混ざりうる要因

- population scopeの不一致
- annual flowとyear-end／10月1日時点stockの不一致
- 犯罪分子のresidency scopeが確立していないこと
- nationality grouping mismatch
- police reporting areaとregistered residenceの不一致
- 集計・記録・取り締まり・通報・公表区分の差
- 年齢・性別・在留期間・就業・所得・都市化等の構成差（current productでは未adjusted）

## small-number warningの意味

- `small_denominator_base`: `denominator_value < 1,000`
- `sparse_numerator_count`: `numerator_value < 20`

これらはofficial reliability thresholdではなく、non-suppressing UI warning heuristicである。flagがあっても値を消さず、raw numerator / denominatorと一緒に表示する。supplementary indicator productには従来のranking-exclusion metadataが残るが、current全国籍比較は`include_all_with_warnings`であり、高い側／低い側に現れる場合もwarningを同時表示する。順位を安定したgroup特性と解釈しない。

## UI / reportでの推奨文面

「この値は1年間の公表crime countを10月1日／12月31日時点の公表populationで単純に割った参考比率であり、official crime rateや個人の犯罪発生確率ではありません。犯罪分子から対象者の居住地・residency scopeは確定できません。primary contextの総人口は日本人と外国人を含みます。全国籍比較には日本も含めますが、日本人の分子は全体から全外国人を引いた残差参考値です。nationality別の値や犯罪類型構成は集団の本質や因果を示しません。認知−検挙の同年差分はstrictな未解決件数／率ではありません。分子・分母の定義差、small-numberによる振れやすさ、地理semanticの限界を確認してください。」
