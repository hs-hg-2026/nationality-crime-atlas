# 時系列化に向けた公表資料・定義差・改訂差の調査

調査時点: 2026-09-05（日本時間）

## 結論

最初の時系列版に必要な資料の所在は確認できたが、**dimensionごとに得られる期間が異なる**。現在取得済みの警察庁「令和6年の犯罪」では、表3と表130／131の全国合計は2015–2024年の10点、表144の都道府県別人口も10点ある。一方、表3の地域別内訳と表130／131の国籍別内訳は2024年だけである。地域別・国籍別の5点を得るには、official pageで確認できたR02–R05の各詳細表を追加し、R06と合わせて2020–2024年を構成する。

2025年は一部の確定値・人口が公表済みだが、2024年までと同じ詳細表一式と日本人人口分母が揃っていない。したがって、2025年を既存系列へ無条件に接続せず、利用できる指標だけを別source／別definitionとして表示し、算出できない比率は明示的に`refused`とする。

## 検証状態

- **検証済み**: official URLへの到達、downloadしたfileのhash、Excel archive/openability、主要sheet・年header、既存raw workbookの2015–2024年headerを実fileで確認した。
- **検証済み**: 警察庁R02–R07概要表の共通cellを機械比較し、edition間の一致・差分・header変更を集計した。
- **検証済み**: 総務省統計局の年次人口推計と後発の補間補正人口を同一cellで比較した。
- **判断**: どのvintage（公表時点版）をcanonicalにするか、どの定義差をseries breakとして扱うかは、このprojectの明示的な採用方針であり、公的機関が示す「唯一の正解」ではない。
- **未検証**: 令和7年の表3・130・131・144に相当する詳細年報は、2026-09-05時点でofficial pageと推定direct URLから確認できなかった。未公表と断定するのではなく、`not_verified_as_published`として扱う。

## 利用可能期間と採用候補

| 表示・計算対象 | 公表資料 | 実fileで確認した期間 | 最初の採用方針 | 主な注意 |
|---|---|---:|---|---|
| 全住民の全国犯罪context | 警察庁 詳細表3 | 2015–2024（10点） | 既存S15 fileの全国年次行を抽出 | annual national totalで、地域別内訳ではない |
| 全住民の地域別犯罪context | 警察庁 詳細表3 | 各editionの最新年のみ | R02–R06を使い2020–2024（5点） | 警察統計上の地域であり、被疑者の居住地ではない |
| 全住民の地域別人口 | 警察庁 詳細表144 | 2015–2024（10点） | 既存S16 fileから全10年を抽出 | 10月1日時点stock、千人単位丸め |
| 全外国人の全国合計 | 警察庁 詳細表130 | 2015–2024（10点） | 既存S08 fileの全国年次行を抽出 | 国籍別内訳ではない |
| 全外国人・国籍別の検挙件数／人員・犯罪種類 | 警察庁 詳細表130 | 各editionの最新年のみ | R02–R06を使い2020–2024（5点） | source上の「中国」は台湾・香港等を含む。地域別分子はない |
| 来日外国人・国籍別の検挙件数／人員 | 警察庁 詳細表131 | 各editionの最新年のみ | R02–R06を使い2020–2024（5点） | 「来日外国人」は全在留外国人と同義ではない |
| 在留外国人数・国籍別分母 | 出入国在留管理庁 在留外国人統計 表1 | 2016–2025（10点） | まず2016–2024を犯罪分子とpairing | 各年末stock。2016–2021と2022–2025でworkbook layoutが異なる |
| 日本人人口・都道府県別／全国分母 | 総務省統計局 人口推計 | 2015–2024（10点以上） | 2015–2020は後発の補間補正版、2021–2024は年次版 | 10月1日時点stock、千人単位。補間補正版は国籍不詳の按分を含む |
| 2025年の選択的な全国trend | 警察庁 R07図表 | 2016–2025（rolling 10点） | 詳細表系列とは別seriesとして候補化 | 国・地域の掲載選択条件や定義注記があり、表130の代替ではない |
| 2025年の前年同期比較 | 警察庁／e-Stat S02 | 2024・2025 | 現行S02のscope内だけ利用 | 詳細年報の全dimensionを持たない |

### まず作れる共通期間

- 全住民の全国context: **2015–2024、10点**。地域別contextはR02–R06を追加して**2020–2024、5点**。
- 日本人の全国参考比率: 全住民値−全外国人値の算術残差を採用する指標に限り、**2015–2024、10点**。各年でderived valueと明示する。
- 外国籍別の人口当たり参考比率: R02–R06表130と在留外国人統計表1をpairingし、**2020–2024、5点**。
- 国籍別の犯罪種類構成: R02–R06表130を使い、**2020–2024、5点**。小さいnumeratorに伴う年ごとの振れを同時表示する。

## 警察庁の犯罪資料

### 既存R06詳細表

次の4fileで2015–2024年のyear labelを確認した後、内訳rowの位置も再確認した。この再確認により、「year labelがある」ことと「全dimensionの内訳が各年にある」ことを分けて扱う必要が判明した。

| source ID | file | table | 現parser | file内の実coverage |
|---|---|---:|---|---:|
| S15 | `R06_003.xlsx` | 3 | 2024地域別 | 全国合計2015–2024、地域別2024 |
| S08 | `R06_130.xlsx` | 130 | 2024国籍別 | 全国合計2015–2024、国籍別2024 |
| S09 | `R06_131.xlsx` | 131 | 2024国籍別 | 全国合計2015–2024、国籍別2024 |
| S16 | `R06_144.xlsx` | 144 | 2024のみ | 全国＋都道府県別2015–2024 |

したがって、同じfileから10点を得られるのは全国合計と表144の人口である。地域別・国籍別・国籍別犯罪種類の内訳は、各editionの最新年rowを連結する必要がある。

公式landing page: [警察庁 令和6年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm)

### R02–R05詳細表の存在確認

R02–R05のofficial landing pageで、各年の表3、表130、表131、表144へのExcel linkを確認した。最初の5点ではR02–R06の表3／130／131を使う。

| edition | 対象年 | official landing page | 必要file |
|---|---:|---|---|
| R02 | 2020 | [令和2年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R02/R02hanzaitoukei.htm) | `R02_003.xlsx`, `R02_130.xlsx`, `R02_131.xlsx` |
| R03 | 2021 | [令和3年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R03/R03hanzaitoukei.htm) | `R03_003.xlsx`, `R03_130.xlsx`, `R03_131.xlsx` |
| R04 | 2022 | [令和4年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R04/R04hanzaitoukei.htm) | `R04_003.xlsx`, `R04_130.xlsx`, `R04_131.xlsx` |
| R05 | 2023 | [令和5年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R05/R05hanzaitoukei.htm) | `R05_003.xlsx`, `R05_130.xlsx`, `R05_131.xlsx` |
| R06 | 2024 | [令和6年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm) | 既存S15, S08, S09 |

R04概要表3-3-3のquarantineは、上記のR04詳細表130へ自動的には波及させない。詳細表そのものをparseし、前後年とのreconciliationを別途行って採否を決める。

### R07概要図表bundle

[警察庁 R07図表索引](https://www.npa.go.jp/toukei/seianki/R07/r07.zuhyosakuin.htm)から7fileを取得し、size、SHA-256、Excel/CSV formatを確認した。

| file | bytes | SHA-256 |
|---|---:|---|
| `r07.csv` | 284,760 | `ae2b334713722cb350fb2d6dfa73861d5ce74e66c463b3af5611d60fb56c6c7a` |
| `r07_1.xlsx` | 192,505 | `9d0f25831974f262711021879672646b2cb33418a8c2b03df4d810c2d6a40b07` |
| `r07_2-1.xlsx` | 121,778 | `9e9ba222542c1e6251e552c337c6cf6de196cbc9308090dad9402a71a6368459` |
| `r07_2-2.xlsx` | 103,672 | `3f7b330f796afae8d8da9e55a943e99b064e8bd0f2e2a7fa217ec4fadb892b63` |
| `r07_2-3.xlsx` | 174,633 | `04163a91782575c6edc8d29c7ebf8fcabd25be47529172d721f37852aa547ef8` |
| `r07_3.xlsx` | 81,435 | `853bf42f0467389afd4e4f532c09c3fb7bb1f7bf4a05a7dc9911f9b6b20d1b1b` |
| `r07_4.xlsx` | 91,794 | `d0eb0413ec5127a433b32bf7b8dc3548fb79d5c7a11293be44d88db6425d7515` |

`r07_1.xlsx`の1-5-1／1-5-3／1-5-4と、`r07_3.xlsx`の3-3-1／3-3-2／3-3-3／3-3-4には2016–2025年の10点がある。ただし3-3-3は、rolling 10年内に「検挙件数300件以上または検挙人員150人以上」の年がある国・地域を掲載する選択表である。全categoryの固定panelではないため、掲載されなくなった国籍を0として扱ってはならない。

### R02–R07概要表の重複値監査

R02–R07の15 edition pairについて、主要sheetの同じ年・同じlabelのcellを比較した。

- 全差分: 49 cell。
- 差分はすべてR04のsheet 3-3-3を含むpairに限定された。
- R06→R07: 3,582 / 3,582 cellが一致。
- R05→R07: 2,992 / 2,992 cellが一致。
- R04ではブラジル「うち来日」等に前後editionと一致しない値や配置上の異常がある。

したがってR04 3-3-3は、値の原因が公式訂正情報等で説明できるまでcanonical trend入力にしない。これは「R04の全資料が誤り」という判定ではなく、**当該sheet・当該cell群をquarantine（隔離）する判断**である。

### 2025年確定値と詳細年報の違い

[警察庁 令和7年1～12月犯罪統計](https://www.npa.go.jp/toukei/keiji35/new_hanzai07.htm)は数値を確定値と説明し、[e-Stat dataset](https://www.e-stat.go.jp/stat-search/files?layout=datalist&lid=000001476775&page=1)にExcel／CSV／PDFを掲載している。Excel linkの`statInfId=000040410682`は、現在登録済みS02と一致した。

一方、R06詳細年報と同じpath構造を仮定した`R07_003.xlsx`は2026-09-05にHTTP 404であり、表3・130・131・144のR07版landing pageも確認できなかった。よって「2025年の犯罪統計がない」のではなく、**確定値はあるが、現在使う詳細表と同じdimensionの一式をまだ確認できない**という状態である。

## 人口資料

### 総人口・日本人人口

総務省統計局の人口推計について、2016–2019年の初回年次版表2と、後から公表された2015–2020年表5（補間補正人口）を比較した。対象は全国＋47都道府県、総人口／日本人人口の384 cellである。

- 完全一致: 53 cell。
- 差分あり: 331 cell。
- 総人口のabsolute difference: median 3,000人、max 388,000人。
- 日本人人口のabsolute difference: median 2,000人、max 155,000人。
- 全国の補間補正版−初回版: 総人口は2016年+109,000、2017年+213,000、2018年+306,000、2019年+388,000。
- 全国の補間補正版−初回版: 日本人人口は2016年+51,000、2017年+97,000、2018年+131,000、2019年+155,000。

後発workbookは「補間補正人口」と明記し、日本人人口に総人口に対する比率で按分した国籍不詳を含む。時系列の変化と公表vintageの修正を混同しないため、2015–2020年は最新の補間補正版をcanonicalにし、初回年次版はrevision evidenceとして残す。

- 補間補正版file: `estat_000013168605.xlsx`
- SHA-256: `9e28da4c0ef8c2680577ad5ef0b0a78023d389113f66c85ab9e52bdbed89a1fc`
- 2021–2024年: 各年の人口推計表2を使用。
- 2024年公式page: [人口推計 2024年10月1日現在](https://www.stat.go.jp/data/jinsui/2024np/index.html)

### 在留外国人数

[e-Stat 在留外国人統計](https://www.e-stat.go.jp/stat-search/files?kikan=00250&layout=dataset&page=1&toukei=00250012&tstat=000001018034)から、2016–2025年末の表1候補fileを取得し、Excelとして開けることとhashを確認した。

| 年末 | SHA-256 |
|---:|---|
| 2016 | `9c22453746ec6cc1e696db9e5b338e5c76b422aac23a1e9678a3f8a7ee872481` |
| 2017 | `ab1773d57f0dafc9f8e77273ac3bfa317a28b0081f09cb8ea9e051de63c0f0c2` |
| 2018 | `247a2ae232ec04d1360920148aa8d0d01c7c1d802b11b3c050c854919c4c4185` |
| 2019 | `b4c9774ee641ad02ba96c5117b254ded4e16bb4ad19b844148015c2f31883792` |
| 2020 | `b798ad3f892d4da60fd0925ced185eab30b134aab5f5cbb238b04afba52c91a1` |
| 2021 | `2a2253ef440d0444d1f901cadb7798fb334b44994745c9fcf2a282cdd01fc619` |
| 2022 | `2acb2d84748d533ffc8b5bf37f99667ac06c924b9a0fdb2da82c38a970817e25` |
| 2023 | `16f703a47b83448902c332b4a268dc4ade95acf0ec45facecb306d2abf8efcab` |
| 2024 | `d400d8e2b46d2e6384eb6787ad04568e8bfe2b7a5e89f2d2191d5d079c4f4306` |
| 2025 | `cef9a02be7b4c289017e763579fdab4e347e9830aebaeee73be91743ef00d62c` |

2016–2021年は視覚的に組まれたwide workbook、2022–2025年はflatなmachine-readable workbookで、parser layoutに明確なbreakがある。2024・2025年のflat表については、current normalized detailから再集計した国・地域別総数とofficial flat表を照合した。

- 2024年: official／currentとも3,768,977人。`朝鮮`と`（朝鮮）`の明示alias、および無国籍rowを扱うと196 labelすべて一致、差分0。
- 2025年: official／currentとも4,125,395人。197 labelすべて一致、差分0。

これはflat表の数値semanticsがcurrent S14系処理と一致することを示す。2016–2021年用parserは別fixture・別quality profileで実装する。

### 2025年国勢調査

[令和7年国勢調査 結果page](https://www.stat.go.jp/data/kokusei/2025/kekka.html)で、2025-10-01時点の人口速報集計が2026-05-29に公表されていることを確認した。取得した速報表1のSHA-256は`d37d9ce6457f9e9a63019390de32fc2924dd84b4eab642f1af9808eec919a4a1`である。

速報表1は総人口・世帯数で、日本人人口を含まない。国籍を含む人口等基本集計の公表予定は2026-09-29である。このため、それまでは2025年日本人参考比率を直近年人口で代用せず、算出不能として表示する。

## 採用するseries policy

1. sourceに含まれる各年をそのまま抽出し、yearごとのraw valueを保持する。
2. 初回のprimary seriesは、全国合計と人口についてはR06詳細表から得られる2015–2024年、地域別・国籍別内訳についてはR02–R06から得られる2020–2024年とする。
3. 2015–2020年の総人口・日本人人口は、後発のofficial補間補正版をcanonicalにする。元の年次版を消さず、vintage比較用に保持する。
4. R07概要表は、詳細表のreplacementではなく、選択条件付きの別seriesとして登録する。
5. category／law／label／layoutが変わる境界には`definition_segment_id`を付け、異なるsegmentを折れ線で直結しない。
6. 掲載対象から外れたcategory、未公表値、非互換値を0へ変換しない。
7. 日本人値を全住民−全外国人で作る場合は、毎年`derived_residual`、両source ID、式、差異flagを表示する。
8. numeratorはannual flow、populationは特定日stockであることを全ratioに常設する。
9. temporary調査downloadを直接`data/raw/`へcopyしない。採用後に`config/sources.json`へeditionとpinned hashを登録し、`nca-acquire`でimmutable rawへ取得する。

## 実装TODO（順番）

1. **R02–R05詳細表を取得前監査**: 表3／130／131のhash、sheet、最新年、row count、主要anchorを確認する。
2. **historical editionをregistryへ追加**: 各editionを既存seriesへ追加し、`nca-acquire`でimmutable rawへ取得する。
3. **既存parserの互換testを追加**: 各editionがその年の地域別／国籍別内訳を出すことをRED→GREENで確認する。全国合計の10年抽出は別API／record kindとして実装し、current detail rowを壊さない。
4. **在留外国人数2020–2024を登録・取得**: 2020–2021 wide layoutと2022–2024 flat layoutを別profileで処理する。5点版完了後に2016–2019へ拡張する。
5. **総人口・日本人人口2015–2024を登録・取得**: 2015–2020補間補正版＋2021–2024年次版をyear-normalizedにする。
6. **multi-year contractを導入**: yearごとのnumerator／denominator pinとdefinition segmentを固定する。
7. **時系列data productを生成**: raw count、population、参考比率、warning、refusal、source／definitionを同じrowへ出す。
8. **volatility表示を追加**: 母数・分子が小さい年、前年差、複数年の再現性を判断材料として表示する。ただし価値判断はしない。
9. **frontendへyear／trend表示を追加**: まずtableとline chart、次に犯罪種類構成の年変化を追加する。
10. **2025年を別途review**: R07詳細年報と2025年国勢調査の人口等基本集計が確認できた後、同じ定義で接続できる範囲だけ追加する。

## 今回はcanonical rawへ入れないもの

- R02–R06の概要bundle: edition重複値とschema driftの監査資料として保持する。地域別・国籍別内訳のproduction inputには、概要表ではなく各年の詳細表3／130／131を使う。
- R04 sheet 3-3-3: 前後editionと整合しないcellを含むためquarantine。
- R07概要bundle: source登録・definition review前のcandidate。
- 2025年国勢調査速報表1: 日本人人口分母を持たないため、日本人参考比率には使用しない。

## 調査分担について

LunaにはURL・file・sheet・year・hashのinventory、edition overlap、人口vintage差、現pipelineのmechanical gapを担当させた。source pairing、definition break、canonical vintage、2025年の接続可否は判断を伴うため、上記のとおり主agent側で決定した。Lunaの利用上限に達して停止した2件は、詳細年報の重複inventoryと人口の追加overlap確認であり、primary方針を決める必須証拠は主agent側で補完した。
